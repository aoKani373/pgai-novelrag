from dotenv import load_dotenv, find_dotenv

from sqlmodel import SQLModel, Field, Session, select

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from typing import Literal
from openai import OpenAI

_ = load_dotenv(find_dotenv())

from .database import get_session, create_db_and_tables, update_pgai
from .chunk_models import EpisodeChunk, EpisodeChunkPublic, EMBEDD_MODEL, EMBEDD_DIMENSION

openai_client = OpenAI()

class QueryRequest(SQLModel):
    query: str
    top_k: int = Field(default=5, ge=1, lt=50)
    source: Literal["episode", "all"] = Field(default="episode")


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
    pass