"""create episode vectorizer

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-14 10:34:00.890439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgai.vectorizer.configuration import (
    LoadingColumnConfig,
    DestinationTableConfig,
    EmbeddingOpenaiConfig,
    ChunkingRecursiveCharacterTextSplitterConfig,
    FormattingPythonTemplateConfig,
    IndexingHnswConfig,
    SchedulingTimescaledbConfig,
)

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS ai CASCADE;")
    op.create_vectorizer(
        source="episode",
        name="episode_vectorizer",
        loading=LoadingColumnConfig(column_name="content"),
        destination=DestinationTableConfig(
            target_table="episode_chunk"
        ),
        embedding=EmbeddingOpenaiConfig(
            model="text-embedding-3-small",
            dimensions=768
        ),
        chunking=ChunkingRecursiveCharacterTextSplitterConfig(
            chunk_size=1000,
            chunk_overlap=400,
            separators=[".", "!", "?", "。", "．", "！", "？"],
            is_separator_regex=False
        ),
        formatting=FormattingPythonTemplateConfig(
            template=(
                "title: $title\n"
                "content: $chunk"
            )
        ),
        indexing=IndexingHnswConfig(min_rows=50000),
        scheduling=SchedulingTimescaledbConfig(
            schedule_interval="1 day",
            fixed_schedule=True,
            timezone="UTC"
        )
    )


def downgrade() -> None:
    op.drop_vectorizer(name="episode_vectorizer", drop_all=True)
