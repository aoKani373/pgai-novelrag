from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy import DateTime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chunk_models import EpisodeChunk

def utc_now():
    return datetime.now(timezone.utc)

class TimestampModel(SQLModel):
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": utc_now}
    )

# User
class UserBase(TimestampModel):
    name: str = Field(index=True, nullable=False)

class User(UserBase, table=True):
    __table_args__ = {"schema": "data"}

    id: int | None = Field(default=None, primary_key=True)

    novels: list["Novel"] = Relationship(back_populates="author")

class UserCreate(UserBase):
    pass

class UserPublic(UserBase):
    id: int


# Novel
class NovelBase(TimestampModel):
    title: str = Field(index=True, nullable=False)
    author_id: int = Field(foreign_key="data.user.id", nullable=False)

class Novel(NovelBase, table=True):
    __table_args__ = {"schema": "data"}

    id: int | None = Field(default=None, primary_key=True)

    author: User | None = Relationship(back_populates="novels")
    chapters: list["Chapter"] = Relationship(back_populates="novel")

class NovelCreate(NovelBase):
    pass

class NovelPublic(NovelBase):
    id: int


# Chapter
class ChapterBase(TimestampModel):
    title: str = Field(index=True, nullable=False)
    order: int = Field(index=True, nullable=False)
    novel_id: int = Field(foreign_key="data.novel.id", nullable=False)

class Chapter(ChapterBase, table=True):
    __table_args__ = {"schema": "data"}
    
    id: int | None = Field(default=None, primary_key=True)

    novel: Novel | None = Relationship(back_populates="chapters")
    episodes: list["Episode"] = Relationship(back_populates="chapter")

class ChapterCreate(ChapterBase):
    pass

class ChapterPublic(ChapterBase):
    id: int


# Episode
class EpisodeBase(TimestampModel):
    title: str = Field(index=True)
    content: str | None = Field(default=None)
    chapter_id: int = Field(foreign_key="data.chapter.id", nullable=False, index=True)

class Episode(EpisodeBase, table=True):
    __table_args__ = {"schema": "data"}

    id: int | None = Field(default=None, primary_key=True)

    chapter: Chapter | None = Relationship(back_populates="episodes")
    chunks: list["EpisodeChunk"] = Relationship(back_populates="episode")

class EpisodeCreate(EpisodeBase):
    pass

class EpisodePublic(EpisodeBase):
    id: int