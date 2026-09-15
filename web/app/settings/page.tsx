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
    try { localStorage.setItem("watermark.prefs", JSON.stringify(next)); } catch {}
  }

  async function del() {
    const r = await api.deleteAccount();
    setResult(`Deleted: ${Object.entries(r.counts).map(([k, v]) => `${v} ${k}`).join(", ")}. Nothing is retained.`);
    setConfirm("");
  }

  return (
    <div className="grid gap-10 max-w-2xl">
      <section>
        <p className="label text-water">Settings</p>
        <h1 className="text-3xl font-bold mt-1">Account</h1>
        <dl className="mt-3 grid grid-cols-[140px_1fr] gap-y-1 text-sm font-sans">
          <dt className="text-muted">Email</dt><dd>{acct?.email || "–"}</dd>
          <dt className="text-muted">Ring link</dt><dd>{acct?.link_status || "–"}</dd>
          <dt className="text-muted">Subscription</dt><dd>Managed in the Ring app under My Apps. Watermark cannot change it here.</dd>
        </dl>
      </section>

      <section>
        <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold">Notifications</h2></div>
        <div className="grid gap-2 font-sans text-sm">
          {([["chime", "Play the Ring Chime when water is detected"], ["push", "Push notification with the room name"], ["email", "Email me the pack when an incident closes"]] as const).map(([k, label]) => (
            <label key={k} className="flex items-center gap-3">
              <input type="checkbox" checked={prefs[k]} onChange={(e) => savePrefs({ ...prefs, [k]: e.target.checked })} />
              {label}
            </label>
          ))}
        </div>
      </section>

      <section>
        <div className="waterline pb-2 mb-3"><h2 className="text-xl font-bold text-warn">Delete everything</h2></div>
        <p className="text-sm font-sans text-muted">
          Removes every incident, frame, reading, log and pack Watermark holds for this Ring account, including copies
          in storage and anything sent to the caption model. Ring itself keeps its own recordings; unlink the app in the
          Ring app to revoke access. This cannot be undone.
        </p>
        <div className="mt-3 flex gap-2">
          <input className="field max-w-xs" placeholder='type "delete"' value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <button className="btn-danger" disabled={confirm !== "delete"} onClick={del}>Delete my data</button>
        </div>
        {result && <p className="mt-3 text-sm font-sans text-ok">{result}</p>}
      </section>
    </div>
  );
}
