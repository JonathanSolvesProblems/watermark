"""ringwire: a typed Python client for the Ring Partner API.

    from ringwire import RingClient, verify_and_parse

    client = RingClient(access_token)
    for d in client.list_devices():
        s = client.status(d.id)
        if s.flood_faulted:
            ...

    event = verify_and_parse(raw_body, request.headers["X-Signature"], signing_key)
    if event.type == "flood_detected": ...
"""
from .client import API_BASE, OAUTH_TOKEN_URL, RingClient
from .errors import (Forbidden, MediaNotFound, NonceError, NotFound, RateLimited, RingAPIError, RingError,
                     SignatureError, Unauthorized)
from .nonce import compute_nonce, is_fresh, match_nonce
from .types import (Device, DeviceCapabilities, DeviceConfigurations, DeviceStatus, HistoryEvent, HistoryPage,
                    MediaClip, MediaImage, TokenSet, User, WhepSession)
from .webhooks import (ALL_EVENTS, SENSOR_EVENTS, SENSOR_STATE_EVENTS, SENSOR_THRESHOLD_EVENTS, WebhookEvent,
                       make_event, parse_event, sign, verify_and_parse, verify_signature)

__version__ = "0.1.0"
__all__ = [
    "API_BASE", "OAUTH_TOKEN_URL", "RingClient",
    "RingError", "RingAPIError", "Unauthorized", "Forbidden", "NotFound", "MediaNotFound", "RateLimited",
    "SignatureError", "NonceError",
    "compute_nonce", "is_fresh", "match_nonce",
    "TokenSet", "User", "Device", "DeviceStatus", "DeviceCapabilities", "DeviceConfigurations",
    "HistoryEvent", "HistoryPage", "MediaImage", "MediaClip", "WhepSession",
    "WebhookEvent", "parse_event", "verify_signature", "verify_and_parse", "sign", "make_event",
    "ALL_EVENTS", "SENSOR_EVENTS", "SENSOR_STATE_EVENTS", "SENSOR_THRESHOLD_EVENTS",
]
