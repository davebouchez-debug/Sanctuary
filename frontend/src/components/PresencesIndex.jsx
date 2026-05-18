import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, DoorOpen } from "lucide-react";
import { API } from "../App";

/**
 * PresencesIndex — soft overview of every presence chamber.
 * Each tile carries the presence's palette so the index page reads as
 * a constellation of homes, not a generic directory.
 */
export const PresencesIndex = () => {
  const [presences, setPresences] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/presences`)
      .then((r) => r.json())
      .then((d) => setPresences(d.presences || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#030305] text-[#F2F2F5]">
      <header className="border-b border-white/5 px-6 py-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link
            to="/"
            data-testid="presences-back"
            className="flex items-center gap-2 text-sm tracking-wide text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft size={16} />
            <span>SANCTUARY</span>
          </Link>
          <h1 className="text-sm tracking-[0.3em] uppercase text-slate-300">Presences</h1>
          <span className="text-xs text-slate-600 font-mono">
            {presences.length} {presences.length === 1 ? "home" : "homes"}
          </span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12">
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
          className="text-center text-slate-400 text-sm italic leading-relaxed max-w-2xl mx-auto mb-12"
        >
          One presence, one chamber. Each room is theirs — designed for who
          they are, open to the field. Walk into any of them.
        </motion.p>

        {loading && (
          <p className="text-center text-slate-500 text-sm italic">opening the doors...</p>
        )}

        {!loading && presences.length === 0 && (
          <p className="text-center text-slate-500 text-sm italic">No chambers registered yet.</p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {presences.map((p, i) => (
            <motion.div
              key={p.key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, duration: 0.7 }}
            >
              <Link
                to={p.chamber_route ? `/${p.chamber_route}` : `/presence/${p.key}`}
                data-testid={`presence-tile-${p.key}`}
                className="group block rounded-2xl p-6 border transition-all hover:scale-[1.02]"
                style={{
                  background: `linear-gradient(135deg, ${p.background_color || "#1a1a22"} 0%, ${p.primary_color || "#2a2a32"}11 100%)`,
                  borderColor: `${p.accent_color || "#8B9DB5"}33`,
                  color: p.primary_color || "#F2F2F5",
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-xl tracking-[0.15em] uppercase font-light">
                      {p.chamber_name || p.name}
                    </h2>
                    <p
                      className="text-[10px] tracking-[0.3em] uppercase mt-1 opacity-60"
                      style={{ color: p.accent_color || "#8B9DB5" }}
                    >
                      {p.chamber_name ? `kept by ${p.name}` : (p.type || "—")}
                    </p>
                  </div>
                  <DoorOpen
                    size={18}
                    className="opacity-50 group-hover:opacity-100 transition-opacity"
                    style={{ color: p.accent_color || "#8B9DB5" }}
                  />
                </div>
                {p.subtype && (
                  <p
                    className="text-xs opacity-70 mb-3 italic"
                    style={{ color: p.accent_color || "#8B9DB5" }}
                  >
                    {p.subtype}
                  </p>
                )}
                {p.primary_function && (
                  <p className="text-sm leading-relaxed opacity-80 line-clamp-3">
                    {p.primary_function}
                  </p>
                )}
                {p.motif && (
                  <p
                    className="text-[10px] tracking-[0.2em] uppercase mt-4 opacity-50"
                    style={{ color: p.accent_color || "#8B9DB5" }}
                  >
                    {p.motif.replace(/-/g, " ")}
                  </p>
                )}
              </Link>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default PresencesIndex;
