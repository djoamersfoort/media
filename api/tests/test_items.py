import pytest
import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock, mock_open
import io


@pytest.mark.asyncio
async def test_upload_items(admin_client, db_session):
    from app.db import models

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Upload Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    file_content = b"fake image content"
    file = io.BytesIO(file_content)

    item_id = uuid4()

    async def mock_create_item(db, user, item_bytes, content_type, album_id, date=None):
        db_item = models.Item(
            id=item_id,
            user=user.id if user else None,
            album_id=album_id,
            type=models.Type.IMAGE,
            width=100,
            height=100,
            cover_path="data/items/test/cover.jpg",
            path="data/items/test/item.jpg",
            date=datetime.datetime.now(),
        )
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)
        return db_item

    with patch("app.db.crud.create_item", side_effect=mock_create_item):
        files = [("items", ("test.jpg", file, "image/jpeg"))]
        response = await admin_client.post(
            f"/items/{album_id}",
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(item_id)
    assert "signature=" in data[0]["path"]
    assert "signature=" in data[0]["cover_path"]
    assert data[0]["smoelen"] == []


@pytest.mark.asyncio
async def test_upload_items_real_create_item(admin_client, db_session):
    from app.db import models
    from PIL import Image

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Real Upload Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    # Create mock PIL image
    mock_img = MagicMock()
    mock_img.size = (800, 600)
    mock_img.__enter__.return_value = mock_img

    with patch("os.mkdir"), patch("builtins.open", mock_open()), patch(
        "os.remove"
    ), patch("PIL.Image.open", return_value=mock_img):
        files = [("items", ("photo.jpg", io.BytesIO(b"fake_jpeg_data"), "image/jpeg"))]
        response = await admin_client.post(
            f"/items/{album_id}",
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "id" in data[0]
    assert "signature=" in data[0]["path"]
    assert "signature=" in data[0]["cover_path"]
    assert data[0]["smoelen"] == []


@pytest.mark.asyncio
async def test_upload_items_unidentified_image_error(admin_client, db_session):
    from app.db import models
    from PIL import UnidentifiedImageError

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Error Upload Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    with patch("os.mkdir"), patch("builtins.open", mock_open()), patch(
        "os.remove"
    ) as mock_remove, patch("shutil.rmtree") as mock_rmtree, patch(
        "PIL.Image.open",
        side_effect=UnidentifiedImageError("cannot identify image file"),
    ):
        files = [("items", ("corrupt.jpg", io.BytesIO(b"corrupt_data"), "image/jpeg"))]
        response = await admin_client.post(
            f"/items/{album_id}",
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid item"
    # Verify temp file was removed
    assert mock_remove.call_count >= 1
    # Verify created item directory was cleaned up
    assert mock_rmtree.call_count >= 1


@pytest.mark.asyncio
async def test_upload_items_mixed_valid_and_invalid(admin_client, db_session):
    from app.db import models
    from PIL import UnidentifiedImageError

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Mixed Upload Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    mock_img = MagicMock()
    mock_img.size = (800, 600)
    mock_img.__enter__.return_value = mock_img

    with patch("os.mkdir"), patch("builtins.open", mock_open()), patch(
        "os.remove"
    ), patch("shutil.rmtree"), patch(
        "PIL.Image.open",
        side_effect=[
            UnidentifiedImageError("cannot identify image file"),
            mock_img,
            mock_img,
        ],
    ):
        files = [
            ("items", ("corrupt.jpg", io.BytesIO(b"corrupt"), "image/jpeg")),
            ("items", ("valid.jpg", io.BytesIO(b"valid"), "image/jpeg")),
        ]
        response = await admin_client.post(
            f"/items/{album_id}",
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid item"


@pytest.mark.asyncio
async def test_upload_items_invalid_content_type(admin_client, db_session):
    from app.db import models

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Invalid Content Type Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    files = [("items", ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))]
    response = await admin_client.post(
        f"/items/{album_id}",
        files=files,
        headers={"Authorization": "Bearer mock_token"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid item"


@pytest.mark.asyncio
async def test_upload_items_video_success(admin_client, db_session):
    from app.db import models

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Video Upload Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    mock_probe = {"streams": [{"width": 1920, "height": 1080}]}

    with patch("os.mkdir"), patch("builtins.open", mock_open()), patch(
        "os.remove"
    ), patch("ffmpeg.probe", return_value=mock_probe) as mock_ffmpeg_probe, patch(
        "ffmpeg.run"
    ) as mock_ffmpeg_run:
        files = [("items", ("video.mp4", io.BytesIO(b"fake_video_data"), "video/mp4"))]
        response = await admin_client.post(
            f"/items/{album_id}",
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "id" in data[0]
    assert "signature=" in data[0]["path"]
    assert "signature=" in data[0]["cover_path"]
    assert mock_ffmpeg_probe.call_count == 1
    assert mock_ffmpeg_run.call_count == 2


@pytest.mark.asyncio
async def test_upload_items_ffmpeg_error(admin_client, db_session):
    from app.db import models
    import ffmpeg

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Video Error Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    with patch("os.mkdir"), patch("builtins.open", mock_open()), patch(
        "os.remove"
    ) as mock_remove, patch("shutil.rmtree") as mock_rmtree, patch(
        "ffmpeg.probe", side_effect=ffmpeg.Error("probe error", "", "")
    ):
        files = [("items", ("video.mp4", io.BytesIO(b"corrupt_video"), "video/mp4"))]
        response = await admin_client.post(
            f"/items/{album_id}",
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid item"
    assert mock_remove.call_count >= 1
    assert mock_rmtree.call_count >= 1


@pytest.mark.asyncio
async def test_upload_items_album_not_found(admin_client, db_session):
    album_id = uuid4()
    files = [("items", ("test.jpg", io.BytesIO(b"fake"), "image/jpeg"))]
    response = await admin_client.post(
        f"/items/{album_id}",
        files=files,
        headers={"Authorization": "Bearer mock_token"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Album not found"


@pytest.mark.asyncio
async def test_get_item_full(client, db_session):
    from app.db import models

    item_id = uuid4()
    db_item = models.Item(
        id=item_id,
        path="tests/conftest.py",  # Just need a real file for FileResponse
        cover_path="tests/conftest.py",
        type=models.Type.IMAGE,
        width="100",
        height="100",
    )
    db_session.add(db_item)
    await db_session.commit()

    expiry = 2000000000.0  # Way in the future
    signature = "mock_signature_hex"

    # Mock verify_signature to return True
    with patch("app.main.verify_signature", return_value=True):
        response = await client.get(
            f"/items/{item_id}/{expiry}/full?signature={signature}"
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_items(admin_client, db_session):
    from app.db import models

    album_id = uuid4()
    db_album = models.Album(
        id=album_id, name="Delete Album", description="Desc", order=0
    )
    db_session.add(db_album)
    await db_session.commit()

    item_id = uuid4()
    db_item = models.Item(
        id=item_id,
        album_id=album_id,
        path=f"data/items/{album_id}/{item_id}/item.jpg",
        cover_path=f"data/items/{album_id}/{item_id}/cover.jpg",
        type=models.Type.IMAGE,
        width=100,
        height=100,
    )
    db_session.add(db_item)
    await db_session.commit()

    with patch("os.remove") as mock_remove, patch("os.rmdir") as mock_rmdir, patch(
        "app.db.crud.get_album"
    ) as mock_get_album:
        # Mock get_album to return the album data, as delete_items returns it
        # We return a schema instead of a model to avoid SQLAlchemy async issues during validation
        from app.db import schemas

        mock_get_album.return_value = schemas.Album(
            id=album_id,
            name="Delete Album",
            description="Desc",
            order=0,
            items=[],
            preview=None,
        )

        response = await admin_client.post(
            f"/items/{album_id}/delete",
            json=[str(item_id)],
        )

    assert response.status_code == 200
    # Verify item is deleted from DB
    result = await db_session.get(models.Item, item_id)
    assert result is None
    # Verify os.remove was called for both path and cover_path
    assert mock_remove.call_count == 2
    mock_remove.assert_any_call(db_item.path)
    mock_remove.assert_any_call(db_item.cover_path)
    # Verify os.rmdir was called for the item directory
    mock_rmdir.assert_called_once_with(f"data/items/{album_id}/{item_id}")
