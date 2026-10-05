"""Shared test helpers (plain module so pytest and simple runners both work)."""
import json
from pathlib import Path

from resume_builder.jd_parser import heuristic_parse
from resume_builder.models import Profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "data" / "profile.example.json"
if not PROFILE_PATH.exists() and (ROOT / "data" / "profile.json").exists():
    PROFILE_PATH = ROOT / "data" / "profile.json"

JD_PATH = ROOT / "data" / "sample_jd.txt"
if not JD_PATH.exists() and (ROOT / "data" / "amazon.txt").exists():
    JD_PATH = ROOT / "data" / "amazon.txt"


def load_profile() -> Profile:
    return Profile.model_validate(json.loads(PROFILE_PATH.read_text()))


def load_jd(profile: Profile | None = None):
    return heuristic_parse(JD_PATH.read_text(), profile or load_profile())


class FakeLLM:
    """Returns canned structured output keyed by tool name."""

    def __init__(self, **by_tool):
        self.by_tool = by_tool
        self.calls: list[tuple[str, str]] = []

    def structured(self, *, model, system, user, tool_name, schema):
        self.calls.append((tool_name, user))
        out = self.by_tool[tool_name]
        return out(user) if callable(out) else out
