"""Unit tests for DynamoDB operations, TTL, rate limiting, and stats."""

import time
import boto3
from moto import mock_aws
import pytest
from backend.db import Database, SESSIONS_TABLE, STATS_TABLE


@pytest.fixture
def mock_dynamodb():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Create Sessions table
        dynamodb.create_table(
            TableName=SESSIONS_TABLE,
            KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Create Stats table
        dynamodb.create_table(
            TableName=STATS_TABLE,
            KeySchema=[{"AttributeName": "stat_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "stat_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb


def test_session_lifecycle(mock_dynamodb):
    db = Database(mock_dynamodb)
    session_id = "sess-123"

    # Initially empty
    assert db.get_session(session_id) is None

    # Save session
    saved = db.save_session(
        session_id=session_id,
        history=[{"role": "user", "content": "hi"}],
        question_count=1,
        hints_used=0,
        state="asking",
        solved=False,
        show_me_used=False,
        streak=0,
    )
    assert saved["session_id"] == session_id
    assert saved["ttl"] > time.time()

    # Retrieve session
    fetched = db.get_session(session_id)
    assert fetched is not None
    assert fetched["question_count"] == 1
    assert fetched["history"][0]["content"] == "hi"


def test_history_capping(mock_dynamodb):
    db = Database(mock_dynamodb)
    session_id = "sess-cap"

    # Create history with 25 items
    long_history = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
    saved = db.save_session(
        session_id=session_id,
        history=long_history,
        question_count=10,
        hints_used=1,
        state="asking",
        solved=False,
        show_me_used=False,
        streak=1,
    )
    # Should cap at 20
    assert len(saved["history"]) == 20
    assert saved["history"][0]["content"] == "msg 5"


def test_rate_limiting(mock_dynamodb):
    db = Database(mock_dynamodb)
    now = int(time.time())

    # None session should pass
    assert db.check_rate_limit(None) is True

    # Very recent session should fail rate limit (< 1s)
    recent_session = {"updated_at": now}
    assert db.check_rate_limit(recent_session) is False

    # Older session should pass
    old_session = {"updated_at": now - 5}
    assert db.check_rate_limit(old_session) is True


def test_stats_aggregation_and_rating(mock_dynamodb):
    db = Database(mock_dynamodb)

    # Initially empty stats
    stats = db.get_stats()
    assert stats["total_sessions"] == 0
    assert stats["bugs_solved"] == 0
    assert stats["solved_without_show_me_pct"] == 100.0

    # Record sessions and solved bugs
    db.record_new_session_stat()
    db.record_new_session_stat()
    db.record_solved_stat(show_me_used=False, question_count=3)
    db.record_solved_stat(show_me_used=True, question_count=5)

    stats = db.get_stats()
    assert stats["total_sessions"] == 2
    assert stats["bugs_solved"] == 2
    assert stats["solved_without_show_me"] == 1
    assert stats["solved_without_show_me_pct"] == 50.0
    assert stats["avg_questions"] == 4.0

    # Save a session first to record rating
    db.save_session(
        session_id="rate-test",
        history=[],
        question_count=1,
        hints_used=0,
        state="solved",
        solved=True,
        show_me_used=False,
        streak=1,
    )
    db.record_rating_stat("rate-test", "up")
    stats = db.get_stats()
    assert stats["total_ratings"] == 1
    assert stats["positive_ratings"] == 1
    assert stats["thumbs_up_pct"] == 100.0
