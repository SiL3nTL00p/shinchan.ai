"""
data_manager.py - DuckDB Data Manager

Manages the in-memory DuckDB instance: CSV loading, schema management,
indexing, and query validation.
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

    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
        'TRUNCATE', 'CREATE', 'REPLACE',
    }

    def __init__(self, csv_path: str):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Dataset not found: {csv_path}")

        self.csv_path = csv_path
        self.conn = duckdb.connect(database=':memory:')
        self.conn.execute("SET memory_limit='512MB'")

        self._load_data()
        self._create_indexes()
        self._validate_schema()

        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]
        logger.info(f"DataManager initialized: {row_count:,} rows loaded")

    # Column name mappings: CSV header -> expected internal name
    COLUMN_RENAMES = {
        'transaction id': 'transaction_id',
        'transaction type': 'transaction_type',
        'amount (INR)': 'amount_inr',
    }

    def _load_data(self):
        logger.info(f"Loading data from {self.csv_path}...")
        self.conn.execute(f"""
            CREATE TABLE transactions AS
            SELECT * FROM read_csv_auto('{self.csv_path}',
                header=true,
                sample_size=10000
            )
        """)

        # Rename columns that don't match expected schema
        col_info = self.conn.execute(
            "PRAGMA table_info('transactions')"
        ).fetchall()
        loaded_cols = {row[1] for row in col_info}

        for csv_name, expected_name in self.COLUMN_RENAMES.items():
            if csv_name in loaded_cols and expected_name not in loaded_cols:
                self.conn.execute(
                    f'ALTER TABLE transactions RENAME COLUMN "{csv_name}" TO {expected_name}'
                )
                logger.info(f"Renamed column '{csv_name}' -> '{expected_name}'")

        logger.info("Data loaded into DuckDB.")

    def _create_indexes(self):
        for col in ['transaction_status', 'transaction_type', 'fraud_flag']:
            try:
                self.conn.execute(
                    f"CREATE INDEX idx_{col} ON transactions({col})"
                )
            except Exception as e:
                logger.warning(f"Could not create index on {col}: {e}")

    def _validate_schema(self):
        result = self.conn.execute(
            "PRAGMA table_info('transactions')"
        ).fetchall()
        loaded = {row[1].lower() for row in result}
        expected = {col.lower() for col in self.SCHEMA}
        missing = expected - loaded
        if missing:
            logger.warning(f"Missing columns: {missing}")

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    def get_schema(self) -> Dict[str, str]:
        return {
            'transaction_id': 'VARCHAR -- Unique transaction identifier',
            'timestamp': 'TIMESTAMP -- Transaction datetime',
            'transaction_type': "VARCHAR -- One of: 'P2P', 'P2M', 'Bill Payment', 'Recharge'",
            'merchant_category': "VARCHAR -- NULL for P2P transactions (structural)",
            'amount_inr': 'DECIMAL -- Transaction amount in INR',
            'transaction_status': "VARCHAR -- 'SUCCESS' or 'FAILED'",
            'sender_age_group': "VARCHAR -- '18-25', '26-35', '36-45', '46-55', '56+'",
            'receiver_age_group': "VARCHAR -- NULL for non-P2P transactions",
            'sender_state': 'VARCHAR -- Indian state of the sender',
            'sender_bank': 'VARCHAR -- Bank name of the sender',
            'receiver_bank': 'VARCHAR -- Bank name of the receiver',
            'device_type': "VARCHAR -- 'Android', 'iOS', or 'Web'",
            'network_type': "VARCHAR -- '3G', '4G', '5G', or 'WiFi'",
            'fraud_flag': "INTEGER -- 0=Not flagged; 1=Flagged for MANUAL REVIEW (NOT confirmed fraud)",
            'hour_of_day': 'INTEGER -- 0 to 23',
            'day_of_week': "VARCHAR -- e.g., 'Monday', 'Tuesday', etc.",
            'is_weekend': 'INTEGER -- 0=Weekday, 1=Weekend',
        }

    def get_schema_description(self) -> str:
        schema = self.get_schema()
        lines = ["Table: transactions", "Columns:"]
        for col, desc in schema.items():
            lines.append(f"  - {col}: {desc}")
        lines.append("")
        lines.append("IMPORTANT NULL PATTERNS:")
        lines.append("  - merchant_category IS NULL for all P2P transactions (intentional)")
        lines.append("  - receiver_age_group IS NULL for all non-P2P transactions (intentional)")
        lines.append("")
        lines.append("FRAUD FLAG WARNING:")
        lines.append("  - fraud_flag=1 means 'flagged for manual review', NOT 'confirmed fraud'")
        return "\n".join(lines)

    def validate_query(self, sql: str) -> bool:
        sql_upper = sql.upper().strip()
        for kw in self.DANGEROUS_KEYWORDS:
            if kw in sql_upper.split():
                logger.warning(f"Rejected SQL: contains '{kw}'")
                return False
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            logger.warning("Rejected SQL: not a SELECT/WITH statement")
            return False
        return True

    def get_table_stats(self) -> Dict:
        row_count = self.conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]
        col_info = self.conn.execute(
            "PRAGMA table_info('transactions')"
        ).fetchall()
        return {
            'row_count': row_count,
            'column_count': len(col_info),
            'columns': [row[1] for row in col_info],
        }

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed.")
