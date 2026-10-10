"""Unit tests for Lambda handler HTTP routing, CORS, and endpoint responses."""

import json
import boto3
from moto import mock_aws
import pytest
from backend import lambda_function
from backend.db import Database, SESSIONS_TABLE, STATS_TABLE
from backend.llm_provider import MockLLMProvider


@pytest.fixture(autouse=True)
def setup_backend_env(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("SESSIONS_TABLE", SESSIONS_TABLE)
    monkeypatch.setenv("STATS_TABLE", STATS_TABLE)


@pytest.fixture
def mock_aws_services():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName=SESSIONS_TABLE,
            KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb.create_table(
            TableName=STATS_TABLE,
            KeySchema=[{"AttributeName": "stat_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "stat_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Inject mock DB and mock LLM into handler
        lambda_function._DB = Database(dynamodb)
        lambda_function._LLM_PROVIDER = MockLLMProvider()
        yield


def test_cors_options_preflight():
    event = {
        "requestContext": {"http": {"method": "OPTIONS"}},
        "rawPath": "/chat",
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
    assert "POST" in resp["headers"]["Access-Control-Allow-Methods"]


def test_health_check():
    event = {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/health",
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"


def test_post_chat_flow(mock_aws_services):
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/chat",
        "body": json.dumps({
            "session_id": "test-session-1",
            "message": "TypeError: Cannot read properties of undefined (reading 'map')"
        }),
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["session_id"] == "test-session-1"
    assert body["state"] == "asking"
    assert body["question_count"] == 1
    assert "reply" in body


def test_post_rate_flow(mock_aws_services):
    # Rate a session
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/rate",
        "body": json.dumps({
            "session_id": "test-session-1",
            "rating": "up"
        }),
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True


def test_get_stats_endpoint(mock_aws_services):
    event = {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/stats",
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "total_sessions" in body
    assert "solved_without_show_me_pct" in body
    assert "avg_questions" in body


def test_not_found_endpoint():
    event = {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/nonexistent",
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert body["error"] == "NOT_FOUND"


def test_malformed_json_body():
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/chat",
        "body": "not-a-valid-json",
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body["error"] == "BAD_REQUEST"


def test_function_url_cors_deduplication():
    # Simulate an AWS Lambda Function URL event
    event = {
        "version": "2.0",
        "rawPath": "/health",
        "requestContext": {
            "domainName": "kfc3vyzesu6zggzpfgywr5rmhi0vdeqn.lambda-url.us-east-1.on.aws",
            "http": {"method": "GET"},
        },
    }
    resp = lambda_function.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    # Function URL response must NOT have Access-Control-* headers to avoid duplicates
    assert "Access-Control-Allow-Origin" not in resp["headers"]
    assert "Access-Control-Allow-Methods" not in resp["headers"]
    assert "Access-Control-Allow-Headers" not in resp["headers"]
    assert resp["headers"]["Content-Type"] == "application/json"

