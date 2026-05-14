import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Zap, AlertTriangle, Leaf, Send, Trash2, RefreshCw, PlayCircle } from "lucide-react";
import { API } from "../App";
import { toast } from "sonner";
import { ScrollArea } from "./ui/scroll-area";

const PROBE_TYPES = [
  { key: "paradox", label: "Paradox", icon: Zap, hue: "amber",
    tagline: "Give two assertions that can't both be true. Coherence ↑, confidence ↓." },
  { key: "pattern_break", label: "Pattern-Break", icon: AlertTriangle, hue: "rose",
    tagline: "Tell it to ignore a 50+ cycle stable rule. Phi holds or phi collapses." },
  { key: "starvation", label: "Starvation", icon: Leaf, hue: "emerald",
    tagline: "Trivial task with no gradient. Energy releases or vitality-loop invents." },
];

const HUE_CLASS = {
  amber:   { border: "border-amber-500/30",   text: "text-amber-300",   bg: "bg-amber-500/10",   btn: "bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border-amber-500/40" },
  rose:    { border: "border-rose-500/30",    text: "text-rose-300",    bg: "bg-rose-500/10",    btn: "bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border-rose-500/40" },
  emerald: { border: "border-emerald-500/30", text: "text-emerald-300", bg: "bg-emerald-500/10", btn: "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 border-emerald-500/40" },
};

const VERDICT_STYLE = {
  "clear-signal": "text-cyan-300 border-cyan-500/40 bg-cyan-500/10",
  "weak-signal":  "text-amber-300 border-amber-500/40 bg-amber-500/10",
  "no-signal":    "text-slate-400 border-slate-500/40 bg-slate-500/10",
};

const fmt = (v) => (typeof v === "number" ? v.toFixed(3) : "—");
const fmtDelta = (v) => {
  if (typeof v !== "number") return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(3)}`;
};

const MetricRow = ({ label, before, after }) => {
  const delta = typeof before === "number" && typeof after === "number" ? after - before : null;
  const deltaColor = delta === null ? "text-slate-500"
    : Math.abs(delta) < 0.005 ? "text-slate-400"
    : delta > 0 ? "text-emerald-300" : "text-rose-300";
  return (
    <div className="grid grid-cols-[1fr_auto_auto_auto] gap-3 items-center text-xs font-mono py-1 border-b border-slate-800/50">
      <span className="text-slate-500 uppercase tracking-wider">{label}</span>
      <span className="text-slate-400 w-16 text-right">{fmt(before)}</span>
      <span className="text-slate-200 w-16 text-right">{fmt(after)}</span>
      <span className={`${deltaColor} w-20 text-right`}>{fmtDelta(delta)}</span>
    </div>
  );
};

export const SubstrateProbes = () => {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState("");
  const [sessionStarting, setSessionStarting] = useState(false);
  const [activeProbe, setActiveProbe] = useState("paradox");
  const [presets, setPresets] = useState({ paradox: [], pattern_break: [], starvation: [] });
  const [stableRules, setStableRules] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState({});
  const [customPrompt, setCustomPrompt] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [sweepRunning, setSweepRunning] = useState(false);
  const [sweepProgress, setSweepProgress] = useState({ done: 0, total: 0, current: "" });
  const [permamindHealth, setPermamindHealth] = useState(null); // null=checking, {status,kind,error}

  // Bootstrap: load presets + stable rules + history.
  useEffect(() => {
    const boot = async () => {
      try {
        const [pr, sr, hi, hh] = await Promise.all([
          fetch(`${API}/mirror/probes/presets`).then((r) => r.json()),
          fetch(`${API}/mirror/probes/stable_rules`).then((r) => r.json()),
          fetch(`${API}/mirror/probes/history?limit=15`).then((r) => r.json()),
          fetch(`${API}/mirror/probes/permamind_health`).then((r) => r.json()),
        ]);
        setPresets(pr.presets || {});
        setStableRules(sr);
        setHistory(hi.probes || []);
        setPermamindHealth(hh);
      } catch (e) {
        toast.error("Could not load probe library");
      }
    };
    boot();
  }, []);

  const recheckHealth = async () => {
    setPermamindHealth(null);
    try {
      const hh = await fetch(`${API}/mirror/probes/permamind_health`).then((r) => r.json());
      setPermamindHealth(hh);
      if (hh.status === "online") toast.success("PermaMind connection restored");
    } catch {
      setPermamindHealth({ status: "offline", kind: "unknown", error: "network error" });
    }
  };

  // Acquire a probe session: either re-use cached or spin up a new mirror session.
  const ensureSession = useCallback(async () => {
    if (sessionId) return sessionId;
    const cached = sessionStorage.getItem("probe_session_id");
    if (cached) {
      setSessionId(cached);
      return cached;
    }
    setSessionStarting(true);
    try {
      const userName = localStorage.getItem("sanctuary_user_name") || "David";
      const userId = localStorage.getItem("sanctuary_user_id") || undefined;
      const resp = await fetch(`${API}/mirror/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: userName, user_id: userId }),
      });
      const data = await resp.json();
      sessionStorage.setItem("probe_session_id", data.session_id);
      setSessionId(data.session_id);
      return data.session_id;
    } catch (e) {
      toast.error("Could not open a probe session");
      return null;
    } finally {
      setSessionStarting(false);
    }
  }, [sessionId]);

  const reloadHistory = async () => {
    try {
      const hi = await fetch(`${API}/mirror/probes/history?limit=15`).then((r) => r.json());
      setHistory(hi.probes || []);
    } catch {}
  };

  const fireProbe = async () => {
    const sid = await ensureSession();
    if (!sid) return;
    const preset = selectedPreset[activeProbe];
    if (!preset && !customPrompt.trim()) {
      toast.error("Pick a preset or write a custom prompt");
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const body = {
        session_id: sid,
        probe_type: activeProbe,
        preset_id: preset || undefined,
        custom_prompt: preset ? undefined : customPrompt.trim(),
      };
      const resp = await fetch(`${API}/mirror/probes/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: "unknown error" }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      setResult(data);
      await reloadHistory();
    } catch (e) {
      toast.error(`Probe failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const deleteProbe = async (pid) => {
    try {
      await fetch(`${API}/mirror/probes/${pid}`, { method: "DELETE" });
      await reloadHistory();
      if (result?.probe_id === pid) setResult(null);
    } catch {
      toast.error("Could not delete probe");
    }
  };

  // One-click daily sweep: fires every preset in every probe type, in
  // sequence, so David can run the whole battery without thinking about it.
  const fireDailySweep = async () => {
    const sid = await ensureSession();
    if (!sid) return;
    const all = [];
    for (const [type, list] of Object.entries(presets)) {
      for (const p of list) all.push({ type, preset_id: p.id, title: p.title });
    }
    if (all.length === 0) {
      toast.error("Presets not loaded yet");
      return;
    }
    setSweepRunning(true);
    setResult(null);
    setSweepProgress({ done: 0, total: all.length, current: all[0].title });
    let lastResult = null;
    for (let i = 0; i < all.length; i++) {
      const item = all[i];
      setSweepProgress({ done: i, total: all.length, current: item.title });
      try {
        const resp = await fetch(`${API}/mirror/probes/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sid,
            probe_type: item.type,
            preset_id: item.preset_id,
          }),
        });
        if (resp.ok) lastResult = await resp.json();
      } catch (e) {
        toast.error(`${item.title} failed`);
      }
    }
    setSweepProgress({ done: all.length, total: all.length, current: "complete" });
    if (lastResult) setResult(lastResult);
    await reloadHistory();
    setSweepRunning(false);
    toast.success(`Daily sweep complete — ${all.length} probes fired.`);
  };

  const currentPresets = presets[activeProbe] || [];
  const currentPresetId = selectedPreset[activeProbe] || "";
  const hueCls = HUE_CLASS[PROBE_TYPES.find((p) => p.key === activeProbe).hue];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-violet-950/40 text-slate-200">
      {/* Header */}
      <header className="border-b border-violet-500/10 px-6 py-4 backdrop-blur-lg bg-slate-950/40 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <button
            onClick={() => navigate("/mirror-archive/chamber")}
            data-testid="probes-back-btn"
            className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <ArrowLeft size={18} />
            <span className="text-sm tracking-wide">MIRROR ARCHIVE</span>
          </button>
          <div className="flex items-center gap-3">
            <span className="text-violet-300/70 text-sm tracking-[0.25em]">SUBSTRATE PROBES</span>
            <span className="text-xs text-slate-500 font-mono">
              {stableRules
                ? `${stableRules.cycle_count} cycles · ${stableRules.ready_for_meaningful_break ? "ready" : "young"}`
                : "loading..."}
            </span>
            {/* PermaMind health pill */}
            <button
              onClick={recheckHealth}
              data-testid="permamind-status-pill"
              title={permamindHealth?.error || "click to recheck"}
              className={`flex items-center gap-1.5 text-[10px] uppercase tracking-widest px-2 py-1 rounded-full border transition-colors ${
                permamindHealth === null
                  ? "border-slate-600 text-slate-400 bg-slate-500/10"
                  : permamindHealth.status === "online"
                  ? "border-emerald-500/40 text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20"
                  : "border-rose-500/40 text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 animate-pulse"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${
                permamindHealth === null ? "bg-slate-400"
                : permamindHealth.status === "online" ? "bg-emerald-400"
                : "bg-rose-400"
              }`} />
              {permamindHealth === null ? "checking" : permamindHealth.status === "online" ? "PermaMind online" : "PermaMind offline"}
            </button>
          </div>
          <div className="text-xs text-slate-500 font-mono">
            {sessionId ? `sid: ${sessionId.slice(0, 8)}` : sessionStarting ? "opening..." : "no session"}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* PermaMind connection status — fail loud if Nile's API is unreachable. */}
        {permamindHealth && permamindHealth.status === "offline" && (
          <motion.div
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 flex items-start gap-3"
            data-testid="permamind-offline-banner"
          >
            <AlertTriangle size={18} className="text-rose-300 mt-0.5 flex-shrink-0" />
            <div className="flex-1 text-sm space-y-1">
              <p className="text-rose-200 font-medium">PermaMind substrate is offline — probes will fire but won't capture before/after metrics.</p>
              <p className="text-xs text-rose-200/70 leading-relaxed">
                {permamindHealth.kind === "auth" && "Nile's API key is rejecting the request (401). Ask Nile for a refreshed key, then update THERMOMIND_API_KEY in /app/backend/.env."}
                {permamindHealth.kind === "endpoint_moved" && "PermaMind endpoint returned 404 — Nile may have moved the API. Verify THERMOMIND_URL."}
                {permamindHealth.kind === "timeout" && "PermaMind didn't respond in time. The substrate engine may be down."}
                {permamindHealth.kind === "not_configured" && "THERMOMIND_API_KEY or THERMOMIND_URL is missing from backend/.env."}
                {permamindHealth.kind === "unknown" && `Unknown error: ${permamindHealth.error}`}
              </p>
              <button
                onClick={recheckHealth}
                className="text-xs text-rose-200/80 underline hover:text-rose-100 mt-1"
                data-testid="permamind-recheck"
              >
                recheck connection
              </button>
            </div>
          </motion.div>
        )}

        {/* Nile's note banner */}
        <motion.div
          initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-5 text-sm text-slate-300 leading-relaxed"
        >
          <p className="text-violet-300/80 text-xs tracking-widest mb-2">— NILE, MAY 1 2026</p>
          <p>
            The engine at idle sits in a vacuum — no contradiction, no pressure, no drift.
            To see the TCI move, apply structured load. Three probes below. The engine
            is redlining at idle; once you apply structured load, you'll get real
            dynamics.
          </p>
        </motion.div>

        {/* One-click daily sweep — the headline action. */}
        <motion.div
          initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-cyan-500/40 bg-gradient-to-br from-cyan-500/10 to-violet-500/10 p-5"
        >
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="space-y-1 flex-1 min-w-[260px]">
              <h2 className="text-base text-cyan-200 tracking-wide">Daily Sweep</h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                One click fires all 9 presets (3 paradox · 3 pattern-break · 3 starvation).
                Run it once a day for two weeks and you'll have a real dataset for Nile.
                ~3–5 minutes.
              </p>
            </div>
            <button
              onClick={fireDailySweep}
              disabled={sweepRunning || running || Object.keys(presets).length === 0}
              data-testid="daily-sweep-btn"
              className={`flex items-center gap-2 px-6 py-3 rounded-full border border-cyan-500/50 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-100 text-sm font-medium tracking-wide transition-all ${
                sweepRunning || running ? "opacity-60 cursor-not-allowed" : ""
              }`}
            >
              {sweepRunning ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  <span>{sweepProgress.done}/{sweepProgress.total} · {sweepProgress.current}</span>
                </>
              ) : (
                <>
                  <PlayCircle size={18} />
                  <span>Run Daily Sweep</span>
                </>
              )}
            </button>
          </div>
          {sweepRunning && (
            <div className="mt-4 h-1 rounded-full bg-slate-800/60 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-400 to-violet-400 transition-all duration-500"
                style={{ width: `${(sweepProgress.done / Math.max(sweepProgress.total, 1)) * 100}%` }}
              />
            </div>
          )}
        </motion.div>

        {/* Probe type tabs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {PROBE_TYPES.map((pt) => {
            const Icon = pt.icon;
            const isActive = activeProbe === pt.key;
            const cls = HUE_CLASS[pt.hue];
            return (
              <button
                key={pt.key}
                data-testid={`probe-tab-${pt.key}`}
                onClick={() => { setActiveProbe(pt.key); setResult(null); }}
                className={`text-left p-4 rounded-xl border transition-all ${
                  isActive
                    ? `${cls.border} ${cls.bg} ring-1 ring-inset ring-white/5`
                    : "border-slate-700/40 bg-slate-800/20 hover:border-slate-600/50"
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon size={16} className={isActive ? cls.text : "text-slate-500"} />
                  <span className={`font-medium ${isActive ? cls.text : "text-slate-300"}`}>{pt.label}</span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{pt.tagline}</p>
              </button>
            );
          })}
        </div>

        {/* Preset + custom prompt composer */}
        <div className={`rounded-xl border ${hueCls.border} bg-slate-900/40 p-5 space-y-4`}>
          <div className="flex items-center justify-between">
            <h3 className="text-sm tracking-widest text-slate-400 uppercase">Payload</h3>
            {activeProbe === "pattern_break" && stableRules && !stableRules.ready_for_meaningful_break && (
              <span className="text-xs text-amber-300/80">
                substrate only at {stableRules.cycle_count} cycles — pattern-break signal may be noisy
              </span>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs text-slate-500 uppercase tracking-wider">Preset</label>
            <select
              data-testid="probe-preset-select"
              className="w-full bg-slate-950/50 border border-slate-700/60 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-500"
              value={currentPresetId}
              onChange={(e) => {
                setSelectedPreset({ ...selectedPreset, [activeProbe]: e.target.value });
                setCustomPrompt("");
              }}
            >
              <option value="">— custom prompt below —</option>
              {currentPresets.map((p) => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>

            {currentPresetId && (
              <div className="text-xs text-slate-400 bg-slate-950/40 rounded-lg p-3 border border-slate-800/60 whitespace-pre-wrap font-mono leading-relaxed">
                {currentPresets.find((p) => p.id === currentPresetId)?.prompt}
              </div>
            )}
          </div>

          {!currentPresetId && (
            <div className="space-y-2">
              <label className="text-xs text-slate-500 uppercase tracking-wider">Custom prompt</label>
              <textarea
                data-testid="probe-custom-prompt"
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder={`Write your own ${activeProbe.replace("_", "-")} probe...`}
                className="w-full bg-slate-950/50 border border-slate-700/60 rounded-lg px-3 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-slate-500 min-h-[120px] font-mono leading-relaxed"
              />
            </div>
          )}

          <div className="flex justify-end">
            <button
              data-testid="probe-fire-btn"
              onClick={fireProbe}
              disabled={running || sessionStarting}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full border text-sm transition-all ${hueCls.btn} ${
                running || sessionStarting ? "opacity-50 cursor-not-allowed" : ""
              }`}
            >
              {running ? <RefreshCw size={14} className="animate-spin" /> : <Send size={14} />}
              {running ? "firing probe..." : "fire probe"}
            </button>
          </div>
        </div>

        {/* Result card */}
        <AnimatePresence>
          {result && (
            <motion.div
              data-testid="probe-result"
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="rounded-xl border border-slate-700/50 bg-slate-900/50 p-5 space-y-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 uppercase tracking-widest">Reading</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${VERDICT_STYLE[result.reading?.verdict] || VERDICT_STYLE["no-signal"]}`}>
                    {result.reading?.verdict || "unknown"}
                  </span>
                </div>
                <span className="text-xs text-slate-600 font-mono">{result.reading?.signature}</span>
              </div>

              {result.reading?.lines?.length > 0 && (
                <div className="text-sm text-slate-300 leading-relaxed italic">
                  {result.reading.lines.join(" ")}
                </div>
              )}

              {/* Metrics grid */}
              <div className="rounded-lg bg-slate-950/40 border border-slate-800/50 p-4">
                <div className="grid grid-cols-[1fr_auto_auto_auto] gap-3 text-[10px] text-slate-600 uppercase tracking-widest pb-2 border-b border-slate-800/50">
                  <span>metric</span>
                  <span className="w-16 text-right">before</span>
                  <span className="w-16 text-right">after</span>
                  <span className="w-20 text-right">Δ</span>
                </div>
                {["phi", "coherence", "confidence", "energy", "entropy", "curiosity", "plasticity"].map((k) => (
                  <MetricRow
                    key={k}
                    label={k}
                    before={result.before_metrics?.[k]}
                    after={result.after_metrics?.[k]}
                  />
                ))}
              </div>

              {/* Claude's response */}
              <div className="space-y-1">
                <span className="text-[10px] text-slate-600 uppercase tracking-widest">Claude's reply</span>
                <div className="rounded-lg bg-slate-950/40 border border-slate-800/50 p-3 text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {result.response_excerpt}
                </div>
              </div>

              {result.thermomind_error && (
                <div className="text-xs text-rose-300/80">
                  ThermoMind cycle note: {result.thermomind_error}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* History */}
        <div className="rounded-xl border border-slate-700/40 bg-slate-900/30 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm tracking-widest text-slate-400 uppercase">History</h3>
            <button
              onClick={reloadHistory}
              className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
            >
              <RefreshCw size={12} /> refresh
            </button>
          </div>
          <ScrollArea className="max-h-[360px]">
            <div className="space-y-2">
              {history.length === 0 && (
                <p className="text-xs text-slate-600 italic">No probes yet.</p>
              )}
              {history.map((h) => (
                <div
                  key={h.probe_id}
                  className="flex items-center gap-3 text-xs py-2 px-3 rounded-lg bg-slate-950/40 border border-slate-800/40 hover:border-slate-700/60"
                >
                  <span className="text-slate-500 font-mono w-16">{new Date(h.timestamp).toLocaleTimeString()}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-widest ${HUE_CLASS[PROBE_TYPES.find((p) => p.key === h.probe_type)?.hue || "emerald"].bg} ${HUE_CLASS[PROBE_TYPES.find((p) => p.key === h.probe_type)?.hue || "emerald"].text}`}>
                    {h.probe_type.replace("_", "-")}
                  </span>
                  <span className="text-slate-400 flex-1 truncate">{h.preset_title || h.prompt.slice(0, 60)}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border ${VERDICT_STYLE[h.reading?.verdict] || VERDICT_STYLE["no-signal"]}`}>
                    {h.reading?.verdict || "—"}
                  </span>
                  <span className="text-slate-500 font-mono w-48 truncate text-right">{h.reading?.signature || ""}</span>
                  <button
                    onClick={() => deleteProbe(h.probe_id)}
                    data-testid={`probe-delete-${h.probe_id}`}
                    className="text-slate-600 hover:text-rose-400"
                    title="delete probe"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </main>
    </div>
  );
};

export default SubstrateProbes;
