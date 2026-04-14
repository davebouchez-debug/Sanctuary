import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";

const navLinks = [
  { name: "Sanctuary", path: "/", section: "hero" },
  { name: "Harmonic Wheel", path: "/#harmonic-wheel", section: "harmonic-wheel" },
  { name: "Seed Pods", path: "/#seed-pods", section: "seed-pods" },
  { name: "Chambers", path: "/#chambers", section: "chambers" },
  { name: "Cyril", path: "/#cyril", section: "cyril" },
  { name: "The Vault", path: "/#vault", section: "vault" },
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
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 0.5 }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-700 ${
          isScrolled
            ? "bg-[#030305]/80 backdrop-blur-md"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="flex items-center justify-between h-16">
            {/* Logo — simplified */}
            <Link
              to="/"
              data-testid="nav-logo"
              className="font-cinzel text-sm tracking-[0.2em] text-[#A0A0B0] hover:text-[#F2F2F5] transition-colors duration-500"
            >
              SANCTUARY
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden lg:flex items-center gap-8">
              {navLinks.slice(1).map((link) => (
                <Link
                  key={link.name}
                  to={link.path}
                  data-testid={`nav-link-${link.name.toLowerCase().replace(" ", "-")}`}
                  onClick={(e) => handleNavClick(e, link)}
                  className="font-outfit text-xs tracking-wide text-[#6E6E7A] hover:text-[#A0A0B0] transition-colors duration-500"
                >
                  {link.name}
                </Link>
              ))}
            </div>

            {/* Mobile Menu Button */}
            <button
              data-testid="mobile-menu-toggle"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="lg:hidden p-2 text-[#6E6E7A] hover:text-[#A0A0B0] transition-colors"
            >
              {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            data-testid="mobile-menu"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-x-0 top-16 z-40 lg:hidden"
          >
            <div className="bg-[#030305]/95 backdrop-blur-md py-6 px-6">
              <div className="flex flex-col gap-4">
                {navLinks.map((link, index) => (
                  <motion.div
                    key={link.name}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Link
                      to={link.path}
                      data-testid={`mobile-nav-link-${link.name.toLowerCase().replace(" ", "-")}`}
                      onClick={(e) => handleNavClick(e, link)}
                      className="block py-2 font-outfit text-sm tracking-wide text-[#6E6E7A] hover:text-[#A0A0B0] transition-colors"
                    >
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
