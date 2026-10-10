"""Unit tests for GeminiProvider JSON parsing, thinkingConfig, and truncated output recovery."""

import json
import socket
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from backend.llm_provider import GeminiProvider, ModelBusyError


def test_thinking_config_generation():
    provider_38 = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    assert provider_38._get_thinking_config() == {"thinkingLevel": "low"}

    provider_37 = GeminiProvider(api_key="test-key", model="gemini-3.7-flash")
    assert provider_37._get_thinking_config() == {"thinkingLevel": "low"}

    provider_25 = GeminiProvider(api_key="test-key", model="gemini-2.5-flash")
    assert provider_25._get_thinking_config() == {"thinkingBudget": 0}


def test_truncated_json_extracts_reply():
    provider = GeminiProvider(api_key="test-key")
    # Truncated JSON case where closing quote and brace were cut off
    truncated_text = '{\n  "reply": "What is the length of items before line 42?'
    result = provider._parse_json_response(truncated_text)

    assert result["state"] == "asking"
    assert result["reply"] == "What is the length of items before line 42?"
    assert not result["reply"].startswith("{")
    assert '"reply":' not in result["reply"]


def test_truncated_json_with_unclosed_quote_and_state():
    provider = GeminiProvider(api_key="test-key")
    # Truncated JSON with unclosed quote and state cut off
    raw_text = '{"reply": "Does the variable hold None at that point?", "state": "hint'
    result = provider._parse_json_response(raw_text)

    assert result["reply"] == "Does the variable hold None at that point?"
    assert result["state"] == "hint"


def test_corrupted_json_never_returns_raw_json():
    provider = GeminiProvider(api_key="test-key")
    # Corrupted JSON cases
    bad_inputs = [
        '{\n  "reply": ',
        '{\n  "reply": "',
        '{malformed JSON without keys',
        '{\n  "random_key": "some value"',
        '{"other": 123}',
        '',
    ]

    for bad in bad_inputs:
        result = provider._parse_json_response(bad)
        assert result["state"] == "asking"
        assert "Quack" in result["reply"]
        assert not result["reply"].startswith("{")
        assert not result["reply"].endswith("}")
        assert '"reply":' not in result["reply"]


def test_valid_json_parses_properly():
    provider = GeminiProvider(api_key="test-key")
    valid_text = '{"reply": "What is the value of x?", "state": "asking", "recap": null}'
    result = provider._parse_json_response(valid_text)

    assert result["reply"] == "What is the value of x?"
    assert result["state"] == "asking"
    assert result["recap"] is None


def test_max_tokens_triggers_retry():
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")

    # First response returns finishReason = MAX_TOKENS with truncated output
    resp_max_tokens = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{\n  "reply": "What is the'}]
                },
                "finishReason": "MAX_TOKENS",
            }
        ]
    }

    # Second response returns full output
    resp_success = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"reply": "What is the type of that variable on line 12?", "state": "asking"}'}]
                },
                "finishReason": "STOP",
            }
        ]
    }

    call_count = 0
    captured_payloads = []

    def mock_execute(payload):
        nonlocal call_count
        call_count += 1
        captured_payloads.append(json.loads(json.dumps(payload)))
        if call_count == 1:
            return resp_max_tokens
        return resp_success

    provider._execute_api_call = mock_execute

    result = provider.generate(
        system_instruction="duck instructions",
        history=[],
        user_message="TypeError on line 12",
    )

    # Verify retry happened
    assert call_count == 2
    # First payload had maxOutputTokens = 1024
    assert captured_payloads[0]["generationConfig"]["maxOutputTokens"] == 1024
    # Second payload had maxOutputTokens = 2048
    assert captured_payloads[1]["generationConfig"]["maxOutputTokens"] == 2048
    # Successfully parsed output
    assert result["reply"] == "What is the type of that variable on line 12?"
    assert result["state"] == "asking"


def test_timeout_and_retries_constants():
    provider = GeminiProvider(api_key="test-key")
    assert provider.URLOPEN_TIMEOUT == 12.0
    assert provider.MAX_RETRIES == 2
    assert provider.TOTAL_DEADLINE_SECONDS == 20.0
    assert provider.DEFAULT_FALLBACK_MODEL == "gemini-3.5-flash-lite"


@patch("time.sleep")
def test_retry_on_503_success(mock_sleep):
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    call_count = 0

    resp_success = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"reply": "What did you expect here?", "state": "asking"}'}]},
                "finishReason": "STOP",
            }
        ]
    }

    def mock_execute(payload, timeout=12.0):
        nonlocal call_count
        call_count += 1
        assert timeout <= 12.0
        if call_count == 1:
            raise urllib.error.HTTPError("http://gemini", 503, "High Demand", {}, None)
        return resp_success

    provider._execute_api_call = mock_execute

    result = provider.generate(
        system_instruction="duck instructions",
        history=[],
        user_message="Bug on line 5",
    )

    assert call_count == 2
    assert mock_sleep.called
    assert result["reply"] == "What did you expect here?"
    assert result["state"] == "asking"


@patch("time.sleep")
def test_retry_on_timeout_success(mock_sleep):
    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    call_count = 0

    resp_success = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"reply": "Did the function return yet?", "state": "asking"}'}]},
                "finishReason": "STOP",
            }
        ]
    }

    def mock_execute(payload, timeout=12.0):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise socket.timeout("Read timed out")
        return resp_success

    provider._execute_api_call = mock_execute

    result = provider.generate(
        system_instruction="duck instructions",
        history=[],
        user_message="It hangs",
    )

    assert call_count == 2
    assert mock_sleep.called
    assert result["reply"] == "Did the function return yet?"


@patch("time.sleep")
def test_fallback_to_secondary_model_on_503(mock_sleep):
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.8-flash",
        fallback_model="gemini-3.5-flash-lite",
    )
    models_called = []

    resp_fallback_success = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"reply": "From fallback duck: check line 10.", "state": "hint"}'}]},
                "finishReason": "STOP",
            }
        ]
    }

    def mock_execute(payload, timeout=12.0):
        models_called.append(provider.model)
        if provider.model == "gemini-3.8-flash":
            raise urllib.error.HTTPError("http://gemini", 503, "High demand", {}, None)
        return resp_fallback_success

    provider._execute_api_call = mock_execute

    result = provider.generate(
        system_instruction="duck instructions",
        history=[],
        user_message="hint",
    )

    # Primary model called 3 times (1 initial + 2 retries)
    assert models_called.count("gemini-3.8-flash") == 3
    # Fallback model was tried and succeeded
    assert "gemini-3.5-flash-lite" in models_called
    assert result["reply"] == "From fallback duck: check line 10."
    assert result["state"] == "hint"


@patch("time.sleep")
def test_fallback_to_secondary_model_on_timeout(mock_sleep):
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.8-flash",
        fallback_model="gemini-3.5-flash-lite",
    )
    models_called = []

    resp_fallback_success = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"reply": "Check the loop condition.", "state": "asking"}'}]},
                "finishReason": "STOP",
            }
        ]
    }

    def mock_execute(payload, timeout=12.0):
        models_called.append(provider.model)
        if provider.model == "gemini-3.8-flash":
            raise TimeoutError("Socket timeout")
        return resp_fallback_success

    provider._execute_api_call = mock_execute

    result = provider.generate(
        system_instruction="duck instructions",
        history=[],
        user_message="infinite loop",
    )

    assert models_called.count("gemini-3.8-flash") == 3
    assert "gemini-3.5-flash-lite" in models_called
    assert result["reply"] == "Check the loop condition."


@patch("time.sleep")
def test_all_models_fail_raises_model_busy_error(mock_sleep):
    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-3.8-flash",
        fallback_model="gemini-3.5-flash-lite",
    )

    def mock_execute(payload, timeout=12.0):
        raise urllib.error.HTTPError("http://gemini", 503, "High demand on all models", {}, None)

    provider._execute_api_call = mock_execute

    with pytest.raises(ModelBusyError) as exc_info:
        provider.generate(
            system_instruction="duck instructions",
            history=[],
            user_message="Cannot connect",
        )

    assert "experiencing high demand" in str(exc_info.value)

