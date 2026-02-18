"""
Pydantic request models.
"""

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """Request model for chat queries."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language query from user",
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for multi-conversation support",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What is the failure rate for bill payments?",
                "conversation_id": "1234567890"
            }
        }
    }


class ClearRequest(BaseModel):
    """Request model for clearing a conversation."""
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID to clear. If not provided, clears all.",
    )
