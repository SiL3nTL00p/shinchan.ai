"""
Chat API routes.
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.request import QueryRequest, ClearRequest
from app.models.response import QueryResponse
from app.services.engine import InsightXEngine
from app.api.deps import get_engine

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    engine: InsightXEngine = Depends(get_engine),
) -> QueryResponse:
    """
    Process a natural language query and return insights.
    Optionally scoped to a conversation_id for multi-conversation support.
    """
    try:
        result = engine.process_query(request.query)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}",
        )


@router.post("/clear")
async def clear_conversation(request: ClearRequest = ClearRequest()):
    """Clear conversation history. Optionally scoped to a conversation_id."""
    return {
        "message": "Conversation cleared",
        "conversation_id": request.conversation_id,
    }
