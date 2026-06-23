"""
Shared pytest fixtures for the MediQuery test suite.

Tests that only exercise pure-Python logic (auth, JWT, roles) use no fixtures.
Tests that exercise the FastAPI app use the `client` fixture below.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """A FastAPI test client shared across the session."""
    return TestClient(app)


@pytest.fixture(scope="session")
def doctor_token(client: TestClient) -> str:
    """Pre-authenticated JWT for the demo Doctor user."""
    response = client.post(
        "/login",
        json={"username": "dr.bijoy", "password": "doctor123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.fixture(scope="session")
def nurse_token(client: TestClient) -> str:
    """Pre-authenticated JWT for the demo Nurse user."""
    response = client.post(
        "/login",
        json={"username": "nurse.priya", "password": "nurse123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.fixture(scope="session")
def billing_token(client: TestClient) -> str:
    """Pre-authenticated JWT for the demo Billing user."""
    response = client.post(
        "/login",
        json={"username": "billing.niloy", "password": "billing123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]
