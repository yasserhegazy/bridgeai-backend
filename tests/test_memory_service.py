"""
Integration tests for AI memory service.
Tests memory creation, retrieval, search, and deletion with MySQL.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.ai.memory_service import (
    create_memory,
    delete_memory,
    get_project_memory_summary,
    retrieve_memory,
    search_project_memories,
)
from app.models.ai_memory_index import AIMemoryIndex


class TestCreateMemory:
    """Test memory creation."""

    @patch("app.ai.memory_service.store_embedding")
    def test_create_memory_success(self, mock_store, db: Session):
        """Test successful memory creation."""
        mock_store.return_value = None

        memory = create_memory(
            db=db,
            project_id=1,
            text="Test memory content",
            source_type="crs",
            source_id=100,
        )

        assert memory is not None
        assert memory.project_id == 1
        assert memory.source_id == 100
        assert memory.embedding_id is not None

    @patch("app.ai.memory_service.store_embedding")
    def test_create_memory_with_metadata(self, mock_store, db: Session):
        """Test memory creation with metadata."""
        mock_store.return_value = None

        memory = create_memory(
            db=db,
            project_id=1,
            text="Test content",
            source_type="message",
            source_id=200,
            metadata={"key": "value"},
        )

        assert memory is not None

    @patch("app.ai.memory_service.store_embedding")
    def test_create_memory_chroma_failure_rollback(self, mock_store, db: Session):
        """Test rollback when ChromaDB storage fails."""
        mock_store.side_effect = Exception("ChromaDB error")

        memory = create_memory(
            db=db, project_id=1, text="Test content", source_type="crs", source_id=100
        )

        assert memory is None
        # Verify no orphaned records
        count = db.query(AIMemoryIndex).count()
        assert count == 0


class TestRetrieveMemory:
    """Test memory retrieval."""

    @patch("app.ai.memory_service.store_embedding")
    def test_retrieve_existing_memory(self, mock_store, db: Session):
        """Test retrieving an existing memory."""
        mock_store.return_value = None

        memory = create_memory(
            db=db, project_id=1, text="Test content", source_type="crs", source_id=100
        )

        retrieved = retrieve_memory(db, memory.embedding_id)

        assert retrieved is not None
        assert retrieved["memory_id"] == memory.id
        assert retrieved["project_id"] == 1

    def test_retrieve_nonexistent_memory(self, db: Session):
        """Test retrieving non-existent memory returns None."""
        result = retrieve_memory(db, "nonexistent-id")
        assert result is None


class TestSearchMemories:
    """Test memory search."""

    @patch("app.ai.memory_service.search_embeddings")
    @patch("app.ai.memory_service.store_embedding")
    def test_search_project_memories(self, mock_store, mock_search, db: Session):
        """Test searching project memories."""
        mock_store.return_value = None

        memory = create_memory(
            db=db, project_id=1, text="Test content", source_type="crs", source_id=100
        )

        mock_search.return_value = [
            {
                "embedding_id": memory.embedding_id,
                "text": "Test content",
                "similarity_score": 0.9,
            }
        ]

        results = search_project_memories(db, project_id=1, query="test")

        assert len(results) == 1
        assert results[0]["memory_id"] == memory.id

    @patch("app.ai.memory_service.search_embeddings")
    def test_search_no_results(self, mock_search, db: Session):
        """Test search with no results."""
        mock_search.return_value = []

        results = search_project_memories(db, project_id=1, query="test")
        assert results == []


class TestDeleteMemory:
    """Test memory deletion."""

    @patch("app.ai.memory_service.delete_embedding")
    @patch("app.ai.memory_service.store_embedding")
    def test_delete_memory_success(self, mock_store, mock_delete, db: Session):
        """Test successful memory deletion."""
        mock_store.return_value = None
        mock_delete.return_value = None

        memory = create_memory(
            db=db, project_id=1, text="Test content", source_type="crs", source_id=100
        )

        result = delete_memory(db, memory.embedding_id)

        assert result is True
        assert db.query(AIMemoryIndex).filter_by(id=memory.id).first() is None


class TestMemorySummary:
    """Test memory summary statistics."""

    @patch("app.ai.memory_service.store_embedding")
    def test_get_project_summary(self, mock_store, db: Session):
        """Test getting project memory summary."""
        mock_store.return_value = None

        create_memory(db, 1, "Content 1", "crs", 100)
        create_memory(db, 1, "Content 2", "message", 200)

        summary = get_project_memory_summary(db, project_id=1)

        assert summary["total_memories"] == 2
        assert summary["by_source_type"]["crs"] == 1
        assert summary["by_source_type"]["message"] == 1

    def test_get_summary_empty_project(self, db: Session):
        """Test summary for project with no memories."""
        summary = get_project_memory_summary(db, project_id=999)

        assert summary["total_memories"] == 0
        assert summary["by_source_type"] == {}
