"""
engine.py - Shinchan AI Orchestrator

Coordinates the full pipeline: NL → SQL → Execution → Analysis → Insight.
Contains zero business logic.
"""

import time
from typing import Dict, List, Any, Optional
from loguru import logger

from app.services.data_manager import DataManager
from app.services.translator import SQLTranslator, TranslationError
from app.services.executor import SQLExecutor, QueryExecutionError
from app.services.analytics import InsightEngine, InsightGenerationError


class InsightXEngine:
    """Main orchestrator for the Shinchan AI system."""

    def __init__(self, config: Dict[str, Any]):
        logger.info("Initializing Shinchan AI Engine...")
        self.data_manager = DataManager(config['data_path'])
        self.translator = SQLTranslator(
            schema_description=self.data_manager.get_schema_description(),
            api_key=config.get('groq_api_key'),
            model=config.get('groq_model', 'llama-3.3-70b-versatile'),
        )
        self.executor = SQLExecutor(self.data_manager.get_connection())
        self.analytics = InsightEngine(
            hypothesis_library_path=config['hypothesis_path'],
            api_key=config.get('groq_api_key'),
            model=config.get('groq_model', 'llama-3.3-70b-versatile'),
        )
        self._history: List[Dict] = []
        self._max_history = 20
        logger.info("Shinchan AI Engine initialized.")

    def process_query(self, user_query: str) -> Dict[str, Any]:
        start = time.perf_counter()
        result: Dict[str, Any] = {
            'query': user_query,
            'sql': None,
            'data': [],
            'data_summary': '',
            'signals': [],
            'hypotheses': [],
            'insight': '',
            'execution_time_ms': 0,
            'rows_returned': 0,
            'error': None,
        }

        # Step 1: Translate NL → SQL
        try:
            sql = self.translator.translate_with_retry(user_query)
            result['sql'] = sql
        except TranslationError as e:
            result['error'] = str(e)
            result['insight'] = (
                "I couldn't understand that query. Could you try rephrasing it? "
                "For example: 'What's the failure rate for bill payments?'"
            )
            result['execution_time_ms'] = self._elapsed(start)
            return result

        # Step 1.5: Validate
        if not self.data_manager.validate_query(sql):
            result['error'] = "SQL failed safety validation."
            result['insight'] = "The generated query was blocked by safety filters."
            result['execution_time_ms'] = self._elapsed(start)
            return result

        # Step 2: Execute SQL
        try:
            df = self.executor.execute(sql)
            result['data'] = df.to_dict('records')
            result['rows_returned'] = len(df)
        except QueryExecutionError as e:
            result['error'] = str(e)
            result['insight'] = "The data query encountered an error. Try breaking it into simpler parts."
            result['execution_time_ms'] = self._elapsed(start)
            return result

        # Step 3: Extract signals
        try:
            signals = self.analytics.extract_signals(df, user_query)
            result['signals'] = list(signals)
        except Exception:
            signals = set()

        # Step 4: Score hypotheses
        try:
            scored = self.analytics.score_hypotheses(signals)
            result['hypotheses'] = [
                {'id': h['id'], 'name': h['name'], 'description': h.get('description', ''), 'score': s}
                for h, s in scored[:5]
            ]
        except Exception:
            scored = []

        # Step 5: Generate insight
        try:
            insight = self.analytics.generate_insight(user_query, df, scored[:2])
            result['insight'] = insight
        except InsightGenerationError:
            result['insight'] = self.analytics.generate_fallback_insight(df)

        result['execution_time_ms'] = self._elapsed(start)
        self._history.append({'query': user_query, 'sql': sql})
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return result

    def get_system_stats(self) -> Dict[str, Any]:
        db_stats = self.data_manager.get_table_stats()
        exec_stats = self.executor.get_execution_stats()
        return {
            'database': db_stats,
            'executor': exec_stats,
            'history_length': len(self._history),
            'hypotheses_loaded': len(self.analytics.hypotheses),
        }

    def close(self):
        self.data_manager.close()

    @staticmethod
    def _elapsed(start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 2)
