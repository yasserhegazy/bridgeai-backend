"""AI Memory Index repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.base_repository import BaseRepository
from app.models.ai_memory_index import AIMemoryIndex, SourceType


class AIMemoryIndexRepository(BaseRepository[AIMemoryIndex]):
    """Repository for AI memory index operations."""

    def __init__(self, db: Session):
        """
        Initialize AIMemoryIndexRepository.

        Args:
            db: Database session
        """
        super().__init__(AIMemoryIndex, db)

    def get_by_source(
        self, source_type: SourceType, source_id: int
    ) -> Optional[AIMemoryIndex]:
        """
        Get AI memory index by source type and ID.

        Args:
            source_type: Source type (e.g., SourceType.comment, SourceType.crs)
            source_id: Source entity ID

        Returns:
            AIMemoryIndex or None if not found
        """
        return (
            self.db.query(AIMemoryIndex)
            .filter(
                AIMemoryIndex.source_type == source_type,
                AIMemoryIndex.source_id == source_id,
            )
            .first()
        )

    def delete_by_source(self, source_type: SourceType, source_id: int) -> int:
        """
        Delete AI memory index by source type and ID.

        Args:
            source_type: Source type
            source_id: Source entity ID

        Returns:
            Number of deleted records
        """
        deleted_count = (
            self.db.query(AIMemoryIndex)
            .filter(
                AIMemoryIndex.source_type == source_type,
                AIMemoryIndex.source_id == source_id,
            )
            .delete()
        )
        return deleted_count
