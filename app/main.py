from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base
from app.api import router as api_router
from app.api import auth
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="BridgeAI Backend")


# create DB tables (development convenience)
# Base.metadata.create_all(bind=engine)

# Add this CORS middleware
origins = [
    "http://localhost:3000",  # your frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # ✅ this allows OPTIONS, POST, GET etc.
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "BridgeAI backend running"}