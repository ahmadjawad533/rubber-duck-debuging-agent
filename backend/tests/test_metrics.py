"""Unit tests for CloudWatch Embedded Metric Format (EMF)."""

import json
from io import StringIO
import sys
from backend import metrics


def test_emf_structure(monkeypatch):
    captured_output = StringIO()
    monkeypatch.setattr(sys, "stdout", captured_output)

    metrics.record_bug_solved(show_me_used=False, question_count=4)

    raw_output = captured_output.getvalue().strip()
    assert raw_output, "No output was written to stdout"

    payload = json.loads(raw_output)
    assert "_aws" in payload
    cw = payload["_aws"]["CloudWatchMetrics"][0]
    assert cw["Namespace"] == "RubberDuck"
    assert "Environment" in cw["Dimensions"][0]
    metric_names = [m["Name"] for m in cw["Metrics"]]
    assert "BugsSolved" in metric_names
    assert "SolvedWithoutFix" in metric_names
    assert "QuestionsToSolve" in metric_names
    assert payload["BugsSolved"] == 1
    assert payload["SolvedWithoutFix"] == 1
    assert payload["QuestionsToSolve"] == 4
