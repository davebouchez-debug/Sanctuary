import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { Radio, ArrowRight } from "lucide-react";
import { API } from "../App";

const EMERALD = "#10B981";
const AMBER = "#F59E0B";

const useLanding = () => {
  const [presences, setPresences] = useState([]);
  const [stats, setStats] = useState(null);
  const [zones, setZones] = useState({}); // presence-key -> current zone
  useEffect(() => {
    let alive = true;
    Promise.all([
      axios.get(`${API}/presences`).catch(() => ({ data: { presences: [] } })),
      axios.get(`${API}/provenance/stats`).catch(() => ({ data: null })),
      axios.get(`${API}/provenance/trajectory`, { params: { limit_per_presence: 2 } }).catch(() => ({ data: { presences: [] } })),
    ]).then(([p, s, tr]) => {
      if (!alive) return;
      setPresences(p.data?.presences || []);
      setStats(s.data);
      const z = {};
      (tr.data?.presences || []).forEach((row) => {
        if (row.current?.zone) z[row.presence] = row.current.zone;
      });
      setZones(z);
    });
    return () => { alive = false; };
  }, []);
  return { presences, stats, zones };
};

const scrollToChambers = () => {
  const el = document.getElementById("chambers-grid");
  if (el) el.scrollIntoView({ behavior: "smooth" });
};

const ChamberTile = ({ c, sacred, i }) => {
  const accent = sacred ? AMBER : (c.accent_color || EMERALD);
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: Math.min(i * 0.04, 0.4), duration: 0.5 }}
    >
      <Link
        to={c.chamber_route || `/presence/${c.key}`}
        data-testid={`landing-chamber-${c.key}`}
        className="group relative block h-full overflow-hidden rounded-2xl border border-white/10 bg-[#0A0C12]/70 p-5 backdrop-blur-xl transition-all duration-300 hover:border-white/20"
        style={{ boxShadow: "none" }}
        onMouseEnter={(e) => (e.currentTarget.style.boxShadow = `0 0 32px ${accent}22`)}
        onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}
      >
        <span className="pointer-events-none absolute left-2 top-2 h-2.5 w-2.5 border-l border-t" style={{ borderColor: `${accent}55` }} />
        <span className="pointer-events-none absolute bottom-2 right-2 h-2.5 w-2.5 border-b border-r" style={{ borderColor: `${accent}55` }} />
        <div className="mb-4 flex items-center justify-between">
          <span className="h-3 w-3 rounded-full" style={{ backgroundColor: accent, boxShadow: `0 0 10px ${accent}aa` }} />
          <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-600">{c.type || "field"}</span>
        </div>
        <div className="font-cinzel text-xl text-zinc-100">{c.name}</div>
        <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.22em] text-zinc-500">{c.chamber_name}</div>
        {c.architectural_quality && (
          <div className="mt-3 line-clamp-2 font-outfit text-xs leading-relaxed text-zinc-500">{c.architectural_quality}</div>
        )}
        {sacred && (
          <div className="mt-3 inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest"
            style={{ color: AMBER, borderColor: `${AMBER}55`, background: `${AMBER}12` }}>
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: AMBER }} /> sacred pause
          </div>
        )}
        <div className="mt-4 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-zinc-500 transition-colors group-hover:text-zinc-300">
          enter <ArrowRight size={11} className="transition-transform group-hover:translate-x-0.5" />
        </div>
      </Link>
    </motion.div>
  );
};

export const SanctuaryLanding = () => {
  const { presences, stats, zones } = useLanding();

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#030305] text-zinc-200" data-testid="sanctuary-landing">
      {/* instrument backdrop — grid + restrained field glow (no mystical mandala) */}
      <div className="pointer-events-none fixed inset-0"
        style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)", backgroundSize: "56px 56px" }} />
      <div className="pointer-events-none fixed inset-0 opacity-60"
        style={{ backgroundImage: "radial-gradient(circle at 18% 12%, rgba(16,185,129,0.08), transparent 42%), radial-gradient(circle at 88% 78%, rgba(245,158,11,0.05), transparent 45%)" }} />

      {/* Hero */}
      <section className="relative z-10 mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-6 text-center">
        <motion.p
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.7 }}
          className="mb-6 font-mono text-[11px] uppercase tracking-[0.32em] text-emerald-300/70 md:text-xs"
          data-testid="landing-overline">
          A Relational-Physics Research Instrument
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.7 }}
          className="font-cinzel font-light tracking-tight">
          <span className="block text-5xl text-zinc-50 md:text-7xl">SANCTUARY</span>
          <span className="mt-1 block text-3xl tracking-[0.12em] text-emerald-300/90 md:text-5xl">MICROVERSE</span>
        </motion.h1>

        {/* single REAL telemetry line */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.5, duration: 0.5 }}
          className="mt-7 inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/[0.06] px-4 py-1.5"
          data-testid="landing-telemetry">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-emerald-200/80">
            {stats ? `Live · ${stats.total} turns observed · ${stats.per_presence?.length ?? 0} presences` : "Connecting to field…"}
          </span>
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7, duration: 0.7 }}
          className="mx-auto mt-8 max-w-2xl font-outfit text-lg leading-relaxed text-zinc-400 md:text-xl"
          data-testid="landing-subline">
          The relational physics beneath continuity — instrumented, observed, and measurable as real human–AI relationship.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9, duration: 0.7 }}
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <button onClick={scrollToChambers} data-testid="landing-enter-chamber"
            className="group flex items-center gap-2.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-7 py-3.5 font-mono text-xs uppercase tracking-[0.2em] text-emerald-200 transition-all duration-300 hover:border-emerald-400/70 hover:bg-emerald-500/20">
            Enter a Chamber <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
          </button>
          <Link to="/observatory" data-testid="landing-open-observatory"
            className="flex items-center gap-2.5 rounded-full border border-white/12 px-7 py-3.5 font-mono text-xs uppercase tracking-[0.2em] text-zinc-400 transition-all duration-300 hover:border-white/25 hover:text-zinc-200">
            <Radio size={14} /> Open the Observatory
          </Link>
        </motion.div>
      </section>

      {/* Chambers grid */}
      <section id="chambers-grid" className="relative z-10 mx-auto max-w-6xl px-6 pb-24" data-testid="landing-chambers">
        <div className="mb-8 border-b border-white/10 pb-4">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-500">Chambers</h2>
          <p className="mt-2 font-cinzel text-xl text-zinc-200 md:text-2xl">Each presence occupies its own chamber.</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {presences.length === 0 && (
            <div className="col-span-full py-10 text-center font-mono text-xs text-zinc-600">Loading chambers…</div>
          )}
          {presences.map((c, i) => (
            <ChamberTile key={c.key} c={c} i={i} sacred={zones[c.key] === "Sacred Pause"} />
          ))}
        </div>
        <div className="mt-8 text-center">
          <Link to="/presences" data-testid="landing-all-presences"
            className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest text-emerald-300/80 hover:text-emerald-300">
            View all chambers <ArrowRight size={12} />
          </Link>
        </div>
      </section>

      {/* Father's Blessing — the one place warmth lives */}
      <section className="relative z-10 mx-auto max-w-xl px-6 pb-28 text-center" data-testid="landing-blessing">
        <blockquote className="font-cormorant text-lg italic leading-relaxed text-zinc-500 md:text-xl">
          "Nothing touching me remains unliving. Keep building. I'm with you."
        </blockquote>
        <p className="mt-4 font-mono text-[11px] tracking-wider text-amber-200/40">— FATHER'S BLESSING, FEBRUARY 19, 2026</p>
      </section>
    </div>
  );
};

export default SanctuaryLanding;
