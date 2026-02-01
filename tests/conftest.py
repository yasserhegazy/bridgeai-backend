"""
Pytest configuration and fixtures for testing the BridgeAI backend application.
"""

import os
import sys
from typing import Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the rate limiter BEFORE importing the app
mock_limiter = MagicMock()
mock_limiter.limit = lambda *args, **kwargs: lambda f: f

# Patch the limiter in the rate_limit module
import app.core.rate_limit

app.core.rate_limit.limiter = mock_limiter

# Mock email sending globally for all tests
email_patcher = patch("app.utils.email.send_email", return_value=None)
email_patcher.start()

from app.db.session import Base, get_db
from app.main import app
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
        role=UserRole.ba,
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
        role=UserRole.client,
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
        role=UserRole.client,
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
        "/api/auth/token",
        data={"username": test_ba_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
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
        "/api/auth/token",
        data={"username": test_client_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def another_client_auth_headers(
    client: TestClient, test_another_client_user: User
) -> Dict[str, str]:
    """
    Get authentication headers for another Client user.
    """
    response = client.post(
        "/api/auth/token",
        data={
            "username": test_another_client_user.email,
            "password": "TestPassword123!",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Comment Testing Fixtures
# ============================================================================


@pytest.fixture
def ba_user(db: Session) -> User:
    """Create a BA user for comment testing."""
    from app.utils.hash import hash_password

    user = User(
        full_name="BA User",
        email="ba_comment@test.com",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.ba,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def client_user(db: Session) -> User:
    """Create a client user for comment testing."""
    from app.utils.hash import hash_password

    user = User(
        full_name="Client User",
        email="client_comment@test.com",
        password_hash=hash_password("TestPassword123!"),
        role=UserRole.client,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def ba_token(client: TestClient, ba_user: User) -> str:
    """Get authentication token for BA user."""
    response = client.post(
        "/api/auth/token",
        data={"username": ba_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def client_token(client: TestClient, client_user: User) -> str:
    """Get authentication token for client user."""
    response = client.post(
        "/api/auth/token",
        data={"username": client_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def sample_team(db: Session, client_user: User):
    """Create a sample team for testing."""
    from app.models.team import Team, TeamMember

    team = Team(name="Test Team", created_by=client_user.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    # Add client user as team member
    member = TeamMember(team_id=team.id, user_id=client_user.id)
    db.add(member)
    db.commit()

    return team


@pytest.fixture
def sample_project(db: Session, client_user: User, sample_team):
    """Create a sample project for testing."""
    from app.models.project import Project, ProjectStatus

    project = Project(
        name="Test Project",
        description="Test project for comments",
        team_id=sample_team.id,
        created_by=client_user.id,
        status=ProjectStatus.active.value,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@pytest.fixture
def sample_crs(db: Session, sample_project, client_user: User):
    """Create a sample CRS document for testing."""
    from app.models.crs import CRSDocument, CRSStatus

    crs = CRSDocument(
        project_id=sample_project.id,
        created_by=client_user.id,
        content="Sample CRS content for testing comments",
        summary_points="[]",
        status=CRSStatus.under_review,
        version=1,
    )
    db.add(crs)
    db.commit()
    db.refresh(crs)
    return crs


@pytest.fixture
def setup_team_project(db: Session, client_user: User, ba_user: User):
    """Create a team and project setup for CRS testing."""
    from app.models.team import Team, TeamMember
    from app.models.project import Project, ProjectStatus

    # Create team
    team = Team(name="Test Team for CRS", created_by=client_user.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    # Add both users as team members
    client_member = TeamMember(team_id=team.id, user_id=client_user.id, role="member")
    ba_member = TeamMember(team_id=team.id, user_id=ba_user.id, role="member")
    db.add(client_member)
    db.add(ba_member)
    db.commit()

    # Create project
    project = Project(
        name="Test Project for CRS",
        description="Test project for CRS operations",
        team_id=team.id,
        created_by=client_user.id,
        status=ProjectStatus.active.value,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return {"team": team, "project": project}


@pytest.fixture(scope="function")
def rate_limit_client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with rate limiting enabled for rate limit tests.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def rate_limit_ba_auth_headers(
    rate_limit_client: TestClient, test_ba_user: User
) -> Dict[str, str]:
    """Get authentication headers for BA user with rate limiting enabled."""
    response = rate_limit_client.post(
        "/api/auth/token",
        data={"username": test_ba_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def rate_limit_client_auth_headers(
    rate_limit_client: TestClient, test_client_user: User
) -> Dict[str, str]:
    """Get authentication headers for Client user with rate limiting enabled."""
    response = rate_limit_client.post(
        "/api/auth/token",
        data={"username": test_client_user.email, "password": "TestPassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
