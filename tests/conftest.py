"""
Pytest configuration and fixtures for testing the BridgeAI backend application.
"""
import sys
import os
from typing import Generator, Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.session import Base, get_db
from app.models.user import User, UserRole
from app.utils.hash import hash_password


# Create in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test function.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with the test database.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Reset rate limiter for each test to avoid rate limit issues in tests
    if hasattr(app.state, 'limiter'):
        try:
            # Clear the rate limiter storage
            app.state.limiter.reset()
        except:
            pass
    
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_ba_user(db: Session) -> User:
    """
    Create a Business Analyst test user.
    """
    user = User(
        full_name="Test BA User",
        email="ba@test.com",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.ba
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_client_user(db: Session) -> User:
    """
    Create a Client test user.
    """
    user = User(
        full_name="Test Client User",
        email="client@test.com",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.client
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_another_client_user(db: Session) -> User:
    """
    Create another Client test user for multi-user scenarios.
    """
    user = User(
        full_name="Another Client User",
        email="client2@test.com",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.client
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def ba_auth_headers(client: TestClient, test_ba_user: User) -> Dict[str, str]:
    """
    Get authentication headers for BA user.
    """
    response = client.post(
        "/auth/token",
        data={"username": test_ba_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_auth_headers(client: TestClient, test_client_user: User) -> Dict[str, str]:
    """
    Get authentication headers for Client user.
    """
    response = client.post(
        "/auth/token",
        data={"username": test_client_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def another_client_auth_headers(client: TestClient, test_another_client_user: User) -> Dict[str, str]:
    """
    Get authentication headers for another Client user.
    """
    response = client.post(
        "/auth/token",
        data={"username": test_another_client_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
