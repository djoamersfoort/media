from __future__ import annotations

import enum
from typing import List

from sqlalchemy import Column, ForeignKey, String, Uuid, Enum, Integer, DateTime, Boolean, Table
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, expression

from app.db.database import Base


class Type(enum.Enum):
    IMAGE = 1
    VIDEO = 2


class Album(Base):
    __tablename__ = "albums"

    id = Column(Uuid, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    order = Column(Integer)
    preview_id = Column(Uuid, ForeignKey("items.id"), nullable=True)
    preview = relationship("Item", foreign_keys=[preview_id])

    items = relationship(
        "Item",
        back_populates="album",
        order_by="desc(Item.date)",
        foreign_keys="Item.album_id",
    )


association_table = Table(
    "association",
    Base.metadata,
    Column("item_id", Uuid, ForeignKey("items.id")),
    Column("smoel_id", Uuid, ForeignKey("smoelen.id")),
)


class Smoel(Base):
    __tablename__ = "smoelen"
    id = Column(Uuid, primary_key=True, index=True)
    name = Column(String)

    preview_id = Column(Uuid, ForeignKey("items.id"), nullable=True)
    preview = relationship("Item", foreign_keys=[preview_id])

    items: Mapped[List[Item]] = relationship(
        secondary=association_table, back_populates="smoelen"
    )


class Item(Base):
    __tablename__ = "items"

    id = Column(Uuid, primary_key=True, index=True)
    user = Column(String)
    album_id = Column(Uuid, ForeignKey("albums.id"), nullable=True)
    album = relationship("Album", back_populates="items", foreign_keys=[album_id])
    date = Column(DateTime(timezone=True), server_default=func.now())

    processed = Column(Boolean, server_default=expression.false(), nullable=False)
    smoelen: Mapped[List[Smoel]] = relationship(
        secondary=association_table, back_populates="items"
    )

    type = Column(Enum(Type))
    width = Column(String)
    height = Column(String)

    cover_path = Column(String)
    path = Column(String)
