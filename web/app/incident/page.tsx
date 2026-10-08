"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import Staff from "@/components/Staff";
import { api, fmtDate, fmtTime, type IncidentDetail } from "@/lib/api";

function IncidentInner() {
  const id = useSearchParams().get("id") || "";
  const [d, setD] = useState<IncidentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setD(await api.incident(id));
      setErr(null);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, [id]);

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  if (err && !d)
    return (
      <div className="plate p-6 max-w-xl">
        <p className="label">Could not load this incident</p>
        <p className="mt-2">{plainError(err)}</p>
        <Link href="/dashboard" className="btn-ghost mt-4">Back to dashboard</Link>
      </div>
    );
  if (!d) return <Skeleton />;

  const inc = d.incident;
  const st = d.integrity.stats;
  const open = inc.status === "open";
  const controlled = !!d.notes?.controlled_test;
  const end = inc.closed_at_ms ?? Date.now();
  const firstFrame = d.frames.length ? Math.min(...d.frames.map((f) => f.media_ms)) : null;
  const marks = [
    { ms: inc.opened_at_ms, label: `${d.sensor?.name ?? "Sensor"} went wet` },
    ...(firstFrame ? [{ ms: firstFrame, label: "First frame from the Ring camera" }] : []),
    ...(inc.rover_on_station_at_ms ? [{ ms: inc.rover_on_station_at_ms, label: "Rover on station" }] : []),
    ...(inc.closed_at_ms ? [{ ms: inc.closed_at_ms, label: inc.closed_source === "manual" ? "Closed by hand" : "Sensor dry" }] : []),
  ];
  const cam = inc.camera_role === "rover" ? "Rover camera" : inc.camera_role === "fixed" ? "Fixed camera" : "No camera";

  return (
    <div className="grid gap-12">
      <section className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="spot" data-wet={open} aria-hidden="true" />
            <span className="label">{open ? "Water standing" : "Dry"} · {fmtDate(inc.opened_at_ms)}</span>
          </div>
          <h1 className="readout uppercase text-[44px] sm:text-[64px] mt-3">
            {inc.kind === "flood" ? "Water" : "Freeze"} in {inc.room}
          </h1>
          <p className="mt-3 text-stencil">
            {cam}
            {d.camera ? ` · ${d.camera.name}` : ""} · {open ? "recording until the sensor reads dry" : `closed ${fmtTime(inc.closed_at_ms)}`}
          </p>
          <div className="flex flex-wrap gap-2 mt-4">
            {controlled && <span className="label plate px-3 py-2 text-ink">Controlled test. Real device.</span>}
            <span className={`label plate px-3 py-2 ${d.integrity.verdict === "complete" ? "text-ink" : "hatch text-ink"}`}>
              Evidence {d.integrity.verdict}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <a className="btn" href={api.packHtmlUrl(inc.id)} target="_blank" rel="noreferrer">Open evidence pack</a>
          {d.latest_pack?.pdf_path && <a className="btn-ghost" href={api.packPdfUrl(inc.id)} target="_blank" rel="noreferrer">PDF</a>}
          <a className="btn-ghost" href={api.packJsonUrl(inc.id)} target="_blank" rel="noreferrer">JSON</a>
          {open ? (
            <button className="btn-danger" disabled={busy} onClick={async () => { setBusy(true); await api.closeIncident(inc.id).catch(() => {}); setBusy(false); load(); }}>
              Close by hand
            </button>
          ) : (
            <button className="btn-ghost" disabled={busy} onClick={async () => { setBusy(true); await api.rebuildPack(inc.id).catch(() => {}); setBusy(false); load(); }}>
              Rebuild pack
            </button>
          )}
        </div>
      </section>

      <section aria-labelledby="gauge-h">
        <div className="flex flex-wrap items-end justify-between gap-6 mb-5">
          <div>
            <h2 id="gauge-h" className="label">Sensor to first frame</h2>
            <p className="readout text-[88px] sm:text-[120px] mt-1">
              {st.sensor_to_first_frame_s ?? "–"}
              <span className="text-[40px] sm:text-[48px] text-stencil ml-1">s</span>
            </p>
          </div>
          <dl className="flex flex-wrap gap-x-10 gap-y-4">
            <Reading n={st.frames} label="frames from the Ring camera" />
            <Reading n={`${d.claims.answered}/${d.claims.total}`} label="claim questions answered" />
            <Reading n={d.integrity.gaps.length} label="gaps disclosed" hatched={d.integrity.gaps.length > 0} />
          </dl>
        </div>
        <Staff
          start={inc.opened_at_ms}
          end={end}
          open={open}
          notches={d.frames.map((f) => ({ ms: f.media_ms, wet: f.water_visible === 1 }))}
          gaps={d.integrity.gaps.map((g) => ({ start: g.start_ms, end: g.end_ms }))}
          marks={marks}
        />
      </section>

      <section aria-labelledby="frames-h">
        <div className="flex items-baseline justify-between border-b border-seam pb-2 mb-4">
          <h2 id="frames-h" className="label">Frames from the Ring camera</h2>
          <span className="text-[13px] text-stencil">newest first · each frame keeps Ring&apos;s own time</span>
        </div>
        {d.frames.length === 0 ? (
          <div className="plate hatch p-6">
            <p className="font-display text-xl font-bold uppercase tracking-wide">No frames yet</p>
            <p className="mt-1 text-stencil">
              {open
                ? inc.camera_role === "rover" && !inc.rover_on_station_at_ms
                  ? "The rover is on its way. Frames start the moment it reports on station."
                  : "Waiting for the camera's first live session."
                : "This incident closed before any frame was captured. The pack says so."}
            </p>
          </div>
        ) : (
          <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {d.frames.slice(-12).reverse().map((f) => {
              const drift = f.drift_ms != null && Math.abs(f.drift_ms) > 10000;
              return (
                <li key={f.id} className="plate plate-in">
                  <div className="relative">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={api.frameUrl(f.id)} alt={f.caption || "Frame from the Ring camera"} className="w-full aspect-video object-cover" />
                    <span className="absolute left-0 bottom-0 bg-staff text-tick font-display font-extrabold text-[17px] px-2 py-0.5 tracking-wide">
                      {fmtTime(f.media_ms)}
                    </span>
                  </div>
                  <div className="p-3 grid gap-2">
                    <div className="flex items-center gap-2">
                      <span className="spot" data-wet={f.water_visible === 1} aria-hidden="true" />
                      <span className="label">{f.water_visible === 1 ? "Water visible" : f.water_visible === 0 ? "No water visible" : "Not captioned"}</span>
                      {drift && <span className="label hatch px-1 text-ink">Time drift</span>}
                    </div>
                    {f.caption && <p className="text-[14px] leading-snug">{f.caption}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="grid gap-10 lg:grid-cols-[1.1fr_1fr]">
        <div aria-labelledby="timeline-h">
          <h2 id="timeline-h" className="label border-b border-seam pb-2 mb-2">Timeline</h2>
          <table className="log">
            <tbody>
              {d.timeline.slice(-30).map((t, i) => (
                <tr key={i}>
                  <td className="font-display font-bold text-[15px] whitespace-nowrap pr-5 w-[1%]">{fmtTime(t.ts_ms)}</td>
                  <td className="text-[11px] text-stencil uppercase tracking-wider whitespace-nowrap pr-5 w-[1%] align-middle">{t.source}</td>
                  <td>{t.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div aria-labelledby="integrity-h">
          <h2 id="integrity-h" className="label border-b border-seam pb-2 mb-3">What this record cannot vouch for</h2>
          {d.integrity.gaps.length === 0 && d.integrity.flags.length === 0 ? (
            <p className="text-stencil">Nothing so far. Every frame carries Ring&apos;s timestamp and every event arrived by webhook.</p>
          ) : (
            <ul className="grid gap-2">
              {d.integrity.gaps.map((g, i) => (
                <li key={`g${i}`} className="plate grid grid-cols-[12px_1fr]">
                  <span className="hatch border-r border-seam" aria-hidden="true" />
                  <div className="px-3 py-2">
                    <span className="font-display font-bold">{fmtTime(g.start_ms)}{g.end_ms ? `–${fmtTime(g.end_ms)}` : ""}</span>
                    <span className="text-stencil"> · </span>
                    {g.text}
                  </div>
                </li>
              ))}
              {d.integrity.flags.map((f, i) => (
                <li key={`f${i}`} className="plate px-3 py-2 text-stencil">{f.text}</li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section aria-labelledby="claims-h">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-seam pb-2">
          <h2 id="claims-h" className="label">Against the questions on the claim file</h2>
          <span className="text-[13px] text-stencil">{d.claims.source}</span>
        </div>
        <ul>
          {d.claims.rows.map((q) => (
            <li key={q.id} className="grid sm:grid-cols-[150px_1fr_1.1fr] gap-x-6 gap-y-1 py-3 border-b border-seam">
              <span className={`label self-start px-2 py-1 w-fit ${q.status === "answered" ? "bg-ink text-concrete" : q.status === "partial" ? "plate text-ink" : "hatch text-stencil"}`}>
                {q.status === "unanswered" ? "Not answered" : q.status}
              </span>
              <span>{q.question}</span>
              <span className="text-stencil text-[14px]">{q.evidence}</span>
            </li>
          ))}
        </ul>
      </section>

      {d.narrative && (
        <section className="plate p-5 max-w-3xl">
          <h2 className="label">Narrative</h2>
          <p className="mt-2 leading-relaxed">{d.narrative}</p>
        </section>
      )}
      <Link href="/dashboard" className="btn-ghost w-fit">Back to dashboard</Link>
    </div>
  );
}

function Reading({ n, label, hatched }: { n: number | string; label: string; hatched?: boolean }) {
  return (
    <div className={`flex flex-col-reverse border-l-2 border-seam pl-3 ${hatched ? "hatch" : ""}`}>
      <dt className="text-[13px] text-stencil mt-1 max-w-[12ch] leading-tight">{label}</dt>
      <dd className="readout text-[40px]">{n}</dd>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="grid gap-6" aria-busy="true" aria-label="Loading incident">
      <div className="h-6 w-48 plate" />
      <div className="h-16 w-2/3 plate" />
      <div className="h-24 staff opacity-40" />
    </div>
  );
}

function plainError(e: string): string {
  if (e.startsWith("404")) return "This incident no longer exists. It may have been deleted from Settings.";
  if (e.includes("Failed to fetch")) return "Watermark's server is not answering. Check that it is running, then reload.";
  return e;
}

export default function IncidentPage() {
  return (
    <Suspense fallback={null}>
      <IncidentInner />
    </Suspense>
  );
}
