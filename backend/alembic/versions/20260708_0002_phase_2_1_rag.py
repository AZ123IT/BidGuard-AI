"""Add Phase 2.1 RAG embedding metadata and pgvector support.

Revision ID: 20260708_0002
Revises: 20260708_0001
Create Date: 2026-07-08
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260708_0002"
down_revision: str | None = "20260708_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("embedding_provider", sa.String(length=80), nullable=True))
    op.add_column("document_chunks", sa.Column("embedding_model", sa.String(length=160), nullable=True))
    op.add_column("document_chunks", sa.Column("embedding_dimension", sa.Integer(), nullable=True))

    if op.get_bind().dialect.name == "postgresql":
        dimension = _embedding_dimension()
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute(
            f"ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector({dimension})"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector "
            "ON document_chunks USING ivfflat (embedding_vector vector_cosine_ops)"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_vector")
        op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_vector")
    op.drop_column("document_chunks", "embedding_dimension")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding_provider")


def _embedding_dimension() -> int:
    return int(os.getenv("EMBEDDING_DIMENSION", "64"))
