"""Content-addressed immutable object storage; keys are never user supplied."""
import hashlib
import re
from pathlib import Path


class ObjectStore:
    def __init__(self, settings):
        self.root = settings.root / "objects"
        self.bucket = settings.s3_bucket
        self.client = None
        if settings.s3_endpoint:
            import boto3
            self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint)
        else:
            self.root.mkdir(parents=True, exist_ok=True)

    def put(self, tenant: str, data: bytes, suffix: str):
        if suffix not in {".pdf", ".txt", ".md", ".docx"}:
            raise ValueError("unsupported file type")
        digest = hashlib.sha256(data).hexdigest()
        key = f"{hashlib.sha256(tenant.encode()).hexdigest()}/{digest}{suffix}"
        if self.client:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        else:
            path = self.root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic replace prevents partial reads; immutable content has same hash.
            import os, tempfile
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                handle.write(data)
                temporary = handle.name
            os.replace(temporary, path)
        return key, digest

    def get(self, key):
        if not re.fullmatch(r"[a-f0-9]{64}/[a-f0-9]{64}\.(pdf|txt|md|docx)", key):
            raise ValueError("invalid object key")
        if self.client:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        return (self.root / key).read_bytes()
