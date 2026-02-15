"""
Configuration settings for Shinchan AI backend.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    PROJECT_NAME: str = "Shinchan AI"
    API_V1_PREFIX: str = "/api"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Data Paths
    DATA_PATH: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../../data/250k_transactions.csv"
    )
    HYPOTHESIS_PATH: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "../../data/hypotheses.json"
    )

    # Groq API
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Database
    DUCKDB_MEMORY_LIMIT: str = "1GB"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
