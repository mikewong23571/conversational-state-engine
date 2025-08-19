"""
E2E test configuration with self-contained server setup
"""

import os
import signal
import socket
import subprocess
import time
from contextlib import contextmanager

import pytest
import requests


def find_free_port():
    """Find a free port for the test server"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@contextmanager
def test_server():
    """Start a test server in a subprocess"""
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Start server process
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "server.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",  # Reduce noise in test output
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # Create new process group for cleanup
    )

    # Wait for server to start
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            time.sleep(0.1)
    else:
        process.terminate()
        raise RuntimeError("Test server failed to start")

    try:
        yield base_url
    finally:
        # Clean shutdown
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


@pytest.fixture(scope="module")
def server_url():
    """Module-scoped test server for E2E tests"""
    with test_server() as url:
        yield url


@pytest.fixture(scope="module")
def e2e_auth_token(server_url):
    """Get authentication token for E2E tests"""
    response = requests.post(
        f"{server_url}/auth/login",
        json={"email": "test@example.com", "password": "test123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def e2e_headers(e2e_auth_token):
    """Authentication headers for E2E tests"""
    return {"Authorization": f"Bearer {e2e_auth_token}"}


@pytest.fixture
def e2e_session(server_url, e2e_headers):
    """Create a fresh session for each E2E test"""
    response = requests.post(f"{server_url}/sessions", headers=e2e_headers)
    assert response.status_code == 200
    return response.json()["session_id"]
