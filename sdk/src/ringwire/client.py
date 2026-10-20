"""Synchronous client for the Ring Partner API (api.amazonvision.com).

Covers everything a partner app calls: OAuth token exchange and refresh, users,
devices (cameras, doorbells, chimes, sensors), event history, image and clip
download (the two-step 303 flow), WHEP live sessions, chime playback, and the
app-integrations calls that finish account linking.

Retries 429 (honouring Retry-After) and 5xx with backoff. Never follows the 303
on media downloads automatically, because the redirect target must be fetched
without the Bearer header.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx

from .errors import Forbidden, MediaNotFound, NotFound, RateLimited, RingAPIError, Unauthorized
from .types import (Device, DeviceCapabilities, DeviceConfigurations, DeviceStatus, HistoryEvent,
                    HistoryPage, MediaClip, MediaImage, TokenSet, User, WhepSession)

API_BASE = "https://api.amazonvision.com"
OAUTH_TOKEN_URL = "https://oauth.ring.com/oauth/token"
RTSPS_HOST = "video.rtsp.amazonvision.com"
RTSPS_PORT = 322

TokenProvider = Callable[[], str]


def _error_from_response(r: httpx.Response) -> RingAPIError:
    code = detail = None
    try:
        body = r.json()
        errs = body.get("errors") or []
        if errs:
            code = errs[0].get("code")
            detail = errs[0].get("detail") or errs[0].get("title")
        elif "error" in body:
            code = body.get("error")
            detail = body.get("error_description") or body.get("message")
    except Exception:
        detail = r.text[:200] if r.text else None
    rid = r.headers.get("X-Request-ID")
    kw = dict(code=code, detail=detail, request_id=rid)
    if r.status_code == 401:
        return Unauthorized(401, **kw)
    if r.status_code == 403:
        return Forbidden(403, **kw)
    if r.status_code == 404:
        return NotFound(404, **kw)
    if r.status_code == 416:
        return MediaNotFound(416, **kw)
    if r.status_code == 429:
        ra = r.headers.get("Retry-After")
        return RateLimited(retry_after=float(ra) if ra else None, **kw)
    return RingAPIError(r.status_code, **kw)


class RingClient:
    """One client per Ring user. Tokens are user-scoped.

    Pass either a static `access_token` or a `token_provider` callable that
    returns a currently valid access token (so the caller owns refresh).
    """

    def __init__(self, access_token: str | None = None, *, token_provider: TokenProvider | None = None,
                 base_url: str = API_BASE, timeout: float = 20.0, max_retries: int = 3,
                 transport: httpx.BaseTransport | None = None, user_agent: str = "ringwire-py/0.1"):
        if not access_token and not token_provider:
            raise ValueError("access_token or token_provider is required")
        self._token = access_token
        self._provider = token_provider
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._http = httpx.Client(timeout=timeout, transport=transport,
                                  headers={"User-Agent": user_agent}, follow_redirects=False)

    # ---------- auth (static, no token needed) ----------

    @staticmethod
    def exchange_code(code: str, client_id: str, client_secret: str, code_verifier: str | None = None,
                      *, token_url: str = OAUTH_TOKEN_URL, transport: httpx.BaseTransport | None = None) -> TokenSet:
        """Exchange the authorization code Ring POSTed to the Token Exchange URL.
        One-way codes expire in 60 seconds; partner-initiated in 10 minutes."""
        form = {"grant_type": "authorization_code", "code": code, "client_id": client_id,
                "client_secret": client_secret}
        if code_verifier:
            form["code_verifier"] = code_verifier
        with httpx.Client(transport=transport, timeout=20.0) as c:
            r = c.post(token_url, data=form)
        if r.status_code != 200:
            raise _error_from_response(r)
        return TokenSet.from_json(r.json())

    @staticmethod
    def refresh(refresh_token: str, client_id: str, client_secret: str, *, token_url: str = OAUTH_TOKEN_URL,
                transport: httpx.BaseTransport | None = None) -> TokenSet:
        """Refresh tokens are valid ~30 days and rotate on every exchange; store the new pair."""
        form = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id,
                "client_secret": client_secret}
        with httpx.Client(transport=transport, timeout=20.0) as c:
            r = c.post(token_url, data=form)
        if r.status_code != 200:
            raise _error_from_response(r)
        return TokenSet.from_json(r.json())

    # ---------- plumbing ----------

    def _auth(self) -> dict[str, str]:
        token = self._provider() if self._provider else self._token
        return {"Authorization": f"Bearer {token}"}

    def _request(self, method: str, path: str, *, json: Any = None, params: dict[str, Any] | None = None,
                 content: bytes | str | None = None, headers: dict[str, str] | None = None,
                 ok: tuple[int, ...] = (200, 201)) -> httpx.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        attempt = 0
        while True:
            h = {**self._auth(), **(headers or {})}
            r = self._http.request(method, url, json=json, params=params, content=content, headers=h)
            if r.status_code in ok:
                return r
            err = _error_from_response(r)
            retryable = isinstance(err, RateLimited) or 500 <= r.status_code < 600
            if retryable and attempt < self.max_retries:
                delay = err.retry_after if isinstance(err, RateLimited) and err.retry_after else (2 ** attempt) * 0.5
                time.sleep(delay)
                attempt += 1
                continue
            raise err

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params).json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "RingClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ---------- users / account ----------

    def me(self) -> User:
        return User.from_json(self._get_json("/v1/users/me"))

    def confirm_account_link(self, nonce: str, account_identifier: str | None = None) -> dict[str, Any]:
        """One-way linking step 1: POST the nonce. Status becomes `awaiting`."""
        body: dict[str, Any] = {"nonce": nonce}
        if account_identifier:
            body["account_identifier"] = account_identifier
        return self._request("POST", "/v1/accounts/me/app-integrations", json=body).json()

    def update_integration(self, status: str | None = None, account_identifier: str | None = None) -> dict[str, Any]:
        """Step 2, mandatory: PATCH `status: completed`. Without it the integration
        stays `awaiting`, device consents stay inactive and no webhooks arrive."""
        body: dict[str, Any] = {}
        if status:
            body["status"] = status
        if account_identifier:
            body["account_identifier"] = account_identifier
        if not body:
            raise ValueError("status or account_identifier is required")
        return self._request("PATCH", "/v1/accounts/me/app-integrations", json=body).json()

    def subscriptions(self) -> dict[str, Any]:
        return self._get_json("/v1/accounts/me/subscriptions")

    # ---------- devices ----------

    def list_devices(self, include: list[str] | None = None) -> list[Device]:
        params = {"include": ",".join(include)} if include else None
        body = self._get_json("/v1/devices", params=params)
        return [Device.from_json(d) for d in body.get("data", [])]

    def list_devices_raw(self, include: list[str] | None = None) -> dict[str, Any]:
        params = {"include": ",".join(include)} if include else None
        return self._get_json("/v1/devices", params=params)

    def get_device(self, device_id: str) -> Device:
        body = self._get_json(f"/v1/devices/{device_id}")
        return Device.from_json(body.get("data", body))

    def status(self, device_id: str, component_id: int | None = None) -> DeviceStatus:
        params = {"component_id": component_id} if component_id is not None else None
        return DeviceStatus.from_json(self._get_json(f"/v1/devices/{device_id}/status", params=params))

    def capabilities(self, device_id: str, component_id: int | None = None) -> DeviceCapabilities:
        params = {"component_id": component_id} if component_id is not None else None
        return DeviceCapabilities.from_json(self._get_json(f"/v1/devices/{device_id}/capabilities", params=params))

    def configurations(self, device_id: str, component_id: int | None = None) -> DeviceConfigurations:
        params = {"component_id": component_id} if component_id is not None else None
        return DeviceConfigurations.from_json(self._get_json(f"/v1/devices/{device_id}/configurations", params=params))

    def location(self, device_id: str) -> dict[str, Any]:
        return self._get_json(f"/v1/devices/{device_id}/location")

    # ---------- event history (cameras and doorbells only; sensors have none) ----------

    def event_history(self, device_id: str, event_types: str | list[str] | None = None,
                      page_key: str | None = None) -> HistoryPage:
        params: dict[str, Any] = {}
        if event_types:
            params["event_types"] = ",".join(event_types) if isinstance(event_types, list) else event_types
        if page_key:
            params["page[key]"] = page_key
        body = self._get_json(f"/v1/history/devices/{device_id}/events", params=params or None)
        events = [HistoryEvent.from_json(d) for d in body.get("data", [])]
        return HistoryPage(events=events, next_path=(body.get("links") or {}).get("next"), raw=body)

    def iter_event_history(self, device_id: str, event_types: str | list[str] | None = None,
                           max_pages: int = 50) -> Iterator[HistoryEvent]:
        """Follows `links.next` until a page comes back empty. Ring keeps sending a
        `next` link even on the last page, so an empty page is the stop signal."""
        page = self.event_history(device_id, event_types)
        pages = 1
        while True:
            yield from page.events
            if not page.events or not page.next_path or pages >= max_pages:
                return
            key = _page_key_from_path(page.next_path)
            page = self.event_history(device_id, event_types, page_key=key)
            pages += 1

    # ---------- media ----------

    def download_image(self, device_id: str, *, at_timestamp_ms: int | None = None,
                       start_ms: int | None = None, end_ms: int | None = None,
                       fmt: str = "jpeg", width: int = 1920, height: int = 1080,
                       component_id: int | None = None) -> MediaImage:
        """Two-step download. Pass `at_timestamp_ms` (±10 s tolerance) or a
        `start_ms`/`end_ms` window of at most 24 h for the latest frame in it.

        This never captures. If nothing was recorded near that time Ring returns
        416 and this raises `MediaNotFound`.
        """
        if at_timestamp_ms is not None:
            payload: dict[str, Any] = {"type": "at_timestamp", "timestamp": int(at_timestamp_ms)}
        elif start_ms is not None:
            payload = {"type": "latest_in_range", "start_timestamp": int(start_ms)}
            if end_ms is not None:
                payload["end_timestamp"] = int(end_ms)
        else:
            raise ValueError("at_timestamp_ms or start_ms is required")
        payload["image_options"] = {"format": fmt, "resolution": {"width": width, "height": height}}
        params = {"component_id": component_id} if component_id is not None else None
        r = self._request("POST", f"/v1/devices/{device_id}/media/image/download", json=payload,
                          params=params, ok=(303,))
        presigned = r.headers.get("Location")
        if not presigned:
            raise RingAPIError(r.status_code, code="NO_LOCATION", detail="303 without Location header")
        dl = self._http.get(presigned, follow_redirects=True)
        if dl.status_code != 200:
            raise _error_from_response(dl)
        ts = dl.headers.get("X-Media-Timestamp")
        return MediaImage(
            data=dl.content,
            content_type=dl.headers.get("Content-Type", "application/octet-stream"),
            media_timestamp_ms=int(ts) if ts and ts.isdigit() else None,
            media_origin=dl.headers.get("X-Media-Origin"),
            requested_timestamp_ms=at_timestamp_ms,
        )

    def download_clip(self, device_id: str, *, timestamp_ms: int, duration_ms: int = 5000,
                      codec: str = "avc", frame_rate: int = 5, width: int = 1080, height: int = 720,
                      audio: bool = False, component_id: int | None = None) -> MediaClip:
        """MP4 of already-recorded footage (up to 15 minutes). 206 means Ring had
        only part of the window; `partial` is set and the headers say what came back."""
        payload = {
            "timestamp": int(timestamp_ms), "duration": int(duration_ms),
            "video_options": {"codec": codec, "frame_rate": frame_rate,
                              "resolution": {"width": width, "height": height}},
            "audio_options": {"audio_enabled": bool(audio)},
        }
        params = {"component_id": component_id} if component_id is not None else None
        r = self._request("POST", f"/v1/devices/{device_id}/media/video/download", json=payload,
                          params=params, ok=(303,))
        presigned = r.headers.get("Location")
        if not presigned:
            raise RingAPIError(r.status_code, code="NO_LOCATION", detail="303 without Location header")
        dl = self._http.get(presigned, follow_redirects=True)
        if dl.status_code not in (200, 206):
            raise _error_from_response(dl)
        ts = dl.headers.get("X-Media-Timestamp")
        dur = dl.headers.get("X-Media-Duration")
        return MediaClip(data=dl.content, media_timestamp_ms=int(ts) if ts and ts.isdigit() else None,
                         media_duration_ms=int(dur) if dur and dur.isdigit() else None,
                         partial=dl.status_code == 206)

    # ---------- live view ----------

    def create_whep_session(self, device_id: str, sdp_offer: str, component_id: int | None = None) -> WhepSession:
        """POST an SDP offer, get the answer and the session URL. Battery devices
        stream 30 s, line-powered 60 s. Starting a session forces a recording on
        supported devices, which is what makes a later image download possible."""
        params = {"component_id": component_id} if component_id is not None else None
        r = self._request("POST", f"/v1/devices/{device_id}/media/streaming/whep/sessions",
                          content=sdp_offer, headers={"Content-Type": "application/sdp"},
                          params=params, ok=(201,))
        return WhepSession(session_url=r.headers.get("Location", ""), sdp_answer=r.text, device_id=device_id)

    def close_whep_session(self, session: WhepSession | str) -> None:
        url = session.session_url if isinstance(session, WhepSession) else session
        self._request("DELETE", url, ok=(200, 202, 204))

    @staticmethod
    def rtsps_url(device_id: str, access_token: str | None = None) -> str:
        """RTSPS URL for server-side clients (ffmpeg, VLC). With a token it uses the
        Basic-auth-in-URL form Ring documents (empty user, token as password)."""
        auth = f":{access_token}@" if access_token else ""
        return f"rtsps://{auth}{RTSPS_HOST}:{RTSPS_PORT}/v1/devices/{device_id}/stream"

    # ---------- chimes (the only write in the API) ----------

    def play_chime(self, device_id: str, audio_ref: str) -> str:
        """Play the audio in one of the app's slots. Read `audio_ref` from
        `configurations(device_id).chime_slots`; the request carries no slot name."""
        body = {"data": {"type": "audio", "attributes": {"audio_ref": audio_ref}}}
        r = self._request("POST", f"/v1/devices/{device_id}/media/audio/playback", json=body)
        return ((r.json().get("data") or {}).get("attributes") or {}).get("status", "unknown")


def _page_key_from_path(path: str) -> str | None:
    from urllib.parse import parse_qs, urlparse
    q = parse_qs(urlparse(path).query)
    vals = q.get("page[key]") or q.get("page%5Bkey%5D")
    return vals[0] if vals else None
