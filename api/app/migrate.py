from json import loads
from db.database import engine
from db.crud import create_album, create_item, set_preview
from db.schemas import AlbumCreate, User, Item
from fastapi import UploadFile
from datetime import datetime
from sqlalchemy.orm import Session
from starlette.datastructures import Headers


async def migrate():
    with Session(engine) as database:
        with open("data/albums.json", "r") as file:
            albums = loads(file.read())

        for album in albums:
            new_album = create_album(database, AlbumCreate(**album))
            items: list[Item] = []
            for file in album["files"]:
                with open(f"data/files/{file['id']}", "rb") as buffer:
                    headers = Headers({
                        "Content-Type": f"{file['type']}/webp",
                    })
                    item = await create_item(
                        database,
                        User(id=file["user"], admin=False),
                        [UploadFile(buffer, headers=headers)],
                        new_album.id,
                        date=datetime.fromtimestamp(file["date"] / 1000),
                    )
                    items.extend(item)

            if album["preview"]:
                # get index of old preview
                index = next(
                    i for i, item in enumerate(album["files"]) if item["id"] == album["preview"]
                )
                set_preview(database, new_album.id, items[index].id)


if __name__ == "__main__":
    from asyncio import run
    run(migrate())
