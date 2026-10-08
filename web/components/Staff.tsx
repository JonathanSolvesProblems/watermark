"use client";

import { useEffect, useState } from "react";

// The staff gauge: time from the sensor going wet to now (or to dry) painted on
// an enamel staff. The pink fill is how long water stood; notches along the top
// are frames from the Ring camera; hatching is a span the record cannot vouch for.

type Mark = { ms: number; label: string };
type Notch = { ms: number; wet: boolean };
type Span = { start: number; end: number | null };

export default function Staff({
  start,
  end,
  open,
  notches,
  gaps,
  marks,
  viewName,
}: {
  start: number;
  end: number;
  open: boolean;
  notches: Notch[];
  gaps: Span[];
  marks: Mark[];
  viewName?: string;
}) {
  // While water stands, the gauge follows the clock rather than waiting for the next poll.
  const [now, setNow] = useState(end);
  useEffect(() => {
    if (!open) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [open]);
  // A frame cannot be later than the water it shows: if one arrives stamped ahead of this
  // browser's clock, the fill reaches it rather than leaving the notch hanging past the end.
  const latest = notches.reduce((m, n) => Math.max(m, n.ms), 0);
  const until = open ? Math.max(end, now, latest) : Math.max(end, latest);
  const span = Math.max(until - start, 1000);
  // Closed: a little headroom. Open: the scale snaps to whole steps, so between rescales
  // the water visibly climbs against fixed marks, as it does on a real staff.
  const axis = open ? ceilToStep(span * 1.15) : span * 1.04;
  const at = (ms: number) => `${Math.min(100, Math.max(0, ((ms - start) / axis) * 100))}%`;
  const fillPct = (span / axis) * 100;
  const step = niceStep(axis);
  const numerals: number[] = [];
  for (let t = 0; t <= axis; t += step) numerals.push(t);

  return (
    <figure className="select-none" aria-label={`Water stood ${fmtElapsed(span)}${open ? " so far" : ""}`}>
      <div className="relative h-5 mb-1" aria-hidden="true">
        {notches.map((n) => (
          <span
            key={n.ms}
            className="notch-in absolute bottom-0 w-[3px] h-4 -translate-x-1/2"
            style={{ left: at(n.ms), background: n.wet ? "var(--wet)" : "var(--ink)" }}
          />
        ))}
      </div>
      <div className="staff h-16 overflow-hidden" data-view={viewName}
           style={viewName ? { viewTransitionName: viewName } : undefined}>
        <div
          key={open ? "open" : "closed"}
          data-rise="true"
          data-live={open}
          className="staff-fill absolute inset-y-0 left-0"
          style={{ width: `${fillPct}%` }}
        />
        {gaps.map((g, i) => (
          <div
            key={i}
            className="absolute inset-y-0 border-x"
            style={{
              borderColor: "var(--tick)",
              left: at(g.start),
              width: `calc(${at(g.end ?? until)} - ${at(g.start)})`,
              backgroundImage: "repeating-linear-gradient(135deg, rgba(20,24,22,.55) 0 2px, transparent 2px 7px)",
            }}
            title="Not verified"
          />
        ))}
        {/* E-ticks from the same scale as the numerals: a full stroke on each step, half strokes between. */}
        <div className="absolute inset-0" aria-hidden="true">
          {ticks(axis, step).map((t) => (
            <span
              key={t.at}
              className="absolute top-0 -translate-x-1/2"
              style={{ left: `${(t.at / axis) * 100}%`, width: t.major ? 3 : 1, height: t.major ? "100%" : "42%", background: "var(--tick)" }}
            />
          ))}
        </div>
        {open && <div className="absolute inset-y-0 w-[2px] bg-tick" style={{ left: `${fillPct}%` }} aria-hidden="true" />}
      </div>
      <div className="relative h-6 mt-1 text-[12px] font-display font-bold tracking-wide text-stencil" aria-hidden="true">
        {numerals.map((t) => (
          <span key={t} className="absolute -translate-x-1/2" style={{ left: `${(t / axis) * 100}%` }}>
            {fmtElapsed(t)}
          </span>
        ))}
      </div>
      <figcaption className="mt-3 grid gap-x-8 gap-y-2 sm:grid-cols-2 lg:grid-cols-4">
        {marks.map((m) => (
          <div key={m.label} className="flex items-baseline gap-3 border-t border-seam pt-2">
            <span className="readout text-[22px]">+{fmtElapsed(m.ms - start)}</span>
            <span className="text-[14px] text-stencil">{m.label}</span>
          </div>
        ))}
      </figcaption>
    </figure>
  );
}

function ticks(axis: number, step: number): { at: number; major: boolean }[] {
  const minor = step / 5;
  const out: { at: number; major: boolean }[] = [];
  for (let i = 1; i * minor < axis; i++) out.push({ at: i * minor, major: i % 5 === 0 });
  return out;
}

function ceilToStep(ms: number): number {
  const s = niceStep(ms);
  return Math.ceil(ms / s) * s;
}

function niceStep(ms: number): number {
  const targets = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 21600].map((s) => s * 1000);
  return targets.find((s) => ms / s <= 8) ?? 43200000;
}

export function fmtElapsed(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return s % 60 ? `${m}m${String(s % 60).padStart(2, "0")}` : `${m}m`;
  const h = Math.floor(m / 60);
  return m % 60 ? `${h}h${String(m % 60).padStart(2, "0")}` : `${h}h`;
}
