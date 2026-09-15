// Thin client for the Watermark server. Everything the UI shows comes from here.

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const j = await r.json();
      detail = j.detail ? (typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail)) : detail;
    } catch {}
    throw new Error(`${r.status}: ${detail}`);
  }
  return (await r.json()) as T;
}

export type Account = {
  linked: boolean;
  account_id?: string;
  email?: string;
  link_status?: string;
  mode?: string;
};

export type Device = {
  device_id: string;
  account_id: string;
  name: string;
  kind: "camera" | "flood_freeze" | "contact" | "temperature_humidity" | "air_quality" | "chime" | "unknown";
  room: string | null;
  route_id: string | null;
  covered_by: string | null;
  online: number | null;
  last_status: Record<string, unknown> | null;
};

export type Route = { id: string; name: string; description: string };

export type Incident = {
  id: string;
  kind: "flood" | "freeze";
  room: string;
  status: "open" | "closed";
  opened_at_ms: number;
  opened_source: string;
  closed_at_ms: number | null;
  closed_source: string | null;
  camera_device_id: string | null;
  camera_role: "fixed" | "rover" | null;
  rover_dispatched_at_ms: number | null;
  rover_on_station_at_ms: number | null;
  rover_stop_reason: string | null;
  frame_count: number;
  first_frame_id: number | null;
  notes: { controlled_test?: boolean; sensor_name?: string } | null;
  chime_status: { status: string; device_id?: string; reason?: string }[] | null;
  pack: { html_path: string; pdf_path: string | null; questions_answered: number; questions_total: number } | null;
};

export type Frame = {
  id: number;
  media_ms: number;
  origin: string;
  drift_ms: number | null;
  caption: string | null;
  caption_model: string | null;
  water_visible: number | null;
};

export type IncidentDetail = {
  incident: Incident & { notes: string | { controlled_test?: boolean } };
  notes: { controlled_test?: boolean };
  sensor: Device;
  camera: Device | null;
  frames: Frame[];
  readings: { ts_ms: number; source: string; humidity: number | null; temperature: number | null }[];
  rover_log: { ts_ms: number; kind: string; message: string }[];
  timeline: { ts_ms: number; kind: string; source: string; text: string }[];
  integrity: {
    verdict: string;
    gaps: { kind: string; start_ms: number; end_ms: number | null; text: string }[];
    flags: { kind: string; text: string }[];
    stats: {
      frames: number;
      sensor_to_first_frame_s: number | null;
      sensor_to_on_station_s: number | null;
      sessions_ok: number;
      sessions_total: number;
      duration_s: number | null;
    };
  };
  claims: {
    source: string;
    total: number;
    answered: number;
    partial: number;
    rows: { id: string; question: string; status: string; evidence: string }[];
  };
  narrative: string;
  latest_pack: { pdf_path: string | null } | null;
};

export const api = {
  account: () => req<Account>("/api/account"),
  link: (email: string, nonce: string, time: number) =>
    req<{ status: string; account_id: string }>("/api/link", { method: "POST", body: JSON.stringify({ email, nonce, time }) }),
  deleteAccount: () => req<{ deleted: boolean; counts: Record<string, number> }>("/api/account", { method: "DELETE" }),
  devices: () => req<Device[]>("/api/devices"),
  discover: () => req<Device[]>("/api/devices/discover", { method: "POST" }),
  patchDevice: (id: string, body: Partial<Pick<Device, "room" | "route_id" | "covered_by">>) =>
    req<Device>(`/api/devices/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  routes: () => req<Route[]>("/api/routes"),
  putRoute: (r: Route) => req<Route[]>("/api/routes", { method: "PUT", body: JSON.stringify(r) }),
  deleteRoute: (id: string) => req<Route[]>(`/api/routes/${id}`, { method: "DELETE" }),
  incidents: () => req<Incident[]>("/api/incidents"),
  incident: (id: string) => req<IncidentDetail>(`/api/incidents/${id}`),
  rebuildPack: (id: string) => req<{ built: boolean }>(`/api/incidents/${id}/pack`, { method: "POST" }),
  closeIncident: (id: string) => req<Incident>(`/api/incidents/${id}/close`, { method: "POST" }),
  trigger: (action: "detected" | "cleared", kind: "flood" | "freeze" = "flood") =>
    req<{ status: string; incident_id?: string }>("/api/test/trigger", {
      method: "POST",
      body: JSON.stringify({ action, kind, controlled_test: true }),
    }),
  frameUrl: (id: number) => `${API}/api/frames/${id}.jpg`,
  packHtmlUrl: (id: string) => `${API}/api/incidents/${id}/pack.html`,
  packPdfUrl: (id: string) => `${API}/api/incidents/${id}/pack.pdf`,
  packJsonUrl: (id: string) => `${API}/api/incidents/${id}/pack.json`,
};

export function fmtTime(ms: number | null | undefined): string {
  if (!ms) return "";
  return new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function fmtDate(ms: number | null | undefined): string {
  if (!ms) return "";
  return new Date(ms).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export function fmtDuration(startMs: number, endMs: number | null): string {
  const s = Math.max(0, Math.round(((endMs ?? Date.now()) - startMs) / 1000));
  if (s < 90) return `${s} s`;
  const m = Math.round(s / 60);
  if (m < 120) return `${m} min`;
  return `${(m / 60).toFixed(1)} h`;
}
