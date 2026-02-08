import uuid
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import pytest
import urllib.parse


@pytest.mark.asyncio
async def test_create_book(client: TestClient, token: str):
    data = {
        "title": "Count of Monte Cristo",
        "isbn": f"{uuid.uuid4()}",
        "genre": "mystery",
        "condition": "new",
    }
    
    response = client.post(
        "/v1/books",
        json=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_get_books(client: TestClient):
    response = client.get("/v1/books")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_book_by_date(client: TestClient, token: str):
    response = client.get(
        "/v1/books/getbydate",
        params={"date_param": str(datetime.now(timezone.utc)),"compare": "gt"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    now = urllib.parse.quote(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    response = client.get(f"v1/books/getbydate?date_param={now}&compare=gt")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_book(client: TestClient, token: str):
    data = {
        "title": "Count of Monte Cristo",
        "isbn": f"{uuid.uuid4()}",
        "genre": "mystery",
        "condition": "new",
    }
    response = client.post(
        "/v1/books",
        json=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {"create_datetimestamp": f"<{now}", "cores": "5"}

    response = client.post(
        "/v1/books/search",
        json=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
