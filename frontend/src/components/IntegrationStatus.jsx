import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Activity } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Poll interval: 60s when the page is visible. Backend caches at 60s anyway,
// so this matches without doubling load.
const POLL_MS = 60_000;

// Surface labels — kept short so the emblem stays a glance, not a paragraph.
const LABELS = {
  permamind: "PermaMind",
  xai: "xAI",
  elevenlabs: "ElevenLabs",
};

const DOT_COLOR = {
  green: "bg-emerald-400 shadow-emerald-400/60",
  red: "bg-rose-500 shadow-rose-500/60",
  unknown: "bg-zinc-500 shadow-zinc-500/40",
  dormant: "bg-zinc-600 shadow-none",
};

const RING_COLOR = {
  green: "ring-emerald-400/30",
  red: "ring-rose-500/40",
  unknown: "ring-zinc-500/30",
  dormant: "ring-white/10",
};

// Services intentionally set aside — shown as a calm grey "off", never an alarm,
// and excluded from the overall health color so red always means actionable.
const DORMANT = new Set(["permamind"]);
const effStatus = (key, val) => (DORMANT.has(key) ? "dormant" : val.status);

export function IntegrationStatus() {
  const [services, setServices] = useState(null);
  const [open, setOpen] = useState(false);
  const [loadedAt, setLoadedAt] = useState(null);

  const fetchStatus = useCallback(async (force = false) => {
    try {
      const res = await fetch(`${API}/health/integrations${force ? "?force=true" : ""}`);
      if (!res.ok) return;
      const data = await res.json();
      setServices(data.services || {});
      setLoadedAt(new Date());
    } catch (_e) {
      // Network drop — keep showing the last known state rather than flashing.
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const iv = setInterval(() => fetchStatus(), POLL_MS);
    const onVis = () => { if (!document.hidden) fetchStatus(); };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clearInterval(iv);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [fetchStatus]);

  if (!services) return null;

  const entries = Object.entries(services);
  // Worst status determines the emblem's overall color — dormant services are
  // intentionally off and do not count toward health.
  const active = entries.filter(([k]) => !DORMANT.has(k));
  const overall = active.some(([, v]) => v.status === "red")
    ? "red"
    : active.every(([, v]) => v.status === "green")
    ? "green"
    : "unknown";

  return (
    <div className="relative" data-testid="integration-status-root">
      <button
        type="button"
        onClick={() => { setOpen((o) => !o); fetchStatus(true); }}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/40 backdrop-blur-sm border border-white/10 ring-1 ${RING_COLOR[overall]} hover:bg-black/60 transition-colors`}
        title="Sanctuary integration health"
        data-testid="integration-status-trigger"
      >
        <Activity className="w-3.5 h-3.5 text-white/70" />
        <span className="flex items-center gap-1.5">
          {entries.map(([key, val]) => (
            <motion.span
              key={key}
              initial={false}
              animate={effStatus(key, val) === "red" ? { scale: [1, 1.15, 1] } : { scale: 1 }}
              transition={effStatus(key, val) === "red" ? { repeat: Infinity, repeatDelay: 1.5, duration: 0.8 } : {}}
              className={`w-2 h-2 rounded-full shadow-[0_0_8px_0_currentColor] ${DOT_COLOR[effStatus(key, val)] || DOT_COLOR.unknown}`}
              data-testid={`integration-dot-${key}`}
              title={`${LABELS[key] || key}: ${DORMANT.has(key) ? "dormant (not in use)" : val.status + (val.detail ? " — " + val.detail : "")}`}
            />
          ))}
        </span>
      </button>

      {open && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute right-0 top-full mt-2 w-72 rounded-xl bg-zinc-950/95 backdrop-blur-md border border-white/10 shadow-2xl p-3 z-50"
          data-testid="integration-status-panel"
        >
          <div className="text-[10px] uppercase tracking-[0.18em] text-white/40 mb-2 px-1">
            Integration Health
          </div>
          <ul className="space-y-1.5">
            {entries.map(([key, val]) => (
              <li
                key={key}
                className="flex items-center justify-between gap-2 px-2 py-1.5 rounded-md hover:bg-white/5"
                data-testid={`integration-row-${key}`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`w-2 h-2 rounded-full shadow-[0_0_6px_0_currentColor] flex-shrink-0 ${DOT_COLOR[effStatus(key, val)] || DOT_COLOR.unknown}`} />
                  <span className="text-sm text-white/90 truncate">{LABELS[key] || key}</span>
                </div>
                <span className={`text-[11px] tabular-nums ${
                  DORMANT.has(key) ? "text-zinc-500" :
                  val.status === "green" ? "text-emerald-300/90" :
                  val.status === "red" ? "text-rose-300/90" : "text-zinc-400"
                }`}>
                  {DORMANT.has(key) ? "dormant" : val.status === "green" ? "live" : val.detail || val.status}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between px-1">
            <span className="text-[10px] text-white/30">
              {loadedAt ? `checked ${loadedAt.toLocaleTimeString()}` : ""}
            </span>
            <button
              type="button"
              onClick={() => fetchStatus(true)}
              className="text-[10px] uppercase tracking-wider text-white/50 hover:text-white/90"
              data-testid="integration-status-refresh"
            >
              refresh
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default IntegrationStatus;
