import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)

if __name__ == "__main__":
    print("Running tests...")
    try:
        test_login_rate_limit()
        print("✅ test_login_rate_limit passed")
        test_register_rate_limit()
        print("✅ test_register_rate_limit passed")
        print("All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)

def test_login_rate_limit():
    """
    Test that login endpoint is rate limited to 5 requests per minute.
    """
    # Make 5 allowed requests
    for _ in range(5):
        response = client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        # We expect 401 because credentials are wrong, but NOT 429 yet
        assert response.status_code != 429

    # Make 6th request - should be rate limited
    response = client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 429
    # slowapi default handler returns "error" key
    data = response.json()
    assert "error" in data or "detail" in data
    if "error" in data:
        assert "Rate limit exceeded" in data["error"]
    else:
        assert "Rate limit exceeded" in data["detail"]

def test_register_rate_limit():
    """
    Test that register endpoint is rate limited to 3 requests per hour.
    """
    # Make 3 allowed requests
    for i in range(3):
        response = client.post(
            "/auth/register",
            json={
                "email": f"test{i}@example.com",
                "password": "Password123!",
                "full_name": "Test User",
                "role": "client"
            }
        )
        assert response.status_code != 429

    # Make 4th request - should be rate limited
    response = client.post(
        "/auth/register",
        json={
            "email": "test_limit@example.com",
            "password": "Password123!",
            "full_name": "Test User",
            "role": "client"
        }
    )
    
    assert response.status_code == 429
    # slowapi default handler returns "error" key
    data = response.json()
    assert "error" in data or "detail" in data
    if "error" in data:
        assert "Rate limit exceeded" in data["error"]
    else:
        assert "Rate limit exceeded" in data["detail"]
