from uuid import uuid4
import pytest
from app.db import models


@pytest.mark.asyncio
async def test_get_smoelen_and_smoel_album(admin_client, db_session):
    smoel_id = uuid4()
    item_id = uuid4()

    db_item = models.Item(
        id=item_id,
        path="tests/test_full.jpg",
        cover_path="tests/test_cover.jpg",
        type=models.Type.IMAGE,
        width=100,
        height=100,
    )
    db_smoel = models.Smoel(
        id=smoel_id,
        name="Test Person",
        preview_id=item_id,
    )
    db_smoel.items.append(db_item)
    db_session.add(db_item)
    db_session.add(db_smoel)
    await db_session.commit()

    # Test GET /smoelen
    response = await admin_client.get(
        "/smoelen", headers={"Authorization": "Bearer mock_token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    target = next((s for s in data if s["id"] == str(smoel_id)), None)
    assert target is not None
    assert target["name"] == "Test Person"
    assert target["preview"]["id"] == str(item_id)
    assert "signature=" in target["preview"]["cover_path"]
    assert len(target["items"]) == 1
    assert target["items"][0]["id"] == str(item_id)

    # Test GET /smoelen/{smoel_id}
    response = await admin_client.get(
        f"/smoelen/{smoel_id}", headers={"Authorization": "Bearer mock_token"}
    )
    assert response.status_code == 200
    smoel_data = response.json()
    assert smoel_data["id"] == str(smoel_id)
    assert smoel_data["name"] == "Test Person"
    assert len(smoel_data["items"]) == 1
    assert smoel_data["items"][0]["id"] == str(item_id)
    assert "signature=" in smoel_data["items"][0]["path"]
