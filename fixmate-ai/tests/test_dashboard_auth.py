"""Tests for optional dashboard authentication and role-based access control."""

from __future__ import annotations

from src.dashboard_auth import (
    DashboardAuthConfig,
    DashboardUser,
    authenticate,
    is_auth_enabled,
    load_dashboard_auth,
)


def _full_env() -> dict[str, str]:
    return {
        "FIXMATE_DASHBOARD_AUTH_ENABLED": "true",
        "FIXMATE_DASHBOARD_ADMIN_USERNAME": "admin",
        "FIXMATE_DASHBOARD_ADMIN_PASSWORD": "adminpass",
        "FIXMATE_DASHBOARD_TECHNICIAN_USERNAME": "tech",
        "FIXMATE_DASHBOARD_TECHNICIAN_PASSWORD": "techpass",
        "FIXMATE_DASHBOARD_VIEWER_USERNAME": "viewer",
        "FIXMATE_DASHBOARD_VIEWER_PASSWORD": "viewerpass",
    }


def test_auth_disabled_by_default() -> None:
    config = load_dashboard_auth({})
    assert config.enabled is False
    assert config.credentials == {}
    assert "disabled" in config.status_message.casefold()


def test_auth_enabled_but_no_credentials() -> None:
    env = {"FIXMATE_DASHBOARD_AUTH_ENABLED": "true"}
    config = load_dashboard_auth(env)
    assert config.enabled is True
    assert config.credentials == {}
    assert "no credentials" in config.status_message.casefold()


def test_is_auth_enabled_helper() -> None:
    assert is_auth_enabled({}) is False
    assert is_auth_enabled({"FIXMATE_DASHBOARD_AUTH_ENABLED": "true"}) is True
    assert is_auth_enabled({"FIXMATE_DASHBOARD_AUTH_ENABLED": "1"}) is True
    assert is_auth_enabled({"FIXMATE_DASHBOARD_AUTH_ENABLED": "yes"}) is True
    assert is_auth_enabled({"FIXMATE_DASHBOARD_AUTH_ENABLED": "false"}) is False


def test_load_all_three_roles() -> None:
    config = load_dashboard_auth(_full_env())
    assert config.enabled is True
    assert len(config.credentials) == 3
    roles = {c.role for c in config.credentials.values()}
    assert roles == {"admin", "technician", "viewer"}


def test_successful_admin_login() -> None:
    config = load_dashboard_auth(_full_env())
    user = authenticate(config, "admin", "adminpass")
    assert user is not None
    assert user.role == "admin"
    assert user.username == "admin"
    assert user.can("issue_workflow") is True
    assert user.can("dashboard") is True


def test_successful_technician_login() -> None:
    config = load_dashboard_auth(_full_env())
    user = authenticate(config, "tech", "techpass")
    assert user is not None
    assert user.role == "technician"
    assert user.can("issue_workflow") is True
    assert user.can("settings") is False


def test_successful_viewer_login() -> None:
    config = load_dashboard_auth(_full_env())
    user = authenticate(config, "viewer", "viewerpass")
    assert user is not None
    assert user.role == "viewer"
    assert user.can("dashboard") is True
    assert user.can("issue_workflow") is False


def test_wrong_password_rejected() -> None:
    config = load_dashboard_auth(_full_env())
    user = authenticate(config, "admin", "wrongpass")
    assert user is None


def test_unknown_username_rejected() -> None:
    config = load_dashboard_auth(_full_env())
    user = authenticate(config, "hacker", "anypass")
    assert user is None


def test_authenticate_when_disabled_returns_none() -> None:
    config = load_dashboard_auth({"FIXMATE_DASHBOARD_AUTH_ENABLED": "false"})
    user = authenticate(config, "anything", "anything")
    assert user is None


def test_viewer_cannot_issue_workflow() -> None:
    config = load_dashboard_env_viewer_only()
    user = authenticate(config, "viewer", "viewerpass")
    assert user is not None
    assert user.can("issue_workflow") is False
    assert user.can("dashboard") is True


def test_technician_can_issue_workflow() -> None:
    config = load_dashboard_env_tech_only()
    user = authenticate(config, "tech", "techpass")
    assert user is not None
    assert user.can("issue_workflow") is True


def test_no_password_leakage_in_config_status() -> None:
    env = _full_env()
    secret = env["FIXMATE_DASHBOARD_ADMIN_PASSWORD"]
    config = load_dashboard_auth(env)
    assert secret not in config.status_message


def test_no_password_leakage_in_user_object() -> None:
    env = _full_env()
    secret = env["FIXMATE_DASHBOARD_ADMIN_PASSWORD"]
    config = load_dashboard_auth(env)
    user = authenticate(config, "admin", "adminpass")
    assert user is not None
    assert secret not in str(user)
    assert secret not in user.username
    assert secret not in user.role


def test_passwords_are_hashed_not_stored_plaintext() -> None:
    env = _full_env()
    config = load_dashboard_auth(env)
    for username, cred in config.credentials.items():
        assert cred.digest != env.get(
            f"FIXMATE_DASHBOARD_{cred.role.upper()}_PASSWORD", ""
        )
        assert len(cred.salt) == 32
        assert len(cred.digest) == 64


def test_partial_credentials_load_only_configured() -> None:
    env = {
        "FIXMATE_DASHBOARD_AUTH_ENABLED": "true",
        "FIXMATE_DASHBOARD_ADMIN_USERNAME": "admin",
        "FIXMATE_DASHBOARD_ADMIN_PASSWORD": "adminpass",
    }
    config = load_dashboard_auth(env)
    assert len(config.credentials) == 1
    assert "admin" in config.credentials


def test_empty_username_password_skipped() -> None:
    env = {
        "FIXMATE_DASHBOARD_AUTH_ENABLED": "true",
        "FIXMATE_DASHBOARD_VIEWER_USERNAME": "",
        "FIXMATE_DASHBOARD_VIEWER_PASSWORD": "",
    }
    config = load_dashboard_auth(env)
    assert len(config.credentials) == 0


def test_dashboard_user_permissions_consistency() -> None:
    admin = DashboardUser(username="a", role="admin")
    tech = DashboardUser(username="t", role="technician")
    viewer = DashboardUser(username="v", role="viewer")

    admin_perms = admin.permissions
    tech_perms = tech.permissions
    viewer_perms = viewer.permissions

    assert admin_perms > tech_perms > viewer_perms
    assert viewer_perms <= tech_perms <= admin_perms


def test_dashboard_user_unknown_role_has_minimal_permissions() -> None:
    user = DashboardUser(username="x", role="unknown")
    assert user.permissions == set()
    assert user.can("dashboard") is False
    assert user.can("issue_workflow") is False


def load_dashboard_env_viewer_only() -> DashboardAuthConfig:
    return load_dashboard_auth(
        {
            "FIXMATE_DASHBOARD_AUTH_ENABLED": "true",
            "FIXMATE_DASHBOARD_VIEWER_USERNAME": "viewer",
            "FIXMATE_DASHBOARD_VIEWER_PASSWORD": "viewerpass",
        }
    )


def load_dashboard_env_tech_only() -> DashboardAuthConfig:
    return load_dashboard_auth(
        {
            "FIXMATE_DASHBOARD_AUTH_ENABLED": "true",
            "FIXMATE_DASHBOARD_TECHNICIAN_USERNAME": "tech",
            "FIXMATE_DASHBOARD_TECHNICIAN_PASSWORD": "techpass",
        }
    )
