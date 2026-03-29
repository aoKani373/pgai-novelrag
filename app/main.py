import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import json

from sqlmodel import SQLModel, Field, Relationship, create_engine, Session, text, select
from sqlalchemy import DateTime
from datetime import datetime, timezone
import uuid
from pgvector.sqlalchemy import Vector
import pgai

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from typing import Literal
from openai import OpenAI

_ = load_dotenv(find_dotenv())
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
EMBEDD_MODEL = os.getenv("EMBEDD_MODEL", "text-embedding-3-small")
EMBEDD_DIMENSION = int(os.getenv("EMBEDD_DIMENSION", 768))

openai_client = OpenAI()

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


# episode_chunk
class EpisodeChunkBase(SQLModel):
    embedding_uuid: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    chunk_seq: int
    chunk: str
    id: int = Field(foreign_key="data.episode.id")

class EpisodeChunk(EpisodeChunkBase, table=True):
    __tablename__ = "episode_chunk"
    __table_args__ = {"schema": "app"}

    embedding: list[float] = Field(sa_type=Vector(EMBEDD_DIMENSION))

    episode: Episode = Relationship(back_populates="chunks")

class EpisodeChunkPublic(EpisodeChunkBase):
    distance: float

class QueryRequest(SQLModel):
    query: str
    top_k: int = Field(default=5, ge=1, lt=50)
    source: Literal["episode", "all"] = Field(default="episode")


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

@app.post("/search", response_model=list[EpisodeChunkPublic])
def query_episode(*, session: Session=Depends(get_session), body: QueryRequest):
    query_embeddings = openai_client.embeddings.create(
        model=EMBEDD_MODEL, input=body.query, dimensions=EMBEDD_DIMENSION, encoding_format="float"
    ).data[0].embedding

    distance = EpisodeChunk.embedding.cosine_distance(query_embeddings).label("distance")
    results = session.exec(
        select(EpisodeChunk, distance).order_by(distance).limit(body.top_k)
    ).all()
    chunks = [
        EpisodeChunkPublic(
            embedding_uuid=r.embedding_uuid,
            chunk_seq=r.chunk_seq,
            chunk=r.chunk,
            id=r.id,
            distance=distance
        ) for r, distance in results
    ]

    return chunks


if __name__ == "__main__":
    update_pgai()