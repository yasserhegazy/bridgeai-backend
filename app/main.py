from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import engine, Base
from app.api import router as api_router
from app.api import auth
from app import __version__

app = FastAPI(
    title="BridgeAI Backend",
    version=__version__
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# ✅ Include routers
app.include_router(api_router, prefix="/api")
app.include_router(auth.router)  # make sure this defines /auth/token

@app.get("/")
def root():
    return {
        "message": "BridgeAI backend running",
        "version": __version__
    }