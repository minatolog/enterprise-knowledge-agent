"""Create named-volume services, inject private config, then start them.

No host bind mounts are required, including on restricted Docker Desktop setups.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ["docker", "compose", "--env-file", str(ROOT / ".enterprise/compose.env"), "-f", str(ROOT / "compose.enterprise.yml")]
    subprocess.run(base + ["create", "postgres", "redis", "rabbitmq", "s3", "otel", "prometheus", "grafana"], check=True)
    def container(service):
        return subprocess.check_output(base + ["ps", "-a", "-q", service], text=True).strip()
    def copy(source, service, target):
        subprocess.run(["docker", "cp", str(source), container(service) + ":" + target], check=True)
    copy(ROOT / ".enterprise/s3.json", "s3", "/etc/seaweedfs/s3.json")
    copy(ROOT / "deploy/otel.yaml", "otel", "/config/otel.yaml")
    copy(ROOT / ".enterprise/prometheus.yml", "prometheus", "/etc/prometheus/prometheus.yml")
    copy(ROOT / "deploy/alerts.yml", "prometheus", "/etc/prometheus/alerts.yml")
    with tempfile.TemporaryDirectory() as directory:
        token = Path(directory) / "metrics.token"
        shutil.copyfile(ROOT / ".enterprise/metrics.token", token)
        token.chmod(0o644)  # Container Prometheus user; parent directory is private.
        copy(token, "prometheus", "/etc/prometheus/metrics.token")
    copy(str(ROOT / "deploy/grafana") + "/.", "grafana", "/etc/grafana/provisioning")
    subprocess.run(base + ["start", "postgres", "redis", "rabbitmq", "s3", "otel", "prometheus", "grafana"], check=True)


if __name__ == "__main__":
    main()
