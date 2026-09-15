"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Account } from "@/lib/api";

export default function Home() {
  const [acct, setAcct] = useState<Account | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.account().then(setAcct).catch((e) => setErr(String(e.message || e)));
  }, []);

  return (
    <div className="grid gap-10">
      <section className="grid md:grid-cols-[1.4fr_1fr] gap-8 items-end">
        <div>
          <p className="label text-water mb-3">Ring flood sensor · Ring camera · your claim</p>
          <h1 className="text-4xl md:text-5xl font-bold leading-[1.05]">
            When a Ring sensor finds water,
            <br />
            the camera goes to the water.
          </h1>
          <p className="mt-5 text-lg text-muted max-w-xl">
            A timestamped, photographed timeline of a flood from the second it starts, with everything Watermark could
            not verify written down next to everything it could. Built after my condo flooded and the only proof I had
            was two phone videos I happened to take.
          </p>
        </div>
        <div className="border border-line bg-paper p-5">
          {err && <p className="text-warn text-sm font-sans">Server not reachable: {err}</p>}
          {acct?.linked ? (
            <>
              <p className="label text-ok">Ring account linked</p>
              <p className="mt-1 text-sm text-muted font-sans">{acct.email}{acct.mode === "mock" ? " (mock mode)" : ""}</p>
              <Link href="/dashboard" className="btn mt-4">Go to Dashboard</Link>
            </>
          ) : (
            <>
              <p className="label">Not linked yet</p>
              <p className="mt-1 text-sm text-muted font-sans">
                Install Watermark from the Ring Appstore. Ring will send you here to create your account.
              </p>
              <Link href="/link" className="btn mt-4">Create account</Link>
            </>
          )}
        </div>
      </section>

      <section className="grid md:grid-cols-3 gap-6">
        {[
          ["1", "Water touches the sensor", "Ring's Flood & Freeze sensor fires. Watermark stores the event before doing anything else, because Ring keeps no history for sensor events."],
          ["2", "The camera goes to the water", "A fixed Indoor Cam that already sees the room, or the rover carrying one down a tape line. A live session forces a recording; frames carry Ring's own timestamps."],
          ["3", "One pack, gaps included", "Timeline, frames with captions, humidity, device health, an integrity section that lists every gap, and a map against your insurer's questions. Cause is left to the adjuster."],
        ].map(([n, t, d]) => (
          <div key={n} className="waterline pb-5">
            <div className="font-mono text-water text-sm">{n}</div>
            <h2 className="text-xl font-bold mt-1">{t}</h2>
            <p className="text-sm text-muted mt-2">{d}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
