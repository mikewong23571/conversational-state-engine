"""
End-to-end tests with real server - self-contained
"""

import pytest
import requests

# Mark all tests in this file as e2e tests
pytestmark = pytest.mark.e2e


def test_complete_user_flow_e2e(server_url, e2e_headers, e2e_session):
    """Test complete user workflow end-to-end with real server"""

    # Step 1: Verify initial state
    response = requests.get(
        f"{server_url}/sessions/{e2e_session}/state", headers=e2e_headers
    )
    assert response.status_code == 200
    initial_state = response.json()
    assert initial_state["version"] == "v1"
    assert len(initial_state["data"]["stories"]) == 0

    # Step 2: Create intention
    intentions = {
        "items": [
            {
                "action": "add",
                "target_path": "/stories/-",
                "value": {
                    "key": "E2E-Login",
                    "title": "E2E Login Test",
                    "priority": "P0",
                    "platform": ["Web"],
                    "acceptance_criteria": ["Login works"],
                    "dependencies": [],
                    "auth_type": "password",
                },
                "reason": "E2E test story",
                "confidence": 0.9,
            }
        ]
    }

    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/intents",
        json=intentions,
        headers=e2e_headers,
    )
    assert response.status_code == 200
    intention_set_id = response.json()["intention_set_id"]

    # Step 3: Generate patch proposal
    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/patch-proposals",
        json={"intention_set_id": intention_set_id},
        headers=e2e_headers,
    )
    assert response.status_code == 200
    proposal = response.json()
    proposal_id = proposal["proposal_id"]
    assert "impact_analysis" in proposal

    # Step 4: Progressive confirmation
    # Intent confirmation
    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/confirm-intent",
        json={"proposal_id": proposal_id},
        headers=e2e_headers,
    )
    assert response.status_code == 200

    # Changes confirmation
    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/confirm-changes",
        json={"proposal_id": proposal_id, "selected_patch_indices": [0]},
        headers=e2e_headers,
    )
    assert response.status_code == 200

    # Side effects confirmation
    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/confirm-side-effects",
        json={"proposal_id": proposal_id, "apply_auto_fixes": True},
        headers=e2e_headers,
    )
    assert response.status_code == 200

    # Step 5: Commit changes
    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/commit",
        json={"proposal_id": proposal_id, "message": "E2E test commit"},
        headers=e2e_headers,
    )
    assert response.status_code == 200
    commit_result = response.json()
    assert "commit_id" in commit_result
    assert commit_result["version"] == "v2"

    # Step 6: Verify final state
    response = requests.get(
        f"{server_url}/sessions/{e2e_session}/state", headers=e2e_headers
    )
    assert response.status_code == 200
    final_state = response.json()
    assert final_state["version"] == "v2"
    assert len(final_state["data"]["stories"]) == 1
    assert final_state["data"]["stories"][0]["key"] == "E2E-Login"


def test_server_health_e2e(server_url):
    """Test that server is healthy"""
    response = requests.get(f"{server_url}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_authentication_flow_e2e(server_url):
    """Test authentication flow"""
    # Test login
    response = requests.post(
        f"{server_url}/auth/login",
        json={"email": "test@example.com", "password": "test123"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert "token_type" in token_data

    # Test authenticated request
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    response = requests.post(f"{server_url}/sessions", headers=headers)
    assert response.status_code == 200

    # Test unauthenticated request
    response = requests.post(f"{server_url}/sessions")
    assert response.status_code in [401, 403]  # Should be rejected


def test_dependency_validation_e2e(server_url, e2e_headers, e2e_session):
    """Test dependency order validation"""
    intentions = {
        "items": [
            {
                "action": "add",
                "target_path": "/stories/-",
                "value": {
                    "key": "FEATURE-A",
                    "title": "Feature A",
                    "priority": "P0",
                    "dependencies": ["FEATURE-B"],
                },
            },
            {
                "action": "add",
                "target_path": "/stories/-",
                "value": {
                    "key": "FEATURE-B",
                    "title": "Feature B",
                    "priority": "P2",  # Lower priority than A
                },
            },
        ]
    }

    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/intents",
        json=intentions,
        headers=e2e_headers,
    )
    assert response.status_code == 200
    intention_set_id = response.json()["intention_set_id"]

    response = requests.post(
        f"{server_url}/sessions/{e2e_session}/patch-proposals",
        json={"intention_set_id": intention_set_id},
        headers=e2e_headers,
    )
    assert response.status_code == 200
    proposal = response.json()

    # Should detect dependency order conflict
    conflicts = proposal["impact_analysis"]["semantic_conflicts"]
    dep_conflicts = [c for c in conflicts if c["rule"] == "dependency_order"]
    assert len(dep_conflicts) > 0, "Should detect dependency priority issue"
