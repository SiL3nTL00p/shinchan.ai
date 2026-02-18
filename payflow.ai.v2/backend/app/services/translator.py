"""
translator.py - Natural Language to SQL Translator

Converts natural language queries into executable DuckDB SQL
using Llama 3.3 70B via Groq API.
"""

import re
import os
from typing import Optional
from groq import Groq
from loguru import logger


class TranslationError(Exception):
    """Raised when NL-to-SQL translation fails."""
    pass


class SQLTranslator:
    """Convert natural language questions to executable DuckDB SQL."""

    DANGEROUS_PATTERNS = re.compile(
        r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE|EXEC|EXECUTE)\b',
        re.IGNORECASE,
    )

    def __init__(
        self,
        schema_description: str,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
    ):
        self.schema_description = schema_description
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY or pass api_key."
            )
        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.system_prompt = self._build_system_prompt()
        logger.info(f"SQLTranslator initialized with model: {self.model}")

    def _build_system_prompt(self) -> str:
        return f"""You are a SQL expert for a digital payments analytics system running on DuckDB.

DATABASE SCHEMA:
{self.schema_description}

CRITICAL RULES:
1. merchant_category is NULL for all P2P transactions - use IS NULL / IS NOT NULL checks.
2. receiver_age_group is NULL for all non-P2P transactions.
3. fraud_flag=1 means "flagged for manual review", NOT "confirmed fraud".
4. Always use explicit column names (never SELECT *).
5. For percentage calculations, cast numerator to FLOAT.
6. For time-based queries, use hour_of_day (0-23), day_of_week, is_weekend.
7. Prefer CTEs over subqueries for readability.
8. Table name is 'transactions'.
9. Transaction types: 'P2P', 'P2M', 'Bill Payment', 'Recharge' (case-sensitive).
10. Transaction statuses: 'SUCCESS', 'FAILED' (case-sensitive).
11. Device types: 'Android', 'iOS', 'Web'.
12. Network types: '3G', '4G', '5G', 'WiFi'.
13. Always add reasonable GROUP BY clauses for aggregations.
14. failure rate = CAST(SUM(CASE WHEN transaction_status='FAILED' THEN 1 ELSE 0 END) AS FLOAT)/COUNT(*)*100
15. success rate = CAST(SUM(CASE WHEN transaction_status='SUCCESS' THEN 1 ELSE 0 END) AS FLOAT)/COUNT(*)*100
16. Limit results to 10000 rows max unless explicitly asked otherwise.
17. For amount queries, use amount_inr directly.

OUTPUT FORMAT: Return ONLY the SQL query. No explanations, no markdown, no code fences. Just pure SQL."""

    def translate(
        self,
        user_query: str,
        conversation_history: list | None = None,
    ) -> str:
        logger.info(f"Translating: {user_query[:100]}...")

        messages = [{"role": "system", "content": self.system_prompt}]

        # Inject conversation history for follow-up context
        if conversation_history:
            for turn in conversation_history[-50:]:  # last 50 turns (fits within 128K context)
                messages.append({"role": "user", "content": turn["user_query"]})
                messages.append(
                    {"role": "assistant", "content": turn["sql"]}
                )

        messages.append({"role": "user", "content": user_query})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=1024,
                top_p=1.0,
            )
            sql = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise TranslationError(f"Failed to generate SQL: {e}")

        sql = self._clean_sql(sql)
        if not self._validate_sql(sql):
            raise TranslationError(f"SQL failed validation: {sql[:200]}")
        sql = self._ensure_limit(sql)
        logger.info(f"Generated SQL: {sql[:200]}...")
        return sql

    def _clean_sql(self, sql: str) -> str:
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        match = re.search(r'\b(SELECT|WITH)\b', sql, re.IGNORECASE)
        if match:
            sql = sql[match.start():]
        return sql.rstrip(';').strip()

    def _validate_sql(self, sql: str) -> bool:
        if not sql:
            return False
        if self.DANGEROUS_PATTERNS.search(sql):
            return False
        upper = sql.upper().strip()
        if not (upper.startswith('SELECT') or upper.startswith('WITH')):
            return False
        if 'transactions' not in sql.lower():
            return False
        return True

    def _ensure_limit(self, sql: str, max_rows: int = 10000) -> str:
        if 'LIMIT' not in sql.upper():
            sql = f"{sql}\nLIMIT {max_rows}"
        return sql

    def translate_with_retry(
        self,
        user_query: str,
        max_retries: int = 2,
        conversation_history: list | None = None,
    ) -> str:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self.translate(user_query, conversation_history)
            except TranslationError as e:
                last_error = e
                logger.warning(
                    f"Translation attempt {attempt + 1} failed: {e}"
                )
        raise TranslationError(
            f"Translation failed after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )
