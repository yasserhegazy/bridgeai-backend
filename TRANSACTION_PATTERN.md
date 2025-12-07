"""
Transaction Pattern: MySQL + ChromaDB Two-Phase Commit

This document explains how create_memory() handles transaction safety
when storing data in both MySQL and ChromaDB simultaneously.
"""

# ============================================================================
# SCENARIO: Creating a memory with transaction safety
# ============================================================================

"""
User calls:
    memory = create_memory(
        db=db,
        project_id=1,
        text="Need user authentication",
        source_type="crs",
        source_id=5
    )

What happens internally:
"""

# PHASE 1: MYSQL PREPARATION
# ============================================================================

"""
Step 1.1: Generate Embedding ID
    embedding_id = str(uuid.uuid4())
    Example: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

Step 1.2: Create MySQL Record (NOT COMMITTED YET)
    memory = AIMemoryIndex(
        project_id=1,
        source_type=SourceType["crs"],
        source_id=5,
        embedding_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )
    db.add(memory)
    db.flush()  # ← KEY: Get ID but don't commit

Database State After Flush:
    [MySQL Transaction Open]
    Table ai_memory_index:
        - Row exists with embedding_id in this transaction only
        - NOT visible to other connections yet
        - Can be rolled back completely

Step 1.3: Prepare Metadata for ChromaDB
    chroma_metadata = {
        "project_id": 1,
        "source_type": "crs",
        "source_id": 5,
        "memory_id": memory.id,  # Now we have the ID from flush()
        "created_at": "2025-12-07T15:22:30.123456"
    }

Database State:
    [MySQL Transaction Still Open]
    [ChromaDB Empty]
"""

# PHASE 2: CHROMEDB STORAGE
# ============================================================================

"""
Step 2.1: Store Embedding in ChromaDB
    store_embedding(
        embedding_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        text="Need user authentication",
        metadata=chroma_metadata
    )

What Happens Inside store_embedding():
    collection.add(
        ids=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        documents=["Need user authentication"],
        metadatas=[{"project_id": 1, ...}],
        embeddings=None  # ChromaDB generates automatically
    )

    Embedding Generation (Automatic):
    1. Text: "Need user authentication"
    2. Tokenize: [101, 3927, 2188, 22567, 102, ...]
    3. Model: all-MiniLM-L6-v2
    4. Output: 384-dimensional vector
       [-0.123, 0.456, 0.789, -0.234, ...] (384 values)
    5. Store: Vector + metadata in HNSW index
    6. Index: Ready for cosine similarity search

Database State:
    [MySQL Transaction Still Open]
    [ChromaDB Embedding Stored]
"""

# CRITICAL: FAILURE SCENARIOS
# ============================================================================

"""
Scenario A: ChromaDB fails after MySQL flush
─────────────────────────────────────────────

    db.flush()  ✅ MySQL record prepared
    ↓
    store_embedding()  ❌ FAILS (timeout, network error, etc.)
    ↓
    Exception caught in try/except block
    ↓
    db.rollback()  ← Undo MySQL changes
    ↓
    return None

Result:
    MySQL: No record created
    ChromaDB: No embedding stored
    Consistency: ✅ Both systems unchanged

Scenario B: ChromaDB succeeds, MySQL commit fails
──────────────────────────────────────────────────

    db.flush()  ✅ MySQL record prepared
    ↓
    store_embedding()  ✅ ChromaDB embedding stored
    ↓
    db.commit()  ❌ FAILS (connection lost)
    ↓
    Exception caught
    ↓
    db.rollback()  ← Undo MySQL changes (but ChromaDB committed)
    ↓
    return None

Result:
    MySQL: No record created (rolled back)
    ChromaDB: Embedding exists (orphaned)
    Consistency: ⚠️ Orphaned embedding (acceptable risk)
        → Can be cleaned up with separate garbage collection

Scenario C: Both succeed (normal path)
───────────────────────────────────────

    db.flush()  ✅ MySQL record prepared
    ↓
    store_embedding()  ✅ ChromaDB embedding stored
    ↓
    db.commit()  ✅ MySQL transaction committed
    ↓
    return memory

Result:
    MySQL: Record visible to all connections
    ChromaDB: Embedding searchable by all
    Consistency: ✅ Both systems in sync
"""

# PHASE 3: COMMIT (IF BOTH SUCCEED)
# ============================================================================

"""
Step 3.1: Commit MySQL Transaction
    db.commit()

    This makes the MySQL record:
    - Visible to all database connections
    - Permanent on disk
    - Subject to ACID properties
    - Recoverable from backups

Step 3.2: Return Success
    return memory  # AIMemoryIndex object with ID

Final State:
    MySQL:
        ai_memory_index table now has:
        - id: 123 (auto-incremented)
        - project_id: 1
        - source_type: "crs"
        - source_id: 5
        - embedding_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        - created_at: 2025-12-07 15:22:30

    ChromaDB:
        project_memories collection now has:
        - id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        - document: "Need user authentication"
        - embedding: [384-dimensional vector]
        - metadata: {"project_id": 1, ...}
        - indexed for cosine similarity search

    Link between systems:
        MySQL.embedding_id = ChromaDB.id
        Both reference the same memory
"""

# ERROR HANDLING AND LOGGING
# ============================================================================

"""
All errors are logged with full context:

logger.error(
    f"❌ Failed to create memory for project 1\\n"
    f"   Embedding ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890\\n"
    f"   Error: The read operation timed out in add.\\n"
    f"   Action: MySQL rolled back to prevent orphaned records"
)

Log Format Includes:
    - Status indicator (❌ Failed, ✅ Success)
    - Operation (create memory)
    - Project context
    - Embedding ID (for tracking)
    - Actual error message
    - Action taken (rollback, etc.)

Log Level: ERROR (if failed), INFO (if successful)
Log Stream: Python logging → captured in app logs
"""

# TRANSACTION ISOLATION
# ============================================================================

"""
Why MySQL transaction stays open during ChromaDB operation:

Reason 1: Get the Memory ID
    db.flush() gives us memory.id
    This ID is needed for ChromaDB metadata

Reason 2: All-or-Nothing Semantics
    If ChromaDB fails, we can roll back MySQL
    If we committed early, rollback would be impossible

Reason 3: Consistency
    No other process can see the half-created memory
    If app crashes, MySQL transaction aborts automatically
    Nothing left hanging

Transaction Isolation Level (MySQL):
    Default: REPEATABLE READ
    Sufficient for this use case
    (No concurrent writes to same project_id)
"""

# EDGE CASES HANDLED
# ============================================================================

"""
1. Connection Pool Exhaustion
   Problem: MySQL connection lost during transaction
   Solution: db.rollback() succeeds, returns None
   
2. ChromaDB Timeout
   Problem: Embedding generation takes too long
   Solution: Exception caught, MySQL rolled back
   
3. Duplicate Embedding ID
   Problem: UUID collision (astronomically unlikely)
   Solution: ChromaDB would reject, MySQL rolled back
   
4. Disk Full
   Problem: ChromaDB can't write embedding to disk
   Solution: Exception caught, MySQL rolled back
   
5. Invalid Text
   Problem: Text is None or empty
   Solution: Stored as-is, ChromaDB creates "empty" embedding
   (This is a business decision - allow or validate upstream)
   
6. Memory Leak (Orphaned Embeddings)
   Problem: ChromaDB succeeds, MySQL fails
   Solution: Acceptable - embeddings are small, can cleanup later
"""

# VERIFICATION
# ============================================================================

"""
After create_memory() succeeds, verify both systems:

from app.db.session import SessionLocal
from app.ai.chroma_manager import get_collection

# Check MySQL
db = SessionLocal()
memory = db.query(AIMemoryIndex).filter(
    AIMemoryIndex.embedding_id == embedding_id
).first()
print(f"MySQL: {memory is not None}")  # Should be True

# Check ChromaDB
collection = get_collection()
result = collection.get(ids=[embedding_id])
print(f"ChromaDB: {len(result['ids']) > 0}")  # Should be True

# Check Link
print(f"Link: {memory.embedding_id == result['ids'][0]}")  # Should be True
"""

# PERFORMANCE NOTES
# ============================================================================

"""
Operation Timing (approximate):

create_memory():
    1. MySQL flush: <1ms
    2. Embedding generation: 10-100ms (first time slower due to model load)
    3. ChromaDB store: <10ms
    4. MySQL commit: <5ms
    Total: 15-115ms per memory

Factors affecting speed:
    - Text length (longer = slower embedding)
    - Model cache (first run downloads 22MB)
    - Disk speed (affects ChromaDB storage)
    - MySQL connection pool (if busy)
    - System load (CPU for embedding generation)
"""
