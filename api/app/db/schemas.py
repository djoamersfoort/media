from datetime import datetime
from functools import lru_cache
from uuid import UUID

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from pydantic import BaseModel


@lru_cache()
def get_signer():
    with open("private.key", "r") as buffer:
        key = buffer.read()

    return PKCS1_v1_5.new(RSA.import_key(key))


def sign_url(url: str):
    signature = get_signer().sign(SHA256.new(url.encode("utf-8")))
    return f"{url}?signature={signature.hex()}"


class Smoel(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ItemBase(BaseModel):
    id: UUID
    date: datetime
    width: int
    height: int
    type: int
    user: str | None


class Item(ItemBase):
    path: str
    cover_path: str
    smoelen: list[Smoel]

    class Config:
        from_attributes = True


class AlbumBase(BaseModel):
    name: str
    description: str


class SmoelAlbumBase(BaseModel):
    name: str


class AlbumCreate(AlbumBase):
    pass


class Album(AlbumBase):
    id: UUID
    items: list[Item]
    order: int
    preview: Item | None

    class Config:
        from_attributes = True


class SmoelAlbum(SmoelAlbumBase):
    id: UUID
    items: list[Item]

    class Config:
        from_attributes = True


class AlbumList(AlbumBase):
    id: UUID
    order: int
    preview: Item | None

    class Config:
        from_attributes = True


class SmoelAlbumList(SmoelAlbumBase):
    id: UUID
    preview: Item
    items: list[Item]

    class Config:
        from_attributes = True


class AlbumOrder(BaseModel):
    id: UUID
    order: int


class User(BaseModel):
    id: str
    admin: bool
