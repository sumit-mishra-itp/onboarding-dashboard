"""LLM vendors behind one interface. Callers depend on Provider only; create_provider() picks the vendor
from AI_PROVIDER. To add a vendor: subclass Provider (or OpenAICompatible) and add it to PROVIDERS."""
import json
import os
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel

from ..config import settings

TIMEOUT_S = 20.0


class AIError(Exception):
    """Call failed in a way worth one corrective retry. Timeouts raise TimeoutError instead (no retry)."""


class Provider(ABC):
    name: str
    key_env: str
    default_model: str

    def __init__(self, model: str = ""):
        self.key = os.environ.get(self.key_env, "")
        self.model = model or self.default_model

    @abstractmethod
    def complete(self, system: str, user: str, schema: type[BaseModel]) -> tuple[dict, int | None, int | None]:
        """Ask for a JSON object shaped like `schema`. Returns (object, prompt tokens, completion tokens).
        Raises TimeoutError on timeout and AIError on any other provider failure."""


_http = httpx.Client(timeout=TIMEOUT_S)  # shared: pooled keep-alive connections, thread-safe


class OpenAICompatible(Provider):
    """Groq and Gemini both speak the OpenAI chat-completions dialect. JSON mode; the schema is in the prompt."""
    base_url: str

    def complete(self, system, user, schema):
        try:
            r = _http.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.key}"}, json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
                "max_tokens": 8000,
            })
        except httpx.TimeoutException as e:
            raise TimeoutError(str(e)) from e
        except httpx.HTTPError as e:
            raise AIError(f"network: {e}") from e
        if r.status_code != 200:
            raise AIError(f"HTTP {r.status_code}: {r.text[:500]}")
        try:
            body = r.json()
            choice, usage = body["choices"][0], body.get("usage") or {}
            content = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise AIError(f"unexpected response: {r.text[:500]}") from e
        if choice.get("finish_reason") != "stop":
            raise AIError(f"finish_reason={choice.get('finish_reason')}")
        try:
            return json.loads(content), usage.get("prompt_tokens"), usage.get("completion_tokens")
        except (ValueError, TypeError) as e:
            raise AIError(f"not JSON: {str(content)[:300]}") from e


class Groq(OpenAICompatible):
    name, key_env, default_model = "groq", "GROQ_API_KEY", "openai/gpt-oss-120b"
    base_url = "https://api.groq.com/openai/v1"


class Gemini(OpenAICompatible):
    name, key_env, default_model = "gemini", "GEMINI_API_KEY", "gemini-2.5-flash"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai"


class Anthropic(Provider):
    name, key_env, default_model = "anthropic", "ANTHROPIC_API_KEY", "claude-opus-5"

    def __init__(self, model: str = ""):
        super().__init__(model)
        import anthropic  # only imported when this vendor is selected
        self._sdk = anthropic
        self._client = anthropic.Anthropic(api_key=self.key or "unset", timeout=TIMEOUT_S, max_retries=0)

    def complete(self, system, user, schema):
        try:
            resp = self._client.messages.parse(model=self.model, max_tokens=16000, system=system,
                                               messages=[{"role": "user", "content": user}], output_format=schema)
        except self._sdk.APITimeoutError as e:
            raise TimeoutError(str(e)) from e
        except self._sdk.APIError as e:
            raise AIError(str(e)) from e
        if resp.stop_reason != "end_turn" or resp.parsed_output is None:
            raise AIError(f"stop_reason={resp.stop_reason}")
        return resp.parsed_output.model_dump(), resp.usage.input_tokens, resp.usage.output_tokens


PROVIDERS: dict[str, type[Provider]] = {p.name: p for p in (Groq, Gemini, Anthropic)}


def create_provider(name: str | None = None, model: str | None = None) -> Provider:
    name = (name or settings.ai_provider).strip().lower()
    if name not in PROVIDERS:
        raise RuntimeError(f"AI_PROVIDER must be one of {sorted(PROVIDERS)}, got {name!r}")
    return PROVIDERS[name](settings.ai_model if model is None else model)
