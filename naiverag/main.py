import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import json

from sqlmodel import SQLModel, Field, Relationship, create_engine, Session, text
from sqlalchemy import DateTime
from datetime import datetime, timezone
import uuid
from pgvector.sqlalchemy import Vector
import pgai

from contextlib import asynccontextmanager
from fastapi import FastAPI

_ = load_dotenv(find_dotenv())
DATABASE_URL = os.getenv("DATABASE_URL")
EMBEDD_DIMENSION = os.getenv("EMBEDD_DIMENSION")

def utc_now():
    return datetime.now(timezone.utc)

def to_psycopg3(url: str):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://")
    return url

def to_psycopg2(url: str):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://")
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://")
    return url

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
    id: int | None = Field(default=None, primary_key=True)

    novels: list["Novel"] = Relationship(back_populates="author")

class UserCreate(UserBase):
    pass

class UserPublic(UserBase):
    id: int


# Novel
class NovelBase(TimestampModel):
    title: str = Field(index=True, nullable=False)
    author_id: int = Field(foreign_key="user.id", nullable=False)

class Novel(NovelBase, table=True):
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
    novel_id: int = Field(foreign_key="novel.id", nullable=False)

class Chapter(ChapterBase, table=True):
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
    chapter_id: int = Field(foreign_key="chapter.id", nullable=False, index=True)

class Episode(EpisodeBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    chapter: Chapter | None = Relationship(back_populates="episodes")
    # chunks: list["EpisodeChunk"] = Relationship(back_populates="episode")

class EpisodeCreate(EpisodeBase):
    pass

class EpisodePublic(EpisodeBase):
    id: int


# episode_chunk
# class EpisodeChunkBase(SQLModel):
#     embedding_uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
#     chunk_seq: int
#     id: int = Field(foreign_key="episode.id")

# class EpisodeChunk(EpisodeChunkBase, table=True):
#     __tablename__ = "episode_chunk"

#     embedding: list[float] = Field(sa_type=Vector(EMBEDD_DIMENSION))

#     episode: Episode = Relationship(back_populates="chunks")

# class EpisodeChunkPublic(EpisodeChunkBase):
#     distance: float


engine = create_engine(to_psycopg3(DATABASE_URL), echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def drop_all_tables():
    SQLModel.metadata.drop_all(engine)

def update_pgai():
    with Session(engine) as session:
        session.exec(text("DROP EXTENSION IF EXISTS ai"))
        session.commit()

        pgai.install(to_psycopg2(DATABASE_URL))

        session.exec(text("CREATE EXTENSION IF NOT EXISTS ai cascade"))
        session.commit()

def get_session():
    with Session(engine) as session:
        yield session

def init_data(path: str):
    path_obj = Path(path)
    if not path_obj.exists():
        print(f"File not found: {path}")
        return
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        author = User(name=data["author"])
        session.add(author)
        session.flush()

        novel = Novel(
            title=data["title"],
            author=author
        )

        for ch_data in data["chapters"]:
            chapter = Chapter(
                title=ch_data["title"],
                order=ch_data["order"],
                novel=novel
            )
            
            for ep_data in ch_data["episodes"]:
                episode = Episode(
                    title=ep_data["title"],
                    content=ep_data["content"],
                    chapter=chapter
                )
                chapter.episodes.append(episode)
            
            novel.chapters.append(chapter)
        
        session.add(novel)
        session.commit()
        print(f"Successfully initialized data: {novel.title}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    update_pgai()

    yield

    print("Shutting down complete")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    # drop_all_tables()
    init_data("data/inputs/documents.json")