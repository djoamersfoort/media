import asyncio
import datetime
import os
import shutil
from functools import lru_cache
from uuid import uuid4, UUID

import ffmpeg
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from PIL import Image
from fastapi import UploadFile, status
from fastapi.exceptions import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.orm import selectinload

from app.conf import settings
from app.db import models, schemas
from app.fileresponse import FastApiBaizeFileResponse as FileResponse


@lru_cache()
def get_signer():
    with open("data/private.key", "r", encoding="utf8") as buffer:
        key = buffer.read()

    return PKCS1_v1_5.new(RSA.import_key(key))


@lru_cache()
def get_verifier():
    with open("data/public.key", "r", encoding="utf8") as buffer:
        key = buffer.read()

    return PKCS1_v1_5.new(RSA.import_key(key))


def sign_url(url: str) -> str:
    signature = get_signer().sign(SHA256.new(url.encode("utf-8")))
    return f"{url}?signature={signature.hex()}"


def sign_item(item_data: models.Item) -> schemas.Item:
    item = schemas.Item.model_validate(item_data)
    expiry = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()

    item.cover_path = sign_url(f"{settings.base_url}/items/{item.id}/{expiry}/cover")
    item.path = sign_url(f"{settings.base_url}/items/{item.id}/{expiry}/full")

    return item


async def get_album(db: Session, album_id: UUID) -> schemas.Album:
    result = await db.execute(
        select(models.Album)
        .where(models.Album.id == album_id)
        .options(
            selectinload(models.Album.items).selectinload(models.Item.smoelen),
            selectinload(models.Album.preview).selectinload(models.Item.smoelen),
        )
    )
    db_album = result.scalar_one()
    album = schemas.Album.model_validate(db_album)
    if db_album.preview_id:
        album.preview = sign_item(db_album.preview)
    album.items = [sign_item(item) for item in album.items]

    return album


async def get_smoel_album(db: Session, smoel_id: UUID) -> schemas.SmoelAlbum:
    result = await db.execute(
        select(models.Smoel)
        .where(models.Smoel.id == smoel_id)
        .options(selectinload(models.Smoel.items).selectinload(models.Item.smoelen))
    )
    db_smoel = result.scalar_one()
    smoel = schemas.SmoelAlbum.model_validate(db_smoel)
    smoel.items = [sign_item(item) for item in smoel.items]

    return smoel


async def get_full(db: Session, item_id: UUID) -> FileResponse:
    result = await db.execute(select(models.Item).where(models.Item.id == item_id))
    item = result.scalar_one()

    return FileResponse(item.path)


async def get_cover(db: Session, item_id: UUID) -> FileResponse:
    result = await db.execute(select(models.Item).where(models.Item.id == item_id))
    item = result.scalar_one()

    return FileResponse(item.cover_path)


async def get_albums(db: Session) -> list[schemas.AlbumList]:
    result = await db.execute(
        select(models.Album).options(
            selectinload(models.Album.preview).selectinload(models.Item.smoelen)
        )
    )
    db_albums = result.scalars().all()
    result_list = []

    for db_album in db_albums:
        album = schemas.AlbumList.model_validate(db_album)
        if db_album.preview_id:
            album.preview = sign_item(db_album.preview)

        result_list.append(album)

    return result_list


async def get_smoelen_albums(db: Session) -> list[schemas.SmoelAlbumList]:
    result = await db.execute(
        select(models.Smoel).options(
            selectinload(models.Smoel.preview).selectinload(models.Item.smoelen),
            selectinload(models.Smoel.items).selectinload(models.Item.smoelen),
        )
    )
    smoelen = sorted(result.scalars().all(), key=lambda x: len(x.items), reverse=True)
    result_list = []

    for smoel_data in smoelen:
        smoel = schemas.SmoelAlbumList.model_validate(smoel_data)
        if smoel_data.preview_id:
            smoel.preview = sign_item(smoel_data.preview)
        smoel.items = [sign_item(item) for item in smoel_data.items[:2]]
        result_list.append(smoel)

    return result_list


async def create_album(db: Session, album: schemas.AlbumCreate) -> models.Album:
    album_id = uuid4()
    os.mkdir(f"data/items/{album_id}")

    result = await db.execute(select(func.count(models.Album.id)))
    total_albums = result.scalar_one()
    db_album = models.Album(
        id=album_id, name=album.name, description=album.description, order=total_albums
    )
    db.add(db_album)
    await db.commit()
    await db.refresh(db_album)

    return db_album


async def update_album(
    db: Session, album_id: UUID, album: schemas.AlbumCreate
) -> schemas.Album:
    result = await db.execute(select(models.Album).where(models.Album.id == album_id))
    db_album = result.scalar_one()
    db_album.name = album.name
    db_album.description = album.description
    await db.commit()

    return await get_album(db, album_id)


async def order_albums(db: Session, albums: list[schemas.AlbumOrder]):
    for album in albums:
        result = await db.execute(
            select(models.Album).where(models.Album.id == album.id)
        )
        db_album = result.scalar_one()
        db_album.order = album.order
    await db.commit()
    return await get_albums(db)


async def delete_album(db: Session, album_id: UUID):
    # Get the album first to check if it exists
    result = await db.execute(
        select(models.Album)
        .where(models.Album.id == album_id)
        .options(selectinload(models.Album.items))
    )
    db_album = result.scalar_one_or_none()
    if not db_album:
        return None

    # Get all items in the album to delete them first
    album_items = [item.id for item in db_album.items]

    # Delete all items in the album if there are any (this handles file cleanup too)
    if album_items:
        await delete_items(db, None, db_album.id, album_items)

    # Remove the album directory
    album_folder = f"data/items/{db_album.id}"
    if os.path.exists(album_folder):
        os.rmdir(album_folder)

    # Delete the album from database
    await db.delete(db_album)
    await db.commit()

    return True


async def create_item(
    db: Session,
    user: schemas.User | None,
    item: bytes,
    content_type: str,
    album_id: UUID | None,
    date: datetime = None,
):
    if not content_type or "/" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item"
        )

    # get type
    file_type_str = content_type.split("/")[0]
    if file_type_str not in ["image", "video"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item"
        )

    if file_type_str == "image":
        file_type = models.Type.IMAGE
    else:
        file_type = models.Type.VIDEO

    # write temp file
    item_id = uuid4()
    if album_id is None:
        album_folder = "data/items/smoelen"
        if not os.path.exists(album_folder):
            os.mkdir(album_folder)
    else:
        album_folder = f"data/items/{album_id}"
        if not os.path.exists(album_folder):
            os.mkdir(album_folder)

    item_folder = f"{album_folder}/{item_id}"
    temp_path = f"/tmp/{item_id}"

    if not os.path.exists(item_folder):
        os.mkdir(item_folder)

    with open(temp_path, "wb") as buffer:
        buffer.write(item)

    try:
        # get metadata
        if file_type == models.Type.IMAGE:
            with Image.open(temp_path) as img:
                width, height = img.size

                # create cover image
                cover_path = f"{item_folder}/cover.jpg"
                img.thumbnail((400, 400 * height // width))
                img.save(cover_path)

            path = f"{item_folder}/item.jpg"
            with Image.open(temp_path) as img:
                img.save(path)
        else:
            probe = await asyncio.to_thread(ffmpeg.probe, temp_path)
            width = probe["streams"][0]["width"]
            height = probe["streams"][0]["height"]

            # create cover image
            cover_path = f"{item_folder}/cover.jpg"
            stream = ffmpeg.input(temp_path)
            stream = ffmpeg.filter(stream, "scale", 400, -1)
            stream = ffmpeg.output(stream, cover_path, vframes=1)
            await asyncio.to_thread(ffmpeg.run, stream)

            # store optimized full size image/video
            path = f"{item_folder}/item.mp4"
            stream = ffmpeg.input(temp_path)
            stream = ffmpeg.output(stream, path, crf=23)
            await asyncio.to_thread(ffmpeg.run, stream)

        if user:
            user_id = user.id
        else:
            user_id = None

        db_item = models.Item(
            id=item_id,
            user=user_id,
            album_id=album_id,
            type=file_type,
            width=width,
            height=height,
            cover_path=cover_path,
            path=path,
            date=date,
        )
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)

        return db_item
    except HTTPException:
        shutil.rmtree(item_folder, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(item_folder, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item"
        )
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


async def create_items(
    db: Session,
    user: schemas.User | None,
    items: list[UploadFile],
    album_id: UUID | None,
    date: datetime = None,
) -> list[schemas.Item]:
    if album_id:
        album = await db.get(models.Album, album_id)
        if not album:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Album not found"
            )
        target_album_id = album.id
    else:
        target_album_id = None

    created_ids = []
    for item in items:
        db_item = await create_item(
            db, user, await item.read(), item.content_type, target_album_id, date
        )
        if db_item is not None:
            created_ids.append(db_item.id)

    if not created_ids:
        return []

    result = await db.execute(
        select(models.Item)
        .where(models.Item.id.in_(created_ids))
        .options(selectinload(models.Item.smoelen))
    )
    items_by_id = {item.id: item for item in result.scalars().all()}
    return [
        sign_item(items_by_id[item_id])
        for item_id in created_ids
        if item_id in items_by_id
    ]


async def delete_items(
    db: Session, user: schemas.User | None, album_id: UUID | None, items: list[UUID]
) -> schemas.Album | None:
    # Check if the album exists
    db_album = None
    if album_id:
        db_album = await db.get(models.Album, album_id)
    # First delete the items
    for item_id in items:
        db_item = await db.get(models.Item, item_id)
        if user is not None and db_item.user != user.id and not user.admin:
            continue

        os.remove(db_item.path)
        os.remove(db_item.cover_path)

        album_folder = "data/items/smoelen"
        if db_album:
            album_folder = f"data/items/{db_album.id}"
        os.rmdir(f"{album_folder}/{db_item.id}")
        await db.delete(db_item)
    await db.commit()

    # Return the full album
    return await get_album(db, album_id) if album_id else None


async def set_preview(db: Session, album_id: UUID, item_id: UUID) -> schemas.Album:
    result = await db.execute(select(models.Album).where(models.Album.id == album_id))
    db_album = result.scalar_one()
    result = await db.execute(select(models.Item).where(models.Item.id == item_id))
    db_item = result.scalar_one()
    if db_item.album_id != album_id:
        return await get_album(db, album_id)

    db_album.preview = db_item
    await db.commit()

    return await get_album(db, album_id)
