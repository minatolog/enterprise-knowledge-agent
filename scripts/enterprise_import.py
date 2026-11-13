"""Explicitly copy the approved CNOOC corpus into an isolated enterprise tenant."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".enterprise/local.env")
    parser.add_argument("--tenant", default="demo")
    parser.add_argument("--groups", default="staff")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(args.env, override=True)
    from app.enterprise.auth import Principal
    from app.enterprise.config import Settings
    from app.enterprise.db import Database
    from app.enterprise.storage import ObjectStore
    from app.enterprise.index import Index
    from app.enterprise.runtime import Runtime
    from knowledge_config import selected_paths
    from index_documents import source_rows
    settings = Settings()
    database, objects = Database(settings), ObjectStore(settings)
    runtime = Runtime(settings, database, objects, Index(settings, database, objects))
    principal = Principal("local-corpus-import", args.tenant, tuple(args.groups.split(",")), ("admin",))
    paths = selected_paths()
    source_rows(paths)  # Verify the existing source manifest before reading data.
    for relative, path in paths.items():
        identity = hashlib.sha256((args.tenant + relative).encode()).hexdigest()[:32]
        existing = database.document(principal.tenant, identity)
        runtime.upload(principal, path.name, path.read_bytes(), path.suffix, list(principal.groups),
            identity if existing else None, create_id=identity)
    identity = database.new_job(principal.tenant)
    release = runtime.run_job(identity)
    count = runtime.index.client.get_collection("release_" + release).count()
    print(json.dumps({"documents": len(paths), "chunks": count, "release_id": release,
        "original_corpus_modified": False, "generation_calls": 0}))
    runtime.provider.shutdown()


if __name__ == "__main__":
    main()
