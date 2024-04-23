import asyncio
import logging
from asyncio import ensure_future
from enum import Enum
from functools import wraps
from hashlib import md5
from io import BytesIO
from traceback import format_exception
from typing import Any, Callable, Coroutine, Optional, Union, List
from urllib.request import urlopen
from uuid import UUID

import face_recognition
import requests
from PIL import Image, ImageOps
from app.conf import settings
from app.db import models
from app.db.crud import get_smoel, set_smoel, delete_items, create_item
from numpy import asarray, ndarray
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from weaviate import connect_to_local, WeaviateClient

NoArgsNoReturnFuncT = Callable[[], None]
NoArgsNoReturnAsyncFuncT = Callable[[], Coroutine[Any, Any, None]]
NoArgsNoReturnDecorator = Callable[
    [Union[NoArgsNoReturnFuncT, NoArgsNoReturnAsyncFuncT]], NoArgsNoReturnAsyncFuncT
]


def get_weaviate_client() -> WeaviateClient:
    host, port = settings.weaviate_url.lstrip("https://").split(":")
    return connect_to_local(host, port)


def repeat_every(
    *,
    seconds: float,
    wait_first: bool = False,
    logger: Optional[logging.Logger] = None,
    raise_exceptions: bool = False,
    max_repetitions: Optional[int] = None,
) -> NoArgsNoReturnDecorator:
    """
    This function returns a decorator that modifies a function so it is periodically re-executed after its first call.

    The function it decorates should accept no arguments and return nothing. If necessary, this can be accomplished
    by using `functools.partial` or otherwise wrapping the target function prior to decoration.

    Parameters
    ----------
    seconds: float
        The number of seconds to wait between repeated calls
    wait_first: bool (default False)
        If True, the function will wait for a single period before the first call
    logger: Optional[logging.Logger] (default None)
        The logger to use to log any exceptions raised by calls to the decorated function.
        If not provided, exceptions will not be logged by this function (though they may be handled by the event loop).
    raise_exceptions: bool (default False)
        If True, errors raised by the decorated function will be raised to the event loop's exception handler.
        Note that if an error is raised, the repeated execution will stop.
        Otherwise, exceptions are just logged and the execution continues to repeat.
        See https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.set_exception_handler for more info.
    max_repetitions: Optional[int] (default None)
        The maximum number of times to call the repeated function. If `None`, the function is repeated forever.
    """

    def decorator(
        func: Union[NoArgsNoReturnAsyncFuncT, NoArgsNoReturnFuncT]
    ) -> NoArgsNoReturnAsyncFuncT:
        """
        Converts the decorated function into a repeated, periodically-called version of itself.
        """
        is_coroutine = asyncio.iscoroutinefunction(func)

        @wraps(func)
        async def wrapped() -> None:
            repetitions = 0

            async def loop() -> None:
                nonlocal repetitions
                if wait_first:
                    await asyncio.sleep(seconds)
                while max_repetitions is None or repetitions < max_repetitions:
                    try:
                        if is_coroutine:
                            await func()  # type: ignore
                        else:
                            await run_in_threadpool(func)
                        repetitions += 1
                    except Exception as exc:  # pylint: disable=broad-except
                        if logger is not None:
                            formatted_exception = "".join(
                                format_exception(type(exc), exc, exc.__traceback__)
                            )
                            logger.error(formatted_exception)
                        if raise_exceptions:
                            raise exc
                    await asyncio.sleep(seconds)

            ensure_future(loop())

        return wrapped

    return decorator


class FaceAction(Enum):
    NONE = 0
    CREATE = 1
    UPDATE = 2


def create_encodings(face):
    if isinstance(face, str):
        image = Image.open(face).convert('RGB')
    else:
        image = Image.open(BytesIO(face)).convert('RGB')

    resized_image = ImageOps.contain(image, (1920, 1920))
    data = asarray(resized_image)
    image.close()
    resized_image.close()

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
    current_result = requests.get(f"{settings.weaviate_url}/v1/objects/known_faces/{user['id']}")

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
        requests.post(f"{settings.weaviate_url}/v1/objects", json={
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
        requests.put(f"{settings.weaviate_url}/v1/objects/known_faces/{user['id']}", json={
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
    with get_weaviate_client() as client:
        known_faces = client.collections.get('known_faces')
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

        print(f"processing {item.id}")
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
