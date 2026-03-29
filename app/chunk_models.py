import os
from dotenv import load_dotenv, find_dotenv

from sqlmodel import SQLModel, Field, Relationship
from pgvector.sqlalchemy import Vector
from typing import TYPE_CHECKING
import uuid

_ = load_dotenv(find_dotenv())

EMBEDD_MODEL = os.getenv("EMBEDD_MODEL", "text-embedding-3-small")
EMBEDD_DIMENSION = int(os.getenv("EMBEDD_DIMENSION", 768))

if TYPE_CHECKING:
    from .models import Episode

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

    episode: "Episode" = Relationship(back_populates="chunks")

class EpisodeChunkPublic(EpisodeChunkBase):
    distance: float