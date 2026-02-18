"""
translator.py - Natural Language to SQL Translator for InsightX

Responsibility: Convert natural language queries into executable DuckDB SQL
using Llama 3.1 70B via Groq API. All SQL is schema-grounded and validated
before execution.
"""

import re
import os
from typing import Dict, Optional
from groq import Groq
from loguru import logger


class TranslationError(Exception):
    """Raised when NL-to-SQL translation fails."""
    pass


class SQLTranslator:
    """Convert natural language questions to executable DuckDB SQL."""

    # SQL keywords that must be rejected
    DANGEROUS_PATTERNS = re.compile(
        r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE|EXEC|EXECUTE)\b',
        re.IGNORECASE
    )

    def __init__(self, schema_description: str, api_key: Optional[str] = None):
        """
        Initialize the SQL translator with database schema context.

        Args:
            schema_description: Formatted schema string for LLM context.
            api_key: Groq API key. Falls back to GROQ_API_KEY env var.
        """
        self.schema_description = schema_description
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"

        self.system_prompt = self._build_system_prompt()
        logger.info(f"SQLTranslator initialized with model: {self.model}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with schema context and rules."""
        return f"""You are a SQL expert for a digital payments analytics system running on DuckDB.

DATABASE SCHEMA:
{self.schema_description}

CRITICAL RULES:
1. merchant_category is NULL for all P2P transactions - use IS NULL / IS NOT NULL checks appropriately.
2. receiver_age_group is NULL for all non-P2P transactions.
3. fraud_flag=1 means "flagged for manual review", NOT "confirmed fraud". Never use the word "fraud" to describe these records - use "flagged for review".
4. Always use explicit column names (never SELECT *).
5. For percentage calculations, cast numerator to FLOAT: CAST(... AS FLOAT) / COUNT(*) * 100.
6. For time-based queries, use hour_of_day (0-23), day_of_week (Monday-Sunday), is_weekend (0 or 1).
7. Prefer CTEs over subqueries for readability.
8. The table name is 'transactions'.
9. Transaction types are exactly: 'P2P', 'P2M', 'Bill Payment', 'Recharge' (case-sensitive).
10. Transaction statuses are exactly: 'SUCCESS', 'FAILED' (case-sensitive).
11. Device types: 'Android', 'iOS', 'Web'.
12. Network types: '3G', '4G', '5G', 'WiFi'.
13. Always add reasonable GROUP BY clauses for aggregations.
14. When asked about "failure rate", calculate as: CAST(SUM(CASE WHEN transaction_status='FAILED' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100
15. When asked about "success rate", calculate as: CAST(SUM(CASE WHEN transaction_status='SUCCESS' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100
16. Limit results to 10000 rows max unless explicitly asked otherwise.
17. For amount-related queries, use amount_inr directly (raw INR values).

OUTPUT FORMAT: Return ONLY the SQL query. No explanations, no markdown formatting, no code fences. Just pure SQL."""

    def translate(self, user_query: str) -> str:
        """
        Convert a natural language question to a DuckDB SQL query.

        Args:
            user_query: Natural language question about transaction data.

        Returns:
            Sanitized, validated SQL query string.

        Raises:
            TranslationError: If translation fails or produces invalid SQL.
        """
        logger.info(f"Translating query: {user_query[:100]}...")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.0,
                max_tokens=1024,
                top_p=1.0,
            )

            sql = response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise TranslationError(f"Failed to generate SQL: {e}")

        # Clean up LLM output
        sql = self._clean_sql(sql)

        # Validate the generated SQL
        if not self._validate_sql(sql):
            raise TranslationError(f"Generated SQL failed validation: {sql[:200]}")

        # Ensure LIMIT clause exists
        sql = self._ensure_limit(sql)

        logger.info(f"Generated SQL: {sql[:200]}...")
        return sql

    def _clean_sql(self, sql: str) -> str:
        """
        Clean LLM-generated SQL output by removing markdown fences and extra text.

        Args:
            sql: Raw LLM output.

        Returns:
            Cleaned SQL string.
        """
        # Remove markdown code fences
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)

        # Remove any leading/trailing explanation text
        # Find the first SELECT or WITH statement
        match = re.search(r'\b(SELECT|WITH)\b', sql, re.IGNORECASE)
        if match:
            sql = sql[match.start():]

        # Remove trailing semicolons (DuckDB handles both)
        sql = sql.rstrip(';').strip()

        return sql

    def _validate_sql(self, sql: str) -> bool:
        """
        Validate generated SQL for safety and correctness.

        Args:
            sql: SQL query to validate.

        Returns:
            True if SQL is safe and properly formed.
        """
        if not sql:
            logger.warning("Empty SQL generated")
            return False

        # Check for dangerous operations
        if self.DANGEROUS_PATTERNS.search(sql):
            logger.warning(f"Dangerous SQL detected: {sql[:100]}")
            return False

        # Must start with SELECT or WITH (CTE)
        sql_upper = sql.upper().strip()
        if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
            logger.warning(f"SQL does not start with SELECT/WITH: {sql[:50]}")
            return False

        # Basic structure check - must reference the transactions table
        if 'transactions' not in sql.lower():
            logger.warning(f"SQL does not reference 'transactions' table")
            return False

        return True

    def _ensure_limit(self, sql: str, max_rows: int = 10000) -> str:
        """
        Add LIMIT clause if not already present.

        Args:
            sql: SQL query string.
            max_rows: Maximum rows to return.

        Returns:
            SQL with LIMIT clause added if missing.
        """
        if 'LIMIT' not in sql.upper():
            sql = f"{sql}\nLIMIT {max_rows}"
        return sql

    def translate_with_retry(self, user_query: str, max_retries: int = 2) -> str:
        """
        Translate with automatic retry on failure.

        Args:
            user_query: Natural language question.
            max_retries: Maximum number of retry attempts.

        Returns:
            Validated SQL query string.

        Raises:
            TranslationError: If all retries fail.
        """
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return self.translate(user_query)
            except TranslationError as e:
                last_error = e
                logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying... ({attempt + 2}/{max_retries + 1})")

        raise TranslationError(
            f"Translation failed after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )
