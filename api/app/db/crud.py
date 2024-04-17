import datetime
import os
from functools import lru_cache
from typing import Type
from uuid import uuid4, UUID

import ffmpeg
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from fastapi import UploadFile
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.conf import settings
from app.db import models, schemas
from app.fileresponse import FastApiBaizeFileResponse as FileResponse


@lru_cache()
def get_signer():
    with open("data/private.key", "r") as buffer:
        key = buffer.read()

    return PKCS1_v1_5.new(RSA.import_key(key))


@lru_cache()
def get_verifier():
    with open("data/public.key", "r") as buffer:
        key = buffer.read()

    return PKCS1_v1_5.new(RSA.import_key(key))


def sign_url(url: str):
    signature = get_signer().sign(SHA256.new(url.encode("utf-8")))
    return f"{url}?signature={signature.hex()}"


def sign_item(item_data: models.Item):
    item = schemas.Item.model_validate(item_data)
    expiry = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()

    item.cover_path = sign_url(
        f"{settings.base_url}/items/{item.id}/{expiry}/cover"
    )
    item.path = sign_url(
        f"{settings.base_url}/items/{item.id}/{expiry}/full"
    )

    return item


def get_album(db: Session, album_id: UUID):
    album_data = db.query(models.Album).filter(models.Album.id == album_id).first()
    album = schemas.Album.model_validate(album_data)
    album.items = []

    for item in album_data.items:
        album.items.append(sign_item(item))

    return album


def get_smoel_album(db: Session, album_id: UUID):
    smoel_data = db.query(models.Smoel).filter(models.Smoel.id == album_id).first()
    smoel = schemas.SmoelAlbum.model_validate(smoel_data)
    smoel.items = []

    for item in smoel_data.items:
        smoel.items.append(sign_item(item))

    return smoel


def get_full(db: Session, item_id: UUID):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    return FileResponse(item.path)


def get_cover(db: Session, item_id: UUID):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    return FileResponse(item.cover_path)


def get_albums(db: Session):
    albums = db.query(models.Album).all()
    result = []

    for album_data in albums:
        album = schemas.AlbumList.model_validate(album_data)
        if album_data.preview_id:
            album.preview = sign_item(album_data.preview)

        result.append(album)

    return result


def get_smoelen_albums(db: Session):
    smoelen = sorted(db.query(models.Smoel).all(), key=lambda x: len(x.items), reverse=True)
    result = []

    for smoel_data in smoelen:
        smoel = schemas.SmoelAlbumList.model_validate(smoel_data)
        if smoel_data.preview_id:
            smoel.preview = sign_item(smoel_data.preview)

        smoel.items = []
        for item in smoel_data.items[:2]:
            smoel.items.append(sign_item(item))

        result.append(smoel)

    return result


def create_album(db: Session, album: schemas.AlbumCreate):
    album_id = uuid4()
    os.mkdir(f"data/items/{album_id}")

    total_albums = db.query(models.Album).count()
    db_album = models.Album(
        id=album_id, name=album.name, description=album.description, order=total_albums
    )
    db.add(db_album)
    db.commit()
    db.refresh(db_album)

    return db_album


def update_album(db: Session, album_id: UUID, album: schemas.AlbumCreate):
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    db_album.name = album.name
    db_album.description = album.description
    db.commit()

    return db_album


def order_albums(db: Session, albums: list[schemas.AlbumOrder]):
    for album in albums:
        db_album = db.query(models.Album).filter(models.Album.id == album.id).first()
        db_album.order = album.order
    db.commit()
    return db.query(models.Album).all()


def create_item(
    db: Session,
    user: schemas.User | None,
    item: bytes,
    content_type: str,
    album_id: UUID | None,
    date: datetime = None
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
    probe = ffmpeg.probe(f"/tmp/{item_id}")
    width = probe["streams"][0]["width"]
    height = probe["streams"][0]["height"]

    # create cover image
    cover_path = f"{album_folder}/{item_id}/cover.jpg"

    if file_type == models.Type.VIDEO:
        stream = ffmpeg.input(f"/tmp/{item_id}")
        stream = ffmpeg.filter(stream, "scale", 400, -1)
        stream = ffmpeg.output(stream, cover_path, vframes=1)
        ffmpeg.run(stream)
    else:
        stream = ffmpeg.input(f"/tmp/{item_id}")
        stream = ffmpeg.filter(stream, "scale", 400, -1)
        stream = ffmpeg.output(stream, cover_path)
        ffmpeg.run(stream)

    # store optimized full size image/video
    if file_type == models.Type.VIDEO:
        path = f"{album_folder}/{item_id}/item.mp4"

        stream = ffmpeg.input(f"/tmp/{item_id}")
        stream = ffmpeg.output(stream, path, crf=23)
        ffmpeg.run(stream)
    else:
        path = f"{album_folder}/{item_id}/item.jpg"

        stream = ffmpeg.input(f"/tmp/{item_id}")
        stream = ffmpeg.output(stream, path)
        ffmpeg.run(stream)

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
    db.commit()
    db.refresh(db_item)

    os.remove(f"/tmp/{item_id}")
    return db_item


async def create_items(
    db: Session,
    user: schemas.User | None,
    items: list[UploadFile],
    album_id: UUID | None,
    date: datetime = None,
) -> list[models.Item]:
    db_items = []

    for item in items:
        db_item = create_item(db, user, await item.read(), item.content_type, album_id, date)
        if db_item is not None:
            db_items.append(db_item)

    return db_items


def delete_items(db: Session, user: schemas.User | None, album_id: UUID | None, items: list[UUID]):
    for item in items:
        db_item = db.query(models.Item).filter(models.Item.id == item).first()
        if user is not None and db_item.user != user.id and not user.admin:
            continue

        os.remove(db_item.path)
        os.remove(db_item.cover_path)

        if album_id is None:
            album_folder = "data/items/smoelen"
        else:
            album_folder = f"data/items/{album_id}"
        os.rmdir(f"{album_folder}/{item}")
        db.delete(db_item)
    db.commit()

    if not album_id:
        return None

    return db.query(models.Album).filter(models.Album.id == album_id).first()


def set_preview(db: Session, album_id: UUID, item_id: UUID):
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item.album_id != album_id:
        return db_album

    db_album.preview = db_item
    db.commit()

    return db_album


def get_smoel(db: Session, smoel_id: UUID, name: str):
    smoel = db.query(models.Smoel).filter(models.Smoel.id == smoel_id).first()
    if not smoel:
        smoel = models.Smoel(name=name, id=smoel_id)
        db.add(smoel)
        db.commit()

    return smoel


def set_smoel(db: Session, item: models.Item | Type[models.Item], smoel: models.Smoel):
    smoel.items.append(item)
    db.commit()
