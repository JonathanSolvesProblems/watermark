"""Getting frames out of a Ring camera on demand.

Ring's image and clip endpoints never capture; they only read what was already
recorded. The way to make a camera record right now is to open a live session.
So a capture session is:

  1. open a WHEP session (this forces a recording on supported devices),
  2. pull frames from the WebRTC track for up to 55 s (line-powered cap is 60 s),
  3. close the session,
  4. if WebRTC decoding was not possible (HEVC-only camera, aiortc missing),
     fall back to `download_image(at_timestamp)` for the seconds the session
     covered, which now exist because the session forced a recording.

Every frame keeps Ring's own `X-Media-Timestamp` when it came from the download
path, and the wall-clock receive time when it came off the live track.
"""
from __future__ import annotations

import asyncio
import io
import time
from dataclasses import dataclass, field

from ringpartner import MediaNotFound, RingClient

from .db import now_ms


@dataclass
class Frame:
    data: bytes
    media_ms: int
    requested_ms: int | None
    origin: str                    # live | recording | snapshot | mock
    content_type: str = "image/jpeg"

    @property
    def drift_ms(self) -> int | None:
        return None if self.requested_ms is None else self.media_ms - self.requested_ms


@dataclass
class CaptureResult:
    frames: list[Frame] = field(default_factory=list)
    started_ms: int = 0
    ended_ms: int = 0
    outcome: str = "ok"            # ok | media_not_found | error | unsupported
    detail: str = ""
    session_id: str | None = None


class CaptureBackend:
    async def capture(self, client: RingClient, device_id: str, seconds: int, fps: float) -> CaptureResult:
        raise NotImplementedError


class MockCapture(CaptureBackend):
    """Uses the mock client's `download_image`, one frame per `1/fps` seconds, fast."""

    def __init__(self, real_time: bool = False):
        self.real_time = real_time

    async def capture(self, client, device_id: str, seconds: int, fps: float) -> CaptureResult:
        start = now_ms()
        res = CaptureResult(started_ms=start)
        session = client.create_whep_session(device_id, "v=0 mock offer")
        res.session_id = session.session_id
        n = max(1, int(seconds * fps))
        step_ms = int(1000 / fps)
        for i in range(min(n, 6)):   # six frames is plenty to prove the loop; the demo runs live
            req = start + i * step_ms
            img = client.download_image(device_id, at_timestamp_ms=req)
            res.frames.append(Frame(img.data, img.media_timestamp_ms or req, req, "mock"))
            if self.real_time:
                await asyncio.sleep(1 / fps)
        client.close_whep_session(session)
        res.ended_ms = now_ms()
        return res


class WhepCapture(CaptureBackend):
    """Live WebRTC capture with aiortc, then download fallback."""

    def __init__(self, fallback_to_download: bool = True):
        self.fallback = fallback_to_download

    async def capture(self, client: RingClient, device_id: str, seconds: int, fps: float) -> CaptureResult:
        start = now_ms()
        res = CaptureResult(started_ms=start)
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription  # lazy: optional extra
        except ImportError:
            res.outcome = "unsupported"
            res.detail = "aiortc not installed; install watermark-server[capture]"
            if self.fallback:
                return await self._download_only(client, device_id, seconds, fps, res)
            return res

        pc = RTCPeerConnection()
        pc.addTransceiver("video", direction="recvonly")
        frames: list[Frame] = []
        got_track = asyncio.Event()
        stop_at = time.time() + seconds
        min_gap = 1.0 / fps

        @pc.on("track")
        def on_track(track):
            got_track.set()

            async def pump():
                last = 0.0
                while time.time() < stop_at:
                    try:
                        frame = await asyncio.wait_for(track.recv(), timeout=5)
                    except Exception:  # noqa: BLE001  (timeout or track end)
                        break
                    now = time.time()
                    if now - last < min_gap:
                        continue
                    last = now
                    img = frame.to_image()
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    frames.append(Frame(buf.getvalue(), int(now * 1000), None, "live"))

            asyncio.ensure_future(pump())

        session = None
        try:
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            # aiortc gathers ICE inside setLocalDescription for a plain offer.
            session = await asyncio.to_thread(client.create_whep_session, device_id, pc.localDescription.sdp)
            res.session_id = session.session_id
            await pc.setRemoteDescription(RTCSessionDescription(sdp=session.sdp_answer, type="answer"))
            try:
                await asyncio.wait_for(got_track.wait(), timeout=15)
            except asyncio.TimeoutError:
                res.detail = "no media track within 15 s"
            while time.time() < stop_at:
                await asyncio.sleep(0.5)
        except Exception as e:  # noqa: BLE001
            res.outcome = "error"
            res.detail = f"{type(e).__name__}: {e}"[:300]
        finally:
            try:
                await pc.close()
            except Exception:  # noqa: BLE001
                pass
            if session is not None:
                try:
                    await asyncio.to_thread(client.close_whep_session, session)
                except Exception:  # noqa: BLE001
                    pass
        res.ended_ms = now_ms()
        res.frames = frames
        if not frames and self.fallback:
            # The session ran, so a recording should now exist for that window.
            return await self._download_only(client, device_id, seconds, fps, res, session_ran=session is not None)
        return res

    async def _download_only(self, client, device_id: str, seconds: int, fps: float, res: CaptureResult,
                             session_ran: bool = False) -> CaptureResult:
        """Open a session (if not already), wait, then ask for frames at known timestamps."""
        session = None
        start = res.started_ms or now_ms()
        if not session_ran:
            try:
                session = await asyncio.to_thread(client.create_whep_session, device_id, MINIMAL_SDP_OFFER)
                res.session_id = session.session_id
                start = now_ms()
                await asyncio.sleep(min(seconds, 8))
            except Exception as e:  # noqa: BLE001
                res.outcome = "error"
                res.detail = f"session: {type(e).__name__}: {e}"[:300]
                return res
        step_ms = int(1000 / fps)
        wanted = [start + 2000 + i * step_ms for i in range(min(int(seconds * fps), 8))]
        try:
            for req in wanted:
                if req > now_ms():
                    await asyncio.sleep((req - now_ms()) / 1000)
                try:
                    img = await asyncio.to_thread(client.download_image, device_id, at_timestamp_ms=req)
                except MediaNotFound:
                    continue
                res.frames.append(Frame(img.data, img.media_timestamp_ms or req, req, img.media_origin or "recording",
                                        img.content_type))
        finally:
            if session is not None:
                try:
                    await asyncio.to_thread(client.close_whep_session, session)
                except Exception:  # noqa: BLE001
                    pass
        res.ended_ms = now_ms()
        if not res.frames and res.outcome == "ok":
            res.outcome = "media_not_found"
            res.detail = res.detail or "no frames from live track and no recording found for the window"
        elif res.frames:
            res.outcome = "ok"
        return res


# A syntactically valid recvonly H.264 offer for the case where we only want the
# session side effect (a recording) and cannot decode in-process.
MINIMAL_SDP_OFFER = "\r\n".join([
    "v=0",
    "o=- 0 0 IN IP4 127.0.0.1",
    "s=-",
    "t=0 0",
    "a=group:BUNDLE 0",
    "m=video 9 UDP/TLS/RTP/SAVPF 96",
    "c=IN IP4 0.0.0.0",
    "a=mid:0",
    "a=recvonly",
    "a=rtcp-mux",
    "a=rtpmap:96 H264/90000",
    "a=fmtp:96 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f",
    "a=ice-ufrag:wtrm",
    "a=ice-pwd:watermarkwatermarkwatermark",
    "a=fingerprint:sha-256 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00",
    "a=setup:actpass",
    "",
])


def make_capture_backend(settings) -> CaptureBackend:
    if settings.capture_backend == "whep":
        return WhepCapture(fallback_to_download=settings.capture_download_fallback)
    return MockCapture()
