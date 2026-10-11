"""Static demo credentials, bound to server-owned roles and actor identifiers."""

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.api.config import Settings
from packages.domain.cases import Actor, WorkflowError

bearer = HTTPBearer(auto_error=False, description="Token demo dari konfigurasi server atau --demo.")


def registry(settings: Settings) -> tuple[tuple[bytes, Actor], ...]:
    return tuple(
        (hashlib.sha256(token.encode()).digest(), Actor(actor_id=identifier, role=role))
        for token, identifier, role in (
            (settings.reviewer_token, settings.reviewer_id, "REVIEWER"),
            (settings.supervisor_token, settings.supervisor_id, "SUPERVISOR"),
        )
        if token is not None
    )


def require_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Actor:
    configured = request.app.state.auth_registry
    if not configured:
        raise WorkflowError(503, "AUTH_NOT_CONFIGURED")
    if len(request.headers.getlist("authorization")) != 1 or credentials is None:
        raise WorkflowError(401, "UNAUTHORIZED", {"WWW-Authenticate": "Bearer"})
    if not 32 <= len(credentials.credentials) <= 256:
        raise WorkflowError(401, "UNAUTHORIZED", {"WWW-Authenticate": "Bearer"})
    supplied = hashlib.sha256(credentials.credentials.encode()).digest()
    actor = None
    for digest, candidate in configured:
        if secrets.compare_digest(digest, supplied):
            actor = candidate
    if actor is None:
        raise WorkflowError(401, "UNAUTHORIZED", {"WWW-Authenticate": "Bearer"})
    return actor
