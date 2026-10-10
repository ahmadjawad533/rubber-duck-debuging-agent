"""Unit tests for Rubber Duck Agent logic, state transitions, and constraints."""

import pytest
from backend.agent import RubberDuckAgent
from backend.llm_provider import MockLLMProvider


def test_empty_message_asks_to_paste():
    agent = RubberDuckAgent(MockLLMProvider())
    res = agent.process_message(
        session_id="test-1",
        user_message="",
        history=[],
        current_streak=0,
        hints_used=0,
        question_count=0,
        show_me_used=False,
    )
    assert res["state"] == "asking"
    assert "Quack?" in res["reply"]
    assert res["question_count"] == 0


def test_oversized_message_handled():
    agent = RubberDuckAgent(MockLLMProvider())
    long_msg = "x" * 5000
    res = agent.process_message(
        session_id="test-1",
        user_message=long_msg,
        history=[],
        current_streak=0,
        hints_used=0,
        question_count=0,
        show_me_used=False,
    )
    assert res["state"] == "asking"
    assert "massive snippet" in res["reply"]


def test_standard_question_increments_question_count():
    mock_provider = MockLLMProvider({
        "reply": "What is the value of variable 'user' on line 14?",
        "state": "asking",
        "recap": None,
    })
    agent = RubberDuckAgent(mock_provider)
    res = agent.process_message(
        session_id="test-1",
        user_message="TypeError: Cannot read properties of undefined",
        history=[],
        current_streak=2,
        hints_used=0,
        question_count=1,
        show_me_used=False,
    )
    assert res["state"] == "asking"
    assert res["question_count"] == 2
    assert res["streak"] == 2
    assert len(res["reply"].split()) <= 60


def test_hint_command_increments_hints_used_and_does_not_give_fix():
    mock_provider = MockLLMProvider({
        "reply": "Check line 42. Is the array guaranteed to have at least one element?",
        "state": "hint",
        "recap": None,
    })
    agent = RubberDuckAgent(mock_provider)
    res = agent.process_message(
        session_id="test-1",
        user_message="hint",
        history=[{"role": "user", "content": "list index out of range"}],
        current_streak=0,
        hints_used=0,
        question_count=1,
        show_me_used=False,
    )
    assert res["state"] == "hint"
    assert res["hints_used"] == 1
    assert res["show_me_used"] is False


def test_show_me_command_reveals_fix_and_marks_flag():
    mock_provider = MockLLMProvider({
        "reply": "Here is the fix: check if list is empty with `if not items: return` before indexing.",
        "state": "revealed",
        "recap": None,
    })
    agent = RubberDuckAgent(mock_provider)
    res = agent.process_message(
        session_id="test-1",
        user_message="show me",
        history=[],
        current_streak=1,
        hints_used=1,
        question_count=2,
        show_me_used=False,
    )
    assert res["state"] == "revealed"
    assert res["show_me_used"] is True
    assert res["streak"] == 1  # Streak should not increment


def test_solved_phrase_increments_streak_only_if_show_me_not_used():
    mock_provider = MockLLMProvider({
        "reply": "Quack! You tracked it down yourself. Excellent work.",
        "state": "solved",
        "recap": "Always check bounds before indexing into lists.",
    })
    agent = RubberDuckAgent(mock_provider)

    # Case 1: Solved WITHOUT show me -> streak increases!
    res1 = agent.process_message(
        session_id="test-1",
        user_message="I found it! The array was empty.",
        history=[],
        current_streak=3,
        hints_used=1,
        question_count=2,
        show_me_used=False,
    )
    assert res1["state"] == "solved"
    assert res1["streak"] == 4
    assert res1["recap"] == "Always check bounds before indexing into lists."

    # Case 2: Solved WITH show me -> streak does NOT increase
    res2 = agent.process_message(
        session_id="test-1",
        user_message="I fixed it using your suggestion.",
        history=[],
        current_streak=3,
        hints_used=1,
        question_count=2,
        show_me_used=True,
    )
    assert res2["state"] == "solved"
    assert res2["streak"] == 3


def test_word_count_enforcement():
    # Provide a wordy reply (>65 words) and ensure agent truncates
    wordy_text = "word " * 80
    mock_provider = MockLLMProvider({
        "reply": wordy_text,
        "state": "asking",
        "recap": None,
    })
    agent = RubberDuckAgent(mock_provider)
    res = agent.process_message(
        session_id="test-1",
        user_message="debug me",
        history=[],
        current_streak=0,
        hints_used=0,
        question_count=0,
        show_me_used=False,
    )
    assert len(res["reply"].split()) <= 65
