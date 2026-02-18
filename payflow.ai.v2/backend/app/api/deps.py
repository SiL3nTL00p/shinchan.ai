"""
Dependency injection for FastAPI routes.
"""

from functools import lru_cache
from app.services.engine import InsightXEngine
from app.core.config import settings


@lru_cache()
def get_engine() -> InsightXEngine:
    """
    Get or create InsightXEngine singleton.
    Cached so only one instance exists across all requests.
    """
    config = {
        'data_path': settings.DATA_PATH,
        'hypothesis_path': settings.HYPOTHESIS_PATH,
        'groq_api_key': settings.GROQ_API_KEY,
        'groq_model': settings.GROQ_MODEL,
    }
    return InsightXEngine(config)
