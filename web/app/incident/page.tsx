"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import Counter from "@/components/Counter";
import HighWaterLine from "@/components/HighWaterLine";
import Print from "@/components/Print";
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
      <div className="grid sm:grid-cols-[180px_1fr] gap-6 items-center max-w-2xl">
        <Print name="error" width={180} className="w-[140px] sm:w-[180px]" decorative />
        <div>
          <p className="title text-[26px]">Could not load this incident</p>
          <p className="mt-2">{plainError(err)}</p>
          <Link href="/dashboard" className="btn-ghost mt-4">Back to dashboard</Link>
        </div>
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

  // The page leads with the evidence itself: the Ring frame where water is visible, else the newest.
  const lead = [...d.frames].reverse().find((f) => f.water_visible === 1) ?? d.frames[d.frames.length - 1];
  const s2f = st.sensor_to_first_frame_s;

  return (
    <div className="grid gap-12">
      <section className="grid grid-cols-1 gap-8 lg:grid-cols-[1.3fr_1fr] lg:items-start [&>*]:min-w-0">
        {lead ? (
          <figure className="grid gap-2 lg:order-none order-2">
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={api.frameUrl(lead.id)} alt={lead.caption || "Frame from the Ring camera"}
                   className="w-full aspect-video object-cover rounded-[3px] border border-seam" />
              <span className="absolute left-0 bottom-0 bg-staff text-tick font-display font-extrabold text-[17px] px-2 py-0.5 rounded-bl-[3px]">
                {fmtTime(lead.media_ms)}
              </span>
            </div>
            <figcaption className="text-[14px] text-stencil">
              {lead.water_visible === 1 ? "Water visible. " : ""}A frame from the Ring camera, with Ring&apos;s own time.
              {controlled && <strong className="text-ink font-semibold"> Controlled test. Real device.</strong>}
            </figcaption>
          </figure>
        ) : (
          <figure className="grid gap-2 order-2 lg:order-none">
            {/* The frame's own slot, the size a Ring frame lands at, so nothing moves when it does. */}
            <div className="relative w-full aspect-video rounded-[3px] border border-dashed border-stencil bg-plate grid place-items-center text-center px-6">
              <p className="text-stencil">
                {open
                  ? inc.camera_role === "rover" && !inc.rover_on_station_at_ms
                    ? `The rover is on its way to ${inc.room}. Frames start the moment it reports on station.`
                    : `Waiting for ${d.camera?.name ?? "the camera"}'s first live session.`
                  : "This incident closed before any frame was captured. The pack says so."}
              </p>
              {open && <Elapsed since={inc.opened_at_ms} />}
            </div>
            <figcaption className="text-[14px] text-stencil">
              The first frame from the Ring camera lands here, with Ring&apos;s own time.
              {controlled && <strong className="text-ink font-semibold"> Controlled test. Real device.</strong>}
            </figcaption>
          </figure>
        )}

        <div className="grid gap-6">
          {/* The plaque: what happened above the line, when below it. The line is as wide as the name. */}
          <HighWaterLine
            className="w-fit max-w-full"
            above={<h1 className="headline text-[34px] sm:text-[44px]">{inc.room}</h1>}
            below={
              <p>
                {inc.kind === "flood" ? "Water" : "Freezing"} {open ? "since" : "on"} {fmtDate(inc.opened_at_ms)}
                {open ? ", recording until the sensor reads dry" : `, dry at ${fmtTime(inc.closed_at_ms)}`}
              </p>
            }
          />
          <p className="text-[17px] leading-relaxed" aria-live="polite">
            {s2f != null ? (
              <>
                The first frame from <strong className="font-semibold">{d.camera?.name ?? cam}</strong> arrived{" "}
                <strong className="font-semibold"><Counter value={s2f} decimals={1} /> s</strong>{" "}
                after the sensor went wet.
              </>
            ) : open ? (
              <>Waiting for the first frame from {d.camera?.name ?? "the camera"}.</>
            ) : (
              <>No frame arrived before the sensor read dry.</>
            )}{" "}
            {st.frames} {st.frames === 1 ? "frame" : "frames"} so far, {d.claims.answered} of {d.claims.total} claim questions answered,{" "}
            {d.integrity.gaps.length ? (
              <span className="border-b border-dashed border-stencil">
                {d.integrity.gaps.length} {d.integrity.gaps.length === 1 ? "gap" : "gaps"} disclosed below.
              </span>
            ) : d.integrity.verdict === "complete" ? (
              "and no gaps in the record."
            ) : (
              <span className="border-b border-dashed border-stencil">
                {d.integrity.verdict === "sensor-only" ? "and so far only the sensor's times." : `and the evidence is ${d.integrity.verdict}.`}
              </span>
            )}
          </p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
            <a className="btn" href={api.packHtmlUrl(inc.id)} target="_blank" rel="noreferrer">Open evidence pack</a>
            {open ? (
              <button className="text-[15px] underline decoration-line underline-offset-4 hover:text-line min-h-[44px]" disabled={busy} onClick={async () => { setBusy(true); await api.closeIncident(inc.id).catch(() => {}); setBusy(false); load(); }}>
                Close by hand
              </button>
            ) : (
              <button className="text-[15px] underline underline-offset-4 hover:text-stencil min-h-[44px]" disabled={busy} onClick={async () => { setBusy(true); await api.rebuildPack(inc.id).catch(() => {}); setBusy(false); load(); }}>
                Rebuild pack
              </button>
            )}
            <span className="text-[14px] text-stencil">
              Download{" "}
              {d.latest_pack?.pdf_path && (
                <><a className="underline hover:text-ink" href={api.packPdfUrl(inc.id)} target="_blank" rel="noreferrer">PDF</a>{" or "}</>
              )}
              <a className="underline hover:text-ink" href={api.packJsonUrl(inc.id)} target="_blank" rel="noreferrer">data file</a>
            </span>
          </div>
        </div>
      </section>

      <section aria-label="How long the water stood">
        <Staff
          start={inc.opened_at_ms}
          end={end}
          open={open}
          notches={d.frames.map((f) => ({ ms: f.media_ms, wet: f.water_visible === 1 }))}
          gaps={d.integrity.gaps.map((g) => ({ start: g.start_ms, end: g.end_ms }))}
          marks={marks}
          viewName={`staff-${inc.id}`}
        />
      </section>

      <section aria-labelledby="frames-h">
        <div className="flex items-baseline justify-between border-b border-seam pb-2 mb-4">
          <h2 id="frames-h" className="title">Frames from the Ring camera</h2>
          <span className="text-[13px] text-stencil">newest first · each frame keeps Ring&apos;s own time</span>
        </div>
        {d.frames.length === 0 ? (
          <div className="grid sm:grid-cols-[150px_1fr] gap-6 items-center">
            <Print name={open ? "setup" : "error"} width={150} className="w-[120px] sm:w-[150px]" decorative />
            <div>
            <p className="title text-[22px]">No frames yet</p>
            <p className="mt-1 text-stencil">
              {open
                ? inc.camera_role === "rover" && !inc.rover_on_station_at_ms
                  ? "The rover is on its way. Frames start the moment it reports on station."
                  : "Waiting for the camera's first live session."
                : "This incident closed before any frame was captured. The pack says so."}
            </p>
            </div>
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
                    <span className="absolute left-0 bottom-0 bg-staff text-tick font-display font-extrabold text-[17px] px-2 py-0.5">
                      {fmtTime(f.media_ms)}
                    </span>
                  </div>
                  <div className="p-3 grid gap-2">
                    <div className="flex items-center gap-2">
                      <span className="spot" data-wet={f.water_visible === 1} aria-hidden="true" />
                      <span className="label">{f.water_visible === 1 ? "Water visible" : f.water_visible === 0 ? "No water visible" : "Not captioned"}</span>
                      {drift && <span className="label border border-dashed border-stencil rounded-[3px] px-1 text-ink">Time drift</span>}
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
          <h2 id="timeline-h" className="title border-b border-seam pb-2 mb-2">Timeline</h2>
          <table className="log">
            <tbody>
              {d.timeline.slice(-30).map((t, i) => (
                <tr key={i}>
                  <td className="font-display font-bold text-[15px] whitespace-nowrap pr-5 w-[1%]">{fmtTime(t.ts_ms)}</td>
                  <td className="text-[13px] text-stencil whitespace-nowrap pr-5 w-[1%]">{t.source}</td>
                  <td>{t.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div aria-labelledby="integrity-h">
          <h2 id="integrity-h" className="title border-b border-seam pb-2 mb-3">What this record cannot vouch for</h2>
          {d.integrity.gaps.length === 0 && d.integrity.flags.length === 0 ? (
            <p className="text-stencil">Nothing so far. Every frame carries Ring&apos;s timestamp and every event arrived by webhook.</p>
          ) : (
            <ul className="grid gap-2">
              {d.integrity.gaps.map((g, i) => (
                <li key={`g${i}`} className="plate grid grid-cols-[12px_1fr]">
                  <span className="dots border-r border-seam" aria-hidden="true" />
                  <div className="px-3 py-2">
                    <span className="font-display font-bold">{fmtTime(g.start_ms)}{g.end_ms ? ` to ${fmtTime(g.end_ms)}` : ""}</span>
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
          <h2 id="claims-h" className="title">Against the questions on the claim file</h2>
          <span className="text-[13px] text-stencil">{d.claims.source}</span>
        </div>
        <ul>
          {d.claims.rows.map((q) => (
            <li key={q.id} className="grid sm:grid-cols-[150px_1fr_1.1fr] gap-x-6 gap-y-1 py-3 border-b border-seam">
              <span className={`self-start px-2 py-1 w-fit text-[13px] font-semibold rounded-[3px] ${q.status === "answered" ? "bg-ink text-concrete" : q.status === "partial" ? "plate text-ink" : "text-stencil border border-dashed border-stencil"}`}>
                {q.status === "unanswered" ? "Not answered" : q.status === "answered" ? "Answered" : "Partly answered"}
              </span>
              <span>{q.question}</span>
              <span className="text-stencil text-[14px]">{q.evidence}</span>
            </li>
          ))}
        </ul>
      </section>

      {d.narrative && (
        <section className="plate p-5 max-w-3xl">
          <h2 className="title">Narrative</h2>
          <p className="mt-2 leading-relaxed">{d.narrative}</p>
        </section>
      )}
      <Link href="/dashboard" className="btn-ghost w-fit">Back to dashboard</Link>
    </div>
  );
}

function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const s = Math.max(0, Math.round((now - since) / 1000));
  return (
    <span className="absolute left-0 bottom-0 bg-staff text-tick font-display font-extrabold text-[17px] px-2 py-0.5 rounded-bl-[3px]">
      +{Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")}
    </span>
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
