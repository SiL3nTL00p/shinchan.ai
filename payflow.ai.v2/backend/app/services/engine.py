"""
engine.py - PayFlow AI Orchestrator

Coordinates the full pipeline: NL → SQL → Execution → Analysis → Insight.
Contains zero business logic.
"""

import os
import time
from typing import Dict, List, Any, Optional
from groq import Groq
from loguru import logger

from app.services.data_manager import DataManager
from app.services.translator import SQLTranslator, TranslationError
from app.services.executor import SQLExecutor, QueryExecutionError
from app.services.analytics import InsightEngine, InsightGenerationError
from app.services.router import QueryRouter


class InsightXEngine:
    """Main orchestrator for the PayFlow AI system."""

    def __init__(self, config: Dict[str, Any]):
        logger.info("Initializing PayFlow AI Engine...")
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
        self.router = QueryRouter(
            api_key=config.get('groq_api_key'),
            model=config.get('groq_model', 'llama-3.3-70b-versatile'),
        )
        self._groq_client = Groq(
            api_key=config.get('groq_api_key') or os.environ.get('GROQ_API_KEY')
        )
        self._groq_model = config.get('groq_model', 'llama-3.3-70b-versatile')
        self._conversations: Dict[str, List[Dict]] = {}  # per-conversation history
        self._general_conversations: Dict[str, List[Dict]] = {}  # general chat history
        self._max_history = 100
        logger.info("PayFlow AI Engine initialized.")

    def _get_history(self, conversation_id: Optional[str]) -> List[Dict]:
        if not conversation_id:
            return []
        return self._conversations.get(conversation_id, [])

    def _save_to_history(
        self, conversation_id: Optional[str], user_query: str, sql: str
    ):
        if not conversation_id:
            return
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append(
            {"user_query": user_query, "sql": sql}
        )
        # Trim old entries
        if len(self._conversations[conversation_id]) > self._max_history:
            self._conversations[conversation_id].pop(0)

    def _handle_general_query(
        self, user_query: str, conversation_id: Optional[str], start: float
    ) -> Dict[str, Any]:
        """Handle non-data queries with a direct LLM conversation."""
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

        # Build messages with general conversation history
        messages = [
            {
                "role": "system",
                "content": (
                    "You are PayFlow AI, a friendly and knowledgeable assistant "
                    "specialised in UPI digital payments analytics. You can analyse "
                    "UPI transaction data including volumes, success/failure rates, "
                    "fraud patterns, merchant categories, bank performance, and more.\n\n"
                    "When users greet you or ask general questions, respond warmly and "
                    "helpfully. If they ask what you can do, explain your data analysis "
                    "capabilities. Keep responses concise but friendly.\n\n"
                    "If the user seems to want data analysis but phrased it casually, "
                    "guide them toward asking a data question."
                    "give the response in tabular format only if the user quesry is explicitly asking for a table. Do not collapse rows onto a single line." 
                    "If the response contains tabular data, always format it as a markdown table using | column | syntax."
                ),
            }
        ]

        # Inject general conversation history
        if conversation_id:
            history = self._general_conversations.get(conversation_id, [])
            for turn in history[-50:]:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})

        messages.append({"role": "user", "content": user_query})

        try:
            response = self._groq_client.chat.completions.create(
                model=self._groq_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            insight = response.choices[0].message.content.strip()
            result['insight'] = insight

            # Save to general conversation history
            if conversation_id:
                if conversation_id not in self._general_conversations:
                    self._general_conversations[conversation_id] = []
                self._general_conversations[conversation_id].append(
                    {"user": user_query, "assistant": insight}
                )
                if len(self._general_conversations[conversation_id]) > self._max_history:
                    self._general_conversations[conversation_id].pop(0)

        except Exception as e:
            logger.error(f"General query LLM call failed: {e}")
            result['insight'] = (
                "Hey! I'm PayFlow AI, your UPI payments analytics assistant. "
                "I can help you explore transaction data — try asking something like "
                "'What's the failure rate by bank?' or 'Show top merchants by volume'."
            )

        result['execution_time_ms'] = self._elapsed(start)
        return result

    def process_query(
        self, user_query: str, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        # Step 0: Route the query (with conversation context awareness)
        has_data_history = bool(
            conversation_id
            and self._conversations.get(conversation_id)
        )
        query_type = self.router.classify(
            user_query, has_data_history=has_data_history
        )
        if query_type == "general":
            return self._handle_general_query(user_query, conversation_id, start)

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

        # Step 1: Translate NL → SQL (with conversation context)
        history = self._get_history(conversation_id)
        try:
            sql = self.translator.translate_with_retry(
                user_query, conversation_history=history
            )
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
        self._save_to_history(conversation_id, user_query, sql)

        return result

    def clear_conversation(self, conversation_id: Optional[str] = None):
        if conversation_id:
            self._conversations.pop(conversation_id, None)
            self._general_conversations.pop(conversation_id, None)
            logger.info(f"Cleared history for conversation {conversation_id}")
        else:
            self._conversations.clear()
            self._general_conversations.clear()
            logger.info("Cleared all conversation histories")

    def get_system_stats(self) -> Dict[str, Any]:
        db_stats = self.data_manager.get_table_stats()
        exec_stats = self.executor.get_execution_stats()
        total_history = sum(len(h) for h in self._conversations.values())
        return {
            'database': db_stats,
            'executor': exec_stats,
            'history_length': total_history,
            'active_conversations': len(self._conversations),
            'hypotheses_loaded': len(self.analytics.hypotheses),
        }

    def close(self):
        self.data_manager.close()

    @staticmethod
    def _elapsed(start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 2)
