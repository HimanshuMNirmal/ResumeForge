"""Integration tests for the auth endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def registered_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "Secure123",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "Password1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@example.com"


async def test_register_duplicate_email(client: AsyncClient, registered_user):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Test2",
        "email": "test@example.com",
        "password": "Secure123",
    })
    assert resp.status_code == 409


async def test_login_success(client: AsyncClient, registered_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Secure123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client: AsyncClient, registered_user):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/profile")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no credentials


async def test_protected_route_with_token(client: AsyncClient, registered_user):
    token = registered_user["access_token"]
    resp = await client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
