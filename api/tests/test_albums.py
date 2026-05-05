from unittest.mock import patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_create_album_admin(admin_client):
    album_data = {"name": "Test Album", "description": "Test Description"}
    with patch("os.mkdir"):
        response = await admin_client.post("/albums", json=album_data, headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Album"
    assert data["description"] == "Test Description"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_album_non_admin(regular_client):
    album_data = {"name": "Test Album", "description": "Test Description"}
    response = await regular_client.post("/albums", json=album_data, headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authorized"

@pytest.mark.asyncio
async def test_get_albums(admin_client, db_session):
    from app.db import models
    album_id = uuid4()
    db_album = models.Album(id=album_id, name="Existing Album", description="Desc", order=0)
    db_session.add(db_album)
    await db_session.commit()

    response = await admin_client.get("/albums", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(a["name"] == "Existing Album" for a in data)

@pytest.mark.asyncio
async def test_get_album_details(admin_client, db_session):
    from app.db import models
    album_id = uuid4()
    db_album = models.Album(id=album_id, name="Detailed Album", description="Detailed Desc", order=0)
    db_session.add(db_album)
    await db_session.commit()

    response = await admin_client.get(f"/albums/{album_id}", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Detailed Album"
    assert data["id"] == str(album_id)

@pytest.mark.asyncio
async def test_update_album(admin_client, db_session):
    from app.db import models
    album_id = uuid4()
    db_album = models.Album(id=album_id, name="Old Name", description="Old Desc", order=0)
    db_session.add(db_album)
    await db_session.commit()

    update_data = {"name": "New Name", "description": "New Desc"}
    response = await admin_client.patch(f"/albums/{album_id}", json=update_data, headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "New Desc"
    assert "items" in data
    assert data["items"] == []

@pytest.mark.asyncio
async def test_delete_album(admin_client, db_session):
    from app.db import models
    album_id = uuid4()
    db_album = models.Album(id=album_id, name="To Delete", description="Desc", order=0)
    db_session.add(db_album)
    await db_session.commit()

    with patch("os.path.exists", return_value=True), patch("os.rmdir"), patch("app.db.crud.delete_items"):
        response = await admin_client.delete(f"/albums/{album_id}", headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    assert response.json() == {"success": True}
