"""Provider selection + each provider's request/response handling, using fake SDK modules (no network)."""
import json
import os
import sys
import types

from resume_builder import llm
from resume_builder.llm import LLMUnavailable

KEYS = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "RESUME_PROVIDER",
        "RESUME_FAST_MODEL", "RESUME_STRONG_MODEL", "RESUME_OPENAI_STRONG_MODEL", "RESUME_TEMPERATURE"]


class env:
    """Context manager: clean provider env vars, then apply overrides; restores everything on exit."""

    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        self.saved = {k: os.environ.get(k) for k in KEYS}
        for k in KEYS:
            os.environ.pop(k, None)
        os.environ.update(self.kw)
        llm._active = None

    def __exit__(self, *a):
        for k, v in self.saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        llm._active = None


def test_auto_detect_and_priority():
    with env():
        assert llm.available_providers() == []
        try:
            llm.resolve_provider()
        except LLMUnavailable as e:
            assert "No API key" in str(e)
        else:
            raise AssertionError
    with env(OPENAI_API_KEY="x"):
        assert llm.resolve_provider() == "openai"
    with env(GOOGLE_API_KEY="x"):
        assert llm.resolve_provider() == "gemini"
    with env(OPENAI_API_KEY="x", GEMINI_API_KEY="y", ANTHROPIC_API_KEY="z"):
        assert llm.resolve_provider() == "anthropic"
        assert llm.resolve_provider("chatgpt") == "openai"


def test_explicit_provider_needs_its_key_and_aliases_work():
    with env(OPENAI_API_KEY="x", RESUME_PROVIDER="claude"):
        try:
            llm.resolve_provider()
        except LLMUnavailable as e:
            assert "ANTHROPIC_API_KEY" in str(e)
        else:
            raise AssertionError
    with env(GEMINI_API_KEY="x", RESUME_PROVIDER="Google"):
        assert llm.resolve_provider() == "gemini"
    try:
        llm.normalize_provider("llama")
    except LLMUnavailable:
        pass
    else:
        raise AssertionError


def test_model_defaults_and_overrides_follow_active_provider():
    with env(OPENAI_API_KEY="x"):
        llm._active = "openai"
        assert llm.fast_model() == llm.DEFAULT_MODELS["openai"][0]
        os.environ["RESUME_STRONG_MODEL"] = "generic-model"
        assert llm.strong_model() == "generic-model"
        os.environ["RESUME_OPENAI_STRONG_MODEL"] = "specific-model"
        assert llm.strong_model() == "specific-model"
        llm._active = "gemini"
        assert llm.strong_model() == "generic-model"


def test_parse_json_loose():
    assert llm.parse_json_loose('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.parse_json_loose('Here you go: {"a": {"b": 2}} thanks') == {"a": {"b": 2}}


def _fake_module(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


def test_openai_client_uses_forced_function_call_and_retries_without_temperature():
    calls = []

    class Completions:
        def create(self, **kw):
            calls.append(kw)
            if "temperature" in kw:
                raise RuntimeError("Unsupported value: 'temperature' does not support 0")
            fn = types.SimpleNamespace(arguments=json.dumps({"title": "Engineer"}))
            msg = types.SimpleNamespace(tool_calls=[types.SimpleNamespace(function=fn)])
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class OpenAI:
        def __init__(self, api_key=None):
            self.chat = types.SimpleNamespace(completions=Completions())

    saved = sys.modules.get("openai")
    _fake_module("openai", OpenAI=OpenAI)
    try:
        with env(OPENAI_API_KEY="k"):
            client = llm.get_client()
            assert llm._active == "openai"
            out = client.structured(model="m", system="s", user="u", tool_name="t", schema={"type": "object"})
    finally:
        sys.modules.pop("openai", None)
        if saved:
            sys.modules["openai"] = saved
    assert out == {"title": "Engineer"}
    assert len(calls) == 2 and "temperature" in calls[0] and "temperature" not in calls[1]
    assert calls[0]["tool_choice"]["function"]["name"] == "t"


def test_gemini_client_puts_schema_in_instruction_and_parses_fenced_json():
    seen = {}

    class Models:
        def generate_content(self, model, contents, config):
            seen.update(model=model, contents=contents, config=config)
            return types.SimpleNamespace(text='```json\n{"summary": "hi"}\n```')

    class Client:
        def __init__(self, api_key=None):
            self.models = Models()

    class Config:
        def __init__(self, **kw):
            self.kw = kw

    saved = {k: sys.modules.get(k) for k in ("google", "google.genai", "google.genai.types")}
    types_mod = _fake_module("google.genai.types", GenerateContentConfig=Config)
    genai_mod = _fake_module("google.genai", Client=Client, types=types_mod)
    _fake_module("google", genai=genai_mod)
    try:
        with env(GEMINI_API_KEY="k"):
            client = llm.get_client("gemini")
            out = client.structured(model="gm", system="SYS", user="USER", tool_name="t",
                                    schema={"type": "object", "properties": {"summary": {"type": "string"}}})
    finally:
        for k, v in saved.items():
            sys.modules.pop(k, None)
            if v:
                sys.modules[k] = v
    assert out == {"summary": "hi"}
    kw = seen["config"].kw
    assert "SYS" in kw["system_instruction"] and '"summary"' in kw["system_instruction"]
    assert kw["response_mime_type"] == "application/json" and kw["temperature"] == 0.0
    assert seen["contents"] == "USER" and seen["model"] == "gm"


def test_resolve_client_without_any_key_falls_back_with_note():
    from resume_builder import pipeline

    with env():
        notes = []
        cwd = os.getcwd()
        os.chdir("/tmp")  # make sure no stray .env is picked up
        try:
            assert pipeline.resolve_client(None, notes) is None
        finally:
            os.chdir(cwd)
        assert any("No API key" in n for n in notes)
        try:
            os.chdir("/tmp")
            pipeline.resolve_client(True, [])
        except LLMUnavailable:
            pass
        else:
            raise AssertionError
        finally:
            os.chdir(cwd)
