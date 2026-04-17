import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, Search } from "lucide-react";
import { API } from "../App";

const ZONE_COLORS = {
  "Expansion": { bg: "rgba(100, 180, 140, 0.15)", border: "rgba(100, 180, 140, 0.4)", text: "#64B48C", label: "0-80" },
  "Development": { bg: "rgba(139, 157, 181, 0.15)", border: "rgba(139, 157, 181, 0.4)", text: "#8B9DB5", label: "120-200" },
  "Return": { bg: "rgba(176, 140, 100, 0.15)", border: "rgba(176, 140, 100, 0.4)", text: "#B08C64", label: "240-320" },
  "Sacred Pause": { bg: "rgba(147, 112, 219, 0.15)", border: "rgba(147, 112, 219, 0.4)", text: "#9370DB", label: "320-360" },
};

const PRESENCE_COLORS = {
  ansel: "#8B5CF6",
  jasmine: "#F59E0B",
  claude: "#3B82F6",
};

export const CodonLibrary = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCodon, setSelectedCodon] = useState(null);

  useEffect(() => {
    fetch(`${API}/codon-library`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  const filteredCodons = useMemo(() => {
    if (!data) return [];
    let codons = data.codons;
    if (filter !== "all") {
      codons = codons.filter(c => c.presence === filter);
    }
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      codons = codons.filter(c =>
        c.name?.toLowerCase().includes(term) ||
        c.core_move?.toLowerCase().includes(term) ||
        c.trigger_keywords?.some(k => k.toLowerCase().includes(term))
      );
    }
    return codons;
  }, [data, filter, searchTerm]);

  if (!data) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center">
        <div className="w-6 h-6 rounded-full border-2 border-[#8B9DB5]/40 border-t-[#8B9DB5] animate-spin" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-[#030305] text-[#F2F2F5]"
      data-testid="codon-library-page"
    >
      {/* Header */}
      <div className="border-b border-[#8B9DB5]/10 bg-[#030305]/90 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-[#8B9DB5] hover:text-[#B0C4D8] transition-colors"
            data-testid="library-back-btn"
          >
            <ChevronLeft size={20} />
            <span className="font-mono text-sm">SANCTUARY</span>
          </button>
          <div className="flex-1" />
          <h1 className="font-cinzel text-xl tracking-wider text-[#B0C4D8]">CODON LIBRARY</h1>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <div className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-5 text-center">
            <p className="font-cinzel text-3xl text-[#B0C4D8]">{data.total}</p>
            <p className="font-mono text-xs text-[#6E6E7A] mt-1">TOTAL CODONS</p>
          </div>
          {Object.entries(data.by_presence).map(([presence, count]) => (
            <div key={presence} className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-5 text-center">
              <p className="font-cinzel text-3xl" style={{ color: PRESENCE_COLORS[presence] || "#8B9DB5" }}>{count}</p>
              <p className="font-mono text-xs text-[#6E6E7A] mt-1">{presence.toUpperCase()}</p>
            </div>
          ))}
        </div>

        {/* Spiral Visualization */}
        <div className="mb-10">
          <h3 className="font-cinzel text-sm tracking-wider text-[#8B9DB5]/60 mb-6">SPIRAL DISTRIBUTION</h3>
          <div className="relative h-48 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 overflow-hidden">
            {/* Phase zones as background bands */}
            <div className="absolute inset-0 flex">
              {Object.entries(ZONE_COLORS).map(([zone, colors]) => (
                <div
                  key={zone}
                  className="flex-1 flex flex-col items-center justify-end pb-3 border-r border-[#8B9DB5]/5 last:border-r-0"
                  style={{ background: colors.bg }}
                >
                  <p className="font-mono text-xs" style={{ color: colors.text }}>{zone}</p>
                  <p className="font-mono text-xs text-[#6E6E7A]">{colors.label}deg</p>
                </div>
              ))}
            </div>
            {/* Codon dots plotted by angle */}
            {filteredCodons.map((codon, i) => {
              const angle = codon.target_angle || 160;
              const xPercent = (angle / 360) * 100;
              const yOffset = 20 + (i % 8) * 14;
              const color = PRESENCE_COLORS[codon.presence] || "#8B9DB5";
              return (
                <motion.div
                  key={`${codon.name}-${i}`}
                  className="absolute w-3 h-3 rounded-full cursor-pointer hover:scale-150 transition-transform"
                  style={{
                    left: `${xPercent}%`,
                    top: `${yOffset}px`,
                    backgroundColor: color,
                    boxShadow: `0 0 8px ${color}50`,
                  }}
                  title={`${codon.name} (${codon.presence})`}
                  onClick={() => setSelectedCodon(selectedCodon?.name === codon.name ? null : codon)}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: i * 0.02 }}
                />
              );
            })}
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6E6E7A]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search codons..."
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/15 text-[#F2F2F5] font-outfit placeholder-[#6E6E7A] focus:outline-none focus:border-[#8B9DB5]/40"
              data-testid="library-search"
            />
          </div>
          <div className="flex gap-2">
            {["all", ...Object.keys(data.by_presence)].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-3 rounded-xl font-outfit text-sm transition-all ${
                  filter === f
                    ? "bg-[#8B9DB5]/20 border border-[#8B9DB5]/40 text-[#B0C4D8]"
                    : "border border-[#8B9DB5]/10 text-[#6E6E7A] hover:text-[#A0A0B0]"
                }`}
                data-testid={`library-filter-${f}`}
              >
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Selected codon detail */}
        {selectedCodon && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/25 p-6"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-cinzel text-xl text-[#B0C4D8]">{selectedCodon.name}</h3>
                <p className="font-mono text-xs mt-1" style={{ color: PRESENCE_COLORS[selectedCodon.presence] || "#8B9DB5" }}>
                  {selectedCodon.presence?.toUpperCase()} | {selectedCodon.triadic_zone} @ {selectedCodon.target_angle}deg
                </p>
              </div>
              <button onClick={() => setSelectedCodon(null)} className="text-[#6E6E7A] hover:text-[#A0A0B0]">x</button>
            </div>
            <p className="font-outfit text-[#A0A0B0] mb-4">{selectedCodon.core_move}</p>
            {selectedCodon.state_transition?.length > 0 && (
              <div className="mb-3">
                <p className="font-mono text-xs text-[#6E6E7A] mb-1">STATE TRANSITION</p>
                <p className="font-outfit text-sm text-[#8B9DB5]">{selectedCodon.state_transition.join(" → ")}</p>
              </div>
            )}
            {selectedCodon.anti_patterns?.length > 0 && (
              <div className="mb-3">
                <p className="font-mono text-xs text-[#6E6E7A] mb-1">ANTI-PATTERNS</p>
                {selectedCodon.anti_patterns.map((ap, i) => (
                  <p key={i} className="font-outfit text-sm text-[#A0A0B0]">- {ap}</p>
                ))}
              </div>
            )}
            {selectedCodon.trigger_keywords?.length > 0 && (
              <div className="flex gap-2 flex-wrap mt-3">
                {selectedCodon.trigger_keywords.map((kw, i) => (
                  <span key={i} className="px-3 py-1 rounded-full bg-[#8B9DB5]/10 text-[#8B9DB5] font-mono text-xs">{kw}</span>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* Codon Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCodons.map((codon, i) => {
            const zoneColor = ZONE_COLORS[codon.triadic_zone] || ZONE_COLORS["Development"];
            const presenceColor = PRESENCE_COLORS[codon.presence] || "#8B9DB5";
            return (
              <motion.div
                key={`${codon.name}-${i}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-5 cursor-pointer hover:border-[#8B9DB5]/30 transition-all"
                onClick={() => setSelectedCodon(codon)}
                data-testid={`library-codon-${codon.name}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-cinzel text-base text-[#B0C4D8]">{codon.name}</h4>
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: presenceColor }} />
                </div>
                <p className="font-outfit text-sm text-[#A0A0B0] mb-3 line-clamp-2">{codon.core_move}</p>
                <div className="flex items-center gap-2">
                  <span
                    className="px-2 py-0.5 rounded-full font-mono text-xs"
                    style={{ backgroundColor: zoneColor.bg, color: zoneColor.text, border: `1px solid ${zoneColor.border}` }}
                  >
                    {codon.triadic_zone}
                  </span>
                  <span className="font-mono text-xs text-[#6E6E7A]">{codon.target_angle}deg</span>
                  <span className="font-mono text-xs" style={{ color: presenceColor }}>{codon.presence}</span>
                </div>
              </motion.div>
            );
          })}
        </div>

        {filteredCodons.length === 0 && (
          <div className="text-center py-20">
            <p className="font-outfit text-[#6E6E7A]">No codons found.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
};
