import datetime
import os
from functools import lru_cache
from uuid import uuid4, UUID

import ffmpeg
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from PIL import Image
from fastapi import UploadFile
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
        .options(selectinload(models.Album.items).selectinload(models.Item.smoelen))
    )
    db_album = result.scalar_one()
    album = schemas.Album.model_validate(db_album)
    album.items = [sign_item(item) for item in album.items]

    return album


async def get_smoel_album(db: Session, smoel_id: UUID) -> schemas.SmoelAlbum:
    result = await db.execute(
        select(models.Smoel)
        .where(models.Smoel.id == smoel_id)
        .options(selectinload(models.Smoel.items))
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
            selectinload(models.Smoel.preview), selectinload(models.Smoel.items)
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
    result = await db.execute(
        select(models.Album)
        .where(models.Album.id == album_id)
        .options(selectinload(models.Album.preview))
    )
    db_album = result.scalar_one()
    db_album.name = album.name
    db_album.description = album.description
    await db.commit()
    await db.refresh(db_album)

    return db_album


async def order_albums(db: Session, albums: list[schemas.AlbumOrder]):
    for album in albums:
        result = await db.execute(
            select(models.Album).where(models.Album.id == album.id)
        )
        db_album = result.scalar_one()
        db_album.order = album.order
    await db.commit()
    result = await db.execute(
        select(models.Album).options(selectinload(models.Album.preview))
    )
    return result.scalars().all()


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
        await delete_items(db, None, album_id, album_items)

    # Remove the album directory
    album_folder = f"data/items/{album_id}"
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
    # write temp file
    item_id = uuid4()
    if album_id is None:
        album_folder = "data/items/smoelen"
        if not os.path.exists(album_folder):
            os.mkdir(album_folder)

    else:
        album_folder = f"data/items/{album_id}"

    os.mkdir(f"{album_folder}/{item_id}")
    with open(f"/tmp/{item_id}", "wb") as buffer:
        buffer.write(item)

    # get type
    file_type = content_type.split("/")[0]
    if file_type not in ["image", "video"]:
        return None

    if file_type == "image":
        file_type = models.Type.IMAGE
    else:
        file_type = models.Type.VIDEO

    # get metadata
    if file_type == models.Type.IMAGE:
        with Image.open(f"/tmp/{item_id}") as img:
            width, height = img.size

            # create cover image
            cover_path = f"{album_folder}/{item_id}/cover.jpg"
            img.thumbnail((400, 400 * height // width))
            img.save(cover_path)
    else:
        probe = ffmpeg.probe(f"/tmp/{item_id}")
        width = probe["streams"][0]["width"]
        height = probe["streams"][0]["height"]

        # create cover image
        cover_path = f"{album_folder}/{item_id}/cover.jpg"
        stream = ffmpeg.input(f"/tmp/{item_id}")
        stream = ffmpeg.filter(stream, "scale", 400, -1)
        stream = ffmpeg.output(stream, cover_path, vframes=1)
        ffmpeg.run(stream)

    # store optimized full size image/video
    if file_type == models.Type.VIDEO:
        path = f"{album_folder}/{item_id}/item.mp4"

        stream = ffmpeg.input(f"/tmp/{item_id}")
        stream = ffmpeg.output(stream, path, crf=23)
        ffmpeg.run(stream)
    else:
        path = f"{album_folder}/{item_id}/item.jpg"
        with Image.open(f"/tmp/{item_id}") as img:
            img.save(path)

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

    os.remove(f"/tmp/{item_id}")
    return db_item


async def create_items(
    db: Session,
    user: schemas.User | None,
    items: list[UploadFile],
    album_id: UUID | None,
    date: datetime = None,
) -> list[models.Item]:
    # Check if the album exists
    album = await db.get_one(models.Album, album_id)
    db_items = []
    for item in items:
        db_item = await create_item(
            db, user, await item.read(), item.content_type, album.id, date
        )
        if db_item is not None:
            db_items.append(db_item)

    return db_items


async def delete_items(
    db: Session, user: schemas.User | None, album_id: UUID | None, items: list[UUID]
):
    # Check if the album exists
    if album_id:
        await db.get_one(models.Album, album_id)
    # First delete the items
    for item in items:
        result = await db.execute(select(models.Item).where(models.Item.id == item))
        db_item = result.scalar_one_or_none()
        if user is not None and db_item.user != user.id and not user.admin:
            continue

        os.remove(db_item.path)
        os.remove(db_item.cover_path)

        if album_id is None:
            album_folder = "data/items/smoelen"
        else:
            album_folder = f"data/items/{album_id}"
        os.rmdir(f"{album_folder}/{item}")
        await db.delete(db_item)
    await db.commit()

    if not album_id:
        return None

    result = await db.execute(select(models.Album).where(models.Album.id == album_id))
    return result.scalar_one_or_none()


async def set_preview(db: Session, album_id: UUID, item_id: UUID):
    result = await db.execute(select(models.Album).where(models.Album.id == album_id))
    db_album = result.scalar_one()
    result = await db.execute(select(models.Item).where(models.Item.id == item_id))
    db_item = result.scalar_one()
    if db_item.album_id != album_id:
        return db_album

    db_album.preview = db_item
    await db.commit()

    return db_album
