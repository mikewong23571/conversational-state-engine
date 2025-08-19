"""
Shared pytest configuration and fixtures
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from server.app import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Test client for unit tests - no real server needed"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_token(client):
    """Get authentication token for tests"""
    response = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "test123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def authenticated_client(client, auth_token):
    """Test client with authentication headers"""
    client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return client


@pytest.fixture
def test_session(authenticated_client):
    """Create a test session"""
    response = authenticated_client.post("/sessions")
    assert response.status_code == 200
    return response.json()["session_id"]
