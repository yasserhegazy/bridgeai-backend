from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Optimized connection pooling configuration
# pool_size: Number of connections to maintain in the pool
# max_overflow: Max connections beyond pool_size during high load
# pool_recycle: Recycle connections after 1 hour (prevents MySQL timeouts)
# pool_pre_ping: Test connections before use (adds ~1ms overhead but prevents stale connections)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Base pool size (was implicit default of 5)
    max_overflow=10,  # Allow up to 30 total connections under load
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Test connection validity (prevents OperationalError)
    echo=False,  # Disable SQL logging in production
    pool_timeout=30,  # Wait up to 30s for connection (prevents indefinite blocking)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
