"""One-way (Ring-driven) account linking nonce helpers.

Ring redirects the user to the partner's Account Link URL with `nonce` and `time`.
The nonce is HMAC-SHA256(signing_key, "<time_ms>:<account_id>") encoded as URL-safe
Base64 without padding. Same key as webhooks, different encoding: webhooks are hex.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections.abc import Iterable

from .errors import NonceError

DEFAULT_WINDOW_SECONDS = 600


def compute_nonce(signing_key: str, time_ms: int, account_id: str) -> str:
    mac = hmac.new(signing_key.encode("utf-8"), f"{time_ms}:{account_id}".encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).rstrip(b"=").decode("ascii")


def is_fresh(time_ms: int, now_ms: int | None = None, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> bool:
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    return (now - int(time_ms)) / 1000.0 <= window_seconds and int(time_ms) <= now + 5000


def match_nonce(signing_key: str, nonce: str, time_ms: int, candidate_account_ids: Iterable[str],
                now_ms: int | None = None, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> str:
    """Return the account id whose recomputed nonce matches, constant-time per candidate.

    `candidate_account_ids` is the set of unclaimed tokens' account ids (from
    `GET /v1/users/me` on each token). Raises `NonceError` if stale or unmatched.
    """
    if not is_fresh(time_ms, now_ms, window_seconds):
        raise NonceError("nonce timestamp is outside the validation window")
    for account_id in candidate_account_ids:
        expected = compute_nonce(signing_key, time_ms, account_id)
        if hmac.compare_digest(expected, nonce):
            return account_id
    raise NonceError("nonce did not match any unclaimed token")
