"""
data_manager.py - DuckDB Data Manager for InsightX

Responsibility: Manage the in-memory DuckDB instance and ensure data integrity.
Handles CSV loading, schema management, indexing, and query validation.
"""

import duckdb
import os
from typing import Dict
from loguru import logger


class DataManager:
    """Manage the in-memory DuckDB instance and ensure data integrity."""

    SCHEMA = {
        'transaction_id': 'VARCHAR',
        'timestamp': 'TIMESTAMP',
        'transaction_type': 'VARCHAR',
        'merchant_category': 'VARCHAR',
        'amount_inr': 'DECIMAL',
        'transaction_status': 'VARCHAR',
        'sender_age_group': 'VARCHAR',
        'receiver_age_group': 'VARCHAR',
        'sender_state': 'VARCHAR',
        'sender_bank': 'VARCHAR',
        'receiver_bank': 'VARCHAR',
        'device_type': 'VARCHAR',
        'network_type': 'VARCHAR',
        'fraud_flag': 'INTEGER',
        'hour_of_day': 'INTEGER',
        'day_of_week': 'VARCHAR',
        'is_weekend': 'INTEGER',
    }

    # Critical label mapping to prevent LLM misinterpretation
    FRAUD_FLAG_LABELS = {
        0: "Not flagged for review",
        1: "Flagged for manual review (NOT confirmed fraud)",
    }

    # SQL keywords that are NOT allowed (read-only system)
    DANGEROUS_KEYWORDS = {'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE', 'REPLACE'}

    def __init__(self, csv_path: str):
        """
        Initialize DuckDB and load data from CSV.

        Args:
            csv_path: Path to the transactions CSV file.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Dataset not found: {csv_path}")

        self.csv_path = csv_path
        self.conn = duckdb.connect(database=':memory:')

        # Set memory limit for safety
        self.conn.execute("SET memory_limit='512MB'")

        self._load_data()
        self._create_indexes()
        self._validate_schema()

        row_count = self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        logger.info(f"DataManager initialized: {row_count:,} rows loaded from {csv_path}")

    def _load_data(self):
        """Load CSV into DuckDB as the 'transactions' table."""
        logger.info(f"Loading data from {self.csv_path}...")
        self.conn.execute(f"""
            CREATE TABLE transactions AS 
            SELECT * FROM read_csv_auto('{self.csv_path}', 
                header=true, 
                sample_size=10000
            )
        """)
        logger.info("Data loaded into DuckDB successfully.")

    def _create_indexes(self):
        """Create indexes for high-speed querying on frequently filtered columns."""
        index_columns = ['transaction_status', 'transaction_type', 'fraud_flag']
        for col in index_columns:
            try:
                self.conn.execute(f"CREATE INDEX idx_{col} ON transactions({col})")
                logger.debug(f"Index created on {col}")
            except Exception as e:
                # DuckDB may not support all index types; log and continue
                logger.warning(f"Could not create index on {col}: {e}")

    def _validate_schema(self):
        """Validate that loaded data matches expected schema columns."""
        result = self.conn.execute("PRAGMA table_info('transactions')").fetchall()
        loaded_columns = {row[1].lower() for row in result}
        expected_columns = {col.lower() for col in self.SCHEMA.keys()}

        missing = expected_columns - loaded_columns
        if missing:
            logger.warning(f"Missing columns in dataset: {missing}")
        
        extra = loaded_columns - expected_columns
        if extra:
            logger.info(f"Extra columns in dataset (will be available): {extra}")

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Return the DuckDB connection object."""
        return self.conn

    def get_schema(self) -> Dict[str, str]:
        """
        Return schema dictionary for LLM context injection.

        Returns:
            Dict mapping column names to their SQL types with annotations.
        """
        schema_with_notes = {}
        notes = {
            'transaction_id': 'VARCHAR -- Unique transaction identifier',
            'timestamp': 'TIMESTAMP -- Transaction datetime',
            'transaction_type': "VARCHAR -- One of: 'P2P', 'P2M', 'Bill Payment', 'Recharge'",
            'merchant_category': "VARCHAR -- NULL for P2P transactions (structural, not error)",
            'amount_inr': 'DECIMAL -- Transaction amount in INR (raw values, not normalized)',
            'transaction_status': "VARCHAR -- 'SUCCESS' or 'FAILED'",
            'sender_age_group': "VARCHAR -- Age group of sender (e.g., '18-25', '26-35', '36-45', '46-55', '56+')",
            'receiver_age_group': "VARCHAR -- Age group of receiver; NULL for non-P2P transactions",
            'sender_state': 'VARCHAR -- Indian state of the sender',
            'sender_bank': 'VARCHAR -- Bank name of the sender',
            'receiver_bank': 'VARCHAR -- Bank name of the receiver',
            'device_type': "VARCHAR -- 'Android', 'iOS', or 'Web'",
            'network_type': "VARCHAR -- '3G', '4G', '5G', or 'WiFi'",
            'fraud_flag': "INTEGER -- 0 = Not flagged; 1 = Flagged for MANUAL REVIEW (NOT confirmed fraud)",
            'hour_of_day': 'INTEGER -- 0 to 23',
            'day_of_week': "VARCHAR -- e.g., 'Monday', 'Tuesday', etc.",
            'is_weekend': 'INTEGER -- 0 = Weekday, 1 = Weekend',
        }
        return notes

    def get_schema_description(self) -> str:
        """
        Return a formatted schema description string for LLM prompts.

        Returns:
            Multi-line string describing the table schema.
        """
        schema = self.get_schema()
        lines = ["Table: transactions", "Columns:"]
        for col, desc in schema.items():
            lines.append(f"  - {col}: {desc}")
        
        lines.append("")
        lines.append("IMPORTANT NULL PATTERNS:")
        lines.append("  - merchant_category IS NULL for all P2P transactions (this is intentional)")
        lines.append("  - receiver_age_group IS NULL for all non-P2P transactions (this is intentional)")
        lines.append("")
        lines.append("FRAUD FLAG WARNING:")
        lines.append("  - fraud_flag=1 means 'flagged for manual review', NOT 'confirmed fraud'")
        lines.append("  - Never state that a transaction IS fraud; only that it was flagged for review")

        return "\n".join(lines)

    def validate_query(self, sql: str) -> bool:
        """
        Security check: prevent destructive SQL operations.

        Args:
            sql: SQL query string to validate.

        Returns:
            True if query is safe (read-only), False otherwise.
        """
        sql_upper = sql.upper().strip()

        # Check for dangerous keywords at statement boundaries
        for keyword in self.DANGEROUS_KEYWORDS:
            # Check if keyword appears as a standalone word
            if keyword in sql_upper.split():
                logger.warning(f"Rejected SQL: contains dangerous keyword '{keyword}'")
                return False

        # Must be a SELECT statement
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            logger.warning(f"Rejected SQL: not a SELECT/WITH statement")
            return False

        return True

    def get_sample_values(self, column: str, limit: int = 10) -> list:
        """
        Get sample distinct values for a column (useful for LLM context).

        Args:
            column: Column name to sample.
            limit: Max number of distinct values.

        Returns:
            List of distinct values.
        """
        try:
            result = self.conn.execute(
                f"SELECT DISTINCT {column} FROM transactions WHERE {column} IS NOT NULL LIMIT {limit}"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error sampling {column}: {e}")
            return []

    def get_table_stats(self) -> Dict:
        """
        Get basic table statistics for diagnostics.

        Returns:
            Dict with row count and column count.
        """
        row_count = self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        col_info = self.conn.execute("PRAGMA table_info('transactions')").fetchall()
        return {
            'row_count': row_count,
            'column_count': len(col_info),
            'columns': [row[1] for row in col_info],
        }

    def close(self):
        """Close the DuckDB connection."""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed.")
