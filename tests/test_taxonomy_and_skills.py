"""Tests for skill taxonomy, categorization, backend profile normalization, and markdown rendering."""
import pytest
from resume_builder.models import JD, Profile, Resume, Skill, SkillGroup
from resume_builder.matcher import select
from resume_builder.taxonomy import (
    CATEGORY_AI_DATA,
    CATEGORY_BACKEND,
    CATEGORY_BLOCKCHAIN,
    CATEGORY_CLOUD_DEVOPS,
    CATEGORY_DATABASES,
    CATEGORY_FRONTEND,
    CATEGORY_LANGUAGES,
    CATEGORY_MOBILE,
    CATEGORY_TOOLS,
    classify_skill,
)
from resume_builder.render.markdown import resume_to_markdown
try:
    from backend.app.resume.service import _normalize_skills
except (ImportError, ModuleNotFoundError):
    _normalize_skills = None


def test_classify_skill_known_canonical():
    assert classify_skill("JavaScript") == CATEGORY_LANGUAGES
    assert classify_skill("TypeScript") == CATEGORY_LANGUAGES
    assert classify_skill("Python") == CATEGORY_LANGUAGES
    assert classify_skill("React.js") == CATEGORY_FRONTEND
    assert classify_skill("Next.js") == CATEGORY_FRONTEND
    assert classify_skill("Redux") == CATEGORY_FRONTEND
    assert classify_skill("React Native") == CATEGORY_MOBILE
    assert classify_skill("Android") == CATEGORY_MOBILE
    assert classify_skill("Flutter") == CATEGORY_MOBILE
    assert classify_skill("Node.js") == CATEGORY_BACKEND
    assert classify_skill("Express.js") == CATEGORY_BACKEND
    assert classify_skill("REST APIs") == CATEGORY_BACKEND
    assert classify_skill("PostgreSQL") == CATEGORY_DATABASES
    assert classify_skill("MongoDB") == CATEGORY_DATABASES
    assert classify_skill("Docker") == CATEGORY_CLOUD_DEVOPS
    assert classify_skill("AWS") == CATEGORY_CLOUD_DEVOPS
    assert classify_skill("Git") == CATEGORY_TOOLS
    assert classify_skill("Solidity") == CATEGORY_BLOCKCHAIN
    assert classify_skill("Pandas") == CATEGORY_AI_DATA


def test_classify_skill_heals_generic_existing_category():
    # When a skill was improperly stored under generic "Tools" or "Other", it gets reclassified
    assert classify_skill("React.js", existing_category="Tools") == CATEGORY_FRONTEND
    assert classify_skill("Node.js", existing_category="tools") == CATEGORY_BACKEND
    assert classify_skill("PostgreSQL", existing_category="Other") == CATEGORY_DATABASES
    assert classify_skill("React Native", existing_category="Tools") == CATEGORY_MOBILE


def test_classify_skill_preserves_legitimate_custom_category():
    assert classify_skill("MyEngine", existing_category="Game Engines") == "Game Engines"
    assert classify_skill("CustomTech", existing_category="Bioinformatics") == "Bioinformatics"


def test_normalize_skills_service():
    if _normalize_skills is None:
        pytest.skip("backend dependencies not installed in host venv (run in container)")
    raw_dict = {
        "languages": ["Python", "TypeScript"],
        "tools": ["React.js", "Node.js", "PostgreSQL", "Git", "UnknownWidget"],
    }
    normalized = _normalize_skills(raw_dict)
    cat_by_name = {s["name"]: s["category"] for s in normalized}

    assert cat_by_name["Python"] == CATEGORY_LANGUAGES
    assert cat_by_name["TypeScript"] == CATEGORY_LANGUAGES
    assert cat_by_name["React.js"] == CATEGORY_FRONTEND
    assert cat_by_name["Node.js"] == CATEGORY_BACKEND
    assert cat_by_name["PostgreSQL"] == CATEGORY_DATABASES
    assert cat_by_name["Git"] == CATEGORY_TOOLS
    assert cat_by_name["UnknownWidget"] == CATEGORY_TOOLS


def test_markdown_renders_rich_skill_categories_and_no_target_role():
    resume = Resume(
        basics={"name": "Himanshu Nirmal", "email": "test@example.com"},
        skills=[
            SkillGroup(category="Languages", skills=["JavaScript", "TypeScript", "Python"]),
            SkillGroup(category="Frontend", skills=["React.js", "Next.js"]),
            SkillGroup(category="Mobile", skills=["Android", "React Native"]),
            SkillGroup(category="Backend & Architecture", skills=["Node.js", "Express.js", "REST APIs"]),
            SkillGroup(category="Databases", skills=["MongoDB", "PostgreSQL"]),
            SkillGroup(category="Tools", skills=["Git"]),
        ],
    )
    md = resume_to_markdown(resume, target_title="Senior Developer", target_company="Acme Corp")

    # Target Role header must NOT appear
    assert "Target Role" not in md

    # Distinct categories must be rendered as bullet points with bold categories
    assert "- **Languages**: JavaScript, TypeScript, Python" in md
    assert "- **Frontend**: React.js, Next.js" in md
    assert "- **Mobile**: Android, React Native" in md
    assert "- **Backend & Architecture**: Node.js, Express.js, REST APIs" in md
    assert "- **Databases**: MongoDB, PostgreSQL" in md
    assert "- **Tools**: Git" in md
