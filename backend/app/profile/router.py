"""Profile router: /api/v1/profile endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.auth import get_current_user
from ..auth.models import User
from .import_export import SAMPLE_PROFILE, validate_import_json
from .schemas import (
    BasicsUpdate,
    EducationUpdate,
    ExperienceUpdate,
    PreferencesUpdate,
    ProfileOut,
    ProjectsUpdate,
    SkillsUpdate,
)
from .service import (
    apply_basics,
    apply_education,
    apply_experience,
    apply_preferences,
    apply_projects,
    apply_skills,
    get_or_create_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    return ProfileOut.model_validate(profile)


@router.patch("/basics", response_model=ProfileOut)
async def update_basics(
    body: BasicsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    await apply_basics(profile, body.model_dump(exclude_none=True))
    await db.flush()
    return ProfileOut.model_validate(profile)


@router.patch("/preferences", response_model=ProfileOut)
async def update_preferences(
    body: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    await apply_preferences(profile, body.model_dump(exclude_none=True))
    await db.flush()
    return ProfileOut.model_validate(profile)


@router.patch("/experience", response_model=ProfileOut)
async def update_experience(
    body: ExperienceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    await apply_experience(profile, body.experience)
    await db.flush()
    return ProfileOut.model_validate(profile)


@router.patch("/skills", response_model=ProfileOut)
async def update_skills(
    body: SkillsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    await apply_skills(profile, body.skills, body.summary_facts, body.never_claim)
    await db.flush()
    return ProfileOut.model_validate(profile)


@router.patch("/education", response_model=ProfileOut)
async def update_education(
    body: EducationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    await apply_education(profile, body.education, body.certifications)
    await db.flush()
    return ProfileOut.model_validate(profile)


@router.patch("/projects", response_model=ProfileOut)
async def update_projects(
    body: ProjectsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    await apply_projects(profile, body.projects)
    await db.flush()
    return ProfileOut.model_validate(profile)


# ── Import / Export ───────────────────────────────────────────────────────────

@router.get("/export", summary="Download your full profile as a JSON file")
async def export_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the user's complete profile as a downloadable JSON file."""
    profile = await get_or_create_profile(current_user.id, db)
    data = ProfileOut.model_validate(profile)

    # Build the export dict (matches the import format)
    export_dict = {
        "basics": {
            "full_name": data.full_name,
            "email": data.email,
            "phone": data.phone,
            "location": data.location,
            "links": [lnk.model_dump() for lnk in data.links],
        },
        "preferences": {
            "career_stage": data.career_stage,
            "max_pages": data.max_pages,
            "date_format": data.date_format,
            "paper_size": data.paper_size,
        },
        "summary_facts": data.summary_facts,
        "skills": [s.model_dump() for s in data.skills],
        "experience": [e.model_dump() for e in data.experience],
        "projects": [p.model_dump() for p in data.projects],
        "education": [e.model_dump() for e in data.education],
        "certifications": [c.model_dump() for c in data.certifications],
        "never_claim": data.never_claim,
    }

    filename = f"profile_{(data.full_name or 'export').replace(' ', '_').lower()}.json"
    return Response(
        content=json.dumps(export_dict, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sample", summary="Download a fully annotated sample profile JSON")
async def download_sample_profile():
    """
    Returns a sample profile JSON you can use as a template.
    No authentication required so users can get the format before registering.
    """
    return Response(
        content=json.dumps(SAMPLE_PROFILE, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="profile_sample.json"'},
    )


@router.post("/import", response_model=ProfileOut, summary="Import profile from a JSON file")
async def import_profile(
    file: UploadFile = File(..., description="A JSON file matching the profile schema"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates and imports a JSON profile file.

    - If the JSON is structurally valid, **replaces** the current profile with the imported data.
    - If validation fails, returns HTTP 422 with a detailed list of field-level errors.
    - Returns the saved profile on success.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted")

    raw_bytes = await file.read()
    if len(raw_bytes) > 2 * 1024 * 1024:  # 2 MB max
        raise HTTPException(status_code=413, detail="File too large (max 2 MB)")

    try:
        raw_dict = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    if not isinstance(raw_dict, dict):
        raise HTTPException(status_code=422, detail="JSON root must be an object, not a list or primitive")

    is_valid, errors = validate_import_json(raw_dict)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Profile JSON has {len(errors)} validation error(s). Fix them and try again.",
                "errors": errors,
            },
        )

    # Apply all sections to the profile
    profile = await get_or_create_profile(current_user.id, db)
    basics = raw_dict.get("basics", {})
    prefs = raw_dict.get("preferences", {})

    # Apply basics directly
    profile.full_name = basics.get("full_name") or profile.full_name
    profile.email = basics.get("email") or profile.email
    profile.phone = basics.get("phone") or profile.phone
    profile.location = basics.get("location") or profile.location
    profile.links = basics.get("links", profile.links)

    # Apply preferences
    profile.career_stage = prefs.get("career_stage", profile.career_stage)
    profile.max_pages = prefs.get("max_pages", profile.max_pages)
    profile.date_format = prefs.get("date_format", profile.date_format)
    profile.paper_size = prefs.get("paper_size", profile.paper_size)

    # Apply rich sections
    profile.summary_facts = raw_dict.get("summary_facts", profile.summary_facts)
    profile.skills = raw_dict.get("skills", profile.skills)
    profile.experience = raw_dict.get("experience", profile.experience)
    profile.projects = raw_dict.get("projects", profile.projects)
    profile.education = raw_dict.get("education", profile.education)
    profile.certifications = raw_dict.get("certifications", profile.certifications)
    profile.never_claim = raw_dict.get("never_claim", profile.never_claim)

    await db.flush()
    return ProfileOut.model_validate(profile)
