import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.models import SourceBlock, SourcePage
from app.modules.ingestion.schemas import CanonicalDocument


class IngestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_pages_and_blocks(self, source_id: uuid.UUID, document: CanonicalDocument) -> None:
        """Delete-then-insert so re-ingestion (reprocess) is idempotent."""
        await self._session.execute(delete(SourceBlock).where(SourceBlock.source_id == source_id))
        await self._session.execute(delete(SourcePage).where(SourcePage.source_id == source_id))

        for page in document.pages:
            page_text = "\n".join(block.text for block in page.blocks)
            self._session.add(
                SourcePage(source_id=source_id, page_number=page.number, text=page_text)
            )
            for index, block in enumerate(page.blocks):
                self._session.add(
                    SourceBlock(
                        source_id=source_id,
                        page_number=page.number,
                        block_index=index,
                        type=block.type,
                        level=block.level,
                        text=block.text,
                    )
                )
        await self._session.flush()
