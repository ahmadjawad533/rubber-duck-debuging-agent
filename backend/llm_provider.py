"""LLM Provider abstraction and Google Gemini implementation.

Provides a clean interface allowing the LLM engine to be swapped
(e.g., Gemini, Amazon Bedrock, or Mock) without altering agent logic.
Zero external dependencies: uses Python standard library urllib.request.
"""

from abc import ABC, abstractmethod
import json
import logging
import os
import random
import re
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelBusyError(Exception):
    """Raised when all Gemini attempts (including retries and fallback models) fail due to 429, 500, 503, or timeouts."""
    pass


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

    Features:
    - 12s per-request timeout (strictly under Lambda timeout)
    - Up to 2 retries on 429, 500, 503, and timeouts with exponential backoff and jitter
    - Total deadline enforcement (~20s)
    - Fallback model support (GEMINI_FALLBACK_MODEL)
    - Raises ModelBusyError on persistent failure
    """

    DEFAULT_PRIMARY_MODEL = "gemini-3.8-flash"
    DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash-lite"
    DEFAULT_FALLBACK_REPLY = "Quack. What line does the stack trace point to?"
    URLOPEN_TIMEOUT = 12.0
    MAX_RETRIES = 2
    TOTAL_DEADLINE_SECONDS = 20.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.primary_model = (
            model
            or os.environ.get("GEMINI_MODEL")
            or os.environ.get("GEMINI_MODEL_NAME")
            or self.DEFAULT_PRIMARY_MODEL
        )
        self.fallback_model = (
            fallback_model
            or os.environ.get("GEMINI_FALLBACK_MODEL")
            or self.DEFAULT_FALLBACK_MODEL
        )
        self.model = self.primary_model

    @property
    def endpoint_url(self) -> str:
        return self._get_endpoint_url(self.model)

    def _get_endpoint_url(self, model_name: Optional[str] = None) -> str:
        target = (model_name or self.model).replace("models/", "")
        return f"https://generativelanguage.googleapis.com/v1beta/models/{target}:generateContent"

    def _get_thinking_config(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Build thinkingConfig to minimize or disable thinking based on model family."""
        target = model_name or self.model
        model_lower = target.lower()
        if "gemini-3" in model_lower:
            # Gemini 3.x Flash models support 'low' to minimize latency and token consumption
            return {"thinkingLevel": "low"}
        else:
            # Gemini 2.5 Flash / Flash Lite: thinkingBudget=0 disables thinking
            return {"thinkingBudget": 0}

    def _execute_api_call(self, payload: Dict[str, Any], timeout: float = URLOPEN_TIMEOUT) -> Dict[str, Any]:
        """Execute HTTPS request to Gemini generateContent endpoint for self.model."""
        url = f"{self._get_endpoint_url(self.model)}?key={self.api_key}"
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

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body)

    def _dispatch_call(self, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        """Call _execute_api_call, supporting custom 1-arg mock functions and 2-arg calls."""
        try:
            return self._execute_api_call(payload, timeout=timeout)
        except TypeError:
            return self._execute_api_call(payload)

    def _call_model_with_retries(
        self,
        model_name: str,
        payload: Dict[str, Any],
        deadline: float,
    ) -> Dict[str, Any]:
        """Call a specific Gemini model with up to 2 retries on 429/500/503 and timeouts.

        Enforces exponential backoff with jitter and respects the remaining time before deadline.
        """
        self.model = model_name
        last_exception: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            now = time.time()
            time_left = deadline - now
            if time_left <= 0.5:
                raise TimeoutError(f"Deadline exceeded before calling model {model_name} (attempt {attempt + 1})")

            # Per-request timeout is at most 12s, capped by time left
            current_timeout = min(self.URLOPEN_TIMEOUT, max(1.0, time_left - 0.2))

            try:
                logger.info(
                    "Calling Gemini model %s (attempt %d/%d, timeout=%.1fs, time_left=%.1fs)",
                    model_name,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                    current_timeout,
                    time_left,
                )
                return self._dispatch_call(payload, timeout=current_timeout)

            except urllib.error.HTTPError as e:
                last_exception = e
                err_body = e.read().decode("utf-8") if e.fp else ""
                logger.warning(
                    "Gemini HTTP %d for %s (attempt %d/%d): %s",
                    e.code,
                    model_name,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                    err_body[:200],
                )
                if e.code not in (429, 500, 503):
                    # 400, 401, 404 etc are not retriable on this model
                    raise
                if attempt >= self.MAX_RETRIES:
                    raise

            except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
                last_exception = e
                logger.warning(
                    "Gemini connection/timeout error for %s (attempt %d/%d): %s",
                    model_name,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                    e,
                )
                if attempt >= self.MAX_RETRIES:
                    raise

            # Backoff with jitter: 0.5s * 2^attempt + jitter
            backoff_base = 0.5 * (2 ** attempt)
            jitter = random.uniform(0.05, 0.25)
            sleep_time = backoff_base + jitter

            time_left_after = deadline - time.time()
            if sleep_time + 1.0 > time_left_after:
                sleep_time = max(0.0, time_left_after - 1.0)

            if sleep_time > 0 and (deadline - time.time()) > sleep_time + 0.5:
                logger.info("Backing off for %.2fs before retry...", sleep_time)
                time.sleep(sleep_time)
            else:
                logger.warning("Not enough time remaining to back off (time_left=%.1fs)", deadline - time.time())
                break

        if last_exception:
            raise last_exception
        raise TimeoutError(f"Model {model_name} exhausted retry attempts.")

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
            "thinkingConfig": self._get_thinking_config(self.primary_model),
        }

        payload: Dict[str, Any] = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "generationConfig": generation_config,
        }

        start_time = time.time()
        deadline = start_time + self.TOTAL_DEADLINE_SECONDS

        models_to_try = [self.primary_model]
        if self.fallback_model and self.fallback_model != self.primary_model:
            models_to_try.append(self.fallback_model)

        last_error: Optional[Exception] = None

        for model_idx, current_model in enumerate(models_to_try):
            time_left = deadline - time.time()
            if time_left <= 1.0:
                logger.warning("Deadline reached before trying model %s", current_model)
                break

            payload["generationConfig"]["thinkingConfig"] = self._get_thinking_config(current_model)

            try:
                parsed = self._call_model_with_retries(current_model, payload, deadline)
                candidates = parsed.get("candidates", [])
                if not candidates:
                    raise RuntimeError(f"No candidates returned from Gemini model {current_model}.")

                candidate = candidates[0]
                finish_reason = candidate.get("finishReason")

                # Check finishReason: if MAX_TOKENS, retry once with a higher limit
                if finish_reason == "MAX_TOKENS" and (deadline - time.time() > 5.0):
                    logger.warning("Gemini finishReason was MAX_TOKENS. Retrying once with maxOutputTokens=2048...")
                    payload["generationConfig"]["maxOutputTokens"] = 2048
                    try:
                        retry_parsed = self._call_model_with_retries(current_model, payload, deadline)
                        retry_candidates = retry_parsed.get("candidates", [])
                        if retry_candidates:
                            candidate = retry_candidates[0]
                    except Exception as retry_err:
                        logger.warning("MAX_TOKENS retry failed: %s; using original candidate", retry_err)

                parts = candidate.get("content", {}).get("parts", [])
                raw_text = parts[0].get("text", "") if parts else ""
                return self._parse_json_response(raw_text)

            except Exception as e:
                last_error = e
                logger.warning(
                    "Model %s failed (attempted %d/%d): %s",
                    current_model,
                    model_idx + 1,
                    len(models_to_try),
                    e,
                )

        logger.error("All Gemini models failed or timed out. Last error: %s", last_error)
        raise ModelBusyError(
            f"The Gemini API is currently unavailable or experiencing high demand. Last error: {last_error}"
        ) from last_error

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
