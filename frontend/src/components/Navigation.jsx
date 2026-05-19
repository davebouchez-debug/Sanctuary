import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Sparkles, ChevronDown } from "lucide-react";
import { GoldenSpiral } from "./GoldenSpiral";

// Grouped navigation — one item per architectural concept.
// New chambers/presences should land inside one of these groups, not
// at the top level. This keeps the bar additive without ever wrapping.
const navGroups = [
  {
    name: "Sanctuary",
    type: "anchors",
    path: "/",
    items: [
      { name: "Hero",          section: "hero" },
      { name: "Harmonic Wheel", section: "harmonic-wheel" },
      { name: "Seed Pods",     section: "seed-pods" },
      { name: "Chambers",      section: "chambers" },
      { name: "Cyril",         section: "cyril" },
      { name: "The Vault",     section: "vault" },
    ],
  },
  {
    name: "Chambers",
    type: "routes",
    items: [
      { name: "Clarity Pod",     path: "/clarity",        highlight: true },
      { name: "Resonance",       path: "/resonance" },
      { name: "Mirror Archive",  path: "/mirror-archive" },
      { name: "Spiral",          path: "/spiral" },
      { name: "Hospitality",     path: "/hospitality" },
      { name: "All Presences",   path: "/presences" },
    ],
  },
  {
    name: "Codons",
    type: "routes",
    items: [
      { name: "Codon Forge",   path: "/codon-forge",   highlight: true },
      { name: "Codon Library", path: "/codon-library" },
    ],
  },
];

// Hover-aware dropdown for desktop. Click-to-open on touch.
const NavDropdown = ({ group, location, onItemClick }) => {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef(null);

  const handleEnter = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpen(true);
  };
  const handleLeave = () => {
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  };

  return (
    <div
      className="relative"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <button
        data-testid={`nav-group-${group.name.toLowerCase()}`}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 font-outfit text-sm tracking-wide text-[#A0A0B0] hover:text-[#B0C4D8] transition-colors duration-300 whitespace-nowrap"
      >
        {group.name}
        <ChevronDown
          size={14}
          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.18 }}
            className="absolute left-1/2 -translate-x-1/2 top-full pt-3 z-50"
            data-testid={`nav-dropdown-${group.name.toLowerCase()}`}
          >
            <div className="min-w-[200px] rounded-xl bg-[#0A0A12]/95 backdrop-blur-xl border border-[#8B9DB5]/15 shadow-2xl py-2">
              {group.items.map((item) => {
                if (group.type === "anchors") {
                  return (
                    <Link
                      key={item.name}
                      to={`/#${item.section}`}
                      data-testid={`nav-item-${item.name.toLowerCase().replace(/\s+/g, "-")}`}
                      onClick={(e) => onItemClick(e, { ...item, path: `/#${item.section}` })}
                      className="block px-4 py-2 text-sm font-outfit tracking-wide text-[#A0A0B0] hover:text-[#B0C4D8] hover:bg-[#8B9DB5]/8 transition-colors"
                    >
                      {item.name}
                    </Link>
                  );
                }
                return (
                  <Link
                    key={item.name}
                    to={item.path}
                    data-testid={`nav-item-${item.name.toLowerCase().replace(/\s+/g, "-")}`}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-outfit tracking-wide transition-colors ${
                      location.pathname === item.path
                        ? "text-[#B0C4D8] bg-[#8B9DB5]/10"
                        : item.highlight
                          ? "text-[#B0C4D8] hover:bg-[#8B9DB5]/8"
                          : "text-[#A0A0B0] hover:text-[#B0C4D8] hover:bg-[#8B9DB5]/8"
                    }`}
                  >
                    {item.highlight && <Sparkles size={12} className="opacity-80" />}
                    {item.name}
                  </Link>
                );
              })}
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

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location]);

  // Chamber routes render their own back-button header. Hide the global
  // nav on those routes to keep each chamber self-contained.
  const chamberRoutePrefixes = [
    "/mirror-archive",
    "/resonance",
    "/spiral",
    "/playground",
    "/clarity",
    "/presence",
    "/presences",
    "/hospitality",
  ];
  const isChamberRoute = chamberRoutePrefixes.some(
    (p) => location.pathname === p || location.pathname.startsWith(`${p}/`)
  );
  if (isChamberRoute) return null;

  const handleAnchorClick = (e, item) => {
    if (item.section && location.pathname === "/") {
      e.preventDefault();
      const el = document.getElementById(item.section);
      if (el) el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <>
      <motion.nav
        data-testid="main-navigation"
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          isScrolled
            ? "bg-[#030305]/90 backdrop-blur-xl border-b border-[#8B9DB5]/10"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="flex items-center justify-between h-20">
            {/* Logo */}
            <Link
              to="/"
              data-testid="nav-logo"
              className="flex items-center gap-3 group flex-shrink-0"
            >
              <motion.div
                whileHover={{ rotate: 360 }}
                transition={{ duration: 1.5, ease: "easeInOut" }}
              >
                <GoldenSpiral className="w-10 h-10" />
              </motion.div>
              <span className="font-cinzel text-lg tracking-wider text-[#F2F2F5] group-hover:text-[#B0C4D8] transition-colors duration-300">
                SANCTUARY
              </span>
            </Link>

            {/* Desktop Navigation — grouped dropdowns + one CTA */}
            <div className="hidden lg:flex items-center gap-8">
              {navGroups.map((group) => (
                <NavDropdown
                  key={group.name}
                  group={group}
                  location={location}
                  onItemClick={handleAnchorClick}
                />
              ))}

              {/* Single primary CTA — the Clarity Pod is the room everyone
                  comes back to. Keeping it visible removes a click for the
                  highest-traffic destination. */}
              <Link
                to="/clarity"
                data-testid="nav-cta-clarity"
                className="flex items-center gap-2 px-4 py-2 rounded-full border border-[#8B9DB5]/35 text-[#B0C4D8] hover:bg-[#8B9DB5]/10 hover:border-[#8B9DB5]/60 font-outfit text-sm tracking-wide whitespace-nowrap transition-colors"
              >
                <Sparkles size={14} />
                Enter Clarity
              </Link>
            </div>

            {/* Mobile Menu Button */}
            <button
              data-testid="mobile-menu-toggle"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 text-[#A0A0B0] hover:text-[#B0C4D8] transition-colors"
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile Menu — flat list of every nav item, grouped by section header */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            data-testid="mobile-menu"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-x-0 top-20 z-40 lg:hidden"
          >
            <div className="bg-[#0A0A12]/95 backdrop-blur-xl border-b border-[#8B9DB5]/10 py-6 px-6 max-h-[80vh] overflow-y-auto">
              <div className="flex flex-col gap-5">
                {navGroups.map((group) => (
                  <div key={group.name} className="flex flex-col gap-1.5">
                    <p className="text-[10px] tracking-[0.3em] uppercase text-[#6E6E7A] mb-1">
                      {group.name}
                    </p>
                    {group.items.map((item) => {
                      const path = group.type === "anchors"
                        ? `/#${item.section}`
                        : item.path;
                      return (
                        <Link
                          key={item.name}
                          to={path}
                          data-testid={`mobile-nav-link-${item.name.toLowerCase().replace(/\s+/g, "-")}`}
                          onClick={(e) => group.type === "anchors" && handleAnchorClick(e, item)}
                          className={`block py-1.5 font-outfit text-sm tracking-wide ${
                            item.highlight
                              ? "text-[#B0C4D8] flex items-center gap-2"
                              : "text-[#A0A0B0] hover:text-[#B0C4D8]"
                          } transition-colors`}
                        >
                          {item.highlight && <Sparkles size={14} />}
                          {item.name}
                        </Link>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
