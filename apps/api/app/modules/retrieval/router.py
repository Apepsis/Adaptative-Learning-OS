from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.factory import get_embedding_provider
from app.core.security import get_current_user
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.retrieval import service
from app.modules.retrieval.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/v1/search", tags=["retrieval"])


@router.post("", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    session: AsyncSession = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    results = await service.hybrid_search(
        session,
        embedding_provider,
        user_id=current_user.id,
        query=payload.query,
        subject_id=payload.subject_id,
        source_ids=payload.source_ids,
        top_k=payload.top_k,
    )
    return SearchResponse(query=payload.query, results=results, not_found=len(results) == 0)
