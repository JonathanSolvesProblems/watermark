"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, fmtDate, fmtDuration, type Account, type Device, type Incident } from "@/lib/api";

export default function Dashboard() {
  const [acct, setAcct] = useState<Account | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [a, d, i] = await Promise.all([api.account(), api.devices(), api.incidents()]);
      setAcct(a);
      setDevices(d);
      setIncidents(i);
      setErr(null);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  const open = incidents.filter((i) => i.status === "open");
  const sensors = devices.filter((d) => d.kind === "flood_freeze" || d.kind === "contact" || d.kind === "temperature_humidity");
  const cameras = devices.filter((d) => d.kind === "camera");
  const chimes = devices.filter((d) => d.kind === "chime");
  const unrouted = sensors.filter((s) => s.kind === "flood_freeze" && !s.route_id && !s.covered_by);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    try {
      await fn();
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid gap-10">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="label text-water">Dashboard</p>
          <h1 className="text-3xl font-bold mt-1">{open.length ? `${open.length} open incident${open.length > 1 ? "s" : ""}` : "Dry"}</h1>
          <p className="text-sm text-muted font-sans mt-1">
            {acct?.email}{acct?.mode === "mock" ? " · mock mode: no real Ring devices" : ""}
          </p>
        </div>
        {acct?.mode === "mock" && (
          <div className="flex gap-2">
            <button className="btn-ghost" disabled={!!busy} onClick={() => run("wet", () => api.trigger("detected"))}>
              {busy === "wet" ? "…" : "Simulate: sensor wet"}
            </button>
            <button className="btn-ghost" disabled={!!busy} onClick={() => run("dry", () => api.trigger("cleared"))}>
              {busy === "dry" ? "…" : "Simulate: sensor dry"}
            </button>
          </div>
        )}
      </section>
      {err && <p className="text-warn text-sm font-sans">{err}</p>}

      {unrouted.length > 0 && (
        <div className="border border-warn bg-paper p-4 font-sans text-sm">
          <span className="label text-warn">Setup needed</span>
          <p className="mt-1">
            {unrouted.map((s) => s.name).join(", ")} {unrouted.length > 1 ? "have" : "has"} no camera and no rover route.
            If water reaches {unrouted.length > 1 ? "them" : "it"}, the pack will be sensor-only.{" "}
            <Link href="/setup" className="underline">Fix in Setup</Link>.
          </p>
        </div>
      )}

      <section>
        <div className="waterline pb-2 mb-4 flex items-baseline justify-between">
          <h2 className="text-xl font-bold">Incidents</h2>
          <span className="text-xs text-muted font-sans">{incidents.length} total</span>
        </div>
        {incidents.length === 0 ? (
          <p className="text-muted text-sm font-sans">Nothing yet. The first `flood_detected` webhook creates one.</p>
        ) : (
          <ul className="grid gap-3">
            {incidents.map((i) => (
              <li key={i.id} className={`border ${i.status === "open" ? "border-water" : "border-line"} bg-paper`}>
                <Link href={`/incident?id=${i.id}`} className="grid sm:grid-cols-[120px_1fr_auto] gap-4 p-4 items-center">
                  <div className="aspect-video bg-ground overflow-hidden">
                    {i.first_frame_id ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={api.frameUrl(i.first_frame_id)} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full grid place-items-center text-[10px] text-muted font-sans">no frame</div>
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`label ${i.status === "open" ? "text-water" : "text-muted"}`}>{i.status}</span>
                      {i.notes?.controlled_test && <span className="label text-warn">controlled test</span>}
                    </div>
                    <div className="text-lg font-bold">{i.kind === "flood" ? "Water" : "Freeze"} in {i.room}</div>
                    <div className="text-sm text-muted font-sans">
                      {fmtDate(i.opened_at_ms)} · {fmtDuration(i.opened_at_ms, i.closed_at_ms)} · {i.frame_count} frames ·{" "}
                      {i.camera_role === "rover" ? "rover camera" : i.camera_role === "fixed" ? "fixed camera" : "no camera"}
                    </div>
                  </div>
                  <div className="text-right font-sans text-sm">
                    {i.pack ? (
                      <span className="text-ok">{i.pack.questions_answered}/{i.pack.questions_total} questions</span>
                    ) : (
                      <span className="text-muted">pack pending</span>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid md:grid-cols-3 gap-6">
        <DeviceGroup title="Sensors" devices={sensors} />
        <DeviceGroup title="Cameras" devices={cameras} />
        <DeviceGroup title="Chimes" devices={chimes} />
      </section>
    </div>
  );
}

function DeviceGroup({ title, devices }: { title: string; devices: Device[] }) {
  return (
    <div>
      <div className="waterline pb-2 mb-3"><h2 className="text-lg font-bold">{title}</h2></div>
      <ul className="divide-y divide-line">
        {devices.map((d) => (
          <li key={d.device_id} className="py-2 flex justify-between items-center font-sans text-sm">
            <div>
              <div>{d.name}</div>
              <div className="text-xs text-muted">{d.room || "no room"}{d.route_id ? ` · ${d.route_id}` : ""}</div>
            </div>
            <span className={`label ${d.online ? "text-ok" : "text-warn"}`}>{d.online ? "online" : "offline"}</span>
          </li>
        ))}
        {devices.length === 0 && <li className="py-2 text-muted text-sm font-sans">none</li>}
      </ul>
    </div>
  );
}
