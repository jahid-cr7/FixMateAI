"""Service-layer errors mapped to safe HTTP responses by routers."""


class ServiceUnavailableError(RuntimeError):
    """A diagnostic dependency failed without exposing its traceback."""

