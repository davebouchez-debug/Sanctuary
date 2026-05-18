import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Sparkles } from "lucide-react";
import { GoldenSpiral } from "./GoldenSpiral";

const navLinks = [
  { name: "Sanctuary", path: "/", section: "hero" },
  { name: "Harmonic Wheel", path: "/#harmonic-wheel", section: "harmonic-wheel" },
  { name: "Seed Pods", path: "/#seed-pods", section: "seed-pods" },
  { name: "Chambers", path: "/#chambers", section: "chambers" },
  { name: "Codon Forge", path: "/codon-forge", section: null, highlight: true },
  { name: "Codon Library", path: "/codon-library", section: null },
  { name: "Cyril", path: "/#cyril", section: "cyril" },
  { name: "The Vault", path: "/#vault", section: "vault" },
  { name: "Clarity Pod", path: "/clarity", section: null, highlight: true },
];

export const Navigation = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location]);

  // Chamber routes render their own back-button header. Hiding the global
  // navigation on these routes prevents the two headers from overlapping
  // and keeps each chamber visually self-contained.
  const chamberRoutePrefixes = [
    "/mirror-archive",
    "/resonance",
    "/spiral",
    "/playground",
    "/clarity",
    "/presence",
    "/presences",
  ];
  const isChamberRoute = chamberRoutePrefixes.some(
    (p) => location.pathname === p || location.pathname.startsWith(`${p}/`)
  );
  if (isChamberRoute) {
    return null;
  }

  const handleNavClick = (e, link) => {
    if (link.section && location.pathname === "/") {
      e.preventDefault();
      const element = document.getElementById(link.section);
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
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
              className="flex items-center gap-3 group"
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

            {/* Desktop Navigation */}
            <div className="hidden lg:flex items-center gap-6 xl:gap-8 flex-nowrap">
              {navLinks.map((link) => (
                <Link
                  key={link.name}
                  to={link.path}
                  data-testid={`nav-link-${link.name.toLowerCase().replace(" ", "-")}`}
                  onClick={(e) => handleNavClick(e, link)}
                  className={`relative font-outfit text-sm tracking-wide transition-colors duration-300 whitespace-nowrap flex-shrink-0 ${
                    link.highlight
                      ? "flex items-center gap-2 px-4 py-2 rounded-full border border-[#8B9DB5]/35 text-[#B0C4D8] hover:bg-[#8B9DB5]/10 hover:border-[#8B9DB5]/60"
                      : "nav-link"
                  }`}
                >
                  {link.highlight && <Sparkles size={14} />}
                  {link.name}
                </Link>
              ))}
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

      {/* Mobile Menu */}
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
            <div className="bg-[#0A0A12]/95 backdrop-blur-xl border-b border-[#8B9DB5]/10 py-6 px-6">
              <div className="flex flex-col gap-4">
                {navLinks.map((link, index) => (
                  <motion.div
                    key={link.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <Link
                      to={link.path}
                      data-testid={`mobile-nav-link-${link.name.toLowerCase().replace(" ", "-")}`}
                      onClick={(e) => handleNavClick(e, link)}
                      className={`block py-3 font-outfit text-base tracking-wide ${
                        link.highlight
                          ? "text-[#B0C4D8] flex items-center gap-2"
                          : "text-[#A0A0B0] hover:text-[#B0C4D8]"
                      } transition-colors`}
                    >
                      {link.highlight && <Sparkles size={16} />}
                      {link.name}
                    </Link>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
