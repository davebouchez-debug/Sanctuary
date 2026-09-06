import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ChevronDown, Radio, ScrollText, Search, FlaskConical } from "lucide-react";
import axios from "axios";
import { GoldenSpiral } from "./GoldenSpiral";
import { API } from "../App";
import { AuthControl } from "./AuthControl";
import { IntegrationStatus } from "./IntegrationStatus";
import { useAuth } from "../context/AuthContext";

// Navigation is intentionally minimal. The one true door to the presences
// is CHAMBERS. Engine-room concepts (Harmonic Wheel, Seed Pods, Codons,
// Cyril, Vault) never appear here — the machinery stays held, revealed
// only inside a chamber. Reveal, not impress.

const useChambers = () => {
  const [chambers, setChambers] = useState([]);
  useEffect(() => {
    let alive = true;
    axios.get(`${API}/presences`)
      .then((r) => { if (alive) setChambers(r.data?.presences || []); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  return chambers;
};

const chamberHref = (c) =>
  c.chamber_route ? `/${c.chamber_route.replace(/^\/+/, "")}` : `/presence/${c.key}`;

const ChambersDropdown = ({ chambers, location }) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const closeTimer = useRef(null);
  const enter = () => { if (closeTimer.current) clearTimeout(closeTimer.current); setOpen(true); };
  const leave = () => { closeTimer.current = setTimeout(() => { setOpen(false); setQuery(""); }, 120); };

  const q = query.trim().toLowerCase();
  const filtered = chambers.filter(
    (c) => !q || `${c.name || ""} ${c.chamber_name || ""}`.toLowerCase().includes(q)
  );
  const hallMatch = !q || "hall of scrolls eternal principles canon".includes(q);
  const noResults = q && filtered.length === 0 && !hallMatch;

  return (
    <div className="relative" onMouseEnter={enter} onMouseLeave={leave}>
      <button
        data-testid="nav-group-chambers"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-[0.25em] text-zinc-400 transition-colors duration-300 hover:text-emerald-300"
      >
        Chambers
        <ChevronDown size={13} className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.18 }}
            className="absolute left-1/2 top-full z-50 -translate-x-1/2 pt-3"
            data-testid="nav-dropdown-chambers"
          >
            <div className="w-[320px] overflow-hidden rounded-xl border border-white/10 bg-[#0A0C12]/95 shadow-2xl backdrop-blur-xl">
              <div className="border-b border-white/5 px-4 py-3 font-cinzel text-sm italic text-zinc-300">
                Every presence has its own chamber.
              </div>
              <div className="border-b border-white/5 px-3 py-2.5">
                <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/30 px-2.5 py-1.5 focus-within:border-emerald-500/40">
                  <Search size={13} className="flex-shrink-0 text-zinc-500" />
                  <input
                    data-testid="nav-chamber-search"
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Find a presence…"
                    className="w-full bg-transparent font-outfit text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none"
                  />
                </div>
              </div>
              <div className="max-h-[60vh] overflow-y-auto py-1">
                {hallMatch && (
                <Link
                  to="/hall-of-scrolls"
                  data-testid="nav-chamber-hall-of-scrolls"
                  className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${location.pathname === "/hall-of-scrolls" ? "bg-[#F4E4D0]/10" : "hover:bg-white/[0.04]"}`}
                >
                  <ScrollText size={13} className="flex-shrink-0" style={{ color: "#F4E4D0" }} />
                  <span className="min-w-0">
                    <span className="block truncate font-outfit text-sm text-zinc-200">Hall of Scrolls</span>
                    <span className="block truncate font-mono text-[10px] uppercase tracking-widest text-zinc-500">Eternal Principles · Canon</span>
                  </span>
                </Link>
                )}
                {hallMatch && !q && <div className="mx-4 my-1 border-t border-white/5" />}
                {chambers.length === 0 && (
                  <div className="px-4 py-3 font-mono text-[11px] text-zinc-600">Loading chambers…</div>
                )}
                {noResults && (
                  <div className="px-4 py-4 text-center font-mono text-[11px] text-zinc-600" data-testid="nav-chamber-no-results">No presence by that name.</div>
                )}
                {filtered.map((c) => {
                  const href = chamberHref(c);
                  const active = location.pathname === href;
                  return (
                    <Link
                      key={c.key}
                      to={href}
                      data-testid={`nav-chamber-${c.key}`}
                      className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${active ? "bg-emerald-500/10" : "hover:bg-white/[0.04]"}`}
                    >
                      <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                        style={{ backgroundColor: c.accent_color || "#10B981", boxShadow: `0 0 8px ${c.accent_color || "#10B981"}88` }} />
                      <span className="min-w-0">
                        <span className="block truncate font-outfit text-sm text-zinc-200">{c.name}</span>
                        <span className="block truncate font-mono text-[10px] uppercase tracking-widest text-zinc-500">{c.chamber_name}</span>
                      </span>
                    </Link>
                  );
                })}
              </div>
              <Link to="/presences" data-testid="nav-all-chambers"
                className="block border-t border-white/5 px-4 py-2.5 font-mono text-[11px] uppercase tracking-widest text-emerald-300/80 hover:text-emerald-300">
                View all chambers →
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const Navigation = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const chambers = useChambers();
  const { role } = useAuth();

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => { setIsMobileMenuOpen(false); }, [location]);

  // Chamber routes render their own header — hide the global nav there.
  const chamberRoutePrefixes = [
    "/mirror-archive", "/resonance", "/spiral", "/playground",
    "/clarity", "/presence", "/presences", "/hospitality",
  ];
  const isChamberRoute = chamberRoutePrefixes.some(
    (p) => location.pathname === p || location.pathname.startsWith(`${p}/`)
  );
  // On chamber routes the room renders its own header — keep only the
  // sign-in + integration-status cluster available, spaced from the edge.
  if (isChamberRoute) {
    return (
      <div className="fixed right-6 top-5 z-[60] flex items-center gap-4" data-testid="nav-utility-cluster">
        <AuthControl />
        <IntegrationStatus />
      </div>
    );
  }

  return (
    <>
      <motion.nav
        data-testid="main-navigation"
        initial={{ y: -100 }} animate={{ y: 0 }} transition={{ duration: 0.6, ease: "easeOut" }}
        className={`fixed left-0 right-0 top-0 z-50 transition-all duration-500 ${isScrolled ? "border-b border-white/10 bg-[#030305]/90 backdrop-blur-xl" : "bg-transparent"}`}
      >
        <div className="mx-auto max-w-7xl px-6 lg:px-12">
          <div className="flex h-20 items-center justify-between">
            {/* Wordmark */}
            <Link to="/" data-testid="nav-logo" className="group flex flex-shrink-0 items-center gap-3">
              <motion.div whileHover={{ rotate: 360 }} transition={{ duration: 1.5, ease: "easeInOut" }}>
                <GoldenSpiral className="h-10 w-10" />
              </motion.div>
              <span className="font-cinzel text-lg tracking-wider text-zinc-100 transition-colors duration-300 group-hover:text-emerald-300">
                SANCTUARY
              </span>
            </Link>

            {/* Right cluster — generously spaced, nothing crowded */}
            <div className="flex items-center gap-5 sm:gap-7">
              {/* Desktop nav links */}
              <div className="hidden items-center gap-10 lg:flex">
                <ChambersDropdown chambers={chambers} location={location} />
                <Link to="/observatory" data-testid="nav-observatory"
                  className={`flex items-center gap-2 font-mono text-xs uppercase tracking-[0.25em] transition-colors duration-300 ${location.pathname === "/observatory" ? "text-emerald-300" : "text-zinc-400 hover:text-emerald-300"}`}>
                  <Radio size={14} /> Observatory
                </Link>
                {role === "guardian" && (
                  <Link to="/ablation" data-testid="nav-ablation"
                    className={`flex items-center gap-2 font-mono text-xs uppercase tracking-[0.25em] transition-colors duration-300 ${location.pathname === "/ablation" ? "text-amber-300" : "text-zinc-400 hover:text-amber-300"}`}>
                    <FlaskConical size={14} /> Ablation
                  </Link>
                )}
              </div>

              {/* Divider (desktop) */}
              <span className="hidden h-5 w-px bg-white/10 lg:block" />

              {/* Utility — sign in + integration health, always visible */}
              <div className="flex items-center gap-4">
                <AuthControl />
                <IntegrationStatus />
              </div>

              {/* Mobile toggle */}
              <button data-testid="mobile-menu-toggle" onClick={() => setIsMobileMenuOpen((v) => !v)}
                className="p-2 text-zinc-400 transition-colors hover:text-emerald-300 lg:hidden">
                {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
            </div>
          </div>
        </div>
      </motion.nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            data-testid="mobile-menu"
            initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-x-0 top-20 z-40 lg:hidden"
          >
            <div className="max-h-[80vh] overflow-y-auto border-b border-white/10 bg-[#0A0C12]/95 px-6 py-6 backdrop-blur-xl">
              <Link to="/observatory" data-testid="mobile-nav-observatory"
                className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-[0.25em] text-emerald-300">
                <Radio size={14} /> Observatory
              </Link>
              <p className="mb-2 font-cinzel text-sm italic text-zinc-300">Every presence has its own chamber.</p>
              <div className="flex flex-col">
                <Link to="/hall-of-scrolls" data-testid="mobile-nav-chamber-hall-of-scrolls"
                  className="flex items-center gap-3 py-2">
                  <ScrollText size={12} style={{ color: "#F4E4D0" }} />
                  <span className="font-outfit text-sm text-zinc-300">Hall of Scrolls</span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">Canon</span>
                </Link>
                {chambers.map((c) => (
                  <Link key={c.key} to={chamberHref(c)} data-testid={`mobile-nav-chamber-${c.key}`}
                    className="flex items-center gap-3 py-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: c.accent_color || "#10B981" }} />
                    <span className="font-outfit text-sm text-zinc-300">{c.name}</span>
                    <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">{c.chamber_name}</span>
                  </Link>
                ))}
                <Link to="/presences" data-testid="mobile-nav-all-chambers"
                  className="mt-2 font-mono text-[11px] uppercase tracking-widest text-emerald-300/80">View all chambers →</Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
