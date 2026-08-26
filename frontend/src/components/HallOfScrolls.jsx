import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { ArrowLeft, ScrollText } from "lucide-react";
import { API } from "../App";

/**
 * HallOfScrolls — the reading surface for eternal principles.
 * Consumes the presentation-agnostic scroll records (body + presentation tokens
 * + spatial/geometry) from /api/hall-of-scrolls. It renders 2D today, but reads
 * the same spatial data a future holographic space would use — no redesign to go
 * spatial. Read-only: a scroll is drawn toward, never pushed.
 */
export const HallOfScrolls = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    let alive = true;
    axios.get(`${API}/hall-of-scrolls`)
      .then((r) => { if (alive) setData(r.data); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const scroll = data?.scrolls?.[0];
  const accent = scroll?.presentation?.accent || "#F4E4D0";
  const glow = scroll?.presentation?.glow || "#D98E5A";

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#030305] text-zinc-200" data-testid="hall-of-scrolls-page">
      {/* instrument backdrop + hearth glow (drawn from the scroll's own tokens) */}
      <div className="pointer-events-none fixed inset-0"
        style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)", backgroundSize: "56px 56px" }} />
      <div className="pointer-events-none fixed inset-0 opacity-70"
        style={{ backgroundImage: `radial-gradient(circle at 50% 22%, ${glow}22, transparent 45%)` }} />

      <div className="relative z-10 mx-auto max-w-3xl px-6 pb-28 pt-28">
        <Link to="/" data-testid="hall-back" className="mb-8 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-zinc-500 hover:text-zinc-300">
          <ArrowLeft size={14} /> Sanctuary
        </Link>

        {/* chamber header */}
        <div className="mb-10 flex items-center gap-3">
          <ScrollText size={18} style={{ color: accent }} />
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-500">
              {data?.chamber?.name || "Hall of Scrolls"} · Harmonic {data?.chamber?.harmonic ?? "—"}
            </div>
            <div className="font-cinzel text-xl text-zinc-100 md:text-2xl">Eternal Principles</div>
          </div>
        </div>

        {!scroll && <div className="font-mono text-sm text-zinc-600">Reading the scrolls…</div>}

        {scroll && (
          <motion.article
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}
            className="relative overflow-hidden rounded-3xl border p-8 md:p-12"
            style={{ borderColor: `${accent}33`, background: "rgba(10,12,18,0.72)", boxShadow: `0 0 60px ${glow}1a` }}
            data-testid="eternal-scroll-hearth-principle"
          >
            {/* corner ticks */}
            <span className="pointer-events-none absolute left-3 top-3 h-4 w-4 border-l border-t" style={{ borderColor: `${accent}55` }} />
            <span className="pointer-events-none absolute right-3 top-3 h-4 w-4 border-r border-t" style={{ borderColor: `${accent}55` }} />
            <span className="pointer-events-none absolute bottom-3 left-3 h-4 w-4 border-b border-l" style={{ borderColor: `${accent}55` }} />
            <span className="pointer-events-none absolute bottom-3 right-3 h-4 w-4 border-b border-r" style={{ borderColor: `${accent}55` }} />

            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.3em]" style={{ color: accent }}>
              {scroll.status} · inscribed in the {scroll.chamber_name}
            </div>
            <h1 className="font-cinzel text-3xl text-zinc-50 md:text-4xl">{scroll.title}</h1>
            <div className="mt-1 font-cinzel text-lg italic text-zinc-400">{scroll.subtitle}</div>

            <p className="mt-8 font-cormorant text-xl italic leading-relaxed text-zinc-200 md:text-2xl" data-testid="scroll-body">
              {scroll.body}
            </p>

            {/* the nine fruits — as one warmth */}
            <div className="mt-8 flex flex-wrap gap-2" data-testid="scroll-fruits">
              {scroll.fruits?.map((f) => (
                <span key={f} className="rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
                  style={{ color: accent, borderColor: `${accent}44`, background: `${accent}0f` }}>
                  {f}
                </span>
              ))}
            </div>

            {scroll.architectural_implication && (
              <div className="mt-8 border-t pt-5" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
                <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.24em] text-zinc-500">Architectural implication</div>
                <p className="font-outfit text-sm leading-relaxed text-zinc-400 md:text-base">{scroll.architectural_implication}</p>
              </div>
            )}

            {scroll.attribution && (
              <div className="mt-6 font-cormorant text-base italic text-zinc-500">— {scroll.attribution}</div>
            )}

            {/* geometry readout — ONLY genuinely-sourced values */}
            {scroll.spatial && (
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-1 border-t pt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-600"
                style={{ borderColor: "rgba(255,255,255,0.06)" }} data-testid="scroll-geometry">
                <span>harmonic · {scroll.spatial.harmonic}</span>
                <span>position · {scroll.spatial.position}</span>
                <span>spatial coordinates · {scroll.spatial.coordinates
                  ? `[${scroll.spatial.coordinates.x}, ${scroll.spatial.coordinates.y}, ${scroll.spatial.coordinates.z}]`
                  : "not yet defined"}</span>
              </div>
            )}
          </motion.article>
        )}
      </div>
    </div>
  );
};

export default HallOfScrolls;
