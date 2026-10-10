"""Main AWS Lambda Handler for Rubber Duck.

Provides a serverless REST API behind Lambda Function URL with:
- POST /chat
- POST /rate
- GET /stats
- GET /health
Includes CORS handling, rate limiting, DynamoDB session tracking,
CloudWatch EMF custom metrics, and SSM Parameter Store key resolution.
"""

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional
import boto3

try:
    from agent import RubberDuckAgent
    from db import Database
    from llm_provider import GeminiProvider, MockLLMProvider
    import metrics
except ImportError:
    from backend.agent import RubberDuckAgent
    from backend.db import Database
    from backend.llm_provider import GeminiProvider, MockLLMProvider
    from backend import metrics


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global cached variables across warm invocations
_CACHED_API_KEY: Optional[str] = None
_DB: Optional[Database] = None
_LLM_PROVIDER: Optional[Any] = None


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key from environment variable or SSM Parameter Store."""
    global _CACHED_API_KEY
    if _CACHED_API_KEY:
        return _CACHED_API_KEY

    # Check env var first
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        _CACHED_API_KEY = key
        return key

    # Check SSM parameter store if specified
    ssm_param_name = os.environ.get("GEMINI_SSM_PARAM_NAME", "/rubber-duck/gemini-api-key")
    try:
        ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        resp = ssm.get_parameter(Name=ssm_param_name, WithDecryption=True)
        key = resp.get("Parameter", {}).get("Value", "")
        if key:
            _CACHED_API_KEY = key
            return key
    except Exception as e:
        logger.warning("Could not read SSM parameter %s: %s", ssm_param_name, e)

    return ""


def get_dependencies():
    """Lazily initialize and cache database and LLM provider."""
    global _DB, _LLM_PROVIDER
    if _DB is None:
        _DB = Database()

    if _LLM_PROVIDER is None:
        if os.environ.get("USE_MOCK_LLM", "").lower() == "true":
            _LLM_PROVIDER = MockLLMProvider()
        else:
            api_key = get_gemini_api_key()
            _LLM_PROVIDER = GeminiProvider(api_key=api_key)

    return _DB, _LLM_PROVIDER


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Build API response with full CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        },
        "body": json.dumps(body),
    }


def handle_options() -> Dict[str, Any]:
    """Handle preflight CORS requests."""
    return build_response(200, {"ok": True})


def handle_health() -> Dict[str, Any]:
    """Health check endpoint."""
    return build_response(200, {"status": "ok", "service": "Rubber Duck API", "version": "1.0.0"})


def handle_chat(event_body: Dict[str, Any], db: Database, llm_provider: Any) -> Dict[str, Any]:
    """Handle POST /chat conversation message."""
    session_id = event_body.get("session_id") or str(uuid.uuid4())
    message = event_body.get("message", "")

    # Retrieve existing session
    session = db.get_session(session_id)
    is_new_session = session is None

    # Check rate limit
    if not db.check_rate_limit(session):
        return build_response(
            429,
            {
                "error": "RATE_LIMIT",
                "message": "The duck is still pondering your last thought. Take a breath and try again.",
            },
        )

    # Initialize or load state
    history = session.get("history", []) if session else []
    question_count = session.get("question_count", 0) if session else 0
    hints_used = session.get("hints_used", 0) if session else 0
    current_streak = session.get("streak", 0) if session else 0
    show_me_used = session.get("show_me_used", False) if session else False
    created_at = session.get("created_at") if session else int(time.time())

    if is_new_session:
        metrics.record_session_started()
        db.record_new_session_stat()

    agent = RubberDuckAgent(llm_provider)
    result = agent.process_message(
        session_id=session_id,
        user_message=message,
        history=history,
        current_streak=current_streak,
        hints_used=hints_used,
        question_count=question_count,
        show_me_used=show_me_used,
    )

    # Append to history
    history.append({"role": "user", "content": message, "timestamp": int(time.time())})
    history.append({"role": "duck", "content": result["reply"], "timestamp": int(time.time())})

    # Record metrics on state transitions
    if result["state"] == "solved" and not (session and session.get("solved")):
        metrics.record_bug_solved(
            show_me_used=result["show_me_used"],
            question_count=result["question_count"],
        )
        db.record_solved_stat(
            show_me_used=result["show_me_used"],
            question_count=result["question_count"],
        )
    elif result["state"] == "hint" and result["hints_used"] > hints_used:
        metrics.record_hint_used()
    elif result["state"] == "revealed" and not show_me_used:
        metrics.record_show_me_used()

    # Save session back to DynamoDB
    db.save_session(
        session_id=session_id,
        history=history,
        question_count=result["question_count"],
        hints_used=result["hints_used"],
        state=result["state"],
        solved=(result["state"] == "solved" or (session and session.get("solved", False))),
        show_me_used=result["show_me_used"],
        streak=result["streak"],
        rating=session.get("rating") if session else None,
        created_at=created_at,
    )

    return build_response(
        200,
        {
            "session_id": session_id,
            "reply": result["reply"],
            "state": result["state"],
            "streak": result["streak"],
            "hints_used": result["hints_used"],
            "question_count": result["question_count"],
            "recap": result.get("recap"),
        },
    )


def handle_rate(event_body: Dict[str, Any], db: Database) -> Dict[str, Any]:
    """Handle POST /rate feedback rating."""
    session_id = event_body.get("session_id")
    rating = event_body.get("rating")

    if not session_id or rating not in ["up", "down"]:
        return build_response(
            400,
            {
                "error": "BAD_REQUEST",
                "message": "Quack? A valid session_id and rating ('up' or 'down') are required.",
            },
        )

    db.record_rating_stat(session_id, rating)
    metrics.record_rating(rating)

    return build_response(200, {"ok": True, "message": "Thank you for the feedback!"})


def handle_stats(db: Database) -> Dict[str, Any]:
    """Handle GET /stats live aggregates."""
    stats = db.get_stats()
    return build_response(200, stats)


def is_function_url_request(event: Optional[Dict[str, Any]]) -> bool:
    """Check if the invocation comes through an AWS Lambda Function URL."""
    if not event or not isinstance(event, dict):
        return False
    domain_name = event.get("requestContext", {}).get("domainName", "")
    return ".lambda-url." in domain_name or domain_name.endswith(".on.aws")


def sanitize_response(resp: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize response headers when invoked via Lambda Function URL.

    AWS Lambda Function URL provides built-in CORS handling configured via
    FunctionUrlConfig.Cors. If Lambda code also returns Access-Control-* headers,
    AWS Function URL delivers DUPLICATE CORS headers to the client. Modern browsers
    strictly reject multiple Access-Control-Allow-Origin headers with 'Failed to fetch'.
    """
    if is_function_url_request(event) and isinstance(resp, dict) and "headers" in resp:
        headers = dict(resp["headers"])
        headers.pop("Access-Control-Allow-Origin", None)
        headers.pop("Access-Control-Allow-Methods", None)
        headers.pop("Access-Control-Allow-Headers", None)
        resp["headers"] = headers
    return resp


def _process_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Internal event processor for HTTP requests."""
    # Handle CORS OPTIONS
    http_method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    ).upper()

    if http_method == "OPTIONS":
        return handle_options()

    raw_path = (
        event.get("rawPath")
        or event.get("path")
        or "/"
    )
    # Strip stage or trailing slash
    path = raw_path.rstrip("/")
    if not path:
        path = "/"

    db, llm_provider = get_dependencies()

    try:
        # Parse JSON body for POST requests
        body: Dict[str, Any] = {}
        if http_method == "POST":
            raw_body = event.get("body") or "{}"
            if event.get("isBase64Encoded"):
                import base64
                raw_body = base64.b64decode(raw_body).decode("utf-8")
            if isinstance(raw_body, str):
                body = json.loads(raw_body) if raw_body.strip() else {}
            elif isinstance(raw_body, dict):
                body = raw_body

        if path in ["/health", "", "/api/health", "/api"] or path.endswith("/health"):
            return handle_health()

        if (path.endswith("/chat") or path == "/api/chat") and http_method == "POST":
            return handle_chat(body, db, llm_provider)

        if (path.endswith("/rate") or path == "/api/rate") and http_method == "POST":
            return handle_rate(body, db)

        if (path.endswith("/stats") or path == "/api/stats") and http_method == "GET":
            return handle_stats(db)

        return build_response(
            404,
            {
                "error": "NOT_FOUND",
                "message": "Quack! This path does not exist in our pond.",
            },
        )

    except json.JSONDecodeError:
        return build_response(
            400,
            {
                "error": "BAD_REQUEST",
                "message": "Invalid JSON body provided.",
            },
        )
    except Exception as e:
        logger.exception("Unexpected error in lambda_handler: %s", e)
        return build_response(
            500,
            {
                "error": "SERVER_ERROR",
                "message": "The duck is taking a quick nap. Try again in a few seconds.",
            },
        )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point for Function URL or API Gateway."""
    resp = _process_event(event, context)
    return sanitize_response(resp, event)
