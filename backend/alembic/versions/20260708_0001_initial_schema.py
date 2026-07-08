"""Initial BidGuard AI schema.

Revision ID: 20260708_0001
Revises:
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260708_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("source_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "risk_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False, unique=True),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("answer", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "eval_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_evidence", sa.JSON(), nullable=True),
        sa.Column("expected_answer", sa.Text(), nullable=True),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_table(
        "document_tables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
    )
    op.create_index("ix_document_tables_document_id", "document_tables", ["document_id"])
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_extracted_fields_document_id", "extracted_fields", ["document_id"])
    op.create_table(
        "risk_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("rule_name", sa.String(length=160), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_findings_document_id", "risk_findings", ["document_id"])
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_run_id", sa.Integer(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_table(
        "eval_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("eval_case_id", sa.Integer(), sa.ForeignKey("eval_cases.id"), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_eval_results_eval_case_id", "eval_results", ["eval_case_id"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_eval_case_id", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_tool_calls_agent_run_id", table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_index("ix_risk_findings_document_id", table_name="risk_findings")
    op.drop_table("risk_findings")
    op.drop_index("ix_extracted_fields_document_id", table_name="extracted_fields")
    op.drop_table("extracted_fields")
    op.drop_index("ix_document_tables_document_id", table_name="document_tables")
    op.drop_table("document_tables")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("eval_cases")
    op.drop_table("agent_runs")
    op.drop_table("risk_rules")
    op.drop_table("documents")
