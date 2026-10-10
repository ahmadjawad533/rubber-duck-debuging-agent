"""Unit tests for GeminiProvider JSON parsing, thinkingConfig, and truncated output recovery."""

import json
from unittest.mock import MagicMock, patch
import pytest
from backend.llm_provider import GeminiProvider


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
