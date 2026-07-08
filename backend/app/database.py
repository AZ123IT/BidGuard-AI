from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


def make_engine(settings: Settings) -> Engine:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine, settings: Settings | None = None) -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine, settings or Settings())


def ensure_runtime_schema(engine: Engine, settings: Settings) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "document_chunks" not in table_names:
        return
    existing_columns = {column["name"] for column in inspector.get_columns("document_chunks")}
    metadata_columns = {
        "embedding_provider": "VARCHAR(80)",
        "embedding_model": "VARCHAR(160)",
        "embedding_dimension": "INTEGER",
    }
    risk_finding_columns = (
        {column["name"] for column in inspector.get_columns("risk_findings")}
        if "risk_findings" in table_names
        else set()
    )
    with engine.begin() as connection:
        for column_name, column_type in metadata_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE document_chunks ADD COLUMN {column_name} {column_type}")
                )
        if "risk_findings" in table_names and "category" not in risk_finding_columns:
            connection.execute(
                text("ALTER TABLE risk_findings ADD COLUMN category VARCHAR(80) DEFAULT 'general' NOT NULL")
            )
        if engine.dialect.name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(
                text(
                    "ALTER TABLE document_chunks "
                    f"ADD COLUMN IF NOT EXISTS embedding_vector vector({settings.embedding_dimension})"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector "
                    "ON document_chunks USING ivfflat (embedding_vector vector_cosine_ops)"
                )
            )


def get_session(request: Request) -> Generator[Session, None, None]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
