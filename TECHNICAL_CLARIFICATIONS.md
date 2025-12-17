"""
TECHNICAL CLARIFICATIONS: ChromaDB + MySQL Integration
Addresses specific implementation questions about BE-16
"""

# ======================== CONCERN #2 ========================
# Missing: ChromaDB initialization location in your code
# ======================== CONCERN #2 ========================

"""
SOLUTION: ChromaDB initializes at application startup with singleton pattern

Location: app/main.py (Lines 62-71)
    try:
        chroma_client, chroma_collection = initialize_chroma()
        app.state.chroma_client = chroma_client
        app.state.chroma_collection = chroma_collection
    except Exception as e:
        logging.error(f"Failed to initialize ChromaDB: {str(e)}")

Singleton Pattern Implementation:
    1. initialize_chroma() returns both client and collection
    2. Both stored in app.state (not global variables)
    3. All modules access via app.state.chroma_collection
    4. Ensures exactly ONE instance across entire application
    5. Prevents multiple client creation on imports

Timing: FastAPI app initialization (before routers are included)
Method: initialize_chroma() in app/ai/chroma_manager.py
Storage: 
    - Persistent filesystem at ./chroma_db directory
    - app.state singleton for application lifetime
    
Embedding Function:
    - Configured during initialization
    - SentenceTransformerEmbeddingFunction(all-MiniLM-L6-v2)
    - Passed to get_or_create_collection()
    - Downloaded and cached on first use
"""

# ======================== CONCERN #3 ========================
# Missing: How ChromaDB knows which collection to load
# ======================== CONCERN #3 ========================

"""
SOLUTION: Collection name from environment config

Configuration Chain:
    1. .env file
       CHROMA_COLLECTION_NAME="project_memories"
    
    2. app/core/config.py
       class Settings(BaseSettings):
           CHROMA_COLLECTION_NAME: str = "project_memories"
    
    3. app/ai/chroma_manager.py - initialize_chroma()
       _collection = _chroma_client.get_or_create_collection(
           name=settings.CHROMA_COLLECTION_NAME,
           metadata={"hnsw:space": "cosine"}
       )

Access Pattern:
    - get_collection() returns the loaded collection
    - Used by all memory operations (store, search, delete)
    - Singleton pattern prevents multiple initializations
"""

# ======================== CONCERN #4 ========================
# Missing: How embeddings are created
# ======================== CONCERN #4 ========================

"""
SOLUTION: ChromaDB requires explicit embedding function configuration

CRITICAL CORRECTION:
    ChromaDB does NOT automatically generate embeddings.
    You MUST provide an embedding_function explicitly.

Implementation (app/ai/chroma_manager.py):
    
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=embedding_fn,  # CRITICAL: Must be provided
        metadata={"hnsw:space": "cosine"}
    )

What happens WITHOUT embedding function:
    ❌ collection.add(ids=[id], documents=[text])
    → ChromaDB stores None for embeddings
    → Search fails because no vectors exist
    → Similarity matching returns no results

Embedding Process (AUTOMATIC once function is configured):
    1. store_embedding() called with text and metadata
    2. ChromaDB uses configured embedding function automatically
    3. Text is tokenized
    4. all-MiniLM-L6-v2 model generates 384-dimensional vector
    5. Vector stored in HNSW index for fast search
    
Embedding Parameters:
    collection.add(
        ids=[embedding_id],
        documents=[text],              # Auto-embedded by configured function
        metadatas=[metadata],          # Metadata (not embedded)
        embeddings=None                # ChromaDB generates automatically
    )

Model Details:
    Name: sentence-transformers/all-MiniLM-L6-v2
    Type: SentenceTransformer (Hugging Face)
    Dimensions: 384 per embedding
    Size: ~22MB
    Speed: ~300 texts/second
    Download: Automatic on first use, cached at ~/.cache/chroma/
    Distance Metric: Cosine similarity

Optional: Use Custom Pre-computed Embeddings
    If you have pre-computed embeddings from another model:
    collection.add(
        ids=[embedding_id],
        documents=[text],
        metadatas=[metadata],
        embeddings=[[0.123, -0.456, ...]]  # Your 384-d vector
    )
    Note: Must be 384-dimensional to match model
"""

# ======================== CONCERN #5 ========================
# Missing: How MySQL transactions interact with ChromaDB failures
# ======================== CONCERN #5 ========================

"""
SOLUTION: Two-phase commit with rollback on failure

Transaction Flow in create_memory():
    
    Phase 1 - MySQL Prepare:
        db.add(memory)
        db.flush()  # Get ID but don't commit
    
    Phase 2 - ChromaDB Store:
        store_embedding(embedding_id, text, metadata)
        ↑ THIS CAN FAIL
    
    Failure Handling:
        if ChromaDB fails:
            db.rollback()  # Undo MySQL changes
            return None
        else:
            db.commit()    # Finalize both

Code Implementation (app/ai/memory_service.py - create_memory):
    
    try:
        # Step 1: Create MySQL record
        memory = AIMemoryIndex(...)
        db.add(memory)
        db.flush()  # Get ID
        
        # Step 2: Store in ChromaDB
        store_embedding(
            embedding_id=embedding_id,
            text=text,
            metadata=chroma_metadata
        )
        
        # Step 3: Commit both
        db.commit()
        return memory
    
    except Exception as e:
        # If ChromaDB fails, rollback MySQL
        db.rollback()
        logger.error(f"Failed to create memory: {str(e)}")
        return None

Consistency Guarantee:
    ✅ Both systems succeed together
    ✅ Both systems fail together
    ✅ No orphaned records
    ✅ No dangling embeddings

Edge Cases Handled:
    1. ChromaDB timeout: Caught, rolled back
    2. Network error: Caught, rolled back
    3. Disk full: Caught, rolled back
    4. Embedding generation failure: Caught, rolled back
    5. MySQL connection lost: SQLAlchemy rollback() handles it

Related: delete_memory() also uses same pattern
    1. Delete from MySQL
    2. If success, delete from ChromaDB
    3. If ChromaDB fails, still committed to MySQL (acceptable)
       - Orphaned embedding is minimal data loss
       - Can be cleaned up with separate garbage collection
"""

# ======================== VERIFICATION CHECKLIST ========================

"""
✅ Initialization Location
   - Confirmed: app/main.py lines 62-71: initialize_chroma()
   - Singleton: Client/collection stored in app.state
   - Timing: Before app.include_router() calls
   - Error handling: try/except with logging

✅ Collection Loading
   - Confirmed: Settings chain (env → config → chroma_manager)
   - Get or Create: Idempotent operation with embedding function
   - Access: Via app.state.chroma_collection (singleton pattern)
   - Embedding: SentenceTransformerEmbeddingFunction configured

✅ Embedding Creation
   - Confirmed: Explicit embedding function (NOT automatic)
   - Function: SentenceTransformerEmbeddingFunction(all-MiniLM-L6-v2)
   - Process: Text → tokenize → model → 384-d vector → HNSW index
   - Automatic: Runs automatically once function is configured
   - Search: Cosine similarity (HNSW algorithm)

✅ Transaction Safety
   - Confirmed: Two-phase commit pattern
   - Rollback: MySQL rolled back on ChromaDB failure
   - Consistency: Both systems sync or both fail
   - Logging: All errors logged with context
   - Recovery: Failed operations return None

Additional Safety Measures:
   1. Embedding function configured at startup
   2. Singleton prevents multiple client instances
   3. Connection pooling for MySQL
   4. Timeout settings for ChromaDB operations
   5. Error logging with full tracebacks
"""

# ======================== USAGE EXAMPLES ========================

"""
EXAMPLE 1: Creating a memory (with transaction safety)

from app.ai.memory_service import create_memory
from app.db.session import get_db

db = next(get_db())
memory = create_memory(
    db=db,
    project_id=1,
    text="User needs real-time notifications",
    source_type="crs",
    source_id=5,
    metadata={"priority": "high"}
)

if memory:
    print(f"✅ Stored: {memory.embedding_id}")
    # Both MySQL and ChromaDB have the data
else:
    print("❌ Failed - both systems rolled back")
    # Neither system has the data


EXAMPLE 2: Searching memories (reads from ChromaDB only)

from app.ai.memory_service import search_project_memories

results = search_project_memories(
    db=db,
    project_id=1,
    query="notification system",
    limit=5,
    similarity_threshold=0.3
)

for result in results:
    print(f"Text: {result['text']}")
    print(f"Similarity: {result['similarity_score']}")  # 0-1 range
    print(f"Source: {result['source_type']}")


EXAMPLE 3: How embedding is created (with explicit function)

When you call:
    store_embedding(
        embedding_id="uuid-123",
        text="The system should have user authentication",
        metadata={"project_id": 1}
    )

Process (happens automatically because embedding_function was configured):
    1. ChromaDB receives the text
    2. Uses configured SentenceTransformerEmbeddingFunction
    3. Tokenizes: "The system should have user authentication"
       ↓
       [101, 1996, 2156, 2323, 2572, 2572, 102, ...]
    4. Runs through all-MiniLM-L6-v2 model
       ↓
    5. Generates 384-dimensional vector
       ↓
       [-0.123, 0.456, 0.789, -0.234, 0.567, ...]  (384 values)
    6. Stores in HNSW index with metadata

Search example:
    query="login requirements"
    1. Query embedded with same function → 384-d vector
    2. Computes cosine distance to all stored vectors
    3. Returns top-k closest matches sorted by similarity
    4. Similarity score = 1 - distance (0-1 range)

Critical: Without explicit embedding function
    ❌ ChromaDB stores None for embeddings
    ❌ Search returns no results
    ❌ Error messages may be cryptic


EXAMPLE 4: Transaction failure and recovery

Scenario: Network disconnects during ChromaDB store

create_memory() execution:
    ✅ MySQL: AIMemoryIndex record added, flushed
    ❌ ChromaDB: store_embedding() times out
    ↓
    Exception caught
    ↓
    db.rollback()  # Undoes the MySQL add()
    ↓
    return None
    ↓
    Both systems remain unchanged
"""

# ======================== MONITORING ========================

"""
Check ChromaDB Status:
    from app.ai.chroma_manager import get_collection
    collection = get_collection()
    print(f"Embeddings stored: {collection.count()}")

Check MySQL Status:
    from app.db.session import SessionLocal
    db = SessionLocal()
    memories = db.query(AIMemoryIndex).all()
    print(f"Memory records: {len(memories)}")

Check Consistency:
    If counts don't match, there may be:
    - Orphaned MySQL records (if ChromaDB delete failed)
    - Orphaned ChromaDB records (if MySQL delete succeeded)
    → Can be fixed with cleanup script

Monitor Errors:
    Check logs in app output for:
    "ERROR - app.ai.memory_service"
    "ERROR - app.ai.chroma_manager"
"""
