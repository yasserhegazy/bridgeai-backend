from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Google Auth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

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
    # AI settings - Claude (Anthropic)
    ANTHROPIC_API_KEY: str

    # LLM Model Configuration
    # Default model for all AI operations (can be overridden per component)
    # Available Claude 4.5 models:
    # - claude-sonnet-4-5-20250929 (latest Sonnet 4.5 - best balance)
    # - claude-haiku-4-5-20251001 (latest Haiku 4.5 - fast & cost-effective)
    # - claude-opus-4-5-20251101 (latest Opus 4.5 - most capable but expensive)
    LLM_DEFAULT_MODEL: str = "claude-sonnet-4-5-20250929"

    # Component-specific model configurations
    # Clarification needs good reasoning - use Sonnet 4.5
    LLM_CLARIFICATION_MODEL: str = "claude-sonnet-4-5-20250929"
    LLM_CLARIFICATION_TEMPERATURE: float = 0.3
    LLM_CLARIFICATION_MAX_TOKENS: int = 2048

    # Template Filler needs structured extraction - use Sonnet 4.5
    LLM_TEMPLATE_FILLER_MODEL: str = "claude-sonnet-4-5-20250929"
    LLM_TEMPLATE_FILLER_TEMPERATURE: float = 0.2
    LLM_TEMPLATE_FILLER_MAX_TOKENS: int = 4096

    # Suggestions can use Haiku 4.5 for speed and cost savings
    LLM_SUGGESTIONS_MODEL: str = "claude-haiku-4-5-20251001"
    LLM_SUGGESTIONS_TEMPERATURE: float = 0.7
    LLM_SUGGESTIONS_MAX_TOKENS: int = 2000
    
    # ChromaDB settings (vector database for semantic search)
    CHROMA_SERVER_HOST: str = "localhost"
    CHROMA_SERVER_HTTP_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "project_memories"
    CHROMA_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # 384-dimensional embeddings
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
