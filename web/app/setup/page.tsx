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

  useEffect(() => { load(); }, [load]);

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

  return (
    <div className="grid gap-10">
      <section>
        <p className="label text-water">Setup</p>
        <h1 className="text-3xl font-bold mt-1">Rooms, cameras, routes</h1>
        <p className="text-sm text-muted font-sans mt-1">
          Ring does not tell Watermark which room a sensor is in. You do, once. Names and zones are edited in the Ring app;{" "}
          <button className="underline" onClick={() => api.discover().then(load).catch((e) => setErr(String(e)))}>re-discover devices</button> after changing them.
        </p>
        {err && <p className="text-warn text-sm font-sans mt-2">{err}</p>}
      </section>

      <section>
        <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Sensors</h2></div>
        <table className="log">
          <thead><tr><th>Sensor</th><th>Room</th><th>Camera that sees this room</th><th>Rover route</th><th></th></tr></thead>
          <tbody>
            {sensors.map((s) => (
              <tr key={s.device_id}>
                <td className="font-sans">{s.name}<div className="text-xs text-muted">{s.kind.replace("_", "/")}</div></td>
                <td><input className="field" defaultValue={s.room || ""} placeholder="Water heater closet" onBlur={(e) => e.target.value !== (s.room || "") && patch(s.device_id, { room: e.target.value })} /></td>
                <td>
                  <select className="field" value={s.covered_by || ""} onChange={(e) => patch(s.device_id, { covered_by: e.target.value })}>
                    <option value="">none (use the rover)</option>
                    {cameras.filter((c) => (c.room || "").toLowerCase() !== "rover").map((c) => <option key={c.device_id} value={c.device_id}>{c.name}</option>)}
                  </select>
                </td>
                <td>
                  <select className="field" value={s.route_id || ""} onChange={(e) => patch(s.device_id, { route_id: e.target.value })}>
                    <option value="">none</option>
                    {routes.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </td>
                <td className="text-xs text-muted font-sans">{saving === s.device_id ? "saving…" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Cameras</h2></div>
        <p className="text-xs text-muted font-sans mb-2">Set the room to <span className="font-mono">rover</span> for the camera mounted on the rover.</p>
        <table className="log">
          <thead><tr><th>Camera</th><th>Room</th><th>Status</th></tr></thead>
          <tbody>
            {cameras.map((c) => (
              <tr key={c.device_id}>
                <td className="font-sans">{c.name}</td>
                <td><input className="field" defaultValue={c.room || ""} placeholder="Basement, or rover" onBlur={(e) => e.target.value !== (c.room || "") && patch(c.device_id, { room: e.target.value })} /></td>
                <td className={`label ${c.online ? "text-ok" : "text-warn"}`}>{c.online ? "online" : "offline"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Rover routes</h2></div>
        <p className="text-xs text-muted font-sans mb-3">A route is a tape line from the dock to a room. Its id must match an entry in the rover&rsquo;s <span className="font-mono">routes.yaml</span>.</p>
        <ul className="divide-y divide-line mb-4">
          {routes.map((r) => (
            <li key={r.id} className="py-2 flex justify-between items-start font-sans text-sm">
              <div><span className="font-mono text-xs text-muted">{r.id}</span> · {r.name}<div className="text-xs text-muted">{r.description}</div></div>
              <button className="text-warn text-xs" onClick={() => api.deleteRoute(r.id).then(setRoutes)}>remove</button>
            </li>
          ))}
        </ul>
        <form className="grid sm:grid-cols-[1fr_1fr_2fr_auto] gap-2" onSubmit={async (e) => { e.preventDefault(); setRoutes(await api.putRoute(newRoute)); setNewRoute({ id: "", name: "", description: "" }); }}>
          <input className="field" placeholder="route-id" required value={newRoute.id} onChange={(e) => setNewRoute({ ...newRoute, id: e.target.value })} />
          <input className="field" placeholder="Name" required value={newRoute.name} onChange={(e) => setNewRoute({ ...newRoute, name: e.target.value })} />
          <input className="field" placeholder="Where the tape goes" value={newRoute.description} onChange={(e) => setNewRoute({ ...newRoute, description: e.target.value })} />
          <button className="btn">Add</button>
        </form>
      </section>
    </div>
  );
}
