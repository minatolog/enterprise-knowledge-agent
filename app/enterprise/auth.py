from dataclasses import dataclass

import jwt
from fastapi import HTTPException

from app.enterprise.config import Settings


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    groups: tuple[str, ...]
    roles: tuple[str, ...]

    def editor(self):
        if not set(self.roles) & {"editor", "admin"}:
            raise HTTPException(403, "editor role required")


class Auth:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(settings.jwks_url) if settings.auth_mode == "oidc" else None

    def verify(self, authorization: str | None):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer token required")
        token = authorization[7:]
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key if self.jwks else self.settings.dev_secret
            claims = jwt.decode(
                token, key, algorithms=["RS256"] if self.jwks else ["HS256"],
                audience=self.settings.audience,
                issuer=self.settings.issuer if self.jwks else "enterprise-rag-dev",
                options={"require": ["exp", "iat", "sub", "iss", "aud", "tenant_id"]},
            )
            for name in ("sub", "tenant_id"):
                if not isinstance(claims[name], str) or not claims[name]:
                    raise ValueError("invalid identity")
            for name in ("groups", "roles"):
                if not isinstance(claims.get(name, []), list) or not all(isinstance(x, str) for x in claims.get(name, [])):
                    raise ValueError("invalid groups/roles")
            return Principal(claims["sub"], claims["tenant_id"], tuple(claims.get("groups", [])), tuple(claims.get("roles", [])))
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise HTTPException(401, "invalid or expired token") from exc
