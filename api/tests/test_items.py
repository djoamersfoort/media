import pytest
import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock
import io

@pytest.mark.asyncio
async def test_upload_items(admin_client, db_session):
    from app.db import models
    album_id = uuid4()
    db_album = models.Album(id=album_id, name="Upload Album", description="Desc", order=0)
    db_session.add(db_album)
    await db_session.commit()

    # Create a mock file
    file_content = b"fake image content"
    file = io.BytesIO(file_content)
    
    # Mock the internal create_item calls to avoid ffmpeg/PIL dependencies
    mock_item = MagicMock(spec=models.Item)
    mock_item.id = uuid4()
    mock_item.album_id = album_id
    mock_item.path = "data/items/test/item.jpg"
    mock_item.cover_path = "data/items/test/cover.jpg"
    mock_item.width = 100
    mock_item.height = 100
    mock_item.type = models.Type.IMAGE
    mock_item.date = None

    with patch("app.db.crud.create_item", return_value=mock_item):
        mock_item.user = "test_user"
        mock_item.date = datetime.datetime.now()
        files = [("items", ("test.jpg", file, "image/jpeg"))]
        response = await admin_client.post(f"/items/{album_id}", files=files, headers={"Authorization": "Bearer mock_token"})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(mock_item.id)

@pytest.mark.asyncio
async def test_get_item_full(client, db_session):
    from app.db import models
    item_id = uuid4()
    db_item = models.Item(
        id=item_id, 
        path="tests/conftest.py", # Just need a real file for FileResponse
        cover_path="tests/conftest.py",
        type=models.Type.IMAGE,
        width="100",
        height="100"
    )
    db_session.add(db_item)
    await db_session.commit()

    expiry = 2000000000.0 # Way in the future
    signature = "mock_signature_hex"
    
    # Mock verify_signature to return True
    with patch("app.main.verify_signature", return_value=True):
        response = await client.get(f"/items/{item_id}/{expiry}/full?signature={signature}")
    
    assert response.status_code == 200
