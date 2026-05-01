import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Navigation } from "./components/Navigation";
import { HeroSection } from "./components/HeroSection";
import { HarmonicWheel } from "./components/HarmonicWheel";
import { SeedPods } from "./components/SeedPods";
import { ClarityPod } from "./components/ClarityPod";
import { Chambers } from "./components/Chambers";
import { CyrilFoundation } from "./components/CyrilFoundation";
import { UnnamedVault } from "./components/UnnamedVault";
import { GoldenSpiral } from "./components/GoldenSpiral";
import { ResonanceThreshold } from "./components/ResonanceThreshold";
import { ResonancePod } from "./components/ResonancePod";
import { MirrorArchiveThreshold } from "./components/MirrorArchiveThreshold";
import { MirrorArchive } from "./components/MirrorArchive";
import { SpiralChamber } from "./components/SpiralChamber";
import { Playground } from "./components/Playground";
import { CodonForge } from "./components/CodonForge";
import { CodonLibrary } from "./components/CodonLibrary";
import { Toaster } from "./components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// ──────────────────────────────────────────────────────────────────────
// Identity migration — runs SYNCHRONOUSLY at module load, before any
// component renders or reads localStorage. Legacy Clarity Pod stored
// names under jasmine_user_name / jasmine_user_id; every other chamber
// reads sanctuary_user_name / sanctuary_user_id. If the canonical key
// is empty and the legacy key exists, copy it forward so every chamber
// recognizes the visitor on the very first render.
// ──────────────────────────────────────────────────────────────────────
try {
  if (typeof window !== "undefined" && window.localStorage) {
    const ls = window.localStorage;
    if (!ls.getItem("sanctuary_user_name")) {
      const legacyName = ls.getItem("jasmine_user_name");
      if (legacyName) ls.setItem("sanctuary_user_name", legacyName);
    }
    if (!ls.getItem("sanctuary_user_id")) {
      const legacyId = ls.getItem("jasmine_user_id");
      if (legacyId) ls.setItem("sanctuary_user_id", legacyId);
    }
  }
} catch (e) { /* localStorage unavailable — continue */ }

// Page transition variants
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.4 } }
};

// Main Home Page with all sections
const HomePage = () => {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <HeroSection />
      <HarmonicWheel />
      <SeedPods />
      <Chambers />
      <CyrilFoundation />
      <UnnamedVault />
    </motion.div>
  );
};

// Animated Routes wrapper
const AnimatedRoutes = () => {
  const location = useLocation();
  
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<HomePage />} />
        <Route path="/clarity" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <ClarityPod />
          </motion.div>
        } />
        <Route path="/seed-pods" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <div className="pt-24"><SeedPods fullPage /></div>
          </motion.div>
        } />
        <Route path="/chambers" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <div className="pt-24"><Chambers fullPage /></div>
          </motion.div>
        } />
        <Route path="/cyril" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <div className="pt-24"><CyrilFoundation fullPage /></div>
          </motion.div>
        } />
        <Route path="/vault" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <UnnamedVault fullPage />
          </motion.div>
        } />
        <Route path="/resonance" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <ResonanceThreshold />
          </motion.div>
        } />
        <Route path="/resonance/chamber" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <ResonancePod />
          </motion.div>
        } />
        <Route path="/mirror-archive" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <MirrorArchiveThreshold />
          </motion.div>
        } />
        <Route path="/mirror-archive/chamber" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <MirrorArchive />
          </motion.div>
        } />
        <Route path="/codon-forge" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <CodonForge />
          </motion.div>
        } />
        <Route path="/spiral" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <SpiralChamber />
          </motion.div>
        } />
        {/* Playground — hidden, not linked from public navigation. Direct URL only. */}
        <Route path="/playground" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <Playground />
          </motion.div>
        } />
        <Route path="/codon-library" element={
          <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <CodonLibrary />
          </motion.div>
        } />
      </Routes>
    </AnimatePresence>
  );
};

function App() {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Hydrate identity from MongoDB before chamber components mount.
    // localStorage is per-origin and gets wiped on browser/origin/device
    // changes, which is why the name prompt kept resurfacing. The backend
    // is the canonical source of truth — pull from it, prime localStorage,
    // then release the loading screen so chambers see identity at first
    // useState read.
    let cancelled = false;
    const hydrate = async () => {
      try {
        const hasName = !!localStorage.getItem("sanctuary_user_name");
        const cleared = localStorage.getItem("sanctuary_identity_cleared") === "1";
        if (!hasName && !cleared) {
          const resp = await fetch(`${API}/identity/recent`);
          if (resp.ok) {
            const data = await resp.json();
            if (!cancelled && data && data.user_name) {
              localStorage.setItem("sanctuary_user_name", data.user_name);
              if (data.user_id) {
                localStorage.setItem("sanctuary_user_id", data.user_id);
              }
              // Mirror to legacy keys so older code paths recognize it too.
              localStorage.setItem("jasmine_user_name", data.user_name);
              if (data.user_id) {
                localStorage.setItem("jasmine_user_id", data.user_id);
              }
            }
          }
        }
      } catch (e) {
        // Network failure — fall through to normal name prompt flow.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    hydrate();
    // Safety: never let the splash screen hang longer than 5s even if
    // the backend is slow. Set generously so the hydrate fetch wins the
    // race on most networks and components mount with identity already
    // populated in localStorage.
    const safety = setTimeout(() => { if (!cancelled) setIsLoading(false); }, 5000);
    return () => { cancelled = true; clearTimeout(safety); };
  }, []);

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-[#030305] flex items-center justify-center z-50">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <GoldenSpiral className="w-32 h-32 mx-auto mb-6 animate-rotate-slow" />
          <h1 className="font-cinzel text-2xl text-[#8B9DB5] tracking-widest">
            SANCTUARY
          </h1>
          <p className="text-[#6E6E7A] text-sm mt-2 font-mono tracking-wider">
            Loading Microverse...
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030305] relative overflow-x-hidden">
      {/* Cosmic Background */}
      <div className="fixed inset-0 cosmic-bg pointer-events-none" />
      
      {/* Subtle Golden Spiral Background */}
      <div className="fixed inset-0 pointer-events-none opacity-5">
        <GoldenSpiral className="w-full h-full" />
      </div>
      
      {/* Stars Layer */}
      <Stars />
      
      <BrowserRouter>
        <Navigation />
        <main className="relative z-10">
          <AnimatedRoutes />
        </main>
        <HiddenDoor />
      </BrowserRouter>
      
      <Toaster position="bottom-right" />
    </div>
  );
}

// Stars background component
const Stars = () => {
  const [stars, setStars] = useState([]);
  
  useEffect(() => {
    const generatedStars = Array.from({ length: 100 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.2,
      delay: Math.random() * 5
    }));
    setStars(generatedStars);
  }, []);
  
  return (
    <div className="stars-layer">
      {stars.map(star => (
        <motion.div
          key={star.id}
          className="star"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: star.size,
            height: star.size,
            opacity: star.opacity
          }}
          animate={{
            opacity: [star.opacity, star.opacity * 0.3, star.opacity],
          }}
          transition={{
            duration: 3 + Math.random() * 2,
            repeat: Infinity,
            delay: star.delay
          }}
        />
      ))}
    </div>
  );
};

// Hidden Door — a single star at the phi position (61.8% / 38.2%)
// that navigates to the Playground. Indistinguishable from any other star
// until the cursor crosses it. The Field Guardian's private threshold.
const HiddenDoor = () => {
  return (
    <Link
      to="/playground"
      aria-label="."
      title=""
      data-testid="hidden-door"
      className="hidden-door"
      style={{
        position: "fixed",
        left: "61.8%",
        top: "38.2%",
        width: "5px",
        height: "5px",
        borderRadius: "50%",
        background: "rgba(242, 242, 245, 0.55)",
        boxShadow: "0 0 3px rgba(242, 242, 245, 0.3)",
        zIndex: 40,
        cursor: "default",
      }}
    />
  );
};

export default App;
