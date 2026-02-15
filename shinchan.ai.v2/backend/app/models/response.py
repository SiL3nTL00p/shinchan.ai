"""
Pydantic response models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class HypothesisResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    score: float = Field(ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    query: str
    insight: str
    sql: Optional[str] = None
    execution_time_ms: float = 0
    rows_returned: int = 0
    data: List[Dict[str, Any]] = []
    signals: List[str] = []
    hypotheses: List[HypothesisResponse] = []
    error: Optional[str] = None


class DatabaseStats(BaseModel):
    row_count: int
    column_count: int
    columns: List[str] = []


class ExecutorStats(BaseModel):
    time_ms: float = 0
    rows_returned: int = 0
    cache_size: int = 0


class SystemStatsResponse(BaseModel):
    database: DatabaseStats
    hypotheses_loaded: int
    history_length: int
    executor: ExecutorStats
