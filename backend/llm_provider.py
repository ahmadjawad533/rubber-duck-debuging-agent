"""LLM Provider abstraction and Google Gemini implementation.

Provides a clean interface allowing the LLM engine to be swapped
(e.g., Gemini, Amazon Bedrock, or Mock) without altering agent logic.
Zero external dependencies: uses Python standard library urllib.request.
"""

from abc import ABC, abstractmethod
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_instruction: str,
        history: List[Dict[str, str]],
        user_message: str,
    ) -> Dict[str, Any]:
        """Generate a response given history and the new user message.

        Returns a dictionary expected to contain:
          - reply: str (short, under 60 words)
          - state: 'asking' | 'hint' | 'solved' | 'revealed'
          - recap: Optional[str] (present if state == 'solved')
        """
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini API provider using plain HTTPS (urllib.request).

    Keeps the Lambda deployment zip minimal (<30KB) and avoids arm64 wheel compilation.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = (
            model
            or os.environ.get("GEMINI_MODEL")
            or os.environ.get("GEMINI_MODEL_NAME")
            or self.DEFAULT_MODEL
        )
        self.endpoint_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    def generate(
        self,
        system_instruction: str,
        history: List[Dict[str, str]],
        user_message: str,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        # Build contents array from history + new user message
        contents: List[Dict[str, Any]] = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        contents.append({"role": "user", "parts": [{"text": user_message}]})

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.4,
                "maxOutputTokens": 300,
            },
        }

        url = f"{self.endpoint_url}?key={self.api_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_body = resp.read().decode("utf-8")
                parsed = json.loads(resp_body)
                candidates = parsed.get("candidates", [])
                if not candidates:
                    raise RuntimeError("No candidates returned from Gemini.")

                raw_text = candidates[0]["content"]["parts"][0]["text"]
                return self._parse_json_response(raw_text)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            logger.error("Gemini API HTTP %d: %s", e.code, err_body)
            raise RuntimeError(f"Gemini API returned HTTP {e.code}") from e
        except urllib.error.URLError as e:
            logger.error("Gemini API connection error: %s", e.reason)
            raise RuntimeError(f"Failed to connect to Gemini API: {e.reason}") from e

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parse structured JSON response with regex fallbacks."""
        cleaned = text.strip()
        # Remove potential markdown code fences ```json ... ```
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            res = json.loads(cleaned)
            if isinstance(res, dict) and "reply" in res:
                return res
        except json.JSONDecodeError:
            pass

        # Try finding the first JSON object using regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                res = json.loads(match.group(0))
                if isinstance(res, dict) and "reply" in res:
                    return res
            except json.JSONDecodeError:
                pass

        # Fallback if structure is malformed
        logger.warning("Could not parse structured JSON from LLM: %s", text)
        return {
            "reply": cleaned[:180] if cleaned else "Quack. What line does the stack trace point to?",
            "state": "asking",
            "recap": None,
        }


class MockLLMProvider(LLMProvider):
    """Mock LLM Provider for unit testing and offline development."""

    def __init__(self, canned_response: Optional[Dict[str, Any]] = None):
        self.canned_response = canned_response

    def generate(
        self,
        system_instruction: str,
        history: List[Dict[str, str]],
        user_message: str,
    ) -> Dict[str, Any]:
        if self.canned_response:
            return self.canned_response

        lower = user_message.strip().lower()
        if "show me" in lower:
            return {
                "reply": "Here is the fix: check if the variable is None before calling .get(). Add `if obj is not None:`.",
                "state": "revealed",
                "recap": None,
            }
        elif "hint" in lower:
            return {
                "reply": "Notice what happens when the list is empty on line 42. What value does pop() return?",
                "state": "hint",
                "recap": None,
            }
        elif any(w in lower for idx, w in enumerate(["solved", "found it", "i fixed it", "working now", "i got it"])):
            return {
                "reply": "Quack! You nailed it.",
                "state": "solved",
                "recap": "Always check for undefined before accessing nested object properties.",
            }
        else:
            return {
                "reply": "What is the exact type of that variable right before line 12 executes?",
                "state": "asking",
                "recap": None,
            }
