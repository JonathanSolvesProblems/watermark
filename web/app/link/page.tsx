"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, type Device } from "@/lib/api";

// Ring's Account Link URL lands here with ?nonce=...&time=... By then the token
// exchange has happened, so the email can be pre-filled from the Ring account
// (Ring UX guide). Creating an account is the primary action; there is no
// password and no verification step to drop off at.
function LinkInner() {
  const params = useSearchParams();
  const nonce = params.get("nonce") || "";
  const time = Number(params.get("time") || 0);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);

  useEffect(() => {
    if (nonce && time) api.linkPrefill(nonce, time).then((r) => r.email && setEmail((e) => e || r.email || "")).catch(() => {});
  }, [nonce, time]);

  useEffect(() => {
    if (done) api.devices().then(setDevices).catch(() => {});
  }, [done]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api.link(email, nonce, time);
      setDone(true);
    } catch (e: unknown) {
      setErr(linkError(e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="max-w-2xl grid gap-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="spot" aria-hidden="true" />
            <p className="label">Account linked</p>
          </div>
          <h1 className="readout uppercase text-[48px] sm:text-[64px] mt-2">Ring is connected</h1>
          <p className="mt-3 text-stencil">
            Ring has emailed you a confirmation naming this account. Watermark can now see these devices:
          </p>
        </div>
        <ul className="plate">
          {devices.map((d) => (
            <li key={d.device_id} className="px-4 py-3 border-b border-seam last:border-b-0 flex items-center justify-between gap-4">
              <span>{d.name}</span>
              <span className="flex items-center gap-2">
                <span className="spot" data-off={!d.online} aria-hidden="true" />
                <span className="label">{d.online ? "Online" : "Offline"}</span>
              </span>
            </li>
          ))}
          {devices.length === 0 && (
            <li className="px-4 py-3 hatch">
              No devices yet. Ring can take a minute to share them; this list refreshes when you open the dashboard.
            </li>
          )}
        </ul>
        <div>
          <p className="label">What happens next</p>
          <p className="mt-1">
            Tell Watermark which room each sensor is in and which camera sees it. From then on, water on a sensor starts a
            recording without you doing anything.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/setup" className="btn">Set up rooms</Link>
          <Link href="/dashboard" className="btn-ghost">Go to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg grid gap-6">
      <div>
        <p className="label">From the Ring app · step 2 of 2</p>
        <h1 className="readout uppercase text-[48px] sm:text-[60px] mt-2">Create your Watermark account</h1>
        <p className="mt-3 text-stencil">
          This is separate from your Ring account. One field: your email becomes your account, with no password to
          remember. Ring shows this address when it confirms the link.
        </p>
      </div>
      <form onSubmit={submit} className="plate p-5 grid gap-3">
        <label className="label" htmlFor="email">Email</label>
        <input
          id="email"
          className="field"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        {email && nonce && <p className="text-[13px] text-stencil">Filled in from your Ring account. Change it if you like.</p>}
        {!nonce && (
          <p className="text-[13px] text-stencil">
            Start from the Ring app to link a real account. Opened directly, this page only works in mock mode.
          </p>
        )}
        {err && (
          <p className="hatch px-3 py-2" role="alert">
            {err}
          </p>
        )}
        <button className="btn justify-center" disabled={busy}>{busy ? "Linking…" : "Create account and link Ring"}</button>
      </form>
    </div>
  );
}

// What went wrong, why it matters, where to fix it (Ring UX guide).
function linkError(e: string): string {
  if (e.includes("expired")) return "This link request is more than 10 minutes old, so Ring will not accept it. Go back to the Ring app and choose Watermark again.";
  if (e.includes("nonce")) return "Ring could not match this page to a pending link. Go back to the Ring app and start the link again.";
  if (e.includes("Failed to fetch")) return "Watermark's server is not answering. Try again in a moment.";
  return e;
}

export default function LinkPage() {
  return (
    <Suspense fallback={null}>
      <LinkInner />
    </Suspense>
  );
}
