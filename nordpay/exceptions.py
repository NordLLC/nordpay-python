"""NordPay SDK exceptions."""

from __future__ import annotations


class NordPayError(Exception):
    """Base exception for all NordPay SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        detail: str | None = None,
        response_body: dict | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        self.response_body = response_body
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self.status_code}, detail={self.detail!r})"


class AuthenticationError(NordPayError):
    """Invalid or missing API key (HTTP 401)."""


class ForbiddenError(NordPayError):
    """Insufficient permissions (HTTP 403)."""


class BadRequestError(NordPayError):
    """Invalid request parameters (HTTP 400)."""


class NotFoundError(NordPayError):
    """Resource not found (HTTP 404)."""


class RateLimitError(NordPayError):
    """Too many requests (HTTP 429).

    Check ``retry_after`` for seconds to wait before retrying.
    """

    def __init__(self, *args, retry_after: float | None = None, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServerError(NordPayError):
    """Server-side error (HTTP 5xx)."""


class ConnectionError(NordPayError):
    """Network connectivity error (DNS, TCP, TLS)."""


class TimeoutError(NordPayError):
    """Request timed out."""


class WebhookVerificationError(NordPayError):
    """Postback secret verification failed."""

    def __init__(self, message: str = "Invalid postback secret") -> None:
        super().__init__(message=message)
