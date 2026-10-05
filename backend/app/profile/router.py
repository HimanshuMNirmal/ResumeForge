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


def _format_profile_for_frontend(profile: Profile) -> dict:
    links = profile.links or []
    linkedin = ""
    github = ""
    portfolio = ""
    for lnk in links:
        if isinstance(lnk, dict):
            lbl = lnk.get("label", "").lower()
            url = lnk.get("url", "")
            if "linkedin" in lbl:
                linkedin = url
            elif "github" in lbl:
                github = url
            elif "portfolio" in lbl:
                portfolio = url

    from resume_builder.taxonomy import classify_skill

    skills_dict = {
        "languages": [],
        "frontend": [],
        "mobile": [],
        "backend": [],
        "databases": [],
        "cloud_devops": [],
        "tools": [],
        "frameworks": [],
        "soft": [],
    }

    def _assign(sk_name: str, given_cat: str = ""):
        name_clean = str(sk_name).strip()
        if not name_clean:
            return
        cat = classify_skill(name_clean, existing_category=given_cat).lower()
        if "language" in cat:
            target = "languages"
        elif "frontend" in cat:
            target = "frontend"
        elif "mobile" in cat:
            target = "mobile"
        elif "database" in cat:
            target = "databases"
        elif "cloud" in cat or "devops" in cat:
            target = "cloud_devops"
        elif "backend" in cat or "architecture" in cat or "ai" in cat or "blockchain" in cat:
            target = "backend"
        elif "soft" in cat:
            target = "soft"
        else:
            target = "tools"
        if name_clean not in skills_dict[target]:
            skills_dict[target].append(name_clean)

    if isinstance(profile.skills, dict):
        for k, items in profile.skills.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        _assign(item.get("name", ""), item.get("category", k))
                    elif isinstance(item, str):
                        _assign(item, "" if k in ("tools", "frameworks") else k)
    elif isinstance(profile.skills, list):
        for s in profile.skills:
            if isinstance(s, dict):
                _assign(s.get("name", ""), s.get("category", ""))
            elif isinstance(s, str):
                _assign(s, "")

    experience = []
    if isinstance(profile.experience, list):
        for i, exp in enumerate(profile.experience):
            if isinstance(exp, dict):
                experience.append({
                    "id": exp.get("id") or f"exp-{i+1:03d}",
                    "company": exp.get("company", ""),
                    "role": exp.get("role") or exp.get("title", ""),
                    "start_date": exp.get("start_date") or exp.get("start", ""),
                    "end_date": exp.get("end_date") or exp.get("end", None),
                    "bullets": [
                        {
                            "id": b.get("id") or f"b-{j+1:03d}",
                            "text": b.get("text", "") if isinstance(b, dict) else str(b),
                            "skills": b.get("skills", []) if isinstance(b, dict) else [],
                        }
                        for j, b in enumerate(exp.get("bullets", []))
                    ],
                })

    education = []
    if isinstance(profile.education, list):
        for ed in profile.education:
            if isinstance(ed, dict):
                education.append({
                    "institution": ed.get("institution", ""),
                    "degree": ed.get("degree", ""),
                    "field": ed.get("field") or (ed.get("details", [""])[0] if ed.get("details") else ""),
                    "start_date": ed.get("start_date") or ed.get("start", ""),
                    "end_date": ed.get("end_date") or ed.get("end", None),
                })

    certs = []
    if isinstance(profile.certifications, list):
        for c in profile.certifications:
            if isinstance(c, dict):
                certs.append(c.get("name", ""))
            else:
                certs.append(str(c))

    projects = []
    if isinstance(profile.projects, list):
        for i, pr in enumerate(profile.projects):
            if isinstance(pr, dict):
                projects.append({
                    "id": pr.get("id") or f"proj-{i+1:03d}",
                    "name": pr.get("name", ""),
                    "url": pr.get("url", ""),
                    "skills": pr.get("skills", []) if isinstance(pr.get("skills"), list) else [],
                    "bullets": [
                        {
                            "id": b.get("id") or f"b-proj-{j+1:03d}",
                            "text": b.get("text", "") if isinstance(b, dict) else str(b),
                            "skills": b.get("skills", []) if isinstance(b, dict) else [],
                        }
                        for j, b in enumerate(pr.get("bullets", []))
                    ],
                })

    return {
        "full_name": profile.full_name or "",
        "email": profile.email or "",
        "phone": profile.phone or "",
        "location": profile.location or "",
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
        "experience": experience,
        "projects": projects,
        "education": education,
        "certifications": certs,
        "skills": skills_dict,
    }


@router.get("")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)
    return _format_profile_for_frontend(profile)


@router.put("")
async def update_profile_full(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_profile(current_user.id, db)

    if "full_name" in body:
        profile.full_name = body["full_name"]
    if "email" in body:
        profile.email = body["email"]
    if "phone" in body:
        profile.phone = body["phone"]
    if "location" in body:
        profile.location = body["location"]

    links = []
    if body.get("linkedin"):
        links.append({"label": "LinkedIn", "url": body["linkedin"]})
    if body.get("github"):
        links.append({"label": "GitHub", "url": body["github"]})
    if body.get("portfolio"):
        links.append({"label": "Portfolio", "url": body["portfolio"]})
    if links:
        profile.links = links

    if "skills" in body:
        new_skills = body["skills"]
        # If user passed categorized dict, auto-enroll any skills found on experience bullets
        if isinstance(new_skills, dict):
            from resume_builder.taxonomy import classify_skill

            all_known = set()
            for cat, items in new_skills.items():
                if isinstance(items, list):
                    all_known.update(str(x).strip().lower() for x in items)

            bullets_to_scan = []
            if "experience" in body and isinstance(body["experience"], list):
                for exp in body["experience"]:
                    if isinstance(exp, dict):
                        bullets_to_scan.extend(exp.get("bullets", []))
            if "projects" in body and isinstance(body["projects"], list):
                for pr in body["projects"]:
                    if isinstance(pr, dict):
                        bullets_to_scan.extend(pr.get("bullets", []))

            for b in bullets_to_scan:
                if isinstance(b, dict):
                    for sk in b.get("skills", []):
                        sk_str = str(sk).strip()
                        if sk_str and sk_str.lower() not in all_known:
                            cat_raw = classify_skill(sk_str).lower()
                            if "database" in cat_raw:
                                target_k = "databases"
                            elif "frontend" in cat_raw:
                                target_k = "frontend"
                            elif "mobile" in cat_raw:
                                target_k = "mobile"
                            elif "backend" in cat_raw or "architecture" in cat_raw or "ai" in cat_raw or "blockchain" in cat_raw:
                                target_k = "backend"
                            elif "cloud" in cat_raw or "devops" in cat_raw:
                                target_k = "cloud_devops"
                            elif "language" in cat_raw:
                                target_k = "languages"
                            elif "soft" in cat_raw:
                                target_k = "soft"
                            else:
                                target_k = "tools"
                            new_skills.setdefault(target_k, []).append(sk_str)
                            all_known.add(sk_str.lower())
        profile.skills = new_skills

    if "experience" in body and isinstance(body["experience"], list):
        exp_list = []
        for i, exp in enumerate(body["experience"]):
            if isinstance(exp, dict):
                exp_list.append({
                    "id": exp.get("id") or f"exp-{i+1:03d}",
                    "company": exp.get("company", ""),
                    "title": exp.get("role") or exp.get("title", ""),
                    "title_aliases": exp.get("title_aliases", []),
                    "location": exp.get("location", ""),
                    "start": exp.get("start_date") or exp.get("start", ""),
                    "end": exp.get("end_date") or exp.get("end", None),
                    "bullets": [
                        {
                            "id": b.get("id") or f"b-{j+1:03d}",
                            "text": b.get("text", "") if isinstance(b, dict) else str(b),
                            "skills": b.get("skills", []) if isinstance(b, dict) else [],
                            "metrics": b.get("metrics", []) if isinstance(b, dict) else [],
                            "themes": b.get("themes", []) if isinstance(b, dict) else [],
                        }
                        for j, b in enumerate(exp.get("bullets", []))
                    ],
                })
        profile.experience = exp_list

    if "projects" in body and isinstance(body["projects"], list):
        proj_list = []
        for i, pr in enumerate(body["projects"]):
            if isinstance(pr, dict):
                proj_list.append({
                    "id": pr.get("id") or f"proj-{i+1:03d}",
                    "name": pr.get("name", ""),
                    "url": pr.get("url", ""),
                    "skills": pr.get("skills", []) if isinstance(pr.get("skills"), list) else [],
                    "bullets": [
                        {
                            "id": b.get("id") or f"b-proj-{j+1:03d}",
                            "text": b.get("text", "") if isinstance(b, dict) else str(b),
                            "skills": b.get("skills", []) if isinstance(b, dict) else [],
                            "metrics": b.get("metrics", []) if isinstance(b, dict) else [],
                            "themes": b.get("themes", []) if isinstance(b, dict) else [],
                        }
                        for j, b in enumerate(pr.get("bullets", []))
                    ],
                })
        profile.projects = proj_list

    if "education" in body and isinstance(body["education"], list):
        ed_list = []
        for i, ed in enumerate(body["education"]):
            if isinstance(ed, dict):
                details = [ed.get("field", "")] if ed.get("field") else ed.get("details", [])
                ed_list.append({
                    "id": ed.get("id") or f"edu-{i+1:03d}",
                    "institution": ed.get("institution", ""),
                    "degree": ed.get("degree", ""),
                    "location": ed.get("location", ""),
                    "start": ed.get("start_date") or ed.get("start", ""),
                    "end": ed.get("end_date") or ed.get("end", None),
                    "details": details,
                })
        profile.education = ed_list

    if "certifications" in body and isinstance(body["certifications"], list):
        profile.certifications = [
            {"id": f"cert-{i+1:03d}", "name": c if isinstance(c, str) else c.get("name", "")}
            for i, c in enumerate(body["certifications"])
        ]

    await db.flush()
    return _format_profile_for_frontend(profile)



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

@router.post("/import", summary="Import profile from a JSON file")
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
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"Profile JSON has {len(errors)} validation error(s). Fix them and try again.",
                "errors": errors,
            },
        )

    # Apply all sections to the profile
    profile = await get_or_create_profile(current_user.id, db)
    basics = raw_dict.get("basics", {})
    prefs = raw_dict.get("preferences", {})

    # Apply basics directly
    profile.full_name = basics.get("full_name") or basics.get("name") or profile.full_name
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
    return {
        "message": "Profile imported successfully",
        "profile": _format_profile_for_frontend(profile),
    }
