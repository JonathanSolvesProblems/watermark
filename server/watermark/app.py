"""FastAPI application. Three audiences share it:

- Ring, which POSTs webhooks to `/webhooks/ring`, authorization codes to
  `/oauth/token`, and redirects users to `/link`.
- The web app (`web/`), which talks to `/api/*`.
- The rover, which long-polls `/rover/commands` (local transport) and always
  reports to `/rover/report`.

Run: `uvicorn watermark.main:app --port 8000` (MODE=mock needs nothing else).
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from ringpartner import RingClient, SignatureError, is_fresh, make_event, match_nonce, parse_event, verify_and_parse

from .blobs import make_blob_store
from .capture import make_capture_backend
from .captions import make_captioner
from .config import Settings
from .db import Database, now_ms
from .dispatch import make_dispatcher
from .incidents import IncidentManager
from .pack import PackBuilder
from .ring import MockRing, RingService

log = logging.getLogger("watermark")


class LinkBody(BaseModel):
    nonce: str = ""
    time: int = 0
    email: str


class DevicePatch(BaseModel):
    room: str | None = None
    route_id: str | None = None
    covered_by: str | None = None


class RouteBody(BaseModel):
    id: str
    name: str
    description: str = ""


class RoverReport(BaseModel):
    incident_id: str
    kind: str                       # ack | on_station | blocked | wet | telemetry | error | returned
    message: str = ""
    data: dict[str, Any] = {}


class Trigger(BaseModel):
    device_id: str | None = None
    kind: str = "flood"             # flood | freeze
    action: str = "detected"        # detected | cleared
    controlled_test: bool = True



class AppState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.db_path)
        self.blobs = make_blob_store(settings)
        self.ring = RingService(settings, self.db)
        self.packs = PackBuilder(settings, self.db, self.blobs)
        self.manager = IncidentManager(settings, self.db, self.ring, make_capture_backend(settings),
                                       make_captioner(settings), make_dispatcher(settings), self.blobs, self.packs)
        self.background: list[asyncio.Task] = []
        if settings.is_mock:
            self._seed_mock()

    def _seed_mock(self) -> None:
        """A linked mock account with a sensor, a rover cam, a fixed cam and a chime,
        with the sensor routed to the rover, so `POST /api/test/trigger` exercises
        the whole path on first run."""
        self.db.upsert_account(MockRing.ACCOUNT, email="mock@example.com", link_status="completed",
                               access_token="mock", refresh_token="mock", expires_at=time.time() + 10 ** 9)
        self.ring.discover(MockRing.ACCOUNT)
        self.db.upsert_route("route-water-heater", "Hall to water heater", "tape line from dock, one left turn")
        self.db.upsert_device(MockRing.SENSOR, room="Water heater closet", route_id="route-water-heater")
        self.db.upsert_device(MockRing.CAM, room="rover")
        self.db.upsert_device(MockRing.FIXED_CAM, room="Basement")

    def current_account_id(self) -> str | None:
        if self.settings.is_mock:
            return MockRing.ACCOUNT
        rows = self.db.list_accounts(link_status="completed")
        if not rows:
            return None
        rows.sort(key=lambda r: r.get("updated_at") or 0, reverse=True)
        return rows[0]["account_id"]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    state = AppState(settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        state.background.append(asyncio.create_task(_reconcile_loop(state)))
        state.background.append(asyncio.create_task(_refresh_loop(state)))
        try:
            yield
        finally:
            for t in state.background:
                t.cancel()
            await asyncio.gather(*state.background, return_exceptions=True)
            await state.manager.shutdown()

    app = FastAPI(title="Watermark", version="0.1.0", lifespan=lifespan)
    app.state.wm = state
    app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin, "http://localhost:3000"],
                       allow_methods=["*"], allow_headers=["*"])

    def st() -> AppState:
        return state

    # ------------------------------------------------------------- health

    @app.get("/health")
    async def health(s: AppState = Depends(st)):
        return {"ok": True, "mode": s.settings.mode, "open_incidents": len(s.db.list_incidents(status="open"))}

    # ------------------------------------------------------------- Ring: webhooks

    @app.post("/webhooks/ring")
    async def ring_webhook(request: Request, s: AppState = Depends(st),
                           x_signature: str | None = Header(default=None, alias="X-Signature")):
        raw = await request.body()
        try:
            ev = verify_and_parse(raw, x_signature, s.settings.ring_hmac_key)
        except SignatureError:
            # 4xx: Ring will not retry, and a spoofed body must never be processed.
            raise HTTPException(status_code=401, detail="invalid signature")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"malformed payload: {e}")
        # Persist-first happens inside handle_event; respond well within Ring's 5 s.
        asyncio.create_task(s.manager.handle_event(ev, source="received"))
        return {"status": "accepted", "request_id": ev.request_id}

    # ------------------------------------------------------------- Ring: token exchange + linking

    @app.post("/oauth/token")
    async def token_exchange(request: Request, s: AppState = Depends(st)):
        """Ring POSTs `code` here as application/x-www-form-urlencoded (never JSON)."""
        form = await request.form()
        code = form.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="missing code")
        if s.settings.is_mock:
            return {"status": "mock"}
        try:
            toks = await asyncio.to_thread(RingClient.exchange_code, str(code), s.settings.ring_client_id or "",
                                           s.settings.ring_client_secret or "")
            client = RingClient(toks.access_token, base_url=s.settings.ring_api_base)
            me = await asyncio.to_thread(client.me)
        except Exception as e:  # noqa: BLE001
            log.exception("token exchange failed")
            raise HTTPException(status_code=502, detail=f"token exchange failed: {e}")
        s.ring.store_tokens(me.account_id, toks.access_token, toks.refresh_token, toks.expires_in,
                            link_status="unclaimed", email=me.email)
        return {"status": "ok"}

    @app.get("/link")
    async def link_redirect(nonce: str = "", time_: str = Query(default="", alias="time"), s: AppState = Depends(st)):
        """Ring's Account Link URL. Hand off to the web app's sign-in page with the
        nonce and time preserved (sign-in is mandatory per Ring)."""
        return RedirectResponse(f"{s.settings.web_origin}/link?nonce={nonce}&time={time_}", status_code=302)

    @app.post("/api/link")
    async def complete_link(body: LinkBody, s: AppState = Depends(st)):
        if s.settings.is_mock:
            s.db.upsert_account(MockRing.ACCOUNT, email=body.email, link_status="completed")
            return {"status": "completed", "account_id": MockRing.ACCOUNT, "mock": True}
        if not is_fresh(body.time):
            raise HTTPException(status_code=400, detail="link request expired; start again from the Ring app")
        unclaimed = s.db.list_accounts(link_status="unclaimed")
        try:
            account_id = match_nonce(s.settings.ring_hmac_key, body.nonce, body.time, [a["account_id"] for a in unclaimed])
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="nonce did not match a pending link")
        masked = _mask_email(body.email)
        client = s.ring.client_for(account_id)
        await asyncio.to_thread(client.confirm_account_link, body.nonce, masked)
        await asyncio.to_thread(client.update_integration, "completed", masked)
        s.db.upsert_account(account_id, email=body.email, link_status="completed")
        await asyncio.to_thread(s.ring.discover, account_id)
        return {"status": "completed", "account_id": account_id}

    # ------------------------------------------------------------- account

    @app.get("/api/account")
    async def get_account(s: AppState = Depends(st)):
        aid = s.current_account_id()
        if not aid:
            return {"linked": False}
        acct = s.db.get_account(aid) or {}
        return {"linked": acct.get("link_status") == "completed", "account_id": aid, "email": acct.get("email"),
                "link_status": acct.get("link_status"), "mode": s.settings.mode}

    @app.delete("/api/account")
    async def delete_account(s: AppState = Depends(st)):
        """Content policy: an easy, complete deletion, including derived data and blobs."""
        aid = s.current_account_id()
        if not aid:
            raise HTTPException(status_code=404, detail="no linked account")
        inc_ids = [i["id"] for i in s.db.list_incidents(account_id=aid)]
        for iid in inc_ids:
            t = s.manager._tasks.pop(iid, None)
            if t:
                t.cancel()
        blobs = sum(s.blobs.delete_prefix(f"incidents/{iid}") for iid in inc_ids)
        counts = s.db.delete_account(aid)
        counts["blobs"] = blobs
        if s.settings.is_mock:
            s._seed_mock()
        return {"deleted": True, "counts": counts, "confirmed_at": now_ms()}

    # ------------------------------------------------------------- devices and routes

    @app.get("/api/devices")
    async def list_devices(s: AppState = Depends(st)):
        aid = s.current_account_id()
        rows = s.db.list_devices(account_id=aid) if aid else []
        for r in rows:
            r["last_status"] = _loads(r.get("last_status"))
        return rows

    @app.post("/api/devices/discover")
    async def discover(s: AppState = Depends(st)):
        aid = s.current_account_id()
        if not aid:
            raise HTTPException(status_code=404, detail="no linked account")
        rows = await asyncio.to_thread(s.ring.discover, aid)
        return rows

    @app.patch("/api/devices/{device_id}")
    async def patch_device(device_id: str, body: DevicePatch, s: AppState = Depends(st)):
        if not s.db.get_device(device_id):
            raise HTTPException(status_code=404, detail="unknown device")
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        # Allow clearing with an empty string.
        for k in ("route_id", "covered_by"):
            if fields.get(k) == "":
                s.db.execute(f"UPDATE devices SET {k}=NULL WHERE device_id=?", (device_id,))
                fields.pop(k)
        s.db.upsert_device(device_id, **fields)
        return s.db.get_device(device_id)

    @app.get("/api/routes")
    async def list_routes(s: AppState = Depends(st)):
        return s.db.list_routes()

    @app.put("/api/routes")
    async def put_route(body: RouteBody, s: AppState = Depends(st)):
        s.db.upsert_route(body.id, body.name, body.description)
        return s.db.list_routes()

    @app.delete("/api/routes/{route_id}")
    async def delete_route(route_id: str, s: AppState = Depends(st)):
        s.db.delete_route(route_id)
        return s.db.list_routes()

    # ------------------------------------------------------------- incidents

    @app.get("/api/incidents")
    async def list_incidents(s: AppState = Depends(st)):
        aid = s.current_account_id()
        rows = s.db.list_incidents(account_id=aid) if aid else []
        out = []
        for r in rows:
            frames = s.db.frames_for_incident(r["id"])
            pack = s.db.latest_pack(r["id"])
            out.append({**r, "notes": _loads(r.get("notes")), "chime_status": _loads(r.get("chime_status")),
                        "frame_count": len(frames), "first_frame_id": frames[0]["id"] if frames else None,
                        "pack": pack})
        return out

    @app.get("/api/incidents/{incident_id}")
    async def get_incident(incident_id: str, s: AppState = Depends(st)):
        try:
            pack = await asyncio.to_thread(s.packs.collect, incident_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown incident")
        pack["latest_pack"] = s.db.latest_pack(incident_id)
        return JSONResponse(json.loads(json.dumps(pack, default=str)))

    @app.post("/api/incidents/{incident_id}/pack")
    async def rebuild_pack(incident_id: str, s: AppState = Depends(st)):
        if not s.db.get_incident(incident_id):
            raise HTTPException(status_code=404, detail="unknown incident")
        pack = await asyncio.to_thread(s.packs.build, incident_id)
        return {"built": True, "questions_answered": pack["claims"]["answered"], "questions_total": pack["claims"]["total"]}

    @app.get("/api/incidents/{incident_id}/pack.html", response_class=HTMLResponse)
    async def pack_html(incident_id: str, s: AppState = Depends(st)):
        row = s.db.latest_pack(incident_id)
        if row:
            return HTMLResponse(s.blobs.get(row["html_path"]).decode("utf-8"))
        try:
            pack = await asyncio.to_thread(s.packs.collect, incident_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown incident")
        return HTMLResponse(s.packs.render_html(pack))

    @app.get("/api/incidents/{incident_id}/pack.json")
    async def pack_json(incident_id: str, s: AppState = Depends(st)):
        row = s.db.latest_pack(incident_id)
        if not row:
            raise HTTPException(status_code=404, detail="no pack built yet")
        return Response(s.blobs.get(row["json_path"]), media_type="application/json")

    @app.get("/api/incidents/{incident_id}/pack.pdf")
    async def pack_pdf(incident_id: str, s: AppState = Depends(st)):
        row = s.db.latest_pack(incident_id)
        if not row or not row.get("pdf_path"):
            raise HTTPException(status_code=404, detail="no PDF for this pack (Playwright not installed?)")
        return Response(s.blobs.get(row["pdf_path"]), media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{incident_id}.pdf"'})

    @app.post("/api/incidents/{incident_id}/close")
    async def close_incident(incident_id: str, s: AppState = Depends(st)):
        """Manual close, for the case where the sensor dried but no `flood_cleared`
        arrived and reconcile has not run yet. Recorded as `manual`."""
        if not s.db.get_incident(incident_id):
            raise HTTPException(status_code=404, detail="unknown incident")
        await s.manager.close_incident(incident_id, now_ms(), "manual")
        return s.db.get_incident(incident_id)

    @app.get("/api/frames/{frame_id}.jpg")
    async def frame_image(frame_id: int, s: AppState = Depends(st)):
        f = s.db.get_frame(frame_id)
        if not f:
            raise HTTPException(status_code=404, detail="unknown frame")
        return Response(s.blobs.get(f["path"]), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=3600"})

    # ------------------------------------------------------------- rover

    def rover_auth(x_rover_token: str | None = Header(default=None, alias="X-Rover-Token")):
        if x_rover_token != settings.rover_token:
            raise HTTPException(status_code=401, detail="bad rover token")

    @app.get("/rover/commands", dependencies=[Depends(rover_auth)])
    async def rover_commands(rover_id: str = "rover-1", wait: float = 25.0, s: AppState = Depends(st)):
        cmd = await s.manager.dispatcher.next_command(rover_id, min(wait, 55.0))
        return {"command": cmd.to_json() if cmd else None}

    @app.post("/rover/report", dependencies=[Depends(rover_auth)])
    async def rover_report(body: RoverReport, s: AppState = Depends(st)):
        if not s.db.get_incident(body.incident_id):
            raise HTTPException(status_code=404, detail="unknown incident")
        await s.manager.rover_report(body.incident_id, body.kind, body.message, body.data)
        return {"ok": True}

    # ------------------------------------------------------------- dev tools

    if settings.dev_tools:
        @app.post("/api/test/trigger")
        async def test_trigger(body: Trigger, s: AppState = Depends(st)):
            """Synthesises a sensor event through the same handler real webhooks use,
            marked `synthetic`. In mock mode it also flips the mock sensor's state so
            reconciliation agrees with the event."""
            aid = s.current_account_id()
            device_id = body.device_id or MockRing.SENSOR
            if s.settings.is_mock:
                MockRing.instance(s.settings).set_faulted(device_id, body.action == "detected")
            env = make_event(f"{body.kind}_{body.action}", device_id, account_id=aid or "unknown")
            env["meta"]["controlled_test"] = body.controlled_test
            result = await s.manager.handle_event(parse_event(env), source="synthetic")
            return result

        @app.post("/api/test/reconcile")
        async def test_reconcile(s: AppState = Depends(st)):
            return await s.manager.reconcile()

        @app.post("/api/test/camera-online")
        async def test_camera(online: bool = True, device_id: str = MockRing.CAM, s: AppState = Depends(st)):
            if s.settings.is_mock:
                MockRing.instance(s.settings).set_online(device_id, online)
            env = make_event("device_online" if online else "device_offline", device_id,
                             account_id=s.current_account_id() or "unknown")
            return await s.manager.handle_event(parse_event(env), source="synthetic")

    return app


async def _reconcile_loop(state: AppState) -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await state.manager.reconcile()
        except Exception as e:  # noqa: BLE001
            log.warning("reconcile loop: %s", e)
        await asyncio.sleep(state.settings.reconcile_interval_s)


async def _refresh_loop(state: AppState) -> None:
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            await asyncio.to_thread(state.ring.refresh_all)
        except Exception as e:  # noqa: BLE001
            log.warning("refresh loop: %s", e)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email[:1] + "***"
    user, dom = email.split("@", 1)
    return (user[:1] + "***" + user[-1:] if len(user) > 2 else user[:1] + "***") + "@" + dom


def _loads(v):
    if v is None or not isinstance(v, str):
        return v
    try:
        return json.loads(v)
    except Exception:  # noqa: BLE001
        return v
