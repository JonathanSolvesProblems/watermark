"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, fmtDate, fmtDuration, type Account, type Device, type Incident } from "@/lib/api";

const SENSOR_KINDS = ["flood_freeze", "contact", "temperature_humidity", "air_quality"];

export default function Dashboard() {
  const [acct, setAcct] = useState<Account | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tourOpen, setTourOpen] = useState(false);

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
    try {
      setTourOpen(localStorage.getItem("wm-tour-done") !== "1");
    } catch {}
    return () => clearInterval(t);
  }, [load]);

  const open = incidents.filter((i) => i.status === "open");
  const sensors = devices.filter((d) => SENSOR_KINDS.includes(d.kind));
  const cameras = devices.filter((d) => d.kind === "camera");
  const chimes = devices.filter((d) => d.kind === "chime");
  const unrouted = sensors.filter((s) => s.kind === "flood_freeze" && !s.route_id && !s.covered_by);
  const canSimulate = acct?.mode === "mock" || acct?.mode === "playground";

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

  function closeTour() {
    setTourOpen(false);
    try {
      localStorage.setItem("wm-tour-done", "1");
    } catch {}
  }

  return (
    <div className="grid gap-12">
      <section className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-3">
            <span className="spot" data-wet={open.length > 0} aria-hidden="true" />
            <p className="label">{open.length ? "Water standing" : "All sensors dry"}</p>
          </div>
          <h1 className="readout uppercase text-[56px] sm:text-[80px] mt-2">
            {open.length ? `${open.length} open incident${open.length > 1 ? "s" : ""}` : "Dry"}
          </h1>
          <p className="mt-2 text-stencil">{modeLine(acct)}</p>
        </div>
        {canSimulate && (
          <div className="flex flex-wrap gap-2">
            <button className="btn" disabled={!!busy} onClick={() => run("wet", () => api.trigger("detected"))}>
              {busy === "wet" ? "Sending…" : "Simulate sensor wet"}
            </button>
            <button className="btn-ghost" disabled={!!busy} onClick={() => run("dry", () => api.trigger("cleared"))}>
              {busy === "dry" ? "Sending…" : "Simulate sensor dry"}
            </button>
          </div>
        )}
      </section>

      {acct?.mode === "playground" && (
        <p className="plate hatch px-4 py-3 text-[15px]">
          <span className="label text-ink mr-2">Playground</span>
          The camera is Ring&apos;s Developer Playground doorbell, reached through the real Ring API. Ring offers no
          sensors there, so the flood sensor is simulated, and every pack says so.
        </p>
      )}

      {err && (
        <p className="plate px-4 py-3">
          <span className="label mr-2">Server not answering</span>
          {err.includes("Failed to fetch") ? "Start Watermark's server, then this page reconnects by itself." : err}
        </p>
      )}

      {tourOpen && <Tour onClose={closeTour} />}

      {unrouted.length > 0 && (
        <section className="plate hatch p-4">
          <p className="label text-ink">Setup needed</p>
          <p className="mt-1">
            <strong>{unrouted.map((s) => s.name).join(", ")}</strong> {unrouted.length > 1 ? "have" : "has"} no camera and no
            rover route. If water reaches {unrouted.length > 1 ? "them" : "it"}, the pack will have the sensor&apos;s times
            but no pictures. <Link href="/setup" className="underline">Choose a camera in Setup</Link>.
          </p>
        </section>
      )}

      <section aria-labelledby="stations-h">
        <h2 id="stations-h" className="label border-b border-seam pb-2 mb-4">Sensors</h2>
        {sensors.length === 0 ? (
          <Empty title="No sensors shared yet" body="Share a Flood & Freeze sensor with Watermark from the Ring app, then come back. Watermark only sees the devices you choose." />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sensors.map((s) => {
              const wet = open.some((i) => i.sensor_device_id === s.device_id);
              const cam = cameras.find((c) => c.device_id === s.covered_by);
              return (
                <li key={s.device_id} className="plate p-4 grid gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-display text-[22px] font-bold uppercase leading-tight">{s.name}</p>
                      <p className="text-stencil text-[14px]">{s.room || "Room not set"}</p>
                    </div>
                    <span className="spot mt-1" data-wet={wet} data-off={!s.online} aria-hidden="true" />
                  </div>
                  <div className="staff h-4" aria-hidden="true">
                    {wet && <div className="staff-fill absolute inset-0" data-rise="true" />}
                  </div>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[14px]">
                    <dt className="text-stencil">State</dt>
                    <dd>{!s.online ? "Offline" : wet ? "Wet" : "Dry"}</dd>
                    <dt className="text-stencil">Camera</dt>
                    <dd>{cam ? cam.name : s.route_id ? "Rover, by route" : "None"}</dd>
                  </dl>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="incidents-h">
        <div className="flex items-baseline justify-between border-b border-seam pb-2 mb-4">
          <h2 id="incidents-h" className="label">Incidents</h2>
          <span className="text-[13px] text-stencil">{incidents.length} total</span>
        </div>
        {incidents.length === 0 ? (
          <Empty title="Nothing recorded" body="The first time a sensor reports water, an incident opens here and the camera starts recording." />
        ) : (
          <ul className="grid gap-3">
            {incidents.map((i) => (
              <li key={i.id} className="plate plate-in">
                <Link href={`/incident?id=${i.id}`} className="grid grid-cols-[96px_1fr] sm:grid-cols-[160px_1fr_auto] gap-4 p-3 items-center">
                  <div className="aspect-video bg-concrete overflow-hidden relative">
                    {i.first_frame_id ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={api.frameUrl(i.first_frame_id)} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full hatch" aria-hidden="true" />
                    )}
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="spot" data-wet={i.status === "open"} aria-hidden="true" />
                      <span className="label">{i.status === "open" ? "Open" : "Closed"}</span>
                      {i.notes?.controlled_test && <span className="label">· Controlled test</span>}
                    </div>
                    <p className="font-display text-[24px] font-bold uppercase leading-tight mt-1">
                      {i.kind === "flood" ? "Water" : "Freeze"} in {i.room}
                    </p>
                    <p className="text-[14px] text-stencil">
                      {fmtDate(i.opened_at_ms)} · stood {fmtDuration(i.opened_at_ms, i.closed_at_ms)} · {i.frame_count} frames
                    </p>
                  </div>
                  <div className="col-span-2 sm:col-span-1 sm:text-right">
                    {i.pack ? (
                      <>
                        <span className="readout text-[32px]">{i.pack.questions_answered}/{i.pack.questions_total}</span>
                        <span className="block text-[13px] text-stencil">claim questions</span>
                      </>
                    ) : (
                      <span className="label">Pack when dry</span>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-8 md:grid-cols-2">
        <DeviceList title="Cameras" devices={cameras} empty="No camera shared. Without one, packs have times but no pictures." />
        <DeviceList title="Chimes" devices={chimes} empty="No chime shared. Watermark will still record; it just cannot sound the alarm in the house." />
      </section>
    </div>
  );
}

function modeLine(acct: Account | null): string {
  if (!acct) return "Connecting…";
  if (acct.mode === "mock") return "Mock mode: a stand-in Ring account, no real devices.";
  if (acct.mode === "playground") return "Ring Developer Playground.";
  return acct.email || "";
}

function Tour({ onClose }: { onClose: () => void }) {
  return (
    <section className="plate p-5 grid gap-4" aria-labelledby="tour-h">
      <div className="flex items-start justify-between gap-4">
        <h2 id="tour-h" className="font-display text-[26px] font-bold uppercase leading-none">How Watermark works</h2>
        <button className="btn-ghost" onClick={onClose}>Skip</button>
      </div>
      <ol className="grid gap-4 md:grid-cols-3 text-[15px]">
        <li><span className="label block">1 · Tell it the room</span>In Setup, say which room each sensor is in and which camera sees it.</li>
        <li><span className="label block">2 · Leave it</span>When a sensor reports water, the chime sounds and the camera records until the sensor is dry.</li>
        <li><span className="label block">3 · Hand over the pack</span>Each incident becomes one evidence pack for your insurer, gaps included.</li>
      </ol>
      <p className="text-[14px] text-stencil">
        Motion zones, device names and Smart Alerts are set in the Ring app, not here.
      </p>
    </section>
  );
}

function DeviceList({ title, devices, empty }: { title: string; devices: Device[]; empty: string }) {
  return (
    <div>
      <h2 className="label border-b border-seam pb-2 mb-2">{title}</h2>
      {devices.length === 0 ? (
        <p className="text-stencil text-[15px]">{empty}</p>
      ) : (
        <ul>
          {devices.map((d) => (
            <li key={d.device_id} className="py-2 border-b border-seam flex items-center justify-between gap-4">
              <div>
                <p>{d.name}</p>
                <p className="text-[13px] text-stencil">{d.room || "Room not set"}</p>
              </div>
              <span className="flex items-center gap-2">
                <span className="spot" data-off={!d.online} aria-hidden="true" />
                <span className="label">{d.online ? "Online" : "Offline"}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="plate hatch p-6">
      <p className="font-display text-[22px] font-bold uppercase">{title}</p>
      <p className="mt-1 text-stencil max-w-2xl">{body}</p>
    </div>
  );
}
