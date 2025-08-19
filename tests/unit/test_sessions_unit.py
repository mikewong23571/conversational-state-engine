"""
Unit tests for sessions - using TestClient (no real server)
"""

import pytest
from fastapi.testclient import TestClient

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


def test_create_session(authenticated_client):
    """Test session creation using TestClient"""
    response = authenticated_client.post("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "version" in data
    assert data["version"] == "v1"


def test_get_session_state(authenticated_client, test_session):
    """Test getting session state"""
    response = authenticated_client.get(f"/sessions/{test_session}/state")
    assert response.status_code == 200
    state = response.json()
    assert state["version"] == "v1"
    assert "data" in state
    assert "stories" in state["data"]


def test_create_intention(authenticated_client, test_session):
    """Test creating intentions"""
    intentions = {
        "items": [
            {
                "action": "add",
                "target_path": "/stories/-",
                "value": {
                    "key": "TEST-Story",
                    "title": "Test Story",
                    "priority": "P1",
                    "auth_type": "password",
                    "dependencies": [],
                },
                "reason": "Test story creation",
                "confidence": 0.9,
            }
        ]
    }

    response = authenticated_client.post(
        f"/sessions/{test_session}/intents", json=intentions
    )
    assert response.status_code == 200
    result = response.json()
    assert "intention_set_id" in result


def test_unauthenticated_access(client):
    """Test that unauthenticated requests are rejected"""
    response = client.post("/sessions")
    assert response.status_code == 403  # or 401 depending on your auth setup


@pytest.mark.parametrize("invalid_auth_type", ["local", "invalid", ""])
def test_invalid_auth_type(authenticated_client, test_session, invalid_auth_type):
    """Test that invalid auth types are rejected"""
    intentions = {
        "items": [
            {
                "action": "add",
                "target_path": "/stories/-",
                "value": {
                    "key": "TEST-Invalid",
                    "title": "Invalid Auth Type Test",
                    "priority": "P1",
                    "auth_type": invalid_auth_type,  # Invalid value
                    "dependencies": [],
                },
                "reason": "Test invalid auth type",
            }
        ]
    }

    response = authenticated_client.post(
        f"/sessions/{test_session}/intents", json=intentions
    )
    # Should either reject the intention or patch proposal should fail
    if response.status_code == 200:
        intention_set_id = response.json()["intention_set_id"]
        patch_response = authenticated_client.post(
            f"/sessions/{test_session}/patch-proposals",
            json={"intention_set_id": intention_set_id},
        )
        # Patch proposal should fail due to validation
        assert patch_response.status_code != 200 or "error" in patch_response.json()
