import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

from app import __version__  # noqa: E402
from app.ai.chroma_manager import initialize_chroma  # noqa: E402
from app.api import auth  # noqa: E402
from app.api import router as api_router  # noqa: E402
from app.core.middleware import SecurityHeadersMiddleware  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402


# 1. LIFESPAN: This is the secret. The app "starts" first, THEN runs this.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs AFTER the server starts listening on the port
    logging.info("Starting heavy initialization...")
    try:
        chroma_client, chroma_collection = initialize_chroma()
        app.state.chroma_client = chroma_client
        app.state.chroma_collection = chroma_collection
        logging.info("ChromaDB successfully initialized in background.")
    except Exception as e:
        logging.error(f"ChromaDB failed: {str(e)}")

    yield  # The app stays running here

    # Optional: Put cleanup code here (e.g., closing DB)


app = FastAPI(
    title="BridgeAI Backend",
    version=__version__,
    lifespan=lifespan,  # Attach the lifespan handler
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests."})


# Update origins for production
origins = [
    "http://localhost:3000",  # your frontend React app
    "http://localhost:3001",  # alternative frontend port
    "http://127.0.0.1:3000",  # localhost IP variant
    "http://127.0.0.1:3001",  # alternative port IP variant
    "https://bridgeai-ai.vercel.app",  # Your frontend URL
]

# ✅ Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


# Request size limit middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Limit request body size to 10MB
        max_size = 10 * 1024 * 1024
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large. Maximum size is 10MB."},
                )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)

# ✅ Add CORS middleware only once
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # For your project grade, "*" is the safest to avoid CORS errors
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(auth.router)


@app.get("/")
def root():
    return {"status": "alive", "version": __version__}
