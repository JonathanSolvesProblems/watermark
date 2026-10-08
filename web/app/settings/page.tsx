"use client";

import { useEffect, useState } from "react";
import { api, type Account } from "@/lib/api";

export default function Settings() {
  const [acct, setAcct] = useState<Account | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [confirm, setConfirm] = useState("");
  const [prefs, setPrefs] = useState({ chime: true, push: true, email: false });

  useEffect(() => {
    api.account().then(setAcct).catch(() => {});
    try {
      const p = localStorage.getItem("watermark.prefs");
      if (p) setPrefs(JSON.parse(p));
    } catch {}
  }, []);

  function savePrefs(next: typeof prefs) {
    setPrefs(next);
    try {
      localStorage.setItem("watermark.prefs", JSON.stringify(next));
    } catch {}
  }

  async function del() {
    const r = await api.deleteAccount();
    setResult(`Deleted ${Object.entries(r.counts).map(([k, v]) => `${v} ${k}`).join(", ")}. Nothing is kept.`);
    setConfirm("");
  }

  return (
    <div className="grid grid-cols-1 gap-12 max-w-3xl min-w-0">
      <section>
        <p className="label">Settings</p>
        <h1 className="readout uppercase text-[48px] sm:text-[64px] mt-2">Account</h1>
        <dl className="mt-4 plate grid grid-cols-[minmax(0,110px)_minmax(0,1fr)] sm:grid-cols-[150px_minmax(0,1fr)]">
          <Row k="Email" v={acct?.email || "–"} />
          <Row k="Ring link" v={linkLabel(acct)} />
          <Row k="Subscription" v="Managed in the Ring app under My Apps. Watermark cannot change it here." />
        </dl>
      </section>

      <section aria-labelledby="notify-h">
        <h2 id="notify-h" className="label border-b border-seam pb-2 mb-3">Notifications</h2>
        <div className="grid gap-1">
          {([
            ["chime", "Play the Ring Chime when water is detected"],
            ["push", "Send a push notification with the room name"],
            ["email", "Email me the evidence pack when an incident closes"],
          ] as const).map(([k, label]) => (
            <label key={k} className="flex items-center gap-3 min-h-[44px] cursor-pointer">
              <input type="checkbox" className="w-5 h-5 accent-current" checked={prefs[k]} onChange={(e) => savePrefs({ ...prefs, [k]: e.target.checked })} />
              {label}
            </label>
          ))}
        </div>
      </section>

      <section aria-labelledby="delete-h" className="plate hatch p-5">
        <h2 id="delete-h" className="font-display text-[26px] font-bold uppercase">Delete everything</h2>
        <p className="mt-2 text-[15px]">
          Removes every incident, frame, reading, log and pack Watermark holds for this Ring account, including stored
          copies and anything sent to the caption model. Ring keeps its own recordings; to stop Watermark seeing your
          devices, remove it in the Ring app under My Apps. This cannot be undone.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <input className="field max-w-xs" aria-label='Type "delete" to confirm' placeholder='Type "delete"' value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <button className="btn-danger" disabled={confirm !== "delete"} onClick={del}>Delete my data</button>
        </div>
        {result && <p className="mt-3" role="status">{result}</p>}
      </section>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="label px-4 py-3 border-b border-seam">{k}</dt>
      <dd className="px-4 py-3 border-b border-seam break-words min-w-0">{v}</dd>
    </>
  );
}

function linkLabel(acct: Account | null): string {
  if (!acct) return "–";
  if (acct.mode === "playground") return "Ring Developer Playground (no account link needed)";
  if (acct.mode === "mock") return "Mock account";
  return acct.link_status === "completed" ? "Linked" : acct.link_status || "Not linked";
}
