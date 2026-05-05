from datetime import datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
import requests
from Crypto.Hash import SHA256
from fastapi import FastAPI, Depends, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession as Session

from app.conf import settings
from app.db import schemas, crud
from app.db.database import get_db
from app.db.schemas import User


@lru_cache()
def get_openid_configuration():
    return requests.get(settings.openid_configuration, timeout=10).json()


@lru_cache()
def get_jwks_client():
    return jwt.PyJWKClient(uri=get_openid_configuration()["jwks_uri"])


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def get_user_dep(token: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    openid_configuration = get_openid_configuration()
    jwks_client = get_jwks_client()

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token.credentials)
        decoded_jwt = jwt.decode(
            token.credentials,
            key=signing_key.key,
            algorithms=openid_configuration["id_token_signing_alg_values_supported"],
            options={"verify_aud": False},
        )
    except jwt.exceptions.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token"
        )

    if not decoded_jwt.get("media"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    is_admin = (
        "begeleider" in decoded_jwt["account_type"]
        or decoded_jwt["sub"] in settings.allowed_users
    )
    return User(id=decoded_jwt["sub"], admin=is_admin)


def verify_signature(path: str, signature: str):
    if not crud.get_verifier().verify(
        SHA256.new(path.encode("utf-8")), bytes.fromhex(signature)
    ):
        return False

    return True


@app.post("/albums", response_model=schemas.AlbumList, operation_id="create_album")
async def create_album(
    album: schemas.AlbumCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    return await crud.create_album(db, album)


@app.get("/albums", response_model=list[schemas.AlbumList], operation_id="get_albums")
async def get_albums(
    db: Session = Depends(get_db), _user: User = Depends(get_user_dep)
):
    return await crud.get_albums(db)


@app.patch(
    "/albums", response_model=list[schemas.AlbumList], operation_id="order_albums"
)
async def order_albums(
    albums: list[schemas.AlbumOrder],
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    return await crud.order_albums(db, albums)


@app.get("/albums/{album_id}", response_model=schemas.Album, operation_id="get_album")
async def get_album(
    album_id: UUID, db: Session = Depends(get_db), _user=Depends(get_user_dep)
):
    return await crud.get_album(db, album_id)


@app.patch(
    "/albums/{album_id}", response_model=schemas.Album, operation_id="update_album"
)
async def update_album(
    album_id: UUID,
    album: schemas.AlbumCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    db_album = await crud.update_album(db, album_id, album)
    # Manual conversion to avoid relationship access issues during validation
    album_data = schemas.Album.model_validate(
        {
            "id": db_album.id,
            "name": db_album.name,
            "description": db_album.description,
            "order": db_album.order,
            "items": [],  # We know they are empty or not needed here for the return
            "preview": crud.sign_item(db_album.preview) if db_album.preview else None,
        }
    )
    return album_data


@app.delete("/albums/{album_id}", operation_id="delete_album")
async def delete_album(
    album_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    result = await crud.delete_album(db, album_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Album not found"
        )

    return {"success": True}


@app.post(
    "/items/{album_id}", response_model=list[schemas.Item], operation_id="upload_items"
)
async def upload_items(
    album_id: UUID,
    items: list[UploadFile],
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    return await crud.create_items(db, user, items, album_id)


@app.get("/items/{item_id}/{expiry}/full", include_in_schema=False)
async def get_item(
    item_id: UUID, signature: str, expiry: float, db: Session = Depends(get_db)
):
    if not verify_signature(
        f"{settings.base_url}/items/{item_id}/{expiry}/full", signature
    ):
        return None
    if datetime.now().timestamp() > expiry:
        return None

    return await crud.get_full(db, item_id)


@app.get("/items/{item_id}/{expiry}/cover", include_in_schema=False)
async def get_cover(
    item_id: UUID, signature: str, expiry: float, db: Session = Depends(get_db)
):
    if not verify_signature(
        f"{settings.base_url}/items/{item_id}/{expiry}/cover", signature
    ):
        return None
    if datetime.now().timestamp() > expiry:
        return None

    return await crud.get_cover(db, item_id)


@app.post(
    "/items/{album_id}/delete",
    response_model=schemas.Album,
    operation_id="delete_items",
)
async def delete_items(
    album_id: UUID,
    items: list[UUID],
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    db_album = await crud.delete_items(db, user, album_id, items)
    if db_album is None:
        return None

    # Manual conversion to avoid relationship access issues during validation
    album_data = schemas.Album.model_validate(
        {
            "id": db_album.id,
            "name": db_album.name,
            "description": db_album.description,
            "order": db_album.order,
            "items": [],  # delete_items returns the album, but we don't need items here
            "preview": crud.sign_item(db_album.preview) if db_album.preview else None,
        }
    )
    return album_data


@app.post(
    "/albums/{album_id}/preview",
    response_model=schemas.Album,
    operation_id="set_preview",
)
async def set_preview(
    album_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_user_dep),
):
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )

    db_album = await crud.set_preview(db, album_id, item_id)
    # Manual conversion to avoid relationship access issues during validation
    album_data = schemas.Album.model_validate(
        {
            "id": db_album.id,
            "name": db_album.name,
            "description": db_album.description,
            "order": db_album.order,
            "items": [],
            "preview": crud.sign_item(db_album.preview) if db_album.preview else None,
        }
    )
    return album_data


@app.get("/users/me", response_model=User, operation_id="get_user")
async def get_user(user: User = Depends(get_user_dep)):
    return user


@app.get(
    "/smoelen", response_model=list[schemas.SmoelAlbumList], operation_id="get_smoelen"
)
async def get_smoelen(db: Session = Depends(get_db), _user=Depends(get_user_dep)):
    return await crud.get_smoelen_albums(db)


@app.get(
    "/smoelen/{smoel_id}", response_model=schemas.SmoelAlbum, operation_id="get_smoel"
)
async def get_smoel(
    smoel_id: UUID, db: Session = Depends(get_db), _user=Depends(get_user_dep)
):
    return await crud.get_smoel_album(db, smoel_id)
