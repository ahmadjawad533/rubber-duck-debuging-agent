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
    DEFAULT_FALLBACK_REPLY = "Quack. What line does the stack trace point to?"

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

    def _get_thinking_config(self) -> Dict[str, Any]:
        """Build thinkingConfig to minimize or disable thinking based on model family."""
        model_lower = self.model.lower()
        if "gemini-3" in model_lower:
            # Gemini 3.8 & 3.7 Flash support 'low' to minimize latency and token consumption
            return {"thinkingLevel": "low"}
        else:
            # Gemini 2.5 Flash / Flash Lite: thinkingBudget=0 disables thinking
            return {"thinkingBudget": 0}

    def _execute_api_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTPS request to Gemini generateContent endpoint."""
        url = f"{self.endpoint_url}?key={self.api_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            logger.error("Gemini API HTTP %d: %s", e.code, err_body)
            raise RuntimeError(f"Gemini API returned HTTP {e.code}") from e
        except urllib.error.URLError as e:
            logger.error("Gemini API connection error: %s", e.reason)
            raise RuntimeError(f"Failed to connect to Gemini API: {e.reason}") from e

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

        # responseSchema ensures structured JSON containing {reply, state, recap}
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "reply": {
                    "type": "STRING",
                    "description": "Exactly one short debugging question, hint, or celebration under 60 words",
                },
                "state": {
                    "type": "STRING",
                    "enum": ["asking", "hint", "solved", "revealed"],
                    "description": "Current conversation state",
                },
                "recap": {
                    "type": "STRING",
                    "nullable": True,
                    "description": "One-sentence recap if solved, otherwise null",
                },
            },
            "required": ["reply", "state"],
        }

        generation_config: Dict[str, Any] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "temperature": 0.4,
            "maxOutputTokens": 1024,
            "thinkingConfig": self._get_thinking_config(),
        }

        payload: Dict[str, Any] = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "generationConfig": generation_config,
        }

        parsed = self._execute_api_call(payload)
        candidates = parsed.get("candidates", [])
        if not candidates:
            raise RuntimeError("No candidates returned from Gemini.")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")

        # Check finishReason: if MAX_TOKENS, retry once with a higher limit
        if finish_reason == "MAX_TOKENS":
            logger.warning("Gemini finishReason was MAX_TOKENS. Retrying once with maxOutputTokens=2048...")
            payload["generationConfig"]["maxOutputTokens"] = 2048
            retry_parsed = self._execute_api_call(payload)
            retry_candidates = retry_parsed.get("candidates", [])
            if retry_candidates:
                candidate = retry_candidates[0]

        parts = candidate.get("content", {}).get("parts", [])
        raw_text = parts[0].get("text", "") if parts else ""
        return self._parse_json_response(raw_text)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parse structured JSON response with regex fallbacks.

        Guarantees that raw JSON syntax or corrupted brackets are NEVER returned
        to the end-user.
        """
        cleaned = text.strip()
        # Remove potential markdown code fences ```json ... ```
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # 1. Attempt standard JSON parsing
        try:
            res = json.loads(cleaned)
            if isinstance(res, dict) and "reply" in res:
                reply_val = str(res["reply"]).strip()
                if reply_val and not reply_val.startswith("{"):
                    return {
                        "reply": reply_val,
                        "state": res.get("state", "asking") if res.get("state") in ["asking", "hint", "solved", "revealed"] else "asking",
                        "recap": res.get("recap"),
                    }
        except json.JSONDecodeError:
            pass

        # 2. Try finding the first complete JSON object using regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                res = json.loads(match.group(0))
                if isinstance(res, dict) and "reply" in res:
                    reply_val = str(res["reply"]).strip()
                    if reply_val and not reply_val.startswith("{"):
                        return {
                            "reply": reply_val,
                            "state": res.get("state", "asking") if res.get("state") in ["asking", "hint", "solved", "revealed"] else "asking",
                            "recap": res.get("recap"),
                        }
            except json.JSONDecodeError:
                pass

        # 3. Extract the reply text if JSON was cut off/truncated
        # Handles e.g. '{\n "reply": "What is the length of' or '{"reply": "Check line 42", "state":'
        reply_match = re.search(r'"reply"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)', cleaned)
        if reply_match:
            extracted = reply_match.group(1).strip()
            # Clean up escape sequences if needed
            try:
                extracted = extracted.encode().decode("unicode-escape")
            except Exception:
                pass
            extracted = extracted.strip()

            # Extract state if present (even if closing quote was truncated)
            state_match = re.search(r'"state"\s*:\s*"([^",\s}]+)"?', cleaned)
            extracted_state = state_match.group(1).strip() if state_match else "asking"
            if extracted_state not in ["asking", "hint", "solved", "revealed"]:
                extracted_state = "asking"


            # Ensure extracted text does not look like raw JSON syntax
            if extracted and not any(extracted.startswith(c) for c in ["{", "}", "[", "]", ":"]):
                logger.info("Extracted partial reply from truncated JSON: %s", extracted)
                return {
                    "reply": extracted,
                    "state": extracted_state,
                    "recap": None,
                }

        # 4. Fallback: NEVER return raw JSON text to the user.
        logger.warning("Could not safely parse JSON from LLM: %r", text)
        return {
            "reply": self.DEFAULT_FALLBACK_REPLY,
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
