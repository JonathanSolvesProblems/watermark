"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Device, type Route } from "@/lib/api";

// Where each sensor is, and what reaches it: a camera that already sees the
// room, or a rover route. Device settings themselves (motion zones, names) stay
// in the Ring app, as the Ring UX guide requires.
export default function Setup() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [newRoute, setNewRoute] = useState<Route>({ id: "", name: "", description: "" });

  const load = useCallback(async () => {
    try {
      const [d, r] = await Promise.all([api.devices(), api.routes()]);
      setDevices(d);
      setRoutes(r);
      setErr(null);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function patch(id: string, body: Partial<Pick<Device, "room" | "route_id" | "covered_by">>) {
    setSaving(id);
    try {
      await api.patchDevice(id, body);
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(null);
    }
  }

  const sensors = devices.filter((d) => ["flood_freeze", "contact", "temperature_humidity", "air_quality"].includes(d.kind));
  const cameras = devices.filter((d) => d.kind === "camera");
  const fixedCams = cameras.filter((c) => (c.room || "").toLowerCase() !== "rover");

  return (
    <div className="grid gap-12">
      <section>
        <p className="label">Setup</p>
        <h1 className="readout uppercase text-[48px] sm:text-[64px] mt-2">Rooms and cameras</h1>
        <p className="mt-3 text-stencil max-w-2xl">
          Ring does not tell Watermark which room a sensor is in, so you do it once here. Device names and motion zones
          are changed in the Ring app; after changing them,{" "}
          <button className="underline text-ink" onClick={() => api.discover().then(load).catch((e) => setErr(String(e)))}>
            fetch the device list again
          </button>
          .
        </p>
        {err && <p className="plate hatch px-3 py-2 mt-3" role="alert">{err}</p>}
      </section>

      <section aria-labelledby="sensors-h">
        <h2 id="sensors-h" className="label border-b border-seam pb-2 mb-4">Sensors</h2>
        {sensors.length === 0 && <p className="text-stencil">No sensors shared with Watermark yet. Share one from the Ring app.</p>}
        <ul className="grid gap-4">
          {sensors.map((s) => (
            <li key={s.device_id} className="plate p-4 grid gap-4 md:grid-cols-[1fr_1fr_1fr_1fr] md:items-end">
              <div>
                <p className="font-display text-[22px] font-bold uppercase leading-tight">{s.name}</p>
                <p className="text-[13px] text-stencil">{s.kind === "flood_freeze" ? "Flood & Freeze" : s.kind.replace("_", " ")}</p>
              </div>
              <Field label="Room">
                <input
                  className="field"
                  defaultValue={s.room || ""}
                  placeholder="Water heater closet"
                  onBlur={(e) => e.target.value !== (s.room || "") && patch(s.device_id, { room: e.target.value })}
                />
              </Field>
              <Field label="Camera that already sees it">
                <select className="field" value={s.covered_by || ""} onChange={(e) => patch(s.device_id, { covered_by: e.target.value })}>
                  <option value="">None, send the rover</option>
                  {fixedCams.map((c) => (
                    <option key={c.device_id} value={c.device_id}>{c.name}</option>
                  ))}
                </select>
              </Field>
              <Field label={saving === s.device_id ? "Rover route · saving…" : "Rover route"}>
                <select className="field" value={s.route_id || ""} onChange={(e) => patch(s.device_id, { route_id: e.target.value })}>
                  <option value="">None</option>
                  {routes.map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </Field>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="cams-h">
        <h2 id="cams-h" className="label border-b border-seam pb-2 mb-2">Cameras</h2>
        <p className="text-[14px] text-stencil mb-3">Set the room to &ldquo;rover&rdquo; for the camera that rides on the rover.</p>
        <ul>
          {cameras.map((c) => (
            <li key={c.device_id} className="py-3 border-b border-seam grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-center">
              <span>{c.name}</span>
              <input
                className="field"
                aria-label={`Room for ${c.name}`}
                defaultValue={c.room || ""}
                placeholder="Basement, or rover"
                onBlur={(e) => e.target.value !== (c.room || "") && patch(c.device_id, { room: e.target.value })}
              />
              <span className="flex items-center gap-2">
                <span className="spot" data-off={!c.online} aria-hidden="true" />
                <span className="label">{c.online ? "Online" : "Offline"}</span>
              </span>
            </li>
          ))}
          {cameras.length === 0 && <li className="py-3 text-stencil">No cameras shared with Watermark yet.</li>}
        </ul>
      </section>

      <section aria-labelledby="routes-h">
        <h2 id="routes-h" className="label border-b border-seam pb-2 mb-2">Rover routes</h2>
        <p className="text-[14px] text-stencil mb-3">A route is a tape line from the dock to a room. Its id must match the rover&apos;s routes.yaml.</p>
        <ul className="mb-4">
          {routes.map((r) => (
            <li key={r.id} className="py-3 border-b border-seam flex items-start justify-between gap-4">
              <div>
                <span className="font-display font-bold uppercase tracking-wide">{r.name}</span>
                <span className="text-stencil text-[13px]"> · {r.id}</span>
                <p className="text-[14px] text-stencil">{r.description}</p>
              </div>
              <button className="btn-ghost" onClick={() => api.deleteRoute(r.id).then(setRoutes)}>Remove</button>
            </li>
          ))}
        </ul>
        <form
          className="grid gap-2 sm:grid-cols-[1fr_1fr_2fr_auto]"
          onSubmit={async (e) => {
            e.preventDefault();
            setRoutes(await api.putRoute(newRoute));
            setNewRoute({ id: "", name: "", description: "" });
          }}
        >
          <input className="field" aria-label="Route id" placeholder="route-id" required value={newRoute.id} onChange={(e) => setNewRoute({ ...newRoute, id: e.target.value })} />
          <input className="field" aria-label="Route name" placeholder="Name" required value={newRoute.name} onChange={(e) => setNewRoute({ ...newRoute, name: e.target.value })} />
          <input className="field" aria-label="Where the tape goes" placeholder="Where the tape goes" value={newRoute.description} onChange={(e) => setNewRoute({ ...newRoute, description: e.target.value })} />
          <button className="btn">Add route</button>
        </form>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1">
      <span className="label">{label}</span>
      {children}
    </label>
  );
}
