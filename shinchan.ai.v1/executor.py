"""
executor.py - SQL Execution Engine for InsightX

Responsibility: Execute validated SQL queries against DuckDB and return
results as Pandas DataFrames. Tracks execution statistics.
"""

import time
import pandas as pd
import duckdb
from typing import Dict
from loguru import logger


class QueryExecutionError(Exception):
    """Raised when SQL execution fails."""
    pass


class SQLExecutor:
    """Execute SQL queries and return results as DataFrames."""

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        """
        Initialize with a DuckDB connection.

        Args:
            db_connection: Active DuckDB connection from DataManager.
        """
        self.conn = db_connection
        self._last_execution_time_ms = 0.0
        self._last_rows_returned = 0
        self._query_cache: Dict[str, pd.DataFrame] = {}
        self._cache_max_size = 50

        logger.info("SQLExecutor initialized.")

    def execute(self, sql: str, use_cache: bool = True) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a Pandas DataFrame.

        Args:
            sql: Valid SQL query string (must be pre-validated).
            use_cache: Whether to use cached results for repeated queries.

        Returns:
            Pandas DataFrame with query results.

        Raises:
            QueryExecutionError: If SQL execution fails.
        """
        # Check cache first
        if use_cache and sql in self._query_cache:
            logger.debug("Returning cached result.")
            cached = self._query_cache[sql]
            self._last_rows_returned = len(cached)
            self._last_execution_time_ms = 0.0
            return cached.copy()

        logger.info(f"Executing SQL: {sql[:150]}...")

        start_time = time.perf_counter()

        try:
            result = self.conn.execute(sql)
            df = result.fetchdf()
        except duckdb.Error as e:
            self._last_execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"DuckDB execution error: {e}")
            raise QueryExecutionError(f"Query execution failed: {e}")
        except Exception as e:
            self._last_execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Unexpected execution error: {e}")
            raise QueryExecutionError(f"Unexpected error during query execution: {e}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._last_execution_time_ms = elapsed_ms
        self._last_rows_returned = len(df)

        logger.info(
            f"Query completed in {elapsed_ms:.1f}ms, "
            f"returned {len(df)} rows x {len(df.columns)} columns."
        )

        # Cache the result
        if use_cache and len(self._query_cache) < self._cache_max_size:
            self._query_cache[sql] = df.copy()

        return df

    def get_execution_stats(self) -> Dict:
        """
        Return statistics from the last query execution.

        Returns:
            Dict with execution time and row count.
        """
        return {
            'time_ms': round(self._last_execution_time_ms, 2),
            'rows_returned': self._last_rows_returned,
            'cache_size': len(self._query_cache),
        }

    def clear_cache(self):
        """Clear the query result cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared.")

    def test_connection(self) -> bool:
        """
        Test that the database connection is alive.

        Returns:
            True if connection is working.
        """
        try:
            self.conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False
