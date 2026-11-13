"""Shared SQL schema for SQLite development and PostgreSQL deployments."""
import time
import uuid

from sqlalchemy import JSON, Column, Float, Integer, MetaData, String, Table, create_engine, select

metadata = MetaData()
documents = Table("documents", metadata,
    Column("id", String(64), primary_key=True), Column("tenant", String(256), nullable=False, index=True),
    Column("title", String(512), nullable=False), Column("version", Integer, nullable=False),
    Column("groups", JSON, nullable=False), Column("object_key", String(512), nullable=False),
    Column("digest", String(64), nullable=False), Column("deleted", Integer, nullable=False, default=0))
versions = Table("versions", metadata,
    Column("id", String(64), primary_key=True), Column("document_id", String(64), nullable=False, index=True),
    Column("tenant", String(256), nullable=False), Column("version", Integer, nullable=False),
    Column("object_key", String(512), nullable=False), Column("digest", String(64), nullable=False))
releases = Table("releases", metadata,
    Column("id", String(64), primary_key=True), Column("tenant", String(256), nullable=False, index=True),
    Column("manifest", JSON, nullable=False), Column("created", Float, nullable=False))
active = Table("active_release", metadata,
    Column("tenant", String(256), primary_key=True), Column("release_id", String(64), nullable=False))
jobs = Table("jobs", metadata,
    Column("id", String(64), primary_key=True), Column("tenant", String(256), nullable=False),
    Column("status", String(32), nullable=False), Column("attempts", Integer, nullable=False),
    Column("error", String(256)), Column("release_id", String(64)))
turns = Table("turns", metadata,
    Column("id", String(64), primary_key=True), Column("tenant", String(256), nullable=False),
    Column("subject", String(256), nullable=False), Column("session_id", String(64), nullable=False),
    Column("release_id", String(64), nullable=False), Column("acl_key", String(64), nullable=False),
    Column("payload", JSON, nullable=False), Column("created", Float, nullable=False))


class Database:
    def __init__(self, settings):
        settings.root.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(settings.db_url(), pool_pre_ping=True,
            connect_args={"check_same_thread": False} if settings.db_url().startswith("sqlite") else {})
        metadata.create_all(self.engine)

    def rows(self, statement):
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(statement).mappings()]

    def document(self, tenant, document_id):
        rows = self.rows(select(documents).where(documents.c.tenant == tenant, documents.c.id == document_id, documents.c.deleted == 0))
        return rows[0] if rows else None

    def release(self, tenant):
        rows = self.rows(select(releases).join(active, active.c.release_id == releases.c.id).where(active.c.tenant == tenant))
        return rows[0] if rows else None

    def new_job(self, tenant):
        identity = uuid.uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(jobs.insert().values(id=identity, tenant=tenant, status="queued", attempts=0))
        return identity
