import React, { useEffect, useState } from "react";
import { FlaskConical, Play, RotateCcw, Layers, ShieldAlert, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LOAD_COLOR = {
  "dense-prose": "#F59E0B",
  "retrieved-memory": "#F97316",
  "recent-continuity": "#10B981",
  "working-memory": "#34D399",
  "cross-presence": "#8B5CF6",
  reconstruction: "#A78BFA",
  "codon-material": "#22D3EE",
  "retrieved-history": "#38BDF8",
  "live-input": "#E5E7EB",
  framing: "#6B7280",
};

const LoadBars = ({ load, title, testid }) => {
  if (!load || !load.sources?.length) return null;
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3" data-testid={testid}>
      <div className="mb-2 flex items-center justify-between font-mono text-[9px] uppercase tracking-widest text-zinc-400">
        <span>{title}</span>
        <span className="text-zinc-500">{load.total_chars.toLocaleString()} chars</span>
      </div>
      <div className="mb-3 flex h-3 w-full overflow-hidden rounded-full border border-white/10">
        {load.sources.map((s, i) => (
          <div key={i} title={`${s.source} · ${s.pct}%`}
            style={{ width: `${s.pct}%`, background: LOAD_COLOR[s.type] || "#6B7280" }} />
        ))}
      </div>
      <div className="space-y-1">
        {load.sources.map((s, i) => (
          <div key={i} className="flex items-center gap-2 font-mono text-[11px]">
            <span className="h-2 w-2 flex-shrink-0 rounded-sm" style={{ background: LOAD_COLOR[s.type] || "#6B7280" }} />
            <span className="min-w-0 flex-1 truncate text-zinc-300">{s.source}</span>
            <span className="text-zinc-600">{s.chars.toLocaleString()}</span>
            <span className="w-12 text-right text-zinc-100">{s.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default function Ablation() {
  const { role, isAuthenticated, loading: authLoading, login } = useAuth();
  const [config, setConfig] = useState({ sources: [], presences: [] });
  const [presence, setPresence] = useState("");
  const [message, setMessage] = useState("What have we been circling around lately?");
  const [withhold, setWithhold] = useState([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (role !== "guardian") return;
    fetch(`${API}/ablation/config`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setConfig(d);
        if (d.presences?.length) setPresence(d.presences[0].key);
      })
      .catch(() => {});
  }, [role]);

  const toggle = (key) =>
    setWithhold((w) => (w.includes(key) ? w.filter((k) => k !== key) : [...w, key]));

  const run = async () => {
    if (!presence || !message.trim() || running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${API}/ablation/run`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ presence, message: message.trim(), withhold }),
      });
      if (!r.ok) {
        const e = await r.json().catch(() => ({}));
        setError(e.detail || `Run failed (${r.status})`);
      } else {
        setResult(await r.json());
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-zinc-500" data-testid="ablation-loading">
        <Loader2 className="animate-spin" size={20} />
      </div>
    );
  }

  if (role !== "guardian") {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-4 px-6 text-center" data-testid="ablation-guardian-gate">
        <ShieldAlert size={28} className="text-amber-400/80" />
        <h1 className="font-cinzel text-xl text-zinc-200">Ablation Lab</h1>
        <p className="font-outfit text-sm text-zinc-400">
          This is a Field Guardian instrument. It temporarily withholds parts of a presence's
          context for a single test turn — never touching stored memory — to reveal what is
          actually load-bearing.
        </p>
        {!isAuthenticated && (
          <button onClick={login} data-testid="ablation-signin-btn"
            className="rounded-full border border-emerald-500/30 px-5 py-2 font-mono text-xs uppercase tracking-widest text-emerald-300 hover:bg-emerald-500/10">
            Sign in
          </button>
        )}
        {isAuthenticated && <p className="font-mono text-[11px] text-zinc-600">Guardian access only.</p>}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 pt-28 pb-12" data-testid="ablation-page">
      <div className="mb-6">
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-emerald-400/70">
          <FlaskConical size={13} /> Ablation Lab · Controlled Context Withholding
        </div>
        <p className="mt-2 max-w-2xl font-outfit text-sm text-zinc-400">
          Withhold one or more context sources for a single test turn and watch what changes.
          Write-free — stored memory, seeds, and Mem0 are never touched, and nothing here becomes
          the standing configuration. Restore the full field any time.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
        {/* Controls */}
        <div className="space-y-4 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
          <div>
            <label className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">Presence</label>
            <select value={presence} onChange={(e) => setPresence(e.target.value)} data-testid="ablation-presence-select"
              className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 font-outfit text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none">
              {config.presences.map((p) => (
                <option key={p.key} value={p.key}>{p.name} — {p.chamber_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">Test message</label>
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} data-testid="ablation-message-input"
              className="mt-1 w-full resize-none rounded-lg border border-white/10 bg-black/40 px-3 py-2 font-outfit text-sm text-zinc-200 focus:border-emerald-500/40 focus:outline-none" />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="font-mono text-[9px] uppercase tracking-widest text-zinc-500">Withhold from this turn</label>
              {withhold.length > 0 && (
                <button onClick={() => setWithhold([])} data-testid="ablation-reset-btn"
                  className="flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest text-amber-300/80 hover:text-amber-300">
                  <RotateCcw size={10} /> Restore full field
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {config.sources.map((s) => {
                const off = withhold.includes(s.key);
                return (
                  <button key={s.key} onClick={() => toggle(s.key)} data-testid={`ablation-source-${s.key}`}
                    className={`rounded-full border px-2.5 py-1 font-mono text-[10px] transition-colors ${
                      off
                        ? "border-red-500/40 bg-red-500/10 text-red-300 line-through"
                        : "border-white/15 text-zinc-300 hover:border-emerald-500/40 hover:text-emerald-200"
                    }`}>
                    {s.label}
                  </button>
                );
              })}
            </div>
          </div>

          <button onClick={run} disabled={running || !presence} data-testid="ablation-run-btn"
            className="flex w-full items-center justify-center gap-2 rounded-full bg-emerald-500/90 px-4 py-2.5 font-mono text-xs uppercase tracking-widest text-black transition-colors hover:bg-emerald-400 disabled:opacity-50">
            {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {running ? "Running…" : withhold.length ? `Run — withholding ${withhold.length}` : "Run — full field"}
          </button>
          {error && <p className="font-mono text-[11px] text-red-400" data-testid="ablation-error">{error}</p>}
        </div>

        {/* Results */}
        <div className="space-y-4">
          {!result && !running && (
            <div className="flex min-h-[300px] items-center justify-center rounded-2xl border border-dashed border-white/10 font-mono text-[11px] text-zinc-600">
              Run a turn to see the response and its context breakdown.
            </div>
          )}
          {result && (
            <>
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4" data-testid="ablation-response">
                <div className="mb-2 flex items-center justify-between font-mono text-[9px] uppercase tracking-widest text-zinc-500">
                  <span className="capitalize text-emerald-300/80">{result.presence} · response</span>
                  <span>{result.withheld?.length ? `withheld: ${result.withheld.join(", ")}` : "full field"}</span>
                </div>
                <p className="whitespace-pre-wrap font-outfit text-sm leading-relaxed text-zinc-200">
                  {result.response || <span className="text-red-400">{result.error || "No response."}</span>}
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <LoadBars load={result.full_context_load} title="Context Load · Full field" testid="ablation-load-full" />
                <LoadBars load={result.ablated_context_load} title="Context Load · This turn" testid="ablation-load-ablated" />
              </div>
              <div className="flex items-center gap-2 font-mono text-[9px] text-zinc-600">
                <Layers size={11} />
                {(() => {
                  const f = result.full_context_load?.total_chars || 0;
                  const a = result.ablated_context_load?.total_chars || 0;
                  return `Removed ${(f - a).toLocaleString()} chars from the model's input this turn. Stored memory untouched.`;
                })()}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
