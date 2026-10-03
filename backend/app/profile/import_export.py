"""Profile import/export: schema validation, sample generation, JSON download."""
from __future__ import annotations

import json
import uuid

from pydantic import ValidationError

from ..profile.schemas import (
    BulletSchema,
    CertificationSchema,
    EducationSchema,
    ExperienceSchema,
    LinkSchema,
    ProjectSchema,
    SkillSchema,
)

# ── Sample profile (used for the "download sample" feature) ──────────────────

SAMPLE_PROFILE: dict = {
    "basics": {
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+1-555-0100",
        "location": "San Francisco, CA",
        "links": [
            {"label": "GitHub", "url": "https://github.com/janesmith"},
            {"label": "LinkedIn", "url": "https://linkedin.com/in/janesmith"},
            {"label": "Portfolio", "url": "https://janesmith.dev"},
        ],
    },
    "preferences": {
        "career_stage": "experienced",
        "max_pages": 1,
        "date_format": "MMM YYYY",
        "paper_size": "Letter",
    },
    "summary_facts": [
        "5 years building production Python and TypeScript services",
        "Led a team of 4 engineers at Acme Corp",
        "Reduced API latency by 60% through caching layer redesign",
    ],
    "skills": [
        {"name": "Python", "category": "Languages", "level": "strong", "years": 5, "aliases": ["py"]},
        {"name": "TypeScript", "category": "Languages", "level": "strong", "years": 3},
        {"name": "FastAPI", "category": "Frameworks", "level": "strong", "years": 2},
        {"name": "React", "category": "Frameworks", "level": "working", "years": 2},
        {"name": "PostgreSQL", "category": "Databases", "level": "strong", "years": 4, "aliases": ["Postgres"]},
        {"name": "AWS", "category": "Cloud", "level": "working", "years": 2, "aliases": ["Amazon Web Services"]},
        {"name": "Docker", "category": "DevOps", "level": "working", "years": 3},
    ],
    "experience": [
        {
            "id": "exp-001",
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
            "title_aliases": ["Senior Engineer", "Backend Engineer"],
            "location": "San Francisco, CA",
            "start": "Jan 2023",
            "end": None,
            "bullets": [
                {
                    "id": "b-001",
                    "text": "Redesigned the caching layer using Redis, reducing average API latency by 60% (from 250ms to 100ms).",
                    "skills": ["Python", "FastAPI", "PostgreSQL"],
                    "metrics": ["60%", "250ms", "100ms"],
                    "themes": ["performance", "scalability"],
                },
                {
                    "id": "b-002",
                    "text": "Led a team of 4 engineers to deliver a billing microservice used by 20,000+ customers.",
                    "skills": ["Python", "Docker", "PostgreSQL"],
                    "metrics": ["4 engineers", "20,000+ customers"],
                    "themes": ["leadership", "microservices"],
                },
            ],
        },
        {
            "id": "exp-002",
            "company": "Startup Inc",
            "title": "Software Engineer",
            "location": "Remote",
            "start": "Jun 2021",
            "end": "Jan 2023",
            "bullets": [
                {
                    "id": "b-003",
                    "text": "Built a real-time dashboard in React and TypeScript, processing 5M events/day via WebSockets.",
                    "skills": ["React", "TypeScript"],
                    "metrics": ["5M events/day"],
                    "themes": ["real-time", "frontend"],
                },
            ],
        },
    ],
    "projects": [
        {
            "id": "proj-001",
            "name": "OpenMetrics CLI",
            "url": "https://github.com/janesmith/openmetrics-cli",
            "skills": ["Python", "Docker"],
            "bullets": [
                {
                    "id": "b-004",
                    "text": "Open-source CLI tool with 800+ GitHub stars for monitoring containerized services.",
                    "skills": ["Python", "Docker"],
                    "metrics": ["800+ stars"],
                    "themes": ["open-source", "DevOps"],
                },
            ],
        },
    ],
    "education": [
        {
            "id": "edu-001",
            "institution": "University of California, Berkeley",
            "degree": "B.S. Computer Science",
            "location": "Berkeley, CA",
            "start": "Aug 2017",
            "end": "May 2021",
            "details": ["GPA: 3.8", "Dean's List 2019, 2020"],
        },
    ],
    "certifications": [
        {"name": "AWS Certified Solutions Architect – Associate", "issuer": "Amazon Web Services", "date": "Mar 2023"},
    ],
    "never_claim": ["Machine Learning", "Kubernetes", "Go"],
}


# ── Validation ────────────────────────────────────────────────────────────────

class ImportError(ValueError):
    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


def _validate_section(name: str, data: list, model) -> list[str]:
    errors = []
    for i, item in enumerate(data):
        try:
            model.model_validate(item)
        except ValidationError as e:
            for err in e.errors():
                loc = " → ".join(str(x) for x in err["loc"])
                errors.append(f"{name}[{i}].{loc}: {err['msg']}")
    return errors


def validate_import_json(raw: dict) -> tuple[bool, list[str]]:
    """
    Validate an imported profile JSON dict.
    Returns (is_valid, list_of_error_strings).
    """
    errors: list[str] = []

    # basics
    basics = raw.get("basics", {})
    if not isinstance(basics, dict):
        errors.append("basics: must be an object")
    else:
        name_val = basics.get("full_name") or basics.get("name")
        if not name_val:
            errors.append("basics.full_name: required field is missing or empty")
        if not basics.get("email"):
            errors.append("basics.email: required field is missing or empty")
        links = basics.get("links", [])
        errors += _validate_section("basics.links", links, LinkSchema)

    # skills
    errors += _validate_section("skills", raw.get("skills", []), SkillSchema)

    # experience
    for i, exp in enumerate(raw.get("experience", [])):
        try:
            ExperienceSchema.model_validate(exp)
        except ValidationError as e:
            for err in e.errors():
                loc = " → ".join(str(x) for x in err["loc"])
                errors.append(f"experience[{i}].{loc}: {err['msg']}")

    # projects
    for i, proj in enumerate(raw.get("projects", [])):
        try:
            ProjectSchema.model_validate(proj)
        except ValidationError as e:
            for err in e.errors():
                loc = " → ".join(str(x) for x in err["loc"])
                errors.append(f"projects[{i}].{loc}: {err['msg']}")

    # education
    errors += _validate_section("education", raw.get("education", []), EducationSchema)

    # certifications
    errors += _validate_section("certifications", raw.get("certifications", []), CertificationSchema)

    # bullet id uniqueness
    bullet_ids: set[str] = set()
    duplicates: set[str] = set()
    for exp in raw.get("experience", []):
        for b in exp.get("bullets", []):
            bid = b.get("id", "")
            if bid in bullet_ids:
                duplicates.add(bid)
            bullet_ids.add(bid)
    for proj in raw.get("projects", []):
        for b in proj.get("bullets", []):
            bid = b.get("id", "")
            if bid in bullet_ids:
                duplicates.add(bid)
            bullet_ids.add(bid)
    for dup in duplicates:
        errors.append(f"Duplicate bullet id: '{dup}' — all bullet ids must be unique")

    return len(errors) == 0, errors
