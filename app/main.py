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

# Enable WebSocket support
# WebSocket connections are handled by specific endpoints in the API routers

# ✅ Create database tables (optional)
# Base.metadata.create_all(bind=engine)

# ✅ Include routers
app.include_router(api_router, prefix="/api")
app.include_router(auth.router)  # make sure this defines /auth/token

@app.get("/")
def root():
    return {
        "message": "BridgeAI backend running",
        "version": __version__
    }