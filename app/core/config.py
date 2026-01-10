from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Security settings
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    
    # Email settings
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str = "BridgeAI"
    # AI settings
    GROQ_API_KEY: str
    
    # ChromaDB settings
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "project_memories"
    EMBEDDING_MODEL: str = "openai"  # or "default" for Chroma's default
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()