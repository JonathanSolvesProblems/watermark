"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, type Device } from "@/lib/api";

// Ring's Account Link URL lands here with ?nonce=...&time=... Ring mandates a
// sign-in or create-account step before the nonce is matched, so the user gives
// an email and that is the account (passwordless, per the Ring UX guide).
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
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="max-w-xl">
        <p className="label text-ok">Account linked</p>
        <h1 className="text-3xl font-bold mt-1">Ring is connected to Watermark</h1>
        <p className="text-muted mt-2 font-sans text-sm">
          Ring has emailed you a confirmation naming this account. These devices are shared with Watermark:
        </p>
        <ul className="mt-4 divide-y divide-line border-y border-line">
          {devices.map((d) => (
            <li key={d.device_id} className="py-2 flex justify-between font-sans text-sm">
              <span>{d.name}</span>
              <span className={d.online ? "text-ok" : "text-warn"}>{d.online ? "online" : "offline"}</span>
            </li>
          ))}
          {devices.length === 0 && <li className="py-2 text-muted text-sm font-sans">No devices yet. Ring may still be syncing.</li>}
        </ul>
        <p className="text-sm text-muted mt-4 font-sans">
          Next: tell Watermark which room each sensor is in, and which camera or route reaches it.
        </p>
        <div className="mt-4 flex gap-3">
          <Link href="/setup" className="btn">Set up rooms and routes</Link>
          <Link href="/dashboard" className="btn-ghost">Go to Dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md">
      <p className="label text-water">Ring Appstore · account link</p>
      <h1 className="text-3xl font-bold mt-1">Create your Watermark account</h1>
      <p className="text-muted mt-2 font-sans text-sm">
        One field. Your email becomes your account; there is no password to remember. Ring will show this address
        when it asks you to confirm the link.
      </p>
      <form onSubmit={submit} className="mt-6 grid gap-3">
        <label className="label text-muted" htmlFor="email">Email</label>
        <input id="email" className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        {!nonce && (
          <p className="text-xs text-muted font-sans">
            No link token in the URL. In mock mode this still works; with a real Ring account, start from the Ring app.
          </p>
        )}
        {err && <p className="text-warn text-sm font-sans">{err}</p>}
        <button className="btn justify-center" disabled={busy}>{busy ? "Linking…" : "Create account and link Ring"}</button>
      </form>
    </div>
  );
}

export default function LinkPage() {
  return (
    <Suspense fallback={null}>
      <LinkInner />
    </Suspense>
  );
}
