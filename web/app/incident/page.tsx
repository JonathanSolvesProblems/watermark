"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
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

  if (err) return <p className="text-warn font-sans text-sm">{err}</p>;
  if (!d) return <p className="text-muted font-sans text-sm">Loading…</p>;

  const inc = d.incident;
  const st = d.integrity.stats;
  const open = inc.status === "open";
  const controlled = !!d.notes?.controlled_test;

  return (
    <div className="grid gap-10">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-muted">{inc.id}</p>
          <h1 className="text-3xl font-bold mt-1">{inc.kind === "flood" ? "Water" : "Freeze"} in {inc.room}</h1>
          <p className="text-sm text-muted font-sans mt-1">
            {fmtDate(inc.opened_at_ms)} · {open ? "still open" : `closed ${fmtTime(inc.closed_at_ms)} (${inc.closed_source})`} ·{" "}
            {inc.camera_role === "rover" ? "rover camera" : inc.camera_role === "fixed" ? "fixed camera" : "no camera"}
          </p>
          <div className="flex gap-2 mt-2">
            {controlled && <span className="label text-warn border border-warn px-2 py-1">Controlled test. Real device.</span>}
            <span className={`label border px-2 py-1 ${d.integrity.verdict === "complete" ? "text-ok border-ok" : "text-warn border-warn"}`}>
              Evidence: {d.integrity.verdict}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 font-sans">
          <a className="btn" href={api.packHtmlUrl(inc.id)} target="_blank" rel="noreferrer">Open pack</a>
          {d.latest_pack?.pdf_path && <a className="btn-ghost" href={api.packPdfUrl(inc.id)} target="_blank" rel="noreferrer">PDF</a>}
          <a className="btn-ghost" href={api.packJsonUrl(inc.id)} target="_blank" rel="noreferrer">JSON</a>
          {open ? (
            <button className="btn-danger" disabled={busy} onClick={async () => { setBusy(true); await api.closeIncident(inc.id).catch(() => {}); setBusy(false); load(); }}>
              Close manually
            </button>
          ) : (
            <button className="btn-ghost" disabled={busy} onClick={async () => { setBusy(true); await api.rebuildPack(inc.id).catch(() => {}); setBusy(false); load(); }}>
              Rebuild pack
            </button>
          )}
        </div>
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="stat"><div className="n">{st.sensor_to_first_frame_s ?? "–"}<span className="text-base text-muted"> s</span></div><div className="l">sensor to first frame</div></div>
        <div className="stat"><div className="n">{st.frames}</div><div className="l">frames from the Ring camera</div></div>
        <div className="stat"><div className="n">{d.claims.answered}<span className="text-base text-muted"> / {d.claims.total}</span></div><div className="l">claim questions answered</div></div>
        <div className="stat"><div className="n">{d.integrity.gaps.length}</div><div className="l">gaps disclosed</div></div>
      </section>

      <section className="grid md:grid-cols-[1.2fr_1fr] gap-8">
        <div>
          <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Frames</h2></div>
          {d.frames.length === 0 ? (
            <p className="text-sm text-muted font-sans">
              {open ? "Waiting for the camera. " : "No frames. "}
              {inc.camera_role === "rover" && !inc.rover_on_station_at_ms && open ? "The rover has not reported on station yet." : ""}
            </p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {d.frames.slice(-12).reverse().map((f) => (
                <figure key={f.id} className="border border-line bg-paper">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={api.frameUrl(f.id)} alt="" className="w-full aspect-video object-cover" />
                  <figcaption className="p-2 text-xs font-sans">
                    <div className="font-mono">{fmtTime(f.media_ms)} · {f.origin}{f.drift_ms != null && Math.abs(f.drift_ms) > 10000 ? " · drift" : ""}</div>
                    {f.caption && <div className="mt-1 text-muted">{f.caption}</div>}
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
        </div>
        <div>
          <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Timeline</h2></div>
          <table className="log">
            <tbody>
              {d.timeline.slice(-30).map((t, i) => (
                <tr key={i}>
                  <td className="font-mono text-xs whitespace-nowrap pr-3">{fmtTime(t.ts_ms)}</td>
                  <td className="text-xs text-muted pr-3 whitespace-nowrap">{t.source}</td>
                  <td className="text-sm">{t.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Evidence integrity</h2></div>
        {d.integrity.gaps.length === 0 && d.integrity.flags.length === 0 && <p className="text-sm text-muted font-sans">No gaps or flags yet.</p>}
        <div className="grid gap-2">
          {d.integrity.gaps.map((g, i) => (
            <div key={`g${i}`} className="border-l-4 border-warn bg-paper px-3 py-2 text-sm">
              <span className="font-mono text-xs">{fmtTime(g.start_ms)}{g.end_ms ? ` to ${fmtTime(g.end_ms)}` : ""}</span> · {g.text}
            </div>
          ))}
          {d.integrity.flags.map((f, i) => (
            <div key={`f${i}`} className="border-l-4 border-muted bg-paper px-3 py-2 text-sm">{f.text}</div>
          ))}
        </div>
      </section>

      <section>
        <div className="waterline pb-2 mb-3 flex items-baseline justify-between">
          <h2 className="text-xl font-bold">Against the claim questions</h2>
          <span className="text-xs text-muted font-sans">{d.claims.source}</span>
        </div>
        <div className="divide-y divide-line">
          {d.claims.rows.map((q) => (
            <div key={q.id} className="grid sm:grid-cols-[110px_1fr_1.2fr] gap-3 py-2 text-sm">
              <span className={`label ${q.status === "answered" ? "text-ok" : q.status === "partial" ? "text-warn" : "text-muted"}`}>{q.status}</span>
              <span>{q.question}</span>
              <span className="text-muted font-sans text-xs">{q.evidence}</span>
            </div>
          ))}
        </div>
      </section>

      <p className="text-sm text-muted">{d.narrative}</p>
      <Link href="/dashboard" className="text-sm font-sans underline">Back to dashboard</Link>
    </div>
  );
}

export default function IncidentPage() {
  return (
    <Suspense fallback={null}>
      <IncidentInner />
    </Suspense>
  );
}
