"""Unit tests for WSGI app.py entrypoint for Vercel Python runtime."""

from io import BytesIO
import json
import pytest
from backend.app import app


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    from backend import lambda_function
    lambda_function._LLM_PROVIDER = None




def test_wsgi_health_endpoint():
    status_captured = []
    headers_captured = []

    def mock_start_response(status, headers):
        status_captured.append(status)
        headers_captured.append(headers)

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/health",
        "wsgi.input": BytesIO(b""),
        "CONTENT_LENGTH": "0",
    }

    body_chunks = app(environ, mock_start_response)
    body_str = b"".join(body_chunks).decode("utf-8")
    data = json.loads(body_str)

    assert status_captured[0] == "200 OK"
    assert data["status"] == "ok"


def test_wsgi_post_chat_endpoint():
    status_captured = []
    headers_captured = []

    def mock_start_response(status, headers):
        status_captured.append(status)
        headers_captured.append(headers)

    payload = json.dumps({"session_id": "wsgi-test", "message": "IndexError: list index"}).encode("utf-8")

    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/chat",
        "wsgi.input": BytesIO(payload),
        "CONTENT_LENGTH": str(len(payload)),
        "CONTENT_TYPE": "application/json",
    }

    body_chunks = app(environ, mock_start_response)
    body_str = b"".join(body_chunks).decode("utf-8")
    data = json.loads(body_str)

    assert status_captured[0] == "200 OK"
    assert data["session_id"] == "wsgi-test"
    assert data["state"] == "asking"
