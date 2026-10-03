"""Tests for profile import/export endpoints."""
from __future__ import annotations

import json
import io
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_headers(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Export User",
        "email": "export@example.com",
        "password": "Secure123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


VALID_IMPORT = {
    "basics": {
        "full_name": "Alice Johnson",
        "email": "alice@example.com",
        "phone": "+1-555-9999",
        "location": "New York, NY",
        "links": [{"label": "GitHub", "url": "https://github.com/alice"}],
    },
    "preferences": {"career_stage": "experienced", "max_pages": 1, "date_format": "MMM YYYY", "paper_size": "Letter"},
    "summary_facts": ["10 years of software engineering experience"],
    "skills": [
        {"name": "Python", "category": "Languages", "level": "strong", "years": 7, "aliases": []},
    ],
    "experience": [
        {
            "id": "exp-001",
            "company": "Tech Co",
            "title": "Staff Engineer",
            "location": "NYC",
            "start": "Jan 2020",
            "end": None,
            "bullets": [
                {
                    "id": "b-001",
                    "text": "Architected platform serving 50M users.",
                    "skills": ["Python"],
                    "metrics": ["50M users"],
                    "themes": ["scale"],
                }
            ],
        }
    ],
    "projects": [],
    "education": [
        {
            "id": "edu-001",
            "institution": "MIT",
            "degree": "M.S. Computer Science",
            "start": "Sep 2012",
            "end": "Jun 2014",
            "details": [],
        }
    ],
    "certifications": [],
    "never_claim": ["Blockchain"],
}


# ── Sample download (no auth) ──────────────────────────────────────────────────

async def test_download_sample_no_auth(client: AsyncClient):
    resp = await client.get("/api/v1/profile/sample")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert "content-disposition" in resp.headers
    data = resp.json()
    assert "basics" in data
    assert "experience" in data
    assert "skills" in data


# ── Export ────────────────────────────────────────────────────────────────────

async def test_export_profile(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/profile/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "content-disposition" in resp.headers
    data = resp.json()
    assert "basics" in data
    assert "skills" in data


# ── Import — valid JSON ────────────────────────────────────────────────────────

async def test_import_valid_profile(client: AsyncClient, auth_headers):
    file_bytes = json.dumps(VALID_IMPORT).encode()
    resp = await client.post(
        "/api/v1/profile/import",
        headers=auth_headers,
        files={"file": ("profile.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Alice Johnson"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "Python"
    assert len(data["experience"]) == 1


async def test_import_then_export_roundtrip(client: AsyncClient, auth_headers):
    """Import → export should preserve all data."""
    file_bytes = json.dumps(VALID_IMPORT).encode()
    await client.post(
        "/api/v1/profile/import",
        headers=auth_headers,
        files={"file": ("profile.json", io.BytesIO(file_bytes), "application/json")},
    )
    export_resp = await client.get("/api/v1/profile/export", headers=auth_headers)
    exported = export_resp.json()
    assert exported["basics"]["full_name"] == "Alice Johnson"
    assert len(exported["experience"]) == 1
    assert exported["never_claim"] == ["Blockchain"]


# ── Import — invalid cases ─────────────────────────────────────────────────────

async def test_import_not_json_extension(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/profile/import",
        headers=auth_headers,
        files={"file": ("profile.txt", io.BytesIO(b"{}"), "text/plain")},
    )
    assert resp.status_code == 400


async def test_import_invalid_json_syntax(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/profile/import",
        headers=auth_headers,
        files={"file": ("profile.json", io.BytesIO(b"{invalid json"), "application/json")},
    )
    assert resp.status_code == 400
    assert "Invalid JSON" in resp.json()["detail"]


async def test_import_missing_required_field(client: AsyncClient, auth_headers):
    bad = {**VALID_IMPORT, "basics": {"full_name": "", "email": ""}}  # empty required fields
    file_bytes = json.dumps(bad).encode()
    resp = await client.post(
        "/api/v1/profile/import",
        headers=auth_headers,
        files={"file": ("profile.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "errors" in detail
    assert len(detail["errors"]) > 0


async def test_import_duplicate_bullet_ids(client: AsyncClient, auth_headers):
    bad = {**VALID_IMPORT}
    bad["experience"] = [
        {
            "id": "exp-001",
            "company": "A",
            "title": "Engineer",
            "start": "2020",
            "bullets": [{"id": "DUPE", "text": "foo", "skills": [], "metrics": [], "themes": []}],
        },
        {
            "id": "exp-002",
            "company": "B",
            "title": "Engineer",
            "start": "2019",
            "end": "2020",
            "bullets": [{"id": "DUPE", "text": "bar", "skills": [], "metrics": [], "themes": []}],  # duplicate
        },
    ]
    file_bytes = json.dumps(bad).encode()
    resp = await client.post(
        "/api/v1/profile/import",
        headers=auth_headers,
        files={"file": ("profile.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert resp.status_code == 422
    errors = resp.json()["detail"]["errors"]
    assert any("DUPE" in e for e in errors)
