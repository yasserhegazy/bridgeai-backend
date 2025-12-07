from dotenv import load_dotenv
load_dotenv()
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import engine, Base
from app.api import router as api_router
from app.api import auth
from app.api import ai
from app import __version__
from app.ai.chroma_manager import initialize_chroma

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="BridgeAI Backend",
    version=__version__
)

# Add rate limiter to app state
app.state.limiter = limiter

# Custom rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. You have exceeded the maximum number of attempts. Please wait a few minutes before trying again."
        }
    )

# ✅ Define allowed frontend origins
origins = [
    "http://localhost:3000",  # your frontend React app
    "http://localhost:3001",  # alternative frontend port
]

# ✅ Add CORS middleware only once
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # allow GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],  # allow all headers
)

# ✅ Create database tables (optional)
# Base.metadata.create_all(bind=engine)

# ======================== CHROMEDB INITIALIZATION ========================
# Location: This is where ChromaDB is initialized (app startup)
# 
# Initialization Flow:
#   1. Creates/loads persistent database at ./chroma_db
#   2. Configures SentenceTransformerEmbeddingFunction (all-MiniLM-L6-v2)
#   3. Loads collection named "project_memories" WITH embedding function
#   4. Sets up cosine similarity search
#   5. Stores client/collection in app.state (singleton pattern)
#
# Singleton Pattern:
#   - Client and collection stored in app.state
#   - All modules access via app.state (not global variables)
#   - Ensures single instance across entire application
#
# Critical: Embedding Function
#   - ChromaDB REQUIRES explicit embedding function
#   - SentenceTransformerEmbeddingFunction(all-MiniLM-L6-v2) configured here
#   - Downloads ~22MB model on first run, cached locally
#
# Error Handling:
#   - If initialization fails, error is logged
#   - App continues running (memory features unavailable)
#   - Can be manually re-initialized later
#
# See: app/ai/chroma_manager.py for implementation
# See: TECHNICAL_CLARIFICATIONS.md for detailed explanation
# ======================== CHROMEDB INITIALIZATION ========================

try:
    chroma_client, chroma_collection = initialize_chroma()
    app.state.chroma_client = chroma_client
    app.state.chroma_collection = chroma_collection
    logging.info("ChromaDB singleton stored in app.state")
except Exception as e:
    logging.error(f"Failed to initialize ChromaDB: {str(e)}")

# ✅ Include routers
app.include_router(api_router, prefix="/api")
app.include_router(auth.router)  # make sure this defines /auth/token

@app.get("/")
def root():
    return {
        "message": "BridgeAI backend running",
        "version": __version__
    }