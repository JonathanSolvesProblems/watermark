"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import HighWaterLine from "@/components/HighWaterLine";
import Print from "@/components/Print";
import { api, type Account } from "@/lib/api";

// The three moments of an incident, in the order they happen.
const MARKS = [
  {
    at: "0 s",
    title: "Water touches the sensor",
    body: "A Ring Flood & Freeze sensor fires. Watermark stores the event before anything else, because Ring keeps no history for sensor events.",
  },
  {
    at: "6.85 s",
    title: "The camera goes to the water",
    body: "An Indoor Cam that already sees the room opens a live session, which makes it record. Every frame carries Ring's time. 6.85 s is the median of my 10 measured Ring Playground runs, with a simulated sensor.",
  },
  {
    at: "When dry",
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
    <div className="grid gap-12 lg:gap-20">
      {/* The hero is my own basement on 20 June 2026: evidence, not a drawing of it. */}
      <section className="grid gap-8 lg:grid-cols-[1.2fr_1fr] lg:items-center">
        <div>
          <h1 className="headline text-[38px] sm:text-[52px] max-w-[18ch]">The camera goes to the water when the sensor finds it</h1>
          <p className="mt-6 text-[18px] leading-relaxed text-stencil max-w-xl">
            On June 20, 2026 the city sewer backed up into more than 60 units of my condo. Mine also came in through the
            foundation, gaps beside the electrical panel and a basement window, one week after I had finished rebuilding
            from my first flood. The mitigation report blamed heavy rain. The only thing that stopped it was two phone
            videos I took because I happened to be home. Watermark is the record I wish had been running.
          </p>
          <AccountBox acct={acct} err={err} />
        </div>
        <figure className="grid gap-3 lg:-mr-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/flood/basement-2026-06-20.jpg"
            width={1050}
            height={1400}
            alt="My basement on 20 June 2026: water running down the wall under the window and spreading across the wood floor"
            className="w-full max-h-[560px] object-cover object-[50%_70%] rounded-[3px]"
            fetchPriority="high"
          />
          {/* Home's arrival moment: the high-water line is struck across under the photo. */}
          <HighWaterLine
            above={<p className="title text-[20px]">Water came in under this window and ran across the floor</p>}
            below={<p className="text-[14px]">My basement, 20 June 2026, 4:35 PM, on a floor laid the week before. A phone photo, because nothing was recording.</p>}
          />
        </figure>
      </section>

      <section className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-start" aria-labelledby="keeps-h">
        <figure className="grid gap-3 lg:order-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/flood/ceiling-2025-12-05.jpg"
            width={900}
            height={1600}
            alt="My dining room on 5 December 2025: the ceiling opened up under a leaking bathroom, a blanket on the floor catching the water"
            className="w-full max-w-[420px] max-h-[640px] object-cover lg:ml-auto rounded-[3px]"
            loading="lazy"
          />
          <figcaption className="text-[14px] text-stencil lg:text-right max-w-[420px] lg:ml-auto">
            The first flood, 5 December 2025: through the dining room ceiling. Again, only my phone was recording.
          </figcaption>
        </figure>
        <div className="lg:order-1">
          <h2 id="keeps-h" className="title text-[32px]">What Watermark keeps instead</h2>
          <ol className="mt-8 grid gap-8 border-l-[3px] border-seam pl-6">
            {MARKS.map((m) => (
              <li key={m.title}>
                <p className="readout text-[34px]">{m.at}</p>
                <h3 className="title mt-1">{m.title}</h3>
                <p className="mt-2 text-stencil leading-relaxed max-w-xl">{m.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </div>
  );
}

function AccountBox({ acct, err }: { acct: Account | null; err: string | null }) {
  if (err)
    return (
      <div className="mt-8 grid grid-cols-[88px_1fr] gap-4 items-center max-w-xl">
        <Print name="error" width={88} decorative />
        <p className="text-[15px]">Watermark&apos;s server is not answering. Start it, then reload this page.</p>
      </div>
    );
  if (!acct) return <div className="mt-8 h-[92px]" aria-busy="true" />;
  return (
    <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
      {acct.linked ? (
        <>
          <Link href="/dashboard" className="btn">Go to dashboard</Link>
          <p className="label">
            {acct.mode === "playground" ? "Ring Developer Playground: Ring's simulated doorbell, through the real Ring API" : "Your Ring account is linked"}
          </p>
        </>
      ) : (
        <>
          <Link href="/link" className="btn">Create account</Link>
          <p className="label max-w-sm">Add Watermark from the Ring Appstore. The Ring app sends you back here.</p>
        </>
      )}
    </div>
  );
}
