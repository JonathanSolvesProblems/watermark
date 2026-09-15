"""Announce on the Ring Chime. This is the only write in the whole Partner API.

A chime cannot speak arbitrary text. The app owns up to two audio slots
(`ring-appstore-event-1` and `-2` on a Chime Pro) whose audio is provisioned
outside the device API. Watermark's slots are meant to hold two short recorded
phrases, "Water detected" and "Freeze detected". The room name goes in the push
notification, not the chime.
"""
from __future__ import annotations

from typing import Any

from .db import Database


def announce(client, db: Database, account_id: str, kind: str) -> list[dict[str, Any]]:
    """Play the matching slot on every online, un-snoozed chime the account has."""
    results = []
    for dev in db.list_devices(account_id=account_id, kind="chime"):
        try:
            st = client.status(dev["device_id"])
            if not st.online or st.snooze_active:
                results.append({"device_id": dev["device_id"], "status": "skipped",
                                "reason": "offline" if not st.online else "snoozed"})
                continue
            conf = client.configurations(dev["device_id"])
            slot = _pick_slot(conf.chime_slots, kind)
            if slot is None:
                results.append({"device_id": dev["device_id"], "status": "skipped", "reason": "no audio slot"})
                continue
            status = client.play_chime(dev["device_id"], slot.audio_ref)
            results.append({"device_id": dev["device_id"], "status": status, "slot": slot.event,
                            "audio": slot.audio_name})
        except Exception as e:  # noqa: BLE001
            results.append({"device_id": dev["device_id"], "status": "error", "reason": str(e)[:200]})
    return results


def _pick_slot(slots, kind: str):
    if not slots:
        return None
    enabled = [s for s in slots if not s.disabled]
    if not enabled:
        return None
    # Slot 1 is water, slot 2 is freeze by convention; fall back to whatever exists.
    want = "ring-appstore-event-1" if kind == "flood" else "ring-appstore-event-2"
    for s in enabled:
        if s.event == want:
            return s
    return enabled[0]
