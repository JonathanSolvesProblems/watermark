"""Exceptions raised by the client. Every HTTP failure maps to one of these."""
from __future__ import annotations


class RingError(Exception):
    """Base class for anything this package raises."""


class RingAPIError(RingError):
    """A non-2xx response from the Ring API.

    `code` and `detail` come from Ring's JSON:API error body when present.
    """

    def __init__(self, status: int, code: str | None = None, detail: str | None = None,
                 request_id: str | None = None):
        self.status = status
        self.code = code
        self.detail = detail
        self.request_id = request_id
        super().__init__(f"HTTP {status}" + (f" {code}" if code else "") + (f": {detail}" if detail else ""))


class Unauthorized(RingAPIError):
    """401. The access token is missing, expired, or is a refresh token used as a Bearer."""


class Forbidden(RingAPIError):
    """403. The token is valid but not authorized for this device or scope."""


class NotFound(RingAPIError):
    """404. Device, integration, or resource does not exist for this token."""


class MediaNotFound(RingAPIError):
    """416 MEDIA_NOT_FOUND. No recording or snapshot exists at the requested time.

    The image and clip download endpoints never trigger a capture. Start a live
    session (which forces a recording on supported devices) or wait for a motion
    event, then download.
    """


class RateLimited(RingAPIError):
    """429. `retry_after` is seconds, from the Retry-After header when Ring sends one."""

    def __init__(self, retry_after: float | None = None, **kw):
        self.retry_after = retry_after
        super().__init__(429, **kw)


class SignatureError(RingError):
    """A webhook body failed HMAC verification."""


class NonceError(RingError):
    """An account-linking nonce was stale or did not match any unclaimed token."""
