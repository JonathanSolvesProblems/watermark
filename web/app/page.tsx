"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Account } from "@/lib/api";

const STEPS = [
  {
    mark: "0s",
    title: "Water touches the sensor",
    body: "A Ring Flood & Freeze sensor fires. Watermark stores the event before anything else, because Ring keeps no history for sensor events.",
  },
  {
    mark: "+s",
    title: "The camera goes to the water",
    body: "An Indoor Cam that already sees the room, or the rover carrying one down a tape line. A live session makes it record, and every frame carries Ring's time.",
  },
  {
    mark: "dry",
    title: "One pack, gaps included",
    body: "Timeline, frames, captions, humidity, device health, everything the record cannot vouch for, and a map against your insurer's questions. The cause is left to the adjuster.",
  },
];

export default function Home() {
  const [acct, setAcct] = useState<Account | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.account().then(setAcct).catch((e) => setErr(String(e.message || e)));
  }, []);

  return (
    <div className="grid gap-14">
      <section className="grid gap-10 lg:grid-cols-[1.5fr_1fr] lg:items-end">
        <div>
          <p className="label">Ring flood sensor · Ring camera · your claim</p>
          <h1 className="readout uppercase text-[52px] sm:text-[84px] mt-4">
            When the sensor finds water, <span className="text-stencil">the camera goes to the water.</span>
          </h1>
          <p className="mt-6 text-[18px] leading-relaxed text-stencil max-w-2xl">
            On June 20, 2026 the city sewer backed up into 52 units of my condo. The mitigation report blamed heavy rain.
            The only thing that stopped it was two phone videos I took because I happened to be home. Watermark is the
            record I wish had been running.
          </p>
        </div>
        <div className="plate p-6">
          {err && (
            <p className="text-[15px]">
              <span className="label block mb-1">Server not reachable</span>
              Watermark&apos;s server is not answering. Start it, then reload this page.
            </p>
          )}
          {acct?.linked ? (
            <>
              <div className="flex items-center gap-2">
                <span className="spot" aria-hidden="true" />
                <p className="label">{acct.mode === "playground" ? "Ring Developer Playground" : "Ring account linked"}</p>
              </div>
              <p className="mt-2">{acct.mode === "playground" ? "Ring's simulated doorbell, through the real Ring API." : acct.email}</p>
              <Link href="/dashboard" className="btn mt-5">Go to dashboard</Link>
            </>
          ) : !err ? (
            <>
              <p className="label">Not linked yet</p>
              <p className="mt-2 text-stencil">
                Add Watermark from the Ring Appstore. The Ring app will send you back here to create your account.
              </p>
              <Link href="/link" className="btn mt-5">Create account</Link>
            </>
          ) : null}
        </div>
      </section>

      <section aria-label="How Watermark works">
        <div className="staff h-3 mb-6" aria-hidden="true" />
        <ol className="grid gap-8 md:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.title} className="border-l-2 border-seam pl-4">
              <span className="readout text-[40px] text-stencil">{s.mark}</span>
              <h2 className="font-display text-[24px] font-bold uppercase tracking-wide mt-2">{s.title}</h2>
              <p className="mt-2 text-stencil leading-relaxed">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
