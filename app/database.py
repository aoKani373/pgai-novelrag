import os
from dotenv import load_dotenv, find_dotenv
from sqlmodel import SQLModel, Session, create_engine, text
import pgai

_ = load_dotenv(find_dotenv())

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

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

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

if __name__ == "__main__":
    update_pgai()