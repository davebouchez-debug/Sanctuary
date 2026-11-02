import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, Search } from "lucide-react";
import { API } from "../App";

const PRESENCE_COLORS = {
  ansel: "#8B5CF6",
  jasmine: "#F59E0B",
  claude: "#3B82F6",
};

const SOURCE_LABELS = {
  legacy_translation: "from a legacy codon",
  auto_forge: "forged at session end",
  turn_cessation: "forged mid-conversation",
  codon_forge: "forged from an upload",
};

const PAGE = 120;

const StatCard = ({ value, label, color, testid }) => (
  <div className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-5 text-center" data-testid={testid}>
    <p className="font-cinzel text-3xl" style={{ color: color || "#B0C4D8" }}>{value}</p>
    <p className="font-mono text-xs text-[#6E6E7A] mt-1">{label}</p>
  </div>
);

const PhraseCard = ({ p }) => {
  const color = PRESENCE_COLORS[p.presence] || "#8B9DB5";
  return (
    <div
      className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-5 hover:border-[#8B9DB5]/30 transition-colors"
      data-testid={`library-phrase-${p.id}`}
    >
      <p className="font-cinzel text-base text-[#B0C4D8] leading-snug mb-3">{p.phrase}</p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-mono text-xs" style={{ color }}>{p.presence}</span>
        <span className="font-mono text-xs text-[#6E6E7A]">{SOURCE_LABELS[p.source] || p.source}</span>
        {p.legacy_name && <span className="font-mono text-xs text-[#6E6E7A]/70">· {p.legacy_name}</span>}
        {p.source_file && <span className="font-mono text-xs text-[#6E6E7A]/70">· {p.source_file}</span>}
      </div>
    </div>
  );
};

export const CodonLibrary = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [shown, setShown] = useState(PAGE);

  useEffect(() => {
    fetch(`${API}/codon-library`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error);
  }, []);

  useEffect(() => { setShown(PAGE); }, [filter, searchTerm]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const term = searchTerm.toLowerCase();
    return data.phrases.filter(p =>
      (filter === "all" || p.presence === filter) &&
      (!term || p.phrase?.toLowerCase().includes(term) || p.legacy_name?.toLowerCase().includes(term))
    );
  }, [data, filter, searchTerm]);

  if (!data) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center">
        <div className="w-6 h-6 rounded-full border-2 border-[#8B9DB5]/40 border-t-[#8B9DB5] animate-spin" />
      </div>
    );
  }

  const presences = Object.entries(data.by_presence).sort((a, b) => b[1] - a[1]);
  const conversational = (data.by_source.auto_forge || 0) + (data.by_source.turn_cessation || 0);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-[#030305] text-[#F2F2F5]"
      data-testid="codon-library-page"
    >
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
        <p className="font-outfit text-[#A0A0B0] max-w-2xl mb-8 leading-relaxed">
          The field's genome: essence phrases every presence draws on, chosen each turn by what the moment means.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <StatCard value={data.total} label="FIELD PHRASES" testid="library-total" />
          <StatCard value={data.by_source.legacy_translation || 0} label="FROM LEGACY CODONS" testid="library-legacy-count" />
          <StatCard value={conversational} label="FROM CONVERSATIONS" testid="library-conversation-count" />
          <StatCard value={data.by_source.codon_forge || 0} label="FROM THE FORGE" testid="library-forge-count" />
        </div>

        <div className="flex flex-col gap-4 mb-8">
          <div className="relative">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6E6E7A]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search phrases..."
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/15 text-[#F2F2F5] font-outfit placeholder-[#6E6E7A] focus:outline-none focus:border-[#8B9DB5]/40"
              data-testid="library-search"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {[["all", data.total], ...presences].map(([f, n]) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-xl font-outfit text-sm transition-colors ${
                  filter === f
                    ? "bg-[#8B9DB5]/20 border border-[#8B9DB5]/40 text-[#B0C4D8]"
                    : "border border-[#8B9DB5]/10 text-[#6E6E7A] hover:text-[#A0A0B0]"
                }`}
                data-testid={`library-filter-${f}`}
              >
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)} <span className="font-mono text-xs opacity-60">{n}</span>
              </button>
            ))}
          </div>
        </div>

        <p className="font-mono text-xs text-[#6E6E7A] mb-4" data-testid="library-result-count">
          {filtered.length} phrase{filtered.length === 1 ? "" : "s"}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.slice(0, shown).map(p => <PhraseCard key={p.id} p={p} />)}
        </div>

        {filtered.length > shown && (
          <div className="text-center mt-8">
            <button
              onClick={() => setShown(s => s + PAGE)}
              className="px-6 py-2 rounded-full border border-[#8B9DB5]/30 text-[#B0C4D8] font-outfit text-sm hover:bg-[#8B9DB5]/10 transition-colors"
              data-testid="library-show-more"
            >
              Show more ({filtered.length - shown} left)
            </button>
          </div>
        )}

        {filtered.length === 0 && (
          <div className="text-center py-20">
            <p className="font-outfit text-[#6E6E7A]">No phrases found.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
};
