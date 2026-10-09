"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import GaugeLink from "@/components/GaugeLink";
import Print from "@/components/Print";
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
      {/* Test controls exist only without a real sensor, so they sit in a quiet bar, not the hero. */}
      {canSimulate && (
        <div className="-mt-4 flex flex-wrap items-center gap-x-4 border-b border-dashed border-seam pb-2 text-[14px] text-stencil">
          <span>Test without water:</span>
          <button className="underline underline-offset-4 min-h-[44px] hover:text-ink disabled:opacity-55" disabled={!!busy} onClick={() => run("wet", () => api.trigger("detected"))}>
            {busy === "wet" ? "Sending…" : "Simulate sensor wet"}
          </button>
          <button className="underline underline-offset-4 min-h-[44px] hover:text-ink disabled:opacity-55" disabled={!!busy} onClick={() => run("dry", () => api.trigger("cleared"))}>
            {busy === "dry" ? "Sending…" : "Simulate sensor dry"}
          </button>
        </div>
      )}
      <section>
        <h1 className="headline text-[42px] sm:text-[56px]">
          {open.length ? `${open.length} open incident${open.length > 1 ? "s" : ""}` : "Dry"}
        </h1>
        <p className="mt-2 text-stencil">{modeLine(acct)}</p>
      </section>

      {acct?.mode === "playground" && (
        <p className="plate border border-dashed border-stencil px-4 py-3 text-[15px]">
          <strong className="font-semibold mr-2">Playground.</strong>
          The camera is Ring&apos;s Developer Playground doorbell, reached through the real Ring API. Ring offers no
          sensors there, so the flood sensor is simulated, and every pack says so.
        </p>
      )}

      {err && (
        <p className="plate px-4 py-3">
          <strong className="font-semibold mr-2">Server not answering.</strong>
          {err.includes("Failed to fetch") ? "Start Watermark's server, then this page reconnects by itself." : err}
        </p>
      )}

      {tourOpen && <Tour onClose={closeTour} />}

      {unrouted.length > 0 && (
        <section className="plate p-4 border-l-[3px] border-l-line">
          <p className="title text-[20px]">Setup needed</p>
          <p className="mt-1">
            <strong>{unrouted.map((s) => s.name).join(", ")}</strong> {unrouted.length > 1 ? "have" : "has"} no camera and no
            rover route. If water reaches {unrouted.length > 1 ? "them" : "it"}, the pack will have the sensor&apos;s times
            but no pictures. <Link href="/setup" className="underline">Choose a camera in Setup</Link>.
          </p>
        </section>
      )}

      <section aria-labelledby="stations-h">
        <h2 id="stations-h" className="title border-b border-seam pb-2 mb-4">Sensors</h2>
        {sensors.length === 0 ? (
          <Empty print="setup" title="No sensors shared yet" body="Share a Flood & Freeze sensor with Watermark from the Ring app, then come back. Watermark only sees the devices you choose." />
        ) : (
          <ul>
            {/* One unboxed row per sensor: name, room, state, the camera that answers it. */}
            {sensors.map((s) => {
              const wet = open.some((i) => i.sensor_device_id === s.device_id);
              const cam = cameras.find((c) => c.device_id === s.covered_by);
              return (
                <li key={s.device_id} className="grid grid-cols-[16px_1fr_auto] sm:grid-cols-[16px_1.2fr_1fr_1fr] gap-x-4 gap-y-1 items-baseline py-3 border-b border-seam">
                  <span className="spot translate-y-[2px]" data-wet={wet} data-off={!s.online} aria-hidden="true" />
                  <span>
                    <span className="title text-[20px]">{s.name}</span>
                    <span className="block text-stencil text-[14px]">{s.room || "Room not set"}</span>
                  </span>
                  <span className={wet ? "font-semibold" : ""}>{!s.online ? "Offline" : wet ? "Wet now" : "Dry"}</span>
                  <span className="col-start-2 sm:col-start-auto text-stencil text-[14px]">
                    {cam ? `Watched by ${cam.name}` : s.route_id ? "The rover goes by route" : "No camera yet"}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="incidents-h">
        <div className="flex items-baseline justify-between border-b border-seam pb-2 mb-4">
          <h2 id="incidents-h" className="title">Incidents</h2>
          <span className="text-[13px] text-stencil">{incidents.length} total</span>
        </div>
        {incidents.length === 0 ? (
          <Empty print="empty" title="No marks yet. The sensor is dry" body="The first time a sensor reports water, a mark goes on this board and the camera starts recording." />
        ) : (
          <ol className="relative grid gap-4 pl-10">
            {/* The flood board (charter 10): a staff down the left, each incident a diamond at
                its place with a tag pointing at it, newest on top. */}
            <span className="absolute left-0 top-0 bottom-0 w-5" aria-hidden="true">
              <span className="staff block h-full">
                <span className="staff-col-ticks absolute inset-0" />
              </span>
            </span>
            {incidents.map((i) => (
              <li key={i.id} className="relative plate-in">
                <span
                  className={`absolute -left-[31px] top-7 w-3 h-3 rotate-45 ${i.status === "open" || i.frame_count ? "bg-line" : "bg-stencil"}`}
                  aria-hidden="true"
                />
                <span className="absolute -left-[22px] top-[33px] w-[22px] h-px bg-seam" aria-hidden="true" />
                <GaugeLink href={`/incident?id=${i.id}`} view={`staff-${i.id}`} className="plate grid grid-cols-[96px_1fr] sm:grid-cols-[160px_1fr_auto] gap-4 p-3 items-center hover:bg-raised transition-colors">
                  <div className="aspect-video bg-concrete overflow-hidden relative rounded-[2px]">
                    {i.first_frame_id ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={api.frameUrl(i.first_frame_id)} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full dots" aria-hidden="true" />
                    )}
                  </div>
                  <div>
                    <p className="title text-[22px]">{i.room}</p>
                    <p className="text-[14px] text-stencil mt-1">
                      {i.status === "open" ? "Water standing now" : `${i.kind === "flood" ? "Water" : "Freezing"} on ${fmtDate(i.opened_at_ms)}`} · stood {fmtDuration(i.opened_at_ms, i.closed_at_ms)} · {i.frame_count} frames
                      {i.notes?.controlled_test && " · Controlled test. Real device."}
                    </p>
                    {/* The incident's gauge in miniature; on click it grows into the incident page's staff. */}
                    <div className="staff h-2 mt-2 overflow-hidden" style={{ viewTransitionName: `staff-${i.id}` }} aria-hidden="true">
                      <div className="staff-fill absolute inset-y-0 left-0" style={{ width: i.status === "open" ? "88%" : "96%" }} />
                    </div>
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
                </GaugeLink>
              </li>
            ))}
          </ol>
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
    <section className="flex flex-wrap items-center gap-x-6 gap-y-3 border-y border-seam py-4" aria-label="How Watermark works">
      <ol className="flex flex-wrap gap-x-6 gap-y-1 text-[15px]">
        <li><strong className="font-semibold">1.</strong> Say which room each sensor is in, in <Link href="/setup" className="underline">Setup</Link>.</li>
        <li><strong className="font-semibold">2.</strong> Leave it. When water comes, the camera records until the sensor is dry.</li>
        <li><strong className="font-semibold">3.</strong> Send the pack to your insurer.</li>
      </ol>
      <button className="ml-auto text-[15px] underline underline-offset-4 min-h-[44px]" onClick={onClose}>Got it</button>
    </section>
  );
}

function DeviceList({ title, devices, empty }: { title: string; devices: Device[]; empty: string }) {
  return (
    <div>
      <h2 className="title border-b border-seam pb-2 mb-2">{title}</h2>
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

function Empty({ title, body, print }: { title: string; body: string; print: "empty" | "setup" }) {
  return (
    <div className="grid sm:grid-cols-[160px_1fr] gap-6 items-center">
      <Print name={print} width={160} className="w-[120px] sm:w-[160px]" decorative />
      <div>
        <p className="title text-[22px]">{title}</p>
        <p className="mt-1 text-stencil max-w-2xl">{body}</p>
      </div>
    </div>
  );
}
