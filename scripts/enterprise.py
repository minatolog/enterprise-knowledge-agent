"""Local operator CLI. Tokens are written to private files, never stdout."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["serve", "bucket", "token", "worker"])
    parser.add_argument("--env", type=Path, default=ROOT / ".enterprise/local.env")
    parser.add_argument("--tenant", default="demo")
    parser.add_argument("--subject", default="operator")
    parser.add_argument("--groups", default="staff")
    parser.add_argument("--roles", default="admin")
    parser.add_argument("--output", type=Path, default=ROOT / ".enterprise/operator.token")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(args.env, override=True)
    from app.enterprise.config import Settings
    settings = Settings()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("app.enterprise.api:create_app", factory=True, host="127.0.0.1", port=8030)
    elif args.command == "worker":
        from app.enterprise.worker import app
        app.worker_main(["worker", "--pool=solo", "--concurrency=1", "--loglevel=WARNING"])
    elif args.command == "bucket":
        from app.enterprise.storage import ObjectStore
        store = ObjectStore(settings)
        try:
            store.client.head_bucket(Bucket=settings.s3_bucket)
        except Exception:
            store.client.create_bucket(Bucket=settings.s3_bucket)
        print("Object bucket ready")
    elif args.command == "token":
        if settings.auth_mode != "dev":
            raise SystemExit("Token issuance is available only in explicit local development mode")
        import jwt
        claims = dict(sub=args.subject, tenant_id=args.tenant,
            groups=args.groups.split(","), roles=args.roles.split(",") if args.roles else [],
            iss="enterprise-rag-dev", aud=settings.audience, iat=int(time.time()), exp=int(time.time()) + 3600)
        args.output.parent.mkdir(exist_ok=True, parents=True)
        args.output.write_text(jwt.encode(claims, settings.dev_secret, algorithm="HS256"))
        args.output.chmod(0o600)
        print("Development token saved to the requested private file; expires in one hour")


if __name__ == "__main__":
    main()
