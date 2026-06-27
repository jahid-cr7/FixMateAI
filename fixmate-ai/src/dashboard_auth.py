"""Optional dashboard authentication with role-based access control."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Any

_ROLES = ("admin", "technician", "viewer")

_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"dashboard", "issue_workflow", "settings"},
    "technician": {"dashboard", "issue_workflow"},
    "viewer": {"dashboard"},
}

_HASH_ITERATIONS = 120_000


@dataclass(frozen=True)
class DashboardUser:
    """Authenticated dashboard user with a resolved role."""

    username: str
    role: str

    @property
    def permissions(self) -> set[str]:
        return _ROLE_PERMISSIONS.get(self.role, set())

    def can(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass(frozen=True)
class _Credential:
    """Stored credential with salted hash and role."""

    salt: str
    digest: str
    role: str


def _hash_password(password: str, salt: str) -> str:
    """Derive a PBKDF2-HMAC-SHA256 digest from password and hex salt."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _HASH_ITERATIONS,
    ).hex()


def _credential_from_env(
    env: dict[str, str], role: str
) -> _Credential | None:
    """Build a credential from environment variables if both username and password exist."""
    username_key = f"FIXMATE_DASHBOARD_{role.upper()}_USERNAME"
    password_key = f"FIXMATE_DASHBOARD_{role.upper()}_PASSWORD"
    username = env.get(username_key, "").strip()
    password = env.get(password_key, "").strip()
    if not username or not password:
        return None
    salt = secrets.token_hex(16)
    digest = _hash_password(password, salt)
    return _Credential(salt=salt, digest=digest, role=role)


@dataclass(frozen=True)
class DashboardAuthConfig:
    """Resolved dashboard authentication configuration."""

    enabled: bool
    credentials: dict[str, _Credential]

    @property
    def status_message(self) -> str:
        if not self.enabled:
            return "Dashboard authentication is disabled (demo mode)."
        count = len(self.credentials)
        if count == 0:
            return "Dashboard authentication is enabled but no credentials are configured."
        roles = sorted({c.role for c in self.credentials.values()})
        return f"Dashboard authentication is enabled with {count} user(s) and role(s): {', '.join(roles)}."


def load_dashboard_auth(
    environment: dict[str, str] | None = None,
) -> DashboardAuthConfig:
    """Load dashboard authentication from environment variables only."""
    env = environment if environment is not None else os.environ
    enabled = env.get("FIXMATE_DASHBOARD_AUTH_ENABLED", "false").strip().casefold() in {
        "true",
        "1",
        "yes",
    }
    credentials: dict[str, _Credential] = {}
    if enabled:
        for role in _ROLES:
            cred = _credential_from_env(env, role)
            if cred is not None:
                username = env.get(
                    f"FIXMATE_DASHBOARD_{role.upper()}_USERNAME", ""
                ).strip()
                credentials[username] = cred
    return DashboardAuthConfig(enabled=enabled, credentials=credentials)


def authenticate(
    config: DashboardAuthConfig,
    username: str,
    password: str,
) -> DashboardUser | None:
    """Verify credentials and return the user or None."""
    if not config.enabled:
        return None
    cred = config.credentials.get(username)
    if cred is None:
        return None
    supplied = _hash_password(password, cred.salt)
    if not hmac.compare_digest(supplied, cred.digest):
        return None
    return DashboardUser(username=username, role=cred.role)


def is_auth_enabled(environment: dict[str, str] | None = None) -> bool:
    """Quick check if dashboard auth env var is set to true."""
    env = environment if environment is not None else os.environ
    return env.get("FIXMATE_DASHBOARD_AUTH_ENABLED", "false").strip().casefold() in {
        "true",
        "1",
        "yes",
    }
