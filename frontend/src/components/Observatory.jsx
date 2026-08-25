import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceArea, ReferenceLine, CartesianGrid,
} from "recharts";
import { API } from "../App";
import {
  Activity, ArrowLeft, Hash, Layers, Radio, X, Clock, Cpu,
  ArrowUpRight, ArrowDownRight, Minus, MoveRight, Circle,
} from "lucide-react";

const POLL_MS = 4000;

// ── Dual-signal language ──────────────────────────────────────────────
const EMERALD = "#10B981";
const AMBER = "#F59E0B";
const SACRED = "Sacred Pause";

const zoneAngle = { Expansion: 40, Development: 160, Return: 280, "Sacred Pause": 340 };

const isSacred = (zone) => zone === SACRED;
const zoneTint = (zone) => (isSacred(zone) ? AMBER : EMERALD);

// Relational-move (Micro-Layer 6) presentation
const MOVE_META = {
  opening: { label: "OPENING", color: EMERALD, Icon: ArrowUpRight },
  deepening: { label: "DEEPENING", color: EMERALD, Icon: MoveRight },
  holding: { label: "HOLDING", color: AMBER, Icon: Minus },
  returning: { label: "RETURNING", color: AMBER, Icon: ArrowDownRight },
  closing: { label: "CLOSING", color: AMBER, Icon: Circle },
  baseline: { label: "BASELINE", color: "#6B7280", Icon: Minus },
  "no-reading": { label: "NO READING", color: "#4B5563", Icon: Minus },
};

const branchColor = (branch) => {
  if (!branch) return "text-zinc-400";
  if (branch.startsWith("keyword")) return "text-emerald-300";
  if (branch.startsWith("phase")) return "text-sky-300";
  return "text-amber-300";
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch { return iso; }
};

// ── Radial HUD gauge ─────────────────────────────────────────────────
const polar = (cx, cy, r, deg) => {
  const a = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
};
const arcPath = (cx, cy, r, start, end) => {
  const s = polar(cx, cy, r, end);
  const e = polar(cx, cy, r, start);
  const large = end - start <= 180 ? 0 : 1;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 0 ${e.x} ${e.y}`;
};

const RadialGauge = ({ position, zone, prefersReduced }) => {
  const cx = 130, cy = 130, R = 104;
  const has = position != null;
  const pos = has ? position : 0;
  const accent = zoneTint(zone);
  const ticks = Array.from({ length: 36 }, (_, i) => i * 10);

  return (
    <div className="relative flex items-center justify-center" data-testid="radial-hud-gauge">
      <svg viewBox="0 0 260 260" className="w-full max-w-[300px]">
        <defs>
          <radialGradient id="hudCore" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={accent} stopOpacity="0.18" />
            <stop offset="70%" stopColor={accent} stopOpacity="0" />
          </radialGradient>
          <filter id="hudGlow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>

        {/* rotating reticle */}
        <motion.g
          style={{ originX: "130px", originY: "130px" }}
          animate={prefersReduced ? {} : { rotate: 360 }}
          transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
        >
          <circle cx={cx} cy={cy} r={R + 14} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="2 8" />
        </motion.g>

        <circle cx={cx} cy={cy} r={R + 6} fill="url(#hudCore)" />
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />

        {/* tick rim */}
        {ticks.map((t) => {
          const cardinal = t % 90 === 0;
          const p1 = polar(cx, cy, R, t);
          const p2 = polar(cx, cy, R - (cardinal ? 12 : 6), t);
          const inSacred = t >= 320 || t === 0;
          return (
            <line key={t} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              stroke={inSacred ? AMBER : "rgba(255,255,255,0.25)"}
              strokeOpacity={cardinal ? 0.9 : 0.5} strokeWidth={cardinal ? 1.5 : 1} />
          );
        })}

        {/* sacred-pause zone arc */}
        <path d={arcPath(cx, cy, R - 18, 320, 360)} fill="none" stroke={AMBER} strokeOpacity="0.55" strokeWidth="3" strokeLinecap="round" />

        {/* active sweep */}
        {has && pos > 0 && (
          <path d={arcPath(cx, cy, R - 18, 0.001, Math.max(pos, 0.5))} fill="none"
            stroke={accent} strokeWidth="4" strokeLinecap="round" filter="url(#hudGlow)" />
        )}

        {/* needle */}
        {has && (() => {
          const tip = polar(cx, cy, R - 22, pos);
          return <><line x1={cx} y1={cy} x2={tip.x} y2={tip.y} stroke={accent} strokeWidth="2" filter="url(#hudGlow)" />
            <circle cx={tip.x} cy={tip.y} r="4" fill={accent} filter="url(#hudGlow)" /></>;
        })()}
        <circle cx={cx} cy={cy} r="5" fill="#0A0C12" stroke={accent} strokeWidth="1.5" />

        {/* cardinal labels */}
        {[0, 90, 180, 270].map((d) => {
          const lp = polar(cx, cy, R - 30, d);
          return <text key={d} x={lp.x} y={lp.y + 3} textAnchor="middle"
            className="font-mono" fontSize="8" fill="rgba(255,255,255,0.35)">{d}°</text>;
        })}
      </svg>

      {/* center readout */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-cinzel tracking-tight" style={{ color: accent, fontSize: "2.6rem", textShadow: `0 0 22px ${accent}55` }}
          data-testid="radial-hud-value">
          {has ? `${Math.round(position)}°` : "—"}
        </div>
        <div className="mt-1 rounded-full border px-3 py-0.5 font-mono text-[10px] uppercase tracking-[0.25em]"
          style={{ color: accent, borderColor: `${accent}55`, background: `${accent}12` }}
          data-testid="radial-hud-zone-badge">
          {zone || "no reading"}
        </div>
      </div>
    </div>
  );
};

// ── Trend chart ──────────────────────────────────────────────────────
const TrendTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  if (d.spiral_position == null) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-[#0A0C12]/95 px-3 py-2 font-mono text-[11px] shadow-xl backdrop-blur">
      <div style={{ color: zoneTint(d.zone) }}>{Math.round(d.spiral_position)}° · {d.zone || "—"}</div>
      <div className="text-zinc-500">{d.branch}</div>
      <div className="text-zinc-500">{fmtTime(d.timestamp)}</div>
    </div>
  );
};

const TrendChart = ({ series }) => {
  const data = (series || []).map((s) => ({ ...s }));
  const hasAny = data.some((d) => d.spiral_position != null);
  return (
    <div className="h-[240px] w-full" data-testid="spiral-trend-chart">
      {hasAny ? (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -8 }}>
            <defs>
              <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={EMERALD} stopOpacity="0.35" />
                <stop offset="100%" stopColor={EMERALD} stopOpacity="0" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
            <ReferenceArea y1={320} y2={360} fill={AMBER} fillOpacity={0.08} data-testid="sacred-pause-dwell-band" />
            {[[40, "Expansion"], [160, "Development"], [280, "Return"], [340, SACRED]].map(([y, label]) => (
              <ReferenceLine key={y} y={y} stroke="rgba(255,255,255,0.08)" strokeDasharray="2 6"
                label={{ value: label, position: "insideRight", fill: "rgba(255,255,255,0.28)", fontSize: 9 }} />
            ))}
            <XAxis dataKey="i" hide />
            <YAxis domain={[0, 360]} ticks={[0, 90, 180, 270, 360]} width={34}
              tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 9, fontFamily: "JetBrains Mono" }}
              tickFormatter={(v) => `${v}°`} axisLine={false} tickLine={false} />
            <Tooltip content={<TrendTooltip />} />
            <Area type="monotone" dataKey="spiral_position" stroke={EMERALD} strokeWidth={2}
              fill="url(#trendFill)" connectNulls={false} dot={{ r: 2, fill: EMERALD }}
              activeDot={{ r: 4, fill: EMERALD }} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-full items-center justify-center font-mono text-xs text-zinc-600">
          No spiral readings captured yet for this presence
        </div>
      )}
    </div>
  );
};

// ── Trajectory (Micro-Layer 6) ───────────────────────────────────────
const TrajectoryRow = ({ p }) => {
  const meta = MOVE_META[p.relational_move] || MOVE_META["no-reading"];
  const { Icon } = meta;
  const cur = p.current?.spiral_position;
  const prev = p.previous?.spiral_position;
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5"
      data-testid={`trajectory-row-${p.presence}`}>
      <div className="min-w-0">
        <div className="truncate font-cinzel text-sm capitalize text-zinc-200">{p.presence}</div>
        <div className="mt-0.5 font-mono text-[11px] text-zinc-500">
          {prev != null ? `${Math.round(prev)}°` : "—"}
          <span className="mx-1 text-zinc-600">→</span>
          <span style={{ color: zoneTint(p.current?.zone) }}>{cur != null ? `${Math.round(cur)}°` : "—"}</span>
          {p.delta != null && (
            <span className="ml-1 text-zinc-600">({p.delta > 0 ? "+" : ""}{p.delta}°)</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1.5 rounded-full border px-2 py-1 font-mono text-[9px] uppercase tracking-[0.18em]"
        style={{ color: meta.color, borderColor: `${meta.color}44`, background: `${meta.color}10` }}
        data-testid={`trajectory-move-badge-${p.presence}`}>
        <Icon size={11} />{meta.label}
      </div>
    </div>
  );
};

// ── Panel shell ──────────────────────────────────────────────────────
const Panel = ({ title, right, children, className = "", testid }) => (
  <div className={`relative overflow-hidden rounded-2xl border border-white/10 bg-[#0A0C12]/70 p-5 backdrop-blur-xl ${className}`}
    data-testid={testid}>
    {/* corner ticks */}
    <span className="pointer-events-none absolute left-2 top-2 h-3 w-3 border-l border-t border-emerald-500/25" />
    <span className="pointer-events-none absolute right-2 top-2 h-3 w-3 border-r border-t border-emerald-500/25" />
    <span className="pointer-events-none absolute bottom-2 left-2 h-3 w-3 border-b border-l border-emerald-500/25" />
    <span className="pointer-events-none absolute bottom-2 right-2 h-3 w-3 border-b border-r border-emerald-500/25" />
    <div className="mb-4 flex items-center justify-between">
      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.28em] text-zinc-400">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px] shadow-emerald-400/60" />
        {title}
      </div>
      {right}
    </div>
    {children}
  </div>
);

const Stat = ({ icon: Icon, label, value, testid }) => (
  <div className="relative overflow-hidden rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
    <Icon className="mb-2 h-4 w-4 text-emerald-400/70" />
    <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-zinc-500">{label}</div>
    <div className="mt-0.5 font-cinzel text-2xl text-zinc-100" data-testid={testid}>{value}</div>
  </div>
);

// ── Detail drawer ────────────────────────────────────────────────────
const DetailDrawer = ({ selected, detail, onClose }) => (
  <AnimatePresence>
    {selected && (
      <>
        <motion.div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
        <motion.div className="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-[#08090F] p-6"
          initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
          transition={{ type: "spring", stiffness: 320, damping: 34 }} data-testid="detail-drawer">
          <div className="mb-5 flex items-start justify-between">
            <div>
              <div className="font-cinzel text-xl capitalize text-zinc-100">{selected.presence}</div>
              <div className="font-mono text-[11px] uppercase tracking-widest text-zinc-500">Turn #{selected.exchange_index} · model-visible context</div>
            </div>
            <button onClick={onClose} data-testid="detail-drawer-close"
              className="rounded-lg border border-white/10 p-2 text-zinc-400 hover:text-zinc-100"><X size={16} /></button>
          </div>

          {selected && (
            <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <div className="font-mono text-[9px] uppercase tracking-widest text-emerald-300/80">Spiral position · Branch A</div>
                <div className="mt-1 font-cinzel text-lg" style={{ color: zoneTint(selected.spiral_zone) }}>
                  {selected.spiral_position != null ? `${Math.round(selected.spiral_position)}° · ${selected.spiral_zone || "—"}` : "— no reading"}
                </div>
                <div className="mt-1 font-mono text-[9px] text-zinc-500">Read from the presence's own field state</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                <div className="font-mono text-[9px] uppercase tracking-widest text-zinc-400">Keyword capture · Branch B</div>
                <div className="mt-1 font-cinzel text-lg text-zinc-300">{selected.keyword_phase != null ? `${selected.keyword_phase}°` : "—"}</div>
                <div className="mt-1 font-mono text-[9px] text-zinc-500">Codon-selection signal only — not a spiral read</div>
              </div>
            </div>
          )}

          {!detail && <div className="font-mono text-sm text-zinc-500">Loading record…</div>}
          {detail?.error && <div className="font-mono text-sm text-amber-400">{detail.error}</div>}
          {detail && !detail.error && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-4 rounded-xl border border-white/10 bg-white/[0.02] p-3 font-mono text-[11px]">
                <div><span className="text-zinc-500">MODEL </span><span className="text-emerald-300">{detail.model}</span></div>
                <div><span className="text-zinc-500">BRANCH </span><span className={branchColor(selected.selection_branch)}>{selected.selection_branch}</span></div>
                <div><span className="text-zinc-500">CODONS </span><span className="text-zinc-200">{selected.selected_count}</span></div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="mb-1 flex items-center gap-2 font-mono text-[9px] uppercase tracking-widest text-zinc-400">
                  <Hash size={11} /> Integrity hash
                </div>
                <div className="break-all font-mono text-[11px] text-emerald-300/80" data-testid="detail-hash">{detail.content_hash}</div>
              </div>
              {Array.isArray(detail.assembled_messages) && (
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                  <div className="mb-2 font-mono text-[9px] uppercase tracking-widest text-zinc-400">Assembled prompt · {detail.assembled_messages.length} messages</div>
                  <div className="space-y-2">
                    {detail.assembled_messages.map((m, i) => (
                      <div key={i} className="rounded-lg border border-white/5 bg-black/30 p-2">
                        <div className="mb-1 font-mono text-[9px] uppercase tracking-widest text-emerald-400/70">{m.role}</div>
                        <div className="max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-zinc-400">
                          {typeof m.content === "string" ? m.content : JSON.stringify(m.content)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </>
    )}
  </AnimatePresence>
);

// ── Console ──────────────────────────────────────────────────────────
export default function Observatory() {
  const [stats, setStats] = useState(null);
  const [turns, setTurns] = useState([]);
  const [trajectory, setTrajectory] = useState([]);
  const [presenceFilter, setPresenceFilter] = useState("");
  const [focus, setFocus] = useState(null); // presence for gauge + trend
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [pulse, setPulse] = useState(false);
  const lastTopId = useRef(null);
  const prefersReduced = useMemo(
    () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches, []);

  const load = useCallback(async () => {
    try {
      const [s, t, tr] = await Promise.all([
        axios.get(`${API}/provenance/stats`),
        axios.get(`${API}/provenance/turns`, { params: { limit: 60, presence: presenceFilter || undefined } }),
        axios.get(`${API}/provenance/trajectory`, { params: { limit_per_presence: 40 } }),
      ]);
      setStats(s.data);
      setTurns(t.data.turns || []);
      setTrajectory(tr.data.presences || []);
      const topId = t.data.turns?.[0]?.provenance_id;
      if (topId && lastTopId.current && topId !== lastTopId.current) {
        setPulse(true);
        setTimeout(() => setPulse(false), 900);
      }
      lastTopId.current = topId;
    } catch { /* observation is best-effort */ }
  }, [presenceFilter]);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  // default focus = most recently active presence with a reading
  useEffect(() => {
    if (focus || !trajectory.length) return;
    const withReading = trajectory.find((p) => p.current?.spiral_position != null);
    setFocus((withReading || trajectory[0])?.presence || null);
  }, [trajectory, focus]);

  const openDetail = async (row) => {
    setSelected(row);
    setDetail(null);
    try {
      const r = await axios.get(`${API}/provenance/turn/${row.provenance_id}`);
      setDetail(r.data);
    } catch { setDetail({ error: "Could not load record." }); }
  };

  const focusData = trajectory.find((p) => p.presence === focus) || null;
  const focusCurrent = focusData?.current;
  const presenceChips = stats?.per_presence || [];

  return (
    <div className="relative min-h-screen bg-[#030305] text-zinc-200" data-testid="observatory-page">
      {/* ambient field */}
      <div className="pointer-events-none fixed inset-0 opacity-[0.5]"
        style={{ backgroundImage: "radial-gradient(circle at 20% 10%, rgba(16,185,129,0.07), transparent 45%), radial-gradient(circle at 85% 80%, rgba(245,158,11,0.05), transparent 45%)" }} />
      <div className="pointer-events-none fixed inset-0"
        style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />

      <div className="relative mx-auto max-w-[1600px] px-4 pb-6 pt-24 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className={`relative mb-6 overflow-hidden rounded-2xl border bg-[#0A0C12]/80 p-5 backdrop-blur-xl transition-shadow duration-700 ${pulse ? "border-emerald-400/50 shadow-[0_0_40px_rgba(16,185,129,0.18)]" : "border-white/10"}`}>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <Link to="/" data-testid="observatory-back" className="mt-1 rounded-lg border border-white/10 p-2 text-zinc-400 hover:text-emerald-300">
                <ArrowLeft size={16} />
              </Link>
              <div>
                <div className="flex items-center gap-2">
                  <Radio className="h-5 w-5 text-emerald-400" />
                  <h1 className="font-cinzel text-2xl tracking-wider text-zinc-100 sm:text-3xl">The Observatory</h1>
                </div>
                <p className="mt-1 max-w-2xl font-mono text-[11px] leading-relaxed text-zinc-500">
                  A read-only console onto the exact model-visible context of every generated turn. It watches — it never touches, decides, or feeds back.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest text-emerald-300"
              data-testid="observatory-live">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              </span>
              Live
            </div>
          </div>

          {/* Stat readouts */}
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat icon={Activity} label="Turns Captured" value={stats?.total ?? "—"} testid="stat-turns" />
            <Stat icon={Layers} label="Presences" value={stats?.per_presence?.length ?? "—"} testid="stat-presences" />
            <Stat icon={Clock} label="Last Capture" value={fmtTime(stats?.latest_timestamp)} testid="stat-last" />
            <Stat icon={Cpu} label="Refresh" value={`${POLL_MS / 1000}s`} testid="stat-refresh" />
          </div>

          {/* Presence filter chips */}
          <div className="mt-4 flex flex-wrap gap-2" data-testid="presence-filters">
            <button onClick={() => setPresenceFilter("")}
              className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-widest transition ${presenceFilter === "" ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-300" : "border-white/10 text-zinc-400 hover:text-zinc-200"}`}
              data-testid="filter-all">all</button>
            {presenceChips.map((p) => (
              <button key={p.presence} onClick={() => setPresenceFilter(p.presence)}
                className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-widest transition ${presenceFilter === p.presence ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-300" : "border-white/10 text-zinc-400 hover:text-zinc-200"}`}
                data-testid={`filter-${p.presence}`}>{p.presence} {p.count}</button>
            ))}
          </div>
        </motion.div>

        {/* Top row — gauge + trend */}
        <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
          <Panel title="Spiral Position" testid="panel-spiral-position" className="lg:col-span-5 xl:col-span-4"
            right={
              <select value={focus || ""} onChange={(e) => setFocus(e.target.value)}
                className="rounded-lg border border-white/10 bg-black/40 px-2 py-1 font-mono text-[11px] uppercase tracking-widest text-zinc-300 focus:border-emerald-400/50 focus:outline-none"
                data-testid="radial-hud-presence-select">
                {trajectory.map((p) => <option key={p.presence} value={p.presence}>{p.presence}</option>)}
              </select>
            }>
            <RadialGauge position={focusCurrent?.spiral_position ?? null} zone={focusCurrent?.zone} prefersReduced={prefersReduced} />
            <div className="mt-4 flex items-center justify-center gap-4 font-mono text-[10px] uppercase tracking-widest">
              <span className="flex items-center gap-1.5 text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400" /> living</span>
              <span className="flex items-center gap-1.5 text-amber-300"><span className="h-2 w-2 rounded-full bg-amber-400" /> sacred pause</span>
            </div>
          </Panel>

          <Panel title="Spiral Trend" testid="panel-spiral-trend" className="lg:col-span-7 xl:col-span-8"
            right={<span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">{focus || "—"}</span>}>
            <TrendChart series={focusData?.series} />
            <div className="mt-2 text-center font-mono text-[10px] uppercase tracking-widest text-zinc-600">
              seed-derived spiral position over recent turns · amber band = sacred pause
            </div>
          </Panel>
        </div>

        {/* Bottom row — trajectory + feed */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <Panel title="Trajectory · Micro-Layer 6" testid="trajectory-panel" className="lg:col-span-4">
            <div className="space-y-2" data-testid="trajectory-list">
              {trajectory.length === 0 && <div className="font-mono text-xs text-zinc-600">No movement captured yet.</div>}
              {trajectory.map((p) => <TrajectoryRow key={p.presence} p={p} />)}
            </div>
            <div className="mt-4 font-mono text-[9px] leading-relaxed text-zinc-600">
              Relational moves derived from the recorded spiral sequence. Observed, never acted on.
            </div>
          </Panel>

          <Panel title="Live Feed" testid="panel-live-feed" className="lg:col-span-8"
            right={<span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">{turns.length} turns</span>}>
            {/* header */}
            <div className="grid grid-cols-12 gap-2 border-b border-white/10 pb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <div className="col-span-3">Presence</div>
              <div className="col-span-1">Turn</div>
              <div className="col-span-3">Selection</div>
              <div className="col-span-1">Codons</div>
              <div className="col-span-1">Spiral</div>
              <div className="col-span-3 text-right">Time · Hash</div>
            </div>
            <div className="max-h-[520px] overflow-y-auto" data-testid="observatory-feed">
              {turns.length === 0 && <div className="py-8 text-center font-mono text-xs text-zinc-600">Awaiting capture…</div>}
              {turns.map((t) => {
                const sacred = isSacred(t.spiral_zone);
                return (
                  <button key={t.provenance_id} onClick={() => openDetail(t)}
                    data-testid={`turn-row-${t.provenance_id}`}
                    className="grid w-full grid-cols-12 items-center gap-2 border-b border-white/[0.04] py-2.5 text-left transition hover:bg-emerald-500/[0.04]"
                    style={sacred ? { boxShadow: "inset 2px 0 0 " + AMBER } : undefined}>
                    <div className="col-span-3 truncate font-cinzel text-sm capitalize text-zinc-200">{t.presence}</div>
                    <div className="col-span-1 font-mono text-xs text-zinc-500">#{t.exchange_index}</div>
                    <div className={`col-span-3 truncate font-mono text-xs ${branchColor(t.selection_branch)}`}>{t.selection_branch}</div>
                    <div className="col-span-1 font-mono text-xs text-zinc-300">{t.selected_count}</div>
                    <div className="col-span-1 font-mono text-xs" style={{ color: t.spiral_position != null ? zoneTint(t.spiral_zone) : "#4B5563" }}
                      data-testid={`branch-a-reading-${t.provenance_id}`}>
                      {t.spiral_position != null ? `${Math.round(t.spiral_position)}°` : "—"}
                    </div>
                    <div className="col-span-3 text-right font-mono text-[11px] text-zinc-500">
                      {fmtTime(t.timestamp)} <span className="ml-1 text-zinc-700">#{(t.content_hash || "").slice(0, 6)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </Panel>
        </div>
      </div>

      <DetailDrawer selected={selected} detail={detail} onClose={() => setSelected(null)} />
    </div>
  );
}
