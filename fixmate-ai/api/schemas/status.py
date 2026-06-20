"""API capability and readiness status model."""

from pydantic import BaseModel


class ApiStatus(BaseModel):
    """Non-secret API configuration and data readiness information."""

    status: str
    api_version: str
    database_available: bool
    post_auth_configured: bool
    deterministic_assistant: bool
    optional_ai_provider: str
    optional_ai_configured: bool

