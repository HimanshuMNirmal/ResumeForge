"""Small text helpers: skill/alias normalisation, term matching, dates, slugs."""
from __future__ import annotations

import re
from datetime import date

from .models import Profile

STANDARD_HEADINGS = ["Summary", "Skills", "Experience", "Projects", "Education", "Certifications"]

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ------------------------------------------------------------------ matching
# Terms that are also ordinary English words: match them case-sensitively ("Go" but not "go").
AMBIGUOUS_TERMS = {"go", "rust", "swift", "spark", "ruby", "julia", "dart", "r", "c"}


def term_regex(term: str) -> re.Pattern[str]:
    """Word-boundary-ish regex that also works for C++, C#, .NET, Node.js, CI/CD."""
    term = term.strip()
    flags = 0 if term.lower() in AMBIGUOUS_TERMS else re.IGNORECASE
    return re.compile(r"(?<![\w+#])" + re.escape(term) + r"(?![\w+#])", flags)


def term_in_text(term: str, text: str) -> bool:
    if not term.strip():
        return False
    return term_regex(term).search(text) is not None


def any_in_text(terms, text: str) -> bool:
    return any(term_in_text(t, text) for t in terms)


class SkillIndex:
    """Maps every name/alias of a profile skill to its canonical name."""

    def __init__(self, profile: Profile):
        self._canon: dict[str, str] = {}
        self._variants: dict[str, set[str]] = {}
        for s in profile.skills:
            forms = {s.name, *s.aliases}
            self._variants[s.name] = forms
            for f in forms:
                self._canon[f.lower()] = s.name
        self.blocked = {n.lower() for n in profile.never_claim}

    def canon(self, term: str) -> str | None:
        return self._canon.get(term.strip().lower())

    def variants(self, term: str) -> set[str]:
        """All spellings of a term. Unknown terms just return themselves."""
        c = self.canon(term)
        return set(self._variants[c]) if c else {term}

    def is_blocked(self, term: str) -> bool:
        forms = {term.lower(), *(v.lower() for v in self.variants(term))}
        c = self.canon(term)
        if c:
            forms.add(c.lower())
        return bool(forms & self.blocked)

    def is_supported(self, term: str) -> bool:
        return self.canon(term) is not None and not self.is_blocked(term)

    def canon_skills_in(self, text: str) -> set[str]:
        return {c for c, forms in self._variants.items() if any_in_text(forms, text)}

    def text_has(self, term: str, text: str) -> bool:
        return any_in_text(self.variants(term), text)


# ------------------------------------------------------------------ numbers / verbs
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text)}


WEAK_VERBS = {"assisted", "helped", "supported", "contributed", "participated", "aided", "collaborated"}
STRONG_VERBS = {
    "led", "managed", "owned", "architected", "directed", "spearheaded", "headed",
    "founded", "oversaw", "drove", "pioneered",
}


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z'-]*", text.lower()))


# ------------------------------------------------------------------ dates
def parse_ym(value: str) -> tuple[int, int | None]:
    parts = value.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 and parts[1] else None
    return year, month


def fmt_date(value: str | None, fmt: str = "MMM YYYY") -> str:
    if not value:
        return "Present"
    year, month = parse_ym(value)
    if month is None or fmt == "YYYY":
        return str(year)
    return f"{_MONTHS[month - 1]} {year}"


def date_range(start: str, end: str | None, fmt: str = "MMM YYYY") -> str:
    s = fmt_date(start, fmt) if start else ""
    e = fmt_date(end, fmt)
    return f"{s} – {e}" if s else e


def slugify(text: str, fallback: str = "unknown") -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s or fallback


def today() -> str:
    return date.today().isoformat()
