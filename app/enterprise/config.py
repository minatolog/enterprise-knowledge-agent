from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENTERPRISE_", env_file=".env", extra="ignore")
    root: Path = Path(".enterprise")
    database_url: str = ""
    auth_mode: str = "oidc"
    dev_secret: str = Field(default="", repr=False)
    issuer: str = ""
    audience: str = "enterprise-rag"
    jwks_url: str = ""
    broker_url: str = "memory://"
    eager: bool = True
    redis_url: str = ""
    s3_endpoint: str = ""
    s3_bucket: str = "rag"
    context_tokens: int = Field(default=3000, ge=256, le=16000)
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    connector_hosts: str = ""
    parser: str = "basic"
    otlp_endpoint: str = ""
    verify_answers: bool = True
    connectors_file: Path | None = None
    sync_interval_seconds: int = Field(default=300, ge=60)

    @model_validator(mode="after")
    def validate_mode(self):
        if self.auth_mode not in {"oidc", "dev"}:
            raise ValueError("auth_mode must be oidc or dev")
        if self.auth_mode == "dev" and len(self.dev_secret) < 32:
            raise ValueError("dev mode requires a random secret of at least 32 characters")
        if self.auth_mode == "oidc" and not (self.issuer and self.jwks_url):
            raise ValueError("OIDC issuer and JWKS URL are required")
        if self.parser not in {"basic", "docling"}:
            raise ValueError("parser must be basic or docling")
        return self

    def db_url(self):
        return self.database_url or f"sqlite:///{self.root.resolve() / 'metadata.sqlite3'}"
