from enum import Enum
from hashlib import md5
from io import BytesIO
from typing import List
from urllib.request import urlopen
from uuid import UUID

import face_recognition
import requests
from PIL import Image
from numpy import asarray, ndarray
from sqlalchemy.orm import Session
from weaviate import connect_to_local

from app.conf import settings
from app.db import models
from app.db.crud import get_smoel, set_smoel, delete_items, create_item

client = connect_to_local()
known_faces = client.collections.get('known_faces')


class FaceAction(Enum):
    NONE = 0
    CREATE = 1
    UPDATE = 2


def create_encodings(face):
    if isinstance(face, str):
        image = Image.open(face).convert('RGB')
    else:
        image = Image.open(BytesIO(face)).convert('RGB')
    data = asarray(image)

    locations = face_recognition.face_locations(data)
    encodings = face_recognition.face_encodings(data, locations, num_jitters=20)

    return encodings


def obtain_access_token():
    result = requests.post("https://leden.djoamersfoort.nl/o/token/", data={
        "grant_type": "client_credentials",
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
    }).json()

    return result["access_token"]


def parse_smoel(smoel):
    with urlopen(smoel["photo"]) as response:
        data = response.read()

    return {
        "id": UUID(None, None, None, None, smoel["id"]),
        "name": smoel["first_name"],
        "data": data,
        "hash": md5(data).hexdigest()
    }


def get_action(user):
    current_result = requests.get(f"http://localhost:8080/v1/objects/known_faces/{user['id']}")

    if current_result.status_code != 200:
        return FaceAction.CREATE

    current = current_result.json()
    # Sometimes Weaviate decides to turn hashes into UUIDs
    if "".join(current["properties"]["hash"].split("-")) != user["hash"]:
        return FaceAction.UPDATE

    return FaceAction.NONE


def store_encoding(db: Session, user):
    action = get_action(user)
    if action == FaceAction.NONE:
        return

    encoding = create_encodings(user["data"])
    if len(encoding) == 0:
        return

    smoel = get_smoel(db, user["id"], user["name"])
    smoel_vector = ndarray.tolist(encoding[0])
    if action == FaceAction.CREATE:
        requests.post("http://localhost:8080/v1/objects", json={
            "class": "known_faces",
            "id": str(user["id"]),
            "vector": smoel_vector,
            "properties": {
                "hash": user["hash"],
                "user": str(user["id"]),
                "name": user["name"],
            }
        })
    elif action == FaceAction.UPDATE:
        requests.put(f"http://localhost:8080/v1/objects/known_faces/{user['id']}", json={
            "vector": smoel_vector,
            "properties": {
                "hash": user["hash"],
                "user": str(user["id"]),
                "name": user["name"],
            }
        })

        if smoel.preview_id is not None:
            preview = smoel.preview_id
            smoel.preview_id = None
            delete_items(db, None, None, [preview])

    item = create_item(db, None, user["data"], "image/png", None)
    if item is not None:
        item.processed = True
        smoel.preview_id = item.id

    db.commit()


def obtain_images(db: Session):
    print("Updating smoel index")
    smoelen = requests.get("https://leden.djoamersfoort.nl/api/v1/smoelenboek?large=1/", headers={
        "Authorization": f"Bearer {obtain_access_token()}"
    }).json()

    for smoel in smoelen:
        user = parse_smoel(smoel)
        store_encoding(db, user)

    print("Finished updating smoel index")


def find_people(item: models.Item):
    encodings = create_encodings(item.path)
    smoelen = []
    for encoding in encodings:
        smoel = known_faces.query.near_vector(
            near_vector=ndarray.tolist(encoding),
            distance=0.18,
            limit=1,
        )
        if len(smoel.objects) == 0:
            continue

        smoelen.append(smoel.objects[0].properties)

    return smoelen


def process_smoelen(db: Session, images: List[models.Item]):
    print("processing smoelen")
    for item in images:
        if item.type != models.Type.IMAGE:
            item.processed = True
            db.commit()
            continue

        smoelen = find_people(item)
        for smoel in smoelen:
            db_smoel = get_smoel(db, smoel["user"], smoel["name"])
            set_smoel(db, item, db_smoel)

        item.processed = True
        db.commit()

    print("done processing smoelen")


def handle_unprocessed(db: Session):
    items = db.query(models.Item).where(models.Item.processed == False).all()
    process_smoelen(db, items)
