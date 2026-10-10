"""WSGI entrypoint for Vercel Python runtime.

Wraps the Lambda handler so the backend runs seamlessly on Vercel Services
as well as AWS Lambda.
"""

from typing import Callable, Iterable, List, Tuple

try:
    from lambda_function import lambda_handler
except ImportError:
    from backend.lambda_function import lambda_handler


def app(environ: dict, start_response: Callable[[str, List[Tuple[str, str]]], None]) -> Iterable[bytes]:
    """Standard WSGI entrypoint conforming to PEP 3333."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")

    # Read request body if present
    try:
        content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
    except (ValueError, TypeError):
        content_length = 0

    body = ""
    if content_length > 0 and "wsgi.input" in environ:
        body = environ["wsgi.input"].read(content_length).decode("utf-8")

    # Build Lambda-compatible event dictionary
    headers = {
        k[5:].replace("_", "-").lower(): v
        for k, v in environ.items()
        if k.startswith("HTTP_")
    }
    if "CONTENT_TYPE" in environ:
        headers["content-type"] = environ["CONTENT_TYPE"]

    event = {
        "httpMethod": method,
        "path": path,
        "rawPath": path,
        "body": body,
        "headers": headers,
        "requestContext": {
            "http": {
                "method": method,
                "path": path,
            }
        },
    }

    resp = lambda_handler(event, None)

    status_code = resp.get("statusCode", 200)
    status_phrase = {
        200: "200 OK",
        400: "400 Bad Request",
        404: "404 Not Found",
        429: "429 Too Many Requests",
        500: "500 Internal Server Error",
    }.get(status_code, f"{status_code} Status")

    response_headers = list(resp.get("headers", {}).items())
    start_response(status_phrase, response_headers)

    body_bytes = resp.get("body", "").encode("utf-8")
    return [body_bytes]


# Expose handler alias for Vercel functions compatibility
handler = app
