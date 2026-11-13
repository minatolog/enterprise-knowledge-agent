"""Generate local-only secrets without printing credentials or tokens."""
import json
import os
import secrets
import sys
import time
from pathlib import Path

import jwt

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".enterprise"


def main():
    STATE.mkdir(mode=0o700, exist_ok=True)
    for name in ("state", "backups"):
        (STATE / name).mkdir(exist_ok=True)
    secret_path = STATE / "secrets.json"
    values = json.loads(secret_path.read_text()) if secret_path.exists() else {
        name: secrets.token_hex(24) for name in ("POSTGRES_PASSWORD", "REDIS_PASSWORD", "RABBITMQ_PASSWORD", "MINIO_PASSWORD", "GRAFANA_PASSWORD", "DEV_SECRET")}
    secret_path.write_text(json.dumps(values))
    secret_path.chmod(0o600)
    (STATE / "s3.json").write_text(json.dumps({"identities": [{"name": "rag",
        "credentials": [{"accessKey": "ragadmin", "secretKey": values["MINIO_PASSWORD"]}],
        "actions": ["Admin", "Read", "Write", "List", "Tagging"]}]}))
    (STATE / "s3.json").chmod(0o600)
    def write_env(path, settings):
        path.write_text("\n".join(f"{key}={value}" for key, value in settings.items()) + "\n")
        path.chmod(0o600)
    write_env(STATE / "compose.env", {key: value for key, value in values.items() if key != "DEV_SECRET"})
    runtime = dict(ENTERPRISE_ROOT=str(STATE / "state"), ENTERPRISE_AUTH_MODE="dev", ENTERPRISE_DEV_SECRET=values["DEV_SECRET"],
        ENTERPRISE_DATABASE_URL=f'postgresql+psycopg://rag:{values["POSTGRES_PASSWORD"]}@127.0.0.1:15432/rag',
        ENTERPRISE_REDIS_URL=f'redis://:{values["REDIS_PASSWORD"]}@127.0.0.1:16379/0',
        ENTERPRISE_BROKER_URL=f'amqp://rag:{values["RABBITMQ_PASSWORD"]}@127.0.0.1:15673//',
        ENTERPRISE_EAGER="false", ENTERPRISE_S3_ENDPOINT="http://127.0.0.1:19000",
        AWS_ACCESS_KEY_ID="ragadmin", AWS_SECRET_ACCESS_KEY=values["MINIO_PASSWORD"], AWS_DEFAULT_REGION="us-east-1",
        ENTERPRISE_OTLP_ENDPOINT="http://127.0.0.1:14317")
    write_env(STATE / "runtime.env", runtime)
    write_env(STATE / "local.env", {
        "ENTERPRISE_ROOT": str(STATE / "local"), "ENTERPRISE_AUTH_MODE": "dev",
        "ENTERPRISE_DEV_SECRET": values["DEV_SECRET"], "ENTERPRISE_EAGER": "true",
        "ENTERPRISE_VERIFY_ANSWERS": "true",
    })
    container = {**runtime, "ENTERPRISE_ROOT": "/state"}
    for key, old, new in (
        ("ENTERPRISE_DATABASE_URL", "127.0.0.1:15432", "postgres:5432"),
        ("ENTERPRISE_REDIS_URL", "127.0.0.1:16379", "redis:6379"),
        ("ENTERPRISE_BROKER_URL", "127.0.0.1:15673", "rabbitmq:5672"),
        ("ENTERPRISE_S3_ENDPOINT", "127.0.0.1:19000", "s3:8333"),
        ("ENTERPRISE_OTLP_ENDPOINT", "127.0.0.1:14317", "otel:4317")):
        container[key] = container[key].replace(old, new)
    write_env(STATE / "container.env", container)
    claims = dict(sub="metrics", tenant_id="operations", groups=[], roles=["admin"],
        iss="enterprise-rag-dev", aud="enterprise-rag", iat=int(time.time()), exp=int(time.time()) + 86400)
    (STATE / "metrics.token").write_text(jwt.encode(claims, values["DEV_SECRET"], algorithm="HS256"))
    (STATE / "metrics.token").chmod(0o600)
    (STATE / "prometheus.yml").write_text('''global:
  scrape_interval: 10s
rule_files: [/etc/prometheus/alerts.yml]
scrape_configs:
  - job_name: rag-api
    authorization:
      credentials_file: /etc/prometheus/metrics.token
    static_configs:
      - targets: [host.docker.internal:8030]
  - job_name: rag-spans
    static_configs:
      - targets: [otel:8889]
''')
    print("Generated private configuration under .enterprise; metrics token expires in 24 hours. Re-run to refresh.")


if __name__ == "__main__":
    main()
