from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base
from app.api import router as api_router
from app.api import auth


app = FastAPI(title="BridgeAI Backend")


# create DB tables (development convenience)
# Base.metadata.create_all(bind=engine)


app.include_router(api_router, prefix="/api")
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "BridgeAI backend running"}