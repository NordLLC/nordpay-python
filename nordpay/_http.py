"""Low-level HTTP transport for NordPay SDK."""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any

import httpx

from nordpay.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConnectionError,
    ForbiddenError,
    NordPayError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)

logger = logging.getLogger("nordpay")

DEFAULT_BASE_URL = "https://api.nord-pay.com"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5  # seconds — multiplied by 2^attempt
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_ERROR_MAP: dict[int, type[NordPayError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    429: RateLimitError,
}


def _get_version() -> str:
    try:
        from nordpay import __version__

        return __version__
    except ImportError:
        return "0.0.0"


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": f"nordpay-python/{_get_version()}",
        "Accept": "application/json",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _parse_error(response: httpx.Response) -> NordPayError:
    detail = ""
    body: dict | None = None
    try:
        body = response.json()
        if isinstance(body, dict):
            # NordPay wraps errors: {"error": {"type": "...", "details": "..."}}
            err = body.get("error", {})
            if isinstance(err, dict):
                detail = err.get("details", "") or err.get("detail", "") or err.get("message", "")
            if not detail:
                detail = body.get("detail", "") or body.get("message", "") or str(body)
        else:
            detail = str(body)
    except Exception:
        detail = response.text[:500]

    status = response.status_code
    kwargs: dict[str, Any] = {
        "message": f"HTTP {status}: {detail}",
        "status_code": status,
        "detail": detail,
        "response_body": body,
    }

    if status == 429:
        retry_after_value: float | None = None
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            with contextlib.suppress(ValueError, OverflowError):
                retry_after_value = float(retry_after)
        return RateLimitError(**kwargs, retry_after=retry_after_value)

    exc_class = _ERROR_MAP.get(status, ServerError if status >= 500 else NordPayError)
    return exc_class(**kwargs)


def _log_request(method: str, path: str, kwargs: dict[str, Any]) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    parts = [f"→ {method} {path}"]
    if params := kwargs.get("params"):
        parts.append(f"  params={params}")
    if json_body := kwargs.get("json"):
        parts.append(f"  body={json_body}")
    logger.debug("\n".join(parts))


def _log_response(method: str, path: str, response: httpx.Response) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    body_preview = response.text[:500] if response.content else "(empty)"
    logger.debug("← %s %s %d\n  %s", method, path, response.status_code, body_preview)


def _should_retry(response: httpx.Response, attempt: int, max_retries: int) -> bool:
    return attempt < max_retries and response.status_code in RETRY_STATUS_CODES


def _retry_delay(attempt: int, response: httpx.Response) -> float:
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
    return RETRY_BACKOFF * (2**attempt)


class SyncTransport:
    """Synchronous HTTP transport using httpx with retry support."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        timeout: float,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._client = httpx.Client(
            base_url=base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )
        self._max_retries = max_retries

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        last_response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0 and last_response is not None:
                delay = _retry_delay(attempt - 1, last_response)
                logger.info("Retry %d/%d for %s %s in %.1fs", attempt, self._max_retries, method, path, delay)
                time.sleep(delay)

            _log_request(method, path, kwargs)
            try:
                response = self._client.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                raise TimeoutError(message=f"Request timed out: {method} {path}") from exc
            except httpx.RequestError as exc:
                raise ConnectionError(message=f"Connection error: {exc}") from exc
            last_response = response
            _log_response(method, path, response)

            if response.is_success:
                if not response.content:
                    return None
                return response.json()

            if not _should_retry(response, attempt, self._max_retries):
                break

        assert last_response is not None
        raise _parse_error(last_response)

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport using httpx with retry support."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        timeout: float,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )
        self._max_retries = max_retries

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        import asyncio

        last_response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0 and last_response is not None:
                delay = _retry_delay(attempt - 1, last_response)
                logger.info("Retry %d/%d for %s %s in %.1fs", attempt, self._max_retries, method, path, delay)
                await asyncio.sleep(delay)

            _log_request(method, path, kwargs)
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                raise TimeoutError(message=f"Request timed out: {method} {path}") from exc
            except httpx.RequestError as exc:
                raise ConnectionError(message=f"Connection error: {exc}") from exc
            last_response = response
            _log_response(method, path, response)

            if response.is_success:
                if not response.content:
                    return None
                return response.json()

            if not _should_retry(response, attempt, self._max_retries):
                break

        assert last_response is not None
        raise _parse_error(last_response)

    async def close(self) -> None:
        await self._client.aclose()
