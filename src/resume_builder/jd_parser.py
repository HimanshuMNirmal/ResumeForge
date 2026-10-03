"""Step 2: job description text -> JD. LLM (fast model) with a deterministic fallback."""
from __future__ import annotations

import re

from .llm import LLMClient, fast_model, load_prompt
from .models import JD, Profile

JD_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "title": {"type": "string"},
        "seniority": {"type": "string"},
        "must_have": {"type": "array", "items": {"type": "string"}},
        "nice_to_have": {"type": "array", "items": {"type": "string"}},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "domain": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["title", "must_have", "nice_to_have"],
}


def parse_jd(text: str, profile: Profile, client: LLMClient | None) -> JD:
    """Use the LLM when a client is given; otherwise (or on failure) fall back to heuristics."""
    if client is not None:
        try:
            data = client.structured(
                model=fast_model(),
                system=load_prompt("jd_parser.md"),
                user=f"JOB POSTING:\n\n{text}",
                tool_name="record_job",
                schema=JD_SCHEMA,
            )
            return JD.model_validate(data)
        except Exception as e:  # network / schema problems must not kill the run
            print(f"[jd_parser] LLM parse failed ({e}); using heuristic parser")
    return heuristic_parse(text, profile)


# ------------------------------------------------------------------ heuristic fallback
COMMON_TECH = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#", "Ruby", "PHP", "Kotlin", "Scala",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Kafka", "RabbitMQ", "Spark", "Airflow",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "GitHub Actions",
    "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI", "Spring Boot", "GraphQL", "REST APIs",
    "gRPC", "Linux", "Git", "Machine Learning", "TensorFlow", "PyTorch", "Pandas", "Tableau", "Power BI",
]
COMMON_KEYWORDS = [
    "microservices", "CI/CD", "observability", "distributed systems", "agile", "scrum", "code review",
    "system design", "scalability", "testing", "monitoring", "automation", "data pipelines", "mentoring",
    "cloud", "security", "performance", "APIs",
]
_NICE = re.compile(r"nice to have|preferred|bonus|a plus|good to have|desirable|nice-to-have", re.I)
_MUST = re.compile(r"requirements?|qualifications?|must have|what you.?ll need|you have|about you|skills", re.I)
_RESP = re.compile(r"responsibilit|what you.?ll do|the role|your impact|day to day", re.I)
_SENIORITY = [
    ("principal", r"\bprincipal\b"), ("staff", r"\bstaff\b"), ("lead", r"\blead\b|\btech lead\b"),
    ("senior", r"\bsenior\b|\bsr\.?\b"), ("junior", r"\bjunior\b|\bjr\.?\b|\bentry[- ]level\b|\bgraduate\b"),
    ("intern", r"\bintern(ship)?\b"), ("mid", r"\bmid[- ]level\b"),
]


def _is_heading(line: str) -> bool:
    return len(line) < 70 and (line.endswith(":") or line.istitle() or line.isupper())


def heuristic_parse(text: str, profile: Profile) -> JD:
    from .textutil import SkillIndex, term_in_text

    idx = SkillIndex(profile)
    lines = [l.strip() for l in text.split("\n")]
    nonempty = [l for l in lines if l]

    title = nonempty[0][:100] if nonempty else ""
    company = ""
    m = re.search(r"(?:^|\n)\s*company\s*[:\-]\s*(.+)", text, re.I) or re.search(
        r"\bjoin\s+([A-Z][\w&.\- ]{1,40}?)(?:[,.!]| as | to )", text
    ) or re.search(r"\bat\s+([A-Z][\w&.\-]+(?: [A-Z][\w&.\-]+)?)", nonempty[0] if nonempty else "")
    if m:
        company = m.group(1).strip()

    seniority = ""
    head = " ".join(nonempty[:3])
    for name, pat in _SENIORITY:
        if re.search(pat, head, re.I):
            seniority = name
            break

    candidates: list[str] = []
    for s in profile.skills:  # profile skills first so aliases are honoured
        candidates.append(s.name)
    for t in COMMON_TECH:
        if idx.canon(t) is None:
            candidates.append(t)

    state = "must"
    must: list[str] = []
    nice: list[str] = []
    resp: list[str] = []
    for line in lines:
        if not line:
            continue
        if _is_heading(line) or len(line) < 40:
            if _NICE.search(line):
                state = "nice"
                continue
            if _RESP.search(line):
                state = "resp"
                continue
            if _MUST.search(line):
                state = "must"
                continue
        if state == "resp":
            if len(resp) < 8 and len(line) > 15:
                resp.append(line.lstrip("-•* ").rstrip("."))
        inline_nice = bool(_NICE.search(line))
        for term in candidates:
            variants = idx.variants(term)
            if any(term_in_text(v, line) for v in variants):
                bucket = nice if (state == "nice" or inline_nice) else must
                if term not in bucket:
                    bucket.append(term)
    nice = [t for t in nice if t not in must]

    lower = text.lower()
    keywords = [k for k in COMMON_KEYWORDS if term_in_text(k, lower) and k not in must and k not in nice]

    domain = ""
    for d in ["fintech", "healthcare", "e-commerce", "ecommerce", "edtech", "saas", "gaming", "logistics", "adtech"]:
        if d in lower:
            domain = d
            break
    notes = ""
    yrs = re.search(r"(\d+)\+?\s*(?:years|yrs)", text, re.I)
    if yrs:
        notes = f"{yrs.group(0)} experience"
    return JD(
        company=company, title=title, seniority=seniority, must_have=must, nice_to_have=nice,
        responsibilities=resp, keywords=keywords, domain=domain, notes=notes,
    )
