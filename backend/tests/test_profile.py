"""Integration tests for profile endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def auth_headers(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Profile User",
        "email": "profile@example.com",
        "password": "Secure123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_get_empty_profile(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["experience"] == []
    assert data["skills"] == []


async def test_update_basics(client: AsyncClient, auth_headers):
    resp = await client.patch("/api/v1/profile/basics", json={
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-1234",
        "location": "San Francisco, CA",
        "links": [{"label": "GitHub", "url": "https://github.com/johndoe"}],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "John Doe"
    assert len(data["links"]) == 1


async def test_update_skills(client: AsyncClient, auth_headers):
    resp = await client.patch("/api/v1/profile/skills", json={
        "skills": [
            {"name": "Python", "category": "Languages", "level": "strong"},
            {"name": "FastAPI", "category": "Frameworks", "level": "strong"},
        ],
        "summary_facts": ["5 years of Python experience"],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["skills"]) == 2
    assert data["summary_facts"] == ["5 years of Python experience"]


async def test_update_experience(client: AsyncClient, auth_headers):
    resp = await client.patch("/api/v1/profile/experience", json={
        "experience": [{
            "id": "exp-001",
            "company": "Acme Corp",
            "title": "Senior Engineer",
            "start": "2022-01",
            "end": None,
            "bullets": [
                {
                    "id": "b-001",
                    "text": "Built scalable APIs serving 10M+ requests/day",
                    "skills": ["Python", "FastAPI"],
                    "metrics": ["10M requests/day"],
                    "themes": ["scalability"],
                }
            ],
        }],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["experience"]) == 1
    assert data["experience"][0]["company"] == "Acme Corp"
