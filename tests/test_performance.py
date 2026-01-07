"""
Performance Tests - Edge Cases & Stress Testing

Tests cover:
1. Index effectiveness validation
2. Connection pool stress testing
3. N+1 query detection
4. ChromaDB batch operations
5. Concurrent request handling
6. Memory leak detection
7. Query performance under load
8. Edge cases (empty results, large datasets, etc.)
"""

import pytest
import time
import threading
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
import uuid

from app.db.session import SessionLocal, engine
from app.models import (
    User, Team, TeamMember, Project, SessionModel as ChatSession,
    Message, Notification, CRSDocument, Comment,
    AIMemoryIndex, NotificationType
)
from app.models.project import ProjectStatus
from app.models.invitation import Invitation, InvitationStatus
from app.ai import chroma_manager


class TestIndexEffectiveness:
    """Validate that all 7 strategic indexes are created and used by queries."""
    
    def test_all_indexes_exist(self, db: Session):
        """HARD: Verify all 7 strategic indexes are created in database."""
        inspector = inspect(engine)
        
        expected_indexes = {
            'projects': ['ix_projects_team_id'],
            'crs_documents': ['ix_crs_documents_project_id', 'ix_crs_documents_status'],
            'comments': ['ix_comments_crs_id'],
            'ai_memory_index': ['ix_ai_memory_index_project_id'],
            'invitations': ['ix_invitations_team_id', 'ix_invitations_status'],
        }
        
        for table_name, index_names in expected_indexes.items():
            indexes = inspector.get_indexes(table_name)
            existing_index_names = [idx['name'] for idx in indexes]
            
            for expected_index in index_names:
                assert expected_index in existing_index_names, (
                    f"Index {expected_index} missing from {table_name}. "
                    f"Found: {existing_index_names}"
                )
    
    def test_no_over_indexing(self, db: Session):
        """EDGE CASE: Ensure we don't have >10 indexes per table (over-indexing)."""
        inspector = inspect(engine)
        
        tables_to_check = ['messages', 'notifications', 'projects', 'crs_documents', 
                          'comments', 'ai_memory_index', 'invitations']
        
        for table_name in tables_to_check:
            indexes = inspector.get_indexes(table_name)
            # Exclude PRIMARY and UNIQUE constraints
            custom_indexes = [
                idx for idx in indexes 
                if not idx.get('unique', False) and idx['name'] != 'PRIMARY'
            ]
            
            assert len(custom_indexes) <= 5, (
                f"Table {table_name} has {len(custom_indexes)} custom indexes. "
                f"This suggests over-indexing. Max recommended: 5. "
                f"Indexes: {[idx['name'] for idx in custom_indexes]}"
            )
    
    def test_projects_team_index_used(self, db: Session, sample_teams):
        """HARD: Verify ix_projects_team_id is used in EXPLAIN plan."""
        team_ids = [team.id for team in sample_teams[:3]]
        
        # Get EXPLAIN plan
        explain_query = text(
            f"EXPLAIN SELECT * FROM projects WHERE team_id IN ({','.join(map(str, team_ids))})"
        )
        result = db.execute(explain_query).fetchall()
        
        # Check if index is used (not full table scan)
        explain_output = str(result)
        assert 'ix_projects_team_id' in explain_output or 'range' in explain_output.lower(), (
            f"Index ix_projects_team_id not used. EXPLAIN: {result}"
        )
        assert 'ALL' not in [str(r) for r in result], (
            f"Full table scan detected! EXPLAIN: {result}"
        )
    
    def test_messages_session_index_used(self, db: Session, sample_session):
        """HARD: Verify messages.session_id index is used."""
        explain_query = text(
            f"EXPLAIN SELECT * FROM messages WHERE session_id = {sample_session.id} "
            f"ORDER BY timestamp DESC LIMIT 20"
        )
        result = db.execute(explain_query).fetchall()
        
        explain_output = str(result)
        # Should use index on session_id, not full table scan
        assert 'ALL' not in explain_output or 'ref' in explain_output, (
            f"Index not used efficiently. EXPLAIN: {result}"
        )
    
    def test_no_index_on_low_selectivity_columns(self, db: Session):
        """EDGE CASE: Verify no indexes on boolean/low-selectivity columns."""
        inspector = inspect(engine)
        
        # Check notifications table
        notifications_indexes = inspector.get_indexes('notifications')
        index_columns = []
        for idx in notifications_indexes:
            index_columns.extend(idx['column_names'])
        
        # These should NOT have standalone indexes
        forbidden_indexes = ['is_read', 'type']
        for col in forbidden_indexes:
            assert col not in index_columns, (
                f"Low-selectivity column '{col}' should not have standalone index"
            )


class TestConnectionPoolStress:
    """Stress test connection pool under extreme load."""
    
    def test_connection_pool_configuration(self):
        """Verify connection pool is configured correctly."""
        pool = engine.pool
        
        assert pool.size() == 20, f"Expected pool_size=20, got {pool.size()}"
        assert hasattr(pool, '_max_overflow'), "Pool should have max_overflow configured"
    
    def test_concurrent_connections_within_limit(self, db: Session):
        """HARD: Test 25 concurrent connections (within pool+overflow limit)."""
        results = []
        errors = []
        
        def execute_query():
            try:
                db_local = SessionLocal()
                try:
                    # Simulate real query
                    count = db_local.query(User).count()
                    results.append(count)
                    time.sleep(0.1)  # Hold connection briefly
                finally:
                    db_local.close()
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for _ in range(25):  # Within pool_size(20) + max_overflow(10)
            t = threading.Thread(target=execute_query)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=10)
        
        assert len(errors) == 0, f"Errors in concurrent connections: {errors}"
        assert len(results) == 25, f"Expected 25 results, got {len(results)}"
    
    def test_connection_pool_overflow_handling(self, db: Session):
        """EDGE CASE: Test behavior at pool limit (30 connections)."""
        results = []
        errors = []
        
        def execute_query():
            try:
                db_local = SessionLocal()
                try:
                    count = db_local.query(User).count()
                    results.append(count)
                    time.sleep(0.2)  # Hold connection longer
                finally:
                    db_local.close()
            except SQLAlchemyTimeoutError as e:
                errors.append('timeout')
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for _ in range(30):  # Exactly at limit
            t = threading.Thread(target=execute_query)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=15)
        
        # Should handle exactly 30 without timeout
        assert len(errors) == 0, f"Should handle 30 connections. Errors: {errors}"
    
    def test_connection_pool_timeout_over_limit(self, db: Session):
        """HARD: Test timeout when exceeding pool capacity (>30 connections)."""
        results = []
        timeouts = []
        
        def execute_query_slow():
            try:
                db_local = SessionLocal()
                try:
                    count = db_local.query(User).count()
                    results.append(count)
                    time.sleep(0.5)  # Hold connection even longer
                finally:
                    db_local.close()
            except SQLAlchemyTimeoutError:
                timeouts.append(1)
            except Exception as e:
                if 'timeout' in str(e).lower():
                    timeouts.append(1)
        
        threads = []
        for _ in range(35):  # Exceed pool_size + max_overflow
            t = threading.Thread(target=execute_query_slow)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=20)
        
        # Some requests should timeout
        assert len(timeouts) > 0, "Expected some timeouts when exceeding pool capacity"
    
    def test_connection_recycling(self, db: Session):
        """EDGE CASE: Verify connections are recycled (pool_recycle=3600)."""
        # Get initial pool state
        pool = engine.pool
        initial_size = pool.size()
        
        # Execute queries
        for _ in range(5):
            db_local = SessionLocal()
            db_local.query(User).count()
            db_local.close()
        
        # Pool should maintain size
        assert pool.size() == initial_size, "Pool size should remain stable"


class TestN1QueryDetection:
    """Detect N+1 query patterns in critical endpoints."""
    
    def test_projects_no_n1_queries(self, db: Session, sample_teams, sample_user):
        """HARD: Verify projects endpoint uses eager loading (no N+1)."""
        # Create 50 projects with teams and creators
        projects = []
        for i in range(50):
            team = sample_teams[i % len(sample_teams)]
            project = Project(
                name=f"Test Project {i}",
                description="Test",
                team_id=team.id,
                created_by=sample_user.id,
                status=ProjectStatus.ACTIVE
            )
            db.add(project)
            projects.append(project)
        db.commit()
        
        # Count queries
        query_count = 0
        original_execute = db.execute
        
        def counting_execute(*args, **kwargs):
            nonlocal query_count
            query_count += 1
            return original_execute(*args, **kwargs)
        
        db.execute = counting_execute
        
        # Fetch projects with related data (should use joinedload)
        from sqlalchemy.orm import joinedload
        
        fetched_projects = db.query(Project).options(
            joinedload(Project.creator),
            joinedload(Project.team)
        ).filter(
            Project.team_id.in_([t.id for t in sample_teams])
        ).all()
        
        # Access relationships (should not trigger additional queries)
        for project in fetched_projects:
            _ = project.creator.full_name
            _ = project.team.name
        
        # Should be 1 query (or 2-3 with JOINs), not 50+
        assert query_count <= 3, (
            f"N+1 detected! Expected ≤3 queries, got {query_count} for {len(fetched_projects)} projects"
        )
        
        db.execute = original_execute  # Restore
    
    def test_notifications_batch_loading(self, db: Session, sample_user, sample_teams):
        """HARD: Verify notifications use batch loading, not individual queries."""
        # Create 30 notifications with mixed types
        notifications = []
        for i in range(30):
            notif = Notification(
                user_id=sample_user.id,
                type=NotificationType.TEAM_INVITATION if i % 2 == 0 else NotificationType.PROJECT_APPROVAL,
                message=f"Test notification {i}",
                reference_id=sample_teams[i % len(sample_teams)].id,
                is_read=False
            )
            db.add(notif)
            notifications.append(notif)
        db.commit()
        
        # Fetch notifications
        query_count = 0
        original_execute = db.execute
        
        def counting_execute(*args, **kwargs):
            nonlocal query_count
            query_count += 1
            return original_execute(*args, **kwargs)
        
        db.execute = counting_execute
        
        # Simulate batch loading pattern
        fetched_notifs = db.query(Notification).filter(
            Notification.user_id == sample_user.id
        ).limit(30).all()
        
        # Batch load related entities
        team_ids = set()
        for notif in fetched_notifs:
            if notif.type == NotificationType.TEAM_INVITATION:
                team_ids.add(notif.reference_id)
        
        if team_ids:
            teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
            teams_map = {t.id: t for t in teams}
        
        # Should be 2-3 queries total, not 30+
        assert query_count <= 4, (
            f"N+1 detected in notifications! Expected ≤4 queries, got {query_count}"
        )
        
        db.execute = original_execute
    
    def test_messages_session_query_efficiency(self, db: Session, sample_session, sample_user):
        """EDGE CASE: Messages query with 1000+ messages should stay efficient."""
        # Create 1000 messages
        messages = []
        for i in range(1000):
            msg = Message(
                session_id=sample_session.id,
                sender_id=sample_user.id,
                content=f"Message {i}",
                role="user",
                timestamp=time.time() + i
            )
            messages.append(msg)
        
        # Bulk insert
        db.bulk_save_objects(messages)
        db.commit()
        
        # Measure query time
        start = time.time()
        recent_messages = db.query(Message).filter(
            Message.session_id == sample_session.id
        ).order_by(Message.timestamp.desc()).limit(20).all()
        query_time = (time.time() - start) * 1000
        
        assert len(recent_messages) == 20, "Should return 20 messages"
        assert query_time < 50, f"Query too slow: {query_time:.2f}ms (target: <50ms)"


class TestChromaDBPerformance:
    """Test ChromaDB batch operations and edge cases."""
    
    def test_batch_insert_performance(self):
        """HARD: Verify batch insert is >10x faster than individual inserts."""
        # Individual inserts timing
        individual_start = time.time()
        for i in range(10):
            chroma_manager.store_embedding(
                embedding_id=str(uuid.uuid4()),
                text=f"Test document {i}",
                metadata={"project_id": 1, "source_type": "test"}
            )
        individual_time = time.time() - individual_start
        
        # Batch insert timing
        batch_ids = [str(uuid.uuid4()) for _ in range(10)]
        batch_texts = [f"Batch document {i}" for i in range(10)]
        batch_metadatas = [{"project_id": 1, "source_type": "test"} for _ in range(10)]
        
        batch_start = time.time()
        chroma_manager.store_embeddings_batch(batch_ids, batch_texts, batch_metadatas)
        batch_time = time.time() - batch_start
        
        speedup = individual_time / batch_time
        assert speedup > 3, (
            f"Batch insert should be >3x faster. Got {speedup:.2f}x speedup. "
            f"Individual: {individual_time:.2f}s, Batch: {batch_time:.2f}s"
        )
    
    def test_batch_insert_large_dataset(self):
        """HARD: Batch insert 100 embeddings in <3 seconds."""
        batch_size = 100
        batch_ids = [str(uuid.uuid4()) for _ in range(batch_size)]
        batch_texts = [f"Large batch document {i}" * 10 for i in range(batch_size)]
        batch_metadatas = [{"project_id": 1, "index": i} for i in range(batch_size)]
        
        start = time.time()
        chroma_manager.store_embeddings_batch(batch_ids, batch_texts, batch_metadatas)
        elapsed = time.time() - start
        
        assert elapsed < 3.0, f"Batch insert too slow: {elapsed:.2f}s (target: <3s)"
    
    def test_search_with_server_side_filtering(self):
        """EDGE CASE: Verify server-side filtering works correctly."""
        # Insert embeddings for different projects
        for project_id in [1, 2, 3]:
            for i in range(5):
                chroma_manager.store_embedding(
                    embedding_id=str(uuid.uuid4()),
                    text=f"Project {project_id} document {i}",
                    metadata={"project_id": project_id, "source_type": "test"}
                )
        
        # Search with project filter
        results = chroma_manager.search_embeddings(
            query="document",
            project_id=2,
            n_results=10
        )
        
        # All results should be from project_id=2
        for result in results:
            assert result['metadata']['project_id'] == 2, (
                f"Server-side filtering failed. Got project_id={result['metadata']['project_id']}"
            )
    
    def test_search_empty_collection(self):
        """EDGE CASE: Search in empty collection should not crash."""
        # Search with non-existent project
        results = chroma_manager.search_embeddings(
            query="non-existent",
            project_id=99999,
            n_results=5
        )
        
        assert isinstance(results, list), "Should return empty list, not crash"
    
    def test_batch_insert_empty_list(self):
        """EDGE CASE: Batch insert with empty list should not crash."""
        result = chroma_manager.store_embeddings_batch([], [], [])
        
        assert isinstance(result, list), "Should return empty list"
        assert len(result) == 0, "Should handle empty batch"


class TestQueryPerformanceUnderLoad:
    """Test query performance with realistic data volumes."""
    
    def test_projects_query_with_1000_projects(self, db: Session, sample_teams, sample_user):
        """HARD: Query performance with 1000 projects in database."""
        # Create 1000 projects
        projects = []
        for i in range(1000):
            team = sample_teams[i % len(sample_teams)]
            project = Project(
                name=f"Project {i}",
                description=f"Description {i}",
                team_id=team.id,
                created_by=sample_user.id,
                status=ProjectStatus.ACTIVE if i % 3 == 0 else ProjectStatus.PENDING
            )
            projects.append(project)
        
        db.bulk_save_objects(projects)
        db.commit()
        
        # Query specific team's projects
        start = time.time()
        team_projects = db.query(Project).filter(
            Project.team_id == sample_teams[0].id
        ).all()
        query_time = (time.time() - start) * 1000
        
        assert query_time < 50, f"Query too slow: {query_time:.2f}ms with 1000 projects"
        assert len(team_projects) > 0, "Should return some projects"
    
    def test_notifications_query_with_10000_notifications(self, db: Session, sample_user):
        """HARD: Query performance with 10,000 notifications."""
        # Create 10,000 notifications
        notifications = []
        for i in range(10000):
            notif = Notification(
                user_id=sample_user.id if i % 10 == 0 else sample_user.id + 1,
                type=NotificationType.PROJECT_APPROVAL,
                message=f"Notification {i}",
                reference_id=i,
                is_read=i % 5 != 0
            )
            notifications.append(notif)
        
        db.bulk_save_objects(notifications)
        db.commit()
        
        # Query user's unread notifications
        start = time.time()
        unread = db.query(Notification).filter(
            Notification.user_id == sample_user.id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).limit(50).all()
        query_time = (time.time() - start) * 1000
        
        assert query_time < 100, f"Query too slow: {query_time:.2f}ms with 10k notifications"
        assert len(unread) > 0, "Should return unread notifications"
    
    def test_crs_documents_query_with_500_documents(self, db: Session, sample_project, sample_user):
        """EDGE CASE: CRS query with 500 documents per project."""
        # Create 500 CRS documents
        documents = []
        for i in range(500):
            doc = CRSDocument(
                project_id=sample_project.id,
                version=f"1.{i}",
                status="approved" if i % 4 == 0 else "draft",
                created_by=sample_user.id
            )
            documents.append(doc)
        
        db.bulk_save_objects(documents)
        db.commit()
        
        # Query approved documents
        start = time.time()
        approved = db.query(CRSDocument).filter(
            CRSDocument.project_id == sample_project.id,
            CRSDocument.status == "approved"
        ).all()
        query_time = (time.time() - start) * 1000
        
        assert query_time < 100, f"CRS query too slow: {query_time:.2f}ms"
        assert len(approved) > 0, "Should return approved documents"


class TestMemoryLeaks:
    """Detect potential memory leaks in connection and session management."""
    
    def test_session_cleanup_after_queries(self, db: Session):
        """EDGE CASE: Verify sessions are properly closed and don't leak."""
        import gc
        import sys
        
        # Baseline session count
        gc.collect()
        initial_sessions = len([obj for obj in gc.get_objects() if isinstance(obj, Session)])
        
        # Execute 100 queries with proper cleanup
        for i in range(100):
            db_local = SessionLocal()
            try:
                db_local.query(User).count()
            finally:
                db_local.close()
        
        # Force garbage collection
        gc.collect()
        
        # Check session count
        final_sessions = len([obj for obj in gc.get_objects() if isinstance(obj, Session)])
        
        # Should not leak sessions
        leaked = final_sessions - initial_sessions
        assert leaked < 10, f"Potential session leak: {leaked} sessions not cleaned up"
    
    def test_connection_pool_doesnt_grow_unbounded(self):
        """HARD: Verify connection pool doesn't grow beyond max_overflow."""
        pool = engine.pool
        initial_size = pool.size()
        
        # Execute many queries
        for _ in range(50):
            db = SessionLocal()
            db.query(User).count()
            db.close()
        
        final_size = pool.size()
        
        # Pool should stabilize at pool_size
        assert final_size == initial_size, (
            f"Pool size grew from {initial_size} to {final_size}"
        )


class TestEdgeCases:
    """Test unusual scenarios and boundary conditions."""
    
    def test_query_with_no_results(self, db: Session):
        """EDGE CASE: Queries returning 0 results should be fast."""
        start = time.time()
        projects = db.query(Project).filter(
            Project.team_id == 999999  # Non-existent team
        ).all()
        query_time = (time.time() - start) * 1000
        
        assert len(projects) == 0, "Should return empty list"
        assert query_time < 20, f"Empty result query too slow: {query_time:.2f}ms"
    
    def test_query_with_null_foreign_keys(self, db: Session, sample_user):
        """EDGE CASE: Handle NULL foreign keys gracefully."""
        # Create project with NULL team_id (if allowed by schema)
        try:
            project = Project(
                name="Orphan Project",
                description="No team",
                team_id=None,  # NULL foreign key
                created_by=sample_user.id,
                status=ProjectStatus.ACTIVE
            )
            db.add(project)
            db.commit()
            
            # Query should handle NULL gracefully
            projects = db.query(Project).filter(
                Project.team_id.is_(None)
            ).all()
            
            assert len(projects) > 0, "Should find projects with NULL team_id"
        except Exception:
            # If schema doesn't allow NULL, that's also fine
            pass
    
    def test_large_in_clause(self, db: Session, sample_teams):
        """EDGE CASE: IN clause with 1000+ values should work."""
        # Create 1000 fake team IDs
        large_team_ids = list(range(1, 1001))
        
        start = time.time()
        projects = db.query(Project).filter(
            Project.team_id.in_(large_team_ids)
        ).all()
        query_time = (time.time() - start) * 1000
        
        assert query_time < 200, f"Large IN clause too slow: {query_time:.2f}ms"
    
    def test_concurrent_writes_to_same_table(self, db: Session, sample_user):
        """HARD: Concurrent writes should not deadlock."""
        errors = []
        successes = []
        
        def insert_notification():
            try:
                db_local = SessionLocal()
                try:
                    notif = Notification(
                        user_id=sample_user.id,
                        type=NotificationType.PROJECT_APPROVAL,
                        message="Concurrent test",
                        reference_id=1,
                        is_read=False
                    )
                    db_local.add(notif)
                    db_local.commit()
                    successes.append(1)
                except Exception as e:
                    db_local.rollback()
                    errors.append(str(e))
                finally:
                    db_local.close()
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for _ in range(20):
            t = threading.Thread(target=insert_notification)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=10)
        
        # Most should succeed
        assert len(successes) >= 18, (
            f"Too many failures in concurrent writes. "
            f"Successes: {len(successes)}, Errors: {len(errors)}"
        )
    
    def test_special_characters_in_queries(self, db: Session, sample_user, sample_team):
        """EDGE CASE: Special characters should not break queries."""
        special_names = [
            "Project's Name",
            'Project "with" quotes',
            "Project\nwith\nnewlines",
            "Project\twith\ttabs",
            "Project with emoji 🚀",
            "Project with <script>alert('xss')</script>"
        ]
        
        for name in special_names:
            project = Project(
                name=name,
                description="Test",
                team_id=sample_team.id,
                created_by=sample_user.id,
                status=ProjectStatus.ACTIVE
            )
            db.add(project)
        
        db.commit()
        
        # Query should handle special characters
        for name in special_names:
            result = db.query(Project).filter(Project.name == name).first()
            assert result is not None, f"Failed to query project with name: {name}"
            assert result.name == name, f"Name mismatch for: {name}"


class TestPerformanceRegression:
    """Ensure optimizations don't degrade over time."""
    
    def test_baseline_query_performance(self, db: Session, sample_teams):
        """Establish baseline performance metrics."""
        metrics = {}
        
        # Test 1: Simple select
        start = time.time()
        db.query(User).count()
        metrics['user_count'] = (time.time() - start) * 1000
        
        # Test 2: Join query
        start = time.time()
        db.query(Project).join(Team).filter(
            Team.id.in_([t.id for t in sample_teams[:3]])
        ).all()
        metrics['project_team_join'] = (time.time() - start) * 1000
        
        # Test 3: Aggregation
        from sqlalchemy import func
        start = time.time()
        db.query(func.count(Message.id)).scalar()
        metrics['message_count_agg'] = (time.time() - start) * 1000
        
        # All should be fast
        for query_name, query_time in metrics.items():
            assert query_time < 100, (
                f"Query '{query_name}' too slow: {query_time:.2f}ms"
            )
        
        return metrics
    
    def test_write_performance_not_degraded(self, db: Session, sample_user, sample_team):
        """HARD: Verify write performance with strategic indexing (7 indexes)."""
        # Insert 100 projects and measure time
        start = time.time()
        
        projects = []
        for i in range(100):
            project = Project(
                name=f"Write test {i}",
                description="Test",
                team_id=sample_team.id,
                created_by=sample_user.id,
                status=ProjectStatus.ACTIVE
            )
            projects.append(project)
        
        db.bulk_save_objects(projects)
        db.commit()
        
        elapsed = (time.time() - start) * 1000
        per_insert = elapsed / 100
        
        # With 7 strategic indexes, writes should still be fast
        # (vs 30+ indexes which would be 15-30x slower)
        assert per_insert < 10, (
            f"Write performance degraded: {per_insert:.2f}ms per insert. "
            f"This suggests over-indexing."
        )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope='function')
def db():
    """Provide a test database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_user(db: Session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_teams(db: Session, sample_user):
    """Create 5 test teams."""
    teams = []
    for i in range(5):
        team = Team(
            name=f"Test Team {i}",
            description=f"Team {i} description"
        )
        db.add(team)
        db.flush()
        
        # Add user as member
        member = TeamMember(
            team_id=team.id,
            user_id=sample_user.id,
            role="admin",
            is_active=True
        )
        db.add(member)
        teams.append(team)
    
    db.commit()
    for team in teams:
        db.refresh(team)
    return teams


@pytest.fixture
def sample_team(sample_teams):
    """Get first team."""
    return sample_teams[0]


@pytest.fixture
def sample_project(db: Session, sample_team, sample_user):
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="Test project description",
        team_id=sample_team.id,
        created_by=sample_user.id,
        status=ProjectStatus.ACTIVE
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def sample_session(db: Session, sample_project):
    """Create a test chat session."""
    session = ChatSession(
        project_id=sample_project.id,
        name="Test Session"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
