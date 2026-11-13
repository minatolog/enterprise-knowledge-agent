"""Offline backup and non-destructive restore. Stop API/workers before backup."""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(settings, destination):
    if destination.exists():
        raise ValueError("backup destination must not exist")
    from app.enterprise.db import Database, metadata, versions
    from app.enterprise.storage import ObjectStore
    from sqlalchemy import select
    database = Database(settings)
    store = ObjectStore(settings)
    destination.mkdir(parents=True, mode=0o700)
    backend = "sqlite" if settings.db_url().startswith("sqlite:") else "postgresql"
    # Portable logical export: one transaction, including ACL, release and jobs.
    with database.engine.connect() as connection:
        if backend == "postgresql":
            connection = connection.execution_options(isolation_level="REPEATABLE READ")
        with connection.begin():
            exported = {table.name: [dict(row) for row in connection.execute(select(table)).mappings()]
                for table in metadata.sorted_tables}
    (destination / "metadata.json").write_text(json.dumps(exported, ensure_ascii=False))
    for row in database.rows(select(versions.c.object_key)):
        path = destination / "objects" / row["object_key"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(store.get(row["object_key"]))
    if (settings.root / "chroma").exists():
        shutil.copytree(settings.root / "chroma", destination / "chroma")
    manifest = {str(path.relative_to(destination)): hash_file(path) for path in destination.rglob("*") if path.is_file()}
    (destination / "manifest.json").write_text(json.dumps({"backend": backend, "files": manifest}, indent=2))
    database.engine.dispose()


def restore(source, destination, database_url=None, postgres_database=None):
    if destination.exists():
        raise ValueError("restore destination must be a NEW empty location")
    manifest = json.loads((source / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        path = (source / name).resolve()
        if not path.is_relative_to(source.resolve()) or hash_file(path) != expected:
            raise ValueError("backup checksum mismatch")
    shutil.copytree(source, destination)
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from app.enterprise.db import metadata
    target_url = f"sqlite:///{destination.resolve() / 'metadata.sqlite3'}"
    if postgres_database:
        import re
        if not database_url or not re.fullmatch(r"restore_[a-z0-9_]{1,40}", postgres_database):
            raise ValueError("restore database must have a new restore_ name")
        parent = make_url(database_url)
        admin = create_engine(parent.set(database="postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as connection:
            # createdb refuses an existing name; never drops or overwrites data.
            connection.exec_driver_sql(f'CREATE DATABASE "{postgres_database}"')
        admin.dispose()
        target_url = parent.set(database=postgres_database)
    engine = create_engine(target_url)
    metadata.create_all(engine)
    exported = json.loads((destination / "metadata.json").read_text())
    with engine.begin() as connection:
        for table in metadata.sorted_tables:
            if exported[table.name]:
                connection.execute(table.insert(), exported[table.name])
    engine.dispose()
    return manifest["backend"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["backup", "restore"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument("--env", type=Path, default=ROOT / ".enterprise/runtime.env")
    parser.add_argument("--postgres-database", help="Create a NEW restore_* database; never overwrite an existing database")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(args.env, override=True)
    if args.command == "backup":
        from app.enterprise.config import Settings
        backup(Settings(), args.source)
    else:
        if not args.destination:
            parser.error("restore requires a new destination")
        from app.enterprise.config import Settings
        settings = Settings()
        print("Verified and restored original backend:", restore(args.source, args.destination, settings.db_url(), args.postgres_database))


if __name__ == "__main__":
    main()
