"""CloudWatch Embedded Metric Format (EMF) helper.

Emits structured JSON to stdout so CloudWatch automatically extracts
custom metrics (SessionsStarted, BugsSolved, HintsUsed, ShowMeUsed, Ratings)
without extra API calls or latency, fully within the AWS Free Tier.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

NAMESPACE = os.environ.get("METRICS_NAMESPACE", "RubberDuck")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "Production")


def emit_emf_metric(
    metric_definitions: List[Dict[str, str]],
    values: Dict[str, Any],
    dimensions: Optional[Dict[str, str]] = None,
) -> None:
    """Emit an Embedded Metric Format JSON payload to standard output."""
    dims = dimensions or {"Environment": ENVIRONMENT}
    dim_keys = list(dims.keys())

    emf_payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": NAMESPACE,
                    "Dimensions": [dim_keys],
                    "Metrics": metric_definitions,
                }
            ],
        },
        **dims,
        **values,
    }

    # EMF logs must be printed as a single line JSON string to stdout
    print(json.dumps(emf_payload), file=sys.stdout, flush=True)


def record_session_started() -> None:
    """Record a newly initiated debugging session."""
    emit_emf_metric(
        metric_definitions=[{"Name": "SessionsStarted", "Unit": "Count"}],
        values={"SessionsStarted": 1},
    )


def record_bug_solved(show_me_used: bool, question_count: int) -> None:
    """Record that a bug was resolved."""
    metrics = [
        {"Name": "BugsSolved", "Unit": "Count"},
        {"Name": "QuestionsToSolve", "Unit": "Count"},
    ]
    values: Dict[str, Any] = {
        "BugsSolved": 1,
        "QuestionsToSolve": question_count,
    }
    if not show_me_used:
        metrics.append({"Name": "SolvedWithoutFix", "Unit": "Count"})
        values["SolvedWithoutFix"] = 1

    emit_emf_metric(metric_definitions=metrics, values=values)


def record_hint_used() -> None:
    """Record that the user requested a hint."""
    emit_emf_metric(
        metric_definitions=[{"Name": "HintsUsed", "Unit": "Count"}],
        values={"HintsUsed": 1},
    )


def record_show_me_used() -> None:
    """Record that the user asked to see the full solution."""
    emit_emf_metric(
        metric_definitions=[{"Name": "ShowMeUsed", "Unit": "Count"}],
        values={"ShowMeUsed": 1},
    )


def record_rating(rating: str) -> None:
    """Record a user thumbs up/down rating."""
    metric_name = "RatingPositive" if rating == "up" else "RatingNegative"
    emit_emf_metric(
        metric_definitions=[
            {"Name": "RatingsSubmitted", "Unit": "Count"},
            {"Name": metric_name, "Unit": "Count"},
        ],
        values={"RatingsSubmitted": 1, metric_name: 1},
    )
