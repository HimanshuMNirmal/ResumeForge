"""LLM layer with three interchangeable providers: Anthropic (Claude), OpenAI (ChatGPT), Google (Gemini).

The rest of the project only needs `structured()`: prompt in, JSON dict out.

Pick a provider (first match wins):
  1. `resume --provider openai build ...`      (CLI flag, sets RESUME_PROVIDER)
  2. RESUME_PROVIDER=openai                    (env / .env)
  3. auto-detect from whichever API key is set (order: anthropic, openai, gemini)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

PROVIDERS = ("anthropic", "openai", "gemini")
_ALIASES = {
    "claude": "anthropic", "anthropic": "anthropic",
    "openai": "openai", "chatgpt": "openai", "gpt": "openai",
    "gemini": "gemini", "google": "gemini",
}
KEY_ENV = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
}
# (fast model for JD parsing, strong model for tailoring). Model names change often:
# override with RESUME_FAST_MODEL / RESUME_STRONG_MODEL (or RESUME_<PROVIDER>_FAST_MODEL ...).
DEFAULT_MODELS = {
    "anthropic": ("claude-haiku-4-5-20251001", "claude-sonnet-5-5"),
    "openai": ("gpt-4.1-mini", "gpt-4.1"),
    "gemini": ("gemini-2.5-flash", "gemini-2.5-pro"),
}

_active: str | None = None  # provider of the client most recently created (used by fast_model/strong_model)


class LLMClient(Protocol):
    def structured(
        self, *, model: str, system: str, user: str, tool_name: str, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


class LLMUnavailable(RuntimeError):
    pass


# ------------------------------------------------------------------ provider selection
def normalize_provider(name: str) -> str:
    key = name.strip().lower()
    if key not in _ALIASES:
        raise LLMUnavailable(f"Unknown provider '{name}'. Choose one of: claude, openai (chatgpt), gemini.")
    return _ALIASES[key]


def api_key(provider: str) -> str | None:
    for var in KEY_ENV[provider]:
        if os.environ.get(var):
            return os.environ[var]
    return None


def available_providers() -> list[str]:
    """Providers that have an API key configured, in auto-detect order."""
    return [p for p in PROVIDERS if api_key(p)]


def resolve_provider(explicit: str | None = None) -> str:
    wanted = explicit or os.environ.get("RESUME_PROVIDER") or ""
    if wanted.strip():
        provider = normalize_provider(wanted)
        if not api_key(provider):
            raise LLMUnavailable(f"Provider '{provider}' selected but {' / '.join(KEY_ENV[provider])} is not set.")
        return provider
    found = available_providers()
    if not found:
        raise LLMUnavailable(
            "No API key found. Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY (export it or put it in .env)."
        )
    return found[0]


def _model(tier: int, env_suffix: str) -> str:
    provider = _active or "anthropic"
    specific = os.environ.get(f"RESUME_{provider.upper()}_{env_suffix}")
    return specific or os.environ.get(f"RESUME_{env_suffix}") or DEFAULT_MODELS[provider][tier]


def fast_model() -> str:
    return _model(0, "FAST_MODEL")


def strong_model() -> str:
    return _model(1, "STRONG_MODEL")


def _temperature() -> float | None:
    raw = os.environ.get("RESUME_TEMPERATURE", "0")
    return float(raw) if raw != "" else None


def parse_json_loose(text: str) -> dict[str, Any]:
    """Parse model text as JSON, tolerating ```json fences or a sentence before/after the object."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


# ------------------------------------------------------------------ providers
class AnthropicClient:
    """Claude. Forces a single tool call so the reply is always JSON matching `schema`."""

    provider = "anthropic"

    def __init__(self) -> None:
        key = api_key("anthropic")
        if not key:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set (export it or put it in .env)")
        try:
            import anthropic
        except ImportError as e:
            raise LLMUnavailable("Claude needs the 'anthropic' package: pip install anthropic") from e
        self._client = anthropic.Anthropic(api_key=key)

    def structured(self, *, model, system, user, tool_name, schema):
        kwargs: dict[str, Any] = {}
        temp = _temperature()
        if temp is not None:
            kwargs["temperature"] = temp
        resp = self._client.messages.create(
            model=model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"name": tool_name, "description": "Return the result.", "input_schema": schema}],
            tool_choice={"type": "tool", "name": tool_name},
            **kwargs,
        )
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use":
                return dict(block.input)
        raise RuntimeError("Claude returned no tool call")


class OpenAIClient:
    """ChatGPT. Forces one function call. Set OPENAI_BASE_URL to use any OpenAI-compatible server."""

    provider = "openai"

    def __init__(self) -> None:
        key = api_key("openai")
        if not key:
            raise LLMUnavailable("OPENAI_API_KEY is not set (export it or put it in .env)")
        try:
            import openai
        except ImportError as e:
            raise LLMUnavailable("ChatGPT needs the 'openai' package: pip install openai") from e
        self._client = openai.OpenAI(api_key=key)  # also honours OPENAI_BASE_URL

    def structured(self, *, model, system, user, tool_name, schema):
        base: dict[str, Any] = dict(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            tools=[{"type": "function", "function": {"name": tool_name, "description": "Return the result.", "parameters": schema}}],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )
        temp = _temperature()
        try:
            resp = self._client.chat.completions.create(**base, **({"temperature": temp} if temp is not None else {}))
        except Exception as e:
            # some newer / reasoning models reject a temperature parameter: retry without it
            if temp is not None and "temperature" in str(e).lower():
                resp = self._client.chat.completions.create(**base)
            else:
                raise
        calls = resp.choices[0].message.tool_calls
        if not calls:
            raise RuntimeError("OpenAI returned no function call")
        return json.loads(calls[0].function.arguments)


class GeminiClient:
    """Gemini via the `google-genai` SDK. Uses JSON mode with the schema stated in the prompt."""

    provider = "gemini"

    def __init__(self) -> None:
        key = api_key("gemini")
        if not key:
            raise LLMUnavailable("GEMINI_API_KEY is not set (export it or put it in .env)")
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            raise LLMUnavailable("Gemini needs the 'google-genai' package: pip install google-genai") from e
        self._types = types
        self._client = genai.Client(api_key=key)

    def structured(self, *, model, system, user, tool_name, schema):
        instruction = (
            f"{system}\n\nRespond with ONLY a single JSON object (no prose, no code fences) "
            f"that matches this JSON Schema:\n{json.dumps(schema)}"
        )
        cfg: dict[str, Any] = {"system_instruction": instruction, "response_mime_type": "application/json"}
        temp = _temperature()
        if temp is not None:
            cfg["temperature"] = temp
        resp = self._client.models.generate_content(
            model=model, contents=user, config=self._types.GenerateContentConfig(**cfg)
        )
        if not resp.text:
            raise RuntimeError("Gemini returned an empty response (it may have been blocked)")
        return parse_json_loose(resp.text)


_CLIENTS = {"anthropic": AnthropicClient, "openai": OpenAIClient, "gemini": GeminiClient}


def get_client(provider: str | None = None) -> LLMClient:
    """Create a client for `provider` (or RESUME_PROVIDER, or whichever API key is set)."""
    global _active
    name = resolve_provider(provider)
    client = _CLIENTS[name]()
    _active = name
    return client


def describe_active() -> str:
    p = _active or "none"
    return f"{p} (fast: {fast_model()}, strong: {strong_model()})" if _active else "none"


# ------------------------------------------------------------------ misc helpers
def load_dotenv_if_present(path: str = ".env") -> None:
    """Minimal .env loader so we don't need another dependency."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_prompt(name: str) -> str:
    from importlib import resources

    return resources.files("resume_builder").joinpath("prompts", name).read_text(encoding="utf-8")
