# BE-16 Visual Diagrams & Architecture

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  app/main.py                                                     │
│  │                                                               │
│  ├─ load_dotenv()                                               │
│  ├─ app = FastAPI()                                             │
│  ├─ initialize_chroma() ◄─────────┐                            │
│  └─ app.include_router(api_router)  │ Startup initialization   │
│                                      │                          │
│                                      ▼                          │
│                          ┌──────────────────────┐               │
│                          │ ChromaDB Initialized │               │
│                          │ • Collection loaded  │               │
│                          │ • Model ready        │               │
│                          │ • Embeddings enabled │               │
│                          └──────────────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Configuration Chain (Concern #3)

```
.env File
┌──────────────────────────────────┐
│ CHROMA_DB_PATH="./chroma_db"     │
│ CHROMA_COLLECTION_NAME="proj..."│
│ EMBEDDING_MODEL="default"         │
└──────────────────┬────────────────┘
                   │
                   │ load_dotenv()
                   ▼
        app/core/config.py
      ┌────────────────────────┐
      │ class Settings:        │
      │   CHROMA_DB_PATH       │
      │   CHROMA_COLLECTION..  │
      │   EMBEDDING_MODEL      │
      └────────────┬───────────┘
                   │
                   │ settings.CHROMA_COLLECTION_NAME
                   ▼
    app/ai/chroma_manager.py
  ┌──────────────────────────────┐
  │ _chroma_client.get_or_      │
  │   create_collection(        │
  │   name=settings.CHROMA_...  │
  │ )                           │
  └──────────────────────────────┘
```

## 3. Memory Creation Flow (Concern #5: Transactions)

```
User Input
    │
    ▼
POST /api/memory/create
    │
    ▼
create_memory(db, project_id, text, source_type, source_id)
    │
    ├─ Try Block
    │  │
    │  ├─ Phase 1: MySQL Prepare
    │  │  │
    │  │  ├─ embedding_id = uuid.uuid4()
    │  │  │
    │  │  ├─ memory = AIMemoryIndex(
    │  │  │     project_id=1,
    │  │  │     source_type="crs",
    │  │  │     embedding_id=embedding_id
    │  │  │ )
    │  │  │
    │  │  ├─ db.add(memory)
    │  │  │
    │  │  └─ db.flush() ◄─ Transaction open, ID obtained
    │  │
    │  ├─ Phase 2: ChromaDB Store
    │  │  │
    │  │  └─ store_embedding(
    │  │     embedding_id,
    │  │     text,
    │  │     metadata
    │  │ ) ◄─ CAN FAIL HERE
    │  │
    │  ├─ Phase 3: Commit
    │  │  │
    │  │  └─ db.commit() ◄─ Only if Phase 2 succeeds
    │  │
    │  └─ return memory ✅
    │
    └─ Except Block (Phase 2 fails)
       │
       ├─ db.rollback() ◄─ Undo Phase 1
       │
       ├─ logger.error(...)
       │
       └─ return None ❌
```

## 4. Embedding Creation Process (Concern #4)

```
User Text
┌─────────────────────────────────┐
│ "Need user authentication"      │
└────────────┬────────────────────┘
             │
             ▼
       store_embedding()
             │
             ├─ embeddings=None
             │
             ▼
     ChromaDB Automatic Process
┌────────────────────────────────┐
│ 1. Download Model              │
│    all-MiniLM-L6-v2 (~22MB)   │
│    ↓ Cached at ~/.cache/      │
│                                │
│ 2. Tokenize                    │
│    "Need user authentication"  │
│    ↓                           │
│    [101, 3927, 2188, ...]      │
│                                │
│ 3. Generate Embedding          │
│    Model forward pass          │
│    ↓                           │
│    384-dimensional vector      │
│    [0.123, -0.456, ...]        │
│                                │
│ 4. Index                       │
│    HNSW (cosine similarity)    │
│    Ready for search            │
└────────────┬────────────────────┘
             │
             ▼
    ChromaDB Collection
┌─────────────────────────────────┐
│ id: "uuid-123"                  │
│ text: "Need user auth..."       │
│ embedding: [0.123, -0.456, ..] │
│ metadata: {project_id: 1, ...}  │
└─────────────────────────────────┘
```

## 5. Data Model Relationship

```
┌──────────────────────────────────────────────────────────────────┐
│                          MySQL Database                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Table: ai_memory_index                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ id (PK)      │ project_id (FK) │ source_type │ embedding_id  │
│  ├──────────────┼─────────────────┼─────────────┼──────────────┤
│  │ 1            │ 1               │ crs         │ uuid-123     │─┐
│  │ 2            │ 1               │ message     │ uuid-456     │ │
│  │ 3            │ 2               │ comment     │ uuid-789     │ │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│         Links via embedding_id ────────────────────────────────┐│
│                                                                  ││
└──────────────────────────────────────────────────────────────────┘│
                                                                     │
┌──────────────────────────────────────────────────────────────────┐│
│                      ChromaDB Database                           ││
├──────────────────────────────────────────────────────────────────┤│
│                                                                   ││
│  Collection: project_memories                                   ││
│  ┌──────────────────────────────────────────────────────────┐  ││
│  │ id             │ document      │ embedding (384-d)       │  ││
│  ├────────────────┼───────────────┼─────────────────────────┤  ││
│  │ uuid-123 ◄─────┼──────────────────────────────────────────  ││
│  │                │ "Need auth..." │ [0.123, -0.456, ...]   │  ││
│  │ uuid-456 ◄─────┼──────────────────────────────────────────  ││
│  │                │ "Login sys..." │ [0.234, -0.567, ...]   │  ││
│  │ uuid-789       │ "Comment..."   │ [0.345, -0.678, ...]   │  ││
│  └──────────────────────────────────────────────────────────┘  ││
│                                                                   ││
│  HNSW Index (for fast similarity search)                        ││
│                                                                   ││
└──────────────────────────────────────────────────────────────────┘│
                                                                      │
 ←──────────────────── embedding_id link ──────────────────────────┘
```

## 6. Search Flow

```
User Query
┌─────────────────────────┐
│ "authentication system" │
└────────┬────────────────┘
         │
         ▼
search_project_memories(project_id=1, query="authentication...")
         │
         ├─ ChromaDB Embedding
         │  │
         │  ├─ Tokenize query
         │  │
         │  ├─ Run model
         │  │
         │  └─ Generate 384-d vector
         │
         ├─ Cosine Similarity Search
         │  │
         │  ├─ uuid-123: distance=0.15 → similarity=0.85 ✅
         │  ├─ uuid-456: distance=0.32 → similarity=0.68 ✅
         │  └─ uuid-789: distance=0.87 → similarity=0.13 ❌ (below threshold)
         │
         ├─ Filter by project_id=1
         │
         ├─ Fetch MySQL Metadata
         │  │
         │  ├─ id=1, source_type=crs, source_id=5
         │  └─ id=2, source_type=message, source_id=12
         │
         └─ Return Ranked Results
            │
            ├─ [1] "Need user auth..." (0.85 similarity)
            ├─ [2] "Login system..." (0.68 similarity)
            └─ Total: 2 results
```

## 7. Error Handling & Rollback

```
create_memory() Execution
    │
    ├─ db.add(memory)
    ├─ db.flush() ✅
    │
    ├─ store_embedding()
    │
    ├─ Scenario A: ChromaDB fails ❌
    │  │
    │  ├─ Exception caught
    │  │
    │  ├─ db.rollback()
    │  │  │
    │  │  ├─ MySQL: Undo AIMemoryIndex
    │  │  └─ State: No record created ✓
    │  │
    │  ├─ logger.error("Failed...")
    │  │
    │  └─ return None
    │
    └─ Scenario B: All succeeds ✅
       │
       ├─ store_embedding() ✅
       │
       ├─ db.commit()
       │  │
       │  ├─ MySQL: Save AIMemoryIndex
       │  └─ ChromaDB: Embedding persisted ✓
       │
       └─ return memory


Database State After Each Scenario:

Scenario A (Failure):
    MySQL:     Empty (rolled back)
    ChromaDB:  Empty (exception prevented storage)
    Result:    ✅ Consistent - no orphans

Scenario B (Success):
    MySQL:     AIMemoryIndex record created
    ChromaDB:  Embedding + vector stored
    Result:    ✅ Consistent - linked via embedding_id
```

## 8. Initialization Sequence

```
App Start
  │
  ├─ load_dotenv()
  │  └─ Load .env variables
  │
  ├─ Create FastAPI app
  │
  ├─ Initialize ChromaDB ◄─── CONCERN #2 ANSWER
  │  │
  │  ├─ Create PersistentClient
  │  │  └─ Path: ./chroma_db
  │  │
  │  ├─ Load Collection ◄─── CONCERN #3 ANSWER
  │  │  │
  │  │  ├─ Name from settings
  │  │  │  └─ "project_memories"
  │  │  │
  │  │  ├─ get_or_create_collection()
  │  │  │
  │  │  └─ Metadata:
  │  │     hnsw:space = "cosine"
  │  │
  │  ├─ Download Embedding Model ◄─── CONCERN #4 ANSWER
  │  │  │
  │  │  ├─ Model: all-MiniLM-L6-v2
  │  │  │
  │  │  ├─ Size: ~22MB
  │  │  │
  │  │  └─ Cache: ~/.cache/chroma/
  │  │
  │  └─ Ready for use ✅
  │
  ├─ Register Routers
  │
  └─ Server Ready
     http://localhost:8000 ready to accept requests
```

## 9. Module Dependencies

```
app/main.py
    │
    ├─ imports: initialize_chroma
    │  │
    │  └─ app/ai/chroma_manager.py
    │     │
    │     ├─ chromadb
    │     └─ app/core/config.py
    │
    └─ includes: memory router
       │
       └─ app/api/memory.py
          │
          ├─ app/ai/memory_service.py
          │  │
          │  ├─ app/ai/chroma_manager.py
          │  └─ app/models/ai_memory_index.py
          │
          └─ app/db/session.py

Clarification Node
    │
    └─ uses: search_project_memories
       │
       └─ app/ai/memory_service.py
```

---

**These diagrams provide visual understanding of the 5 concerns and how they're addressed in the implementation.**
