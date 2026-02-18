"""
executor.py - SQL Execution Engine

Executes validated SQL queries against DuckDB and returns DataFrames.
Includes result caching and execution statistics.
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
        self.conn = db_connection
        self._last_execution_time_ms = 0.0
        self._last_rows_returned = 0
        self._query_cache: Dict[str, pd.DataFrame] = {}
        self._cache_max_size = 50
        logger.info("SQLExecutor initialized.")

    def execute(self, sql: str, use_cache: bool = True) -> pd.DataFrame:
        if use_cache and sql in self._query_cache:
            logger.debug("Returning cached result.")
            cached = self._query_cache[sql]
            self._last_rows_returned = len(cached)
            self._last_execution_time_ms = 0.0
            return cached.copy()

        logger.info(f"Executing SQL: {sql[:150]}...")
        start = time.perf_counter()

        try:
            result = self.conn.execute(sql)
            df = result.fetchdf()
        except duckdb.Error as e:
            self._last_execution_time_ms = (time.perf_counter() - start) * 1000
            raise QueryExecutionError(f"Query execution failed: {e}")
        except Exception as e:
            self._last_execution_time_ms = (time.perf_counter() - start) * 1000
            raise QueryExecutionError(f"Unexpected error: {e}")

        elapsed = (time.perf_counter() - start) * 1000
        self._last_execution_time_ms = elapsed
        self._last_rows_returned = len(df)
        logger.info(f"Query: {elapsed:.1f}ms, {len(df)} rows x {len(df.columns)} cols")

        if use_cache and len(self._query_cache) < self._cache_max_size:
            self._query_cache[sql] = df.copy()

        return df

    def get_execution_stats(self) -> Dict:
        return {
            'time_ms': round(self._last_execution_time_ms, 2),
            'rows_returned': self._last_rows_returned,
            'cache_size': len(self._query_cache),
        }

    def clear_cache(self):
        self._query_cache.clear()
        logger.info("Query cache cleared.")
