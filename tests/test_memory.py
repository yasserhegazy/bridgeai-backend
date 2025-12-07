"""
Tests for memory system (MySQL + ChromaDB integration)
"""
import pytest
from sqlalchemy.orm import Session
from app.ai.memory_service import (
    create_memory,
    retrieve_memory,
    search_project_memories,
    delete_memory,
    get_project_memory_summary
)
from app.db.session import SessionLocal


@pytest.fixture
def db():
    """Get database session"""
    db = SessionLocal()
    yield db
    db.close()


class TestMemoryService:
    """Test memory creation, retrieval, and search"""
    
    def test_create_memory(self, db: Session):
        """Test creating a memory"""
        memory = create_memory(
            db=db,
            project_id=1,
            text="This is a test memory about project requirements",
            source_type="crs",
            source_id=1,
            metadata={"priority": "high"}
        )
        
        assert memory is not None
        assert memory.project_id == 1
        assert memory.source_type.value == "crs"
        assert memory.source_id == 1
        assert memory.embedding_id is not None
    
    def test_retrieve_memory(self, db: Session):
        """Test retrieving a memory by ID"""
        # Create a memory first
        memory = create_memory(
            db=db,
            project_id=1,
            text="Test retrieval memory",
            source_type="message",
            source_id=2
        )
        
        # Retrieve it
        retrieved = retrieve_memory(db, memory.embedding_id)
        
        assert retrieved is not None
        assert retrieved["project_id"] == 1
        assert retrieved["embedding_id"] == memory.embedding_id
    
    def test_search_memories(self, db: Session):
        """Test semantic search on memories"""
        # Create multiple memories
        create_memory(
            db=db,
            project_id=1,
            text="The system should have user authentication",
            source_type="crs",
            source_id=1
        )
        
        create_memory(
            db=db,
            project_id=1,
            text="Payment processing needs to be secure",
            source_type="crs",
            source_id=2
        )
        
        # Search for authentication-related memories
        results = search_project_memories(
            db=db,
            project_id=1,
            query="user authentication system",
            limit=5
        )
        
        assert len(results) > 0
        assert results[0]["project_id"] == 1
        assert "similarity_score" in results[0]
    
    def test_delete_memory(self, db: Session):
        """Test deleting a memory"""
        # Create a memory
        memory = create_memory(
            db=db,
            project_id=1,
            text="Test deletion memory",
            source_type="comment",
            source_id=1
        )
        
        # Delete it
        success = delete_memory(db, memory.embedding_id)
        assert success is True
        
        # Verify it's deleted
        retrieved = retrieve_memory(db, memory.embedding_id)
        assert retrieved is None
    
    def test_memory_summary(self, db: Session):
        """Test getting memory summary for a project"""
        # Create multiple memories with different source types
        create_memory(
            db=db,
            project_id=1,
            text="CRS memory",
            source_type="crs",
            source_id=1
        )
        
        create_memory(
            db=db,
            project_id=1,
            text="Message memory",
            source_type="message",
            source_id=1
        )
        
        # Get summary
        summary = get_project_memory_summary(db, 1)
        
        assert summary["project_id"] == 1
        assert summary["total_memories"] >= 2
        assert "by_source_type" in summary
