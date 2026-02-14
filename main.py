"""
main.py - InsightX Orchestrator

Responsibility: Coordinate module hand-offs through the full pipeline.
Contains ZERO business logic, SQL queries, or UI code.

Pipeline: User Query → Translation → Execution → Analysis → Insight
"""

import time
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from loguru import logger

# Load .env file before any module that needs API keys
load_dotenv()

from data_manager import DataManager
from translator import SQLTranslator, TranslationError
from executor import SQLExecutor, QueryExecutionError
from analytics import InsightEngine, InsightGenerationError


class InsightXEngine:
    """
    Main orchestrator for the InsightX Conversational Analytics Engine.
    
    Coordinates the Text-to-SQL-to-Insight pipeline:
    1. Translate natural language to SQL
    2. Execute SQL against DuckDB
    3. Extract signals and score hypotheses
    4. Generate natural language insight
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize all pipeline modules.

        Args:
            config: Configuration dictionary with keys:
                - data_path: Path to CSV dataset
                - hypothesis_path: Path to hypotheses.json
                - groq_api_key: (optional) Groq API key
        """
        if config is None:
            config = self._default_config()

        logger.info("Initializing InsightX Engine...")

        # Initialize modules
        self.data_manager = DataManager(config['data_path'])
        self.translator = SQLTranslator(
            schema_description=self.data_manager.get_schema_description(),
            api_key=config.get('groq_api_key'),
        )
        self.executor = SQLExecutor(self.data_manager.get_connection())
        self.analytics = InsightEngine(
            hypothesis_library_path=config['hypothesis_path'],
            api_key=config.get('groq_api_key'),
        )

        # Conversation memory (last N queries)
        self._history: list = []
        self._max_history = 5

        logger.info("InsightX Engine initialized successfully.")

    @staticmethod
    def _default_config() -> Dict:
        """Return default configuration."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            'data_path': os.path.join(base_dir, '250k_transactions.csv'),
            'hypothesis_path': os.path.join(base_dir, 'hypotheses.json'),
        }

    def process_query(self, user_query: str) -> Dict:
        """
        Orchestrate the full InsightX pipeline.

        Args:
            user_query: Natural language question from the user.

        Returns:
            Dict with keys:
                - query: Original user query
                - sql: Generated SQL
                - data: List of dicts (DataFrame records)
                - data_summary: Text summary of results
                - signals: Detected signals
                - hypotheses: Scored hypotheses
                - insight: Natural language response
                - execution_time_ms: Total pipeline latency
                - error: Error message if any step failed (None on success)
        """
        start_time = time.perf_counter()

        result = {
            'query': user_query,
            'sql': None,
            'data': [],
            'data_summary': '',
            'signals': [],
            'hypotheses': [],
            'insight': '',
            'execution_time_ms': 0,
            'error': None,
        }

        # Step 1: Translate NL → SQL
        try:
            sql = self.translator.translate_with_retry(user_query)
            result['sql'] = sql
        except TranslationError as e:
            logger.error(f"Translation failed: {e}")
            result['error'] = str(e)
            result['insight'] = (
                "I couldn't understand that query. Could you try rephrasing it? "
                "For example: 'What's the failure rate for bill payments?' or "
                "'Compare success rates between Android and iOS users.'"
            )
            result['execution_time_ms'] = self._elapsed_ms(start_time)
            return result

        # Step 1.5: Validate SQL safety
        if not self.data_manager.validate_query(sql):
            logger.warning(f"SQL validation failed: {sql[:100]}")
            result['error'] = "Generated SQL failed safety validation."
            result['insight'] = (
                "The generated query was blocked by our safety filters. "
                "Please try a different question."
            )
            result['execution_time_ms'] = self._elapsed_ms(start_time)
            return result

        # Step 2: Execute SQL
        try:
            df = self.executor.execute(sql)
            result['data'] = df.to_dict('records')
            result['data_summary'] = self.analytics._summarize_dataframe(df)
        except QueryExecutionError as e:
            logger.error(f"Execution failed: {e}")
            result['error'] = str(e)
            result['insight'] = (
                "The data query encountered an error. This might be a complex question — "
                "try breaking it into simpler parts. For example, ask about one metric at a time."
            )
            result['execution_time_ms'] = self._elapsed_ms(start_time)
            return result

        # Step 3: Extract signals
        try:
            signals = self.analytics.extract_signals(df, user_query)
            result['signals'] = list(signals)
        except Exception as e:
            logger.warning(f"Signal extraction failed (non-critical): {e}")
            signals = set()

        # Step 4: Score hypotheses
        try:
            scored_hypotheses = self.analytics.score_hypotheses(signals)
            result['hypotheses'] = [
                {'id': h['id'], 'name': h['name'], 'score': s}
                for h, s in scored_hypotheses[:5]
            ]
        except Exception as e:
            logger.warning(f"Hypothesis scoring failed (non-critical): {e}")
            scored_hypotheses = []

        # Step 5: Generate insight
        try:
            insight = self.analytics.generate_insight(
                user_query, df, scored_hypotheses[:2]
            )
            result['insight'] = insight
        except InsightGenerationError as e:
            logger.error(f"Insight generation failed: {e}")
            # Fall back to raw data summary
            result['insight'] = self.analytics.generate_fallback_insight(df)
            result['error'] = f"Insight generation failed, showing data summary: {e}"

        # Record execution time
        result['execution_time_ms'] = self._elapsed_ms(start_time)

        # Add to conversation history
        self._add_to_history(user_query, result)

        logger.info(
            f"Query processed in {result['execution_time_ms']:.0f}ms "
            f"(SQL: {self.executor.get_execution_stats()['time_ms']:.0f}ms)"
        )

        return result

    def _elapsed_ms(self, start_time: float) -> float:
        """Calculate elapsed milliseconds since start_time."""
        return round((time.perf_counter() - start_time) * 1000, 2)

    def _add_to_history(self, query: str, result: Dict):
        """Add query and result summary to conversation history."""
        self._history.append({
            'query': query,
            'sql': result.get('sql'),
            'insight_preview': result.get('insight', '')[:100],
        })
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def get_history(self) -> list:
        """Return conversation history."""
        return self._history.copy()

    def get_system_stats(self) -> Dict:
        """Return system diagnostics."""
        db_stats = self.data_manager.get_table_stats()
        exec_stats = self.executor.get_execution_stats()
        return {
            'database': db_stats,
            'executor': exec_stats,
            'history_length': len(self._history),
            'hypotheses_loaded': len(self.analytics.hypotheses),
        }

    def close(self):
        """Clean up resources."""
        self.data_manager.close()
        logger.info("InsightX Engine shut down.")


def main():
    """CLI entry point for testing."""
    import sys

    engine = InsightXEngine()

    print("\n" + "=" * 60)
    print("  InsightX Conversational Analytics Engine")
    print("  Type 'quit' to exit, 'stats' for system info")
    print("=" * 60 + "\n")

    while True:
        try:
            query = input("\n💬 Ask a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query:
            continue
        if query.lower() in ('quit', 'exit', 'q'):
            break
        if query.lower() == 'stats':
            import json
            print(json.dumps(engine.get_system_stats(), indent=2))
            continue

        result = engine.process_query(query)

        print(f"\n📊 Insight ({result['execution_time_ms']:.0f}ms):")
        print("-" * 50)
        print(result['insight'])

        if result['sql']:
            print(f"\n🔍 SQL: {result['sql'][:200]}...")

        if result['signals']:
            print(f"\n📡 Signals: {', '.join(result['signals'])}")

        if result['hypotheses']:
            top = result['hypotheses'][0]
            print(f"🧠 Top Hypothesis: {top['name']} ({top['score']:.2f})")

    engine.close()
    print("\nGoodbye!")


if __name__ == '__main__':
    main()
