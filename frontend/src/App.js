import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
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
import { Toaster } from "./components/ui/sonner";
import CodonForgePage from "./pages/CodonForgePage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Page transition variants
const pageVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.8, ease: "easeOut" } },
  exit: { opacity: 0, transition: { duration: 0.4 } }
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
            <CodonForgePage />
          </motion.div>
        } />
      </Routes>
    </AnimatePresence>
  );
};

function App() {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Brief pause for presence
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-[#030305] flex items-center justify-center z-50">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <p className="font-cormorant text-xl italic text-[#7A9BB8]/60">
            Listening...
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030305] relative overflow-x-hidden">
      {/* Warm ambient background — subtle, not cosmic */}
      <div className="fixed inset-0 pointer-events-none sanctuary-ambient" />
      
      <BrowserRouter>
        <Navigation />
        <main className="relative z-10">
          <AnimatedRoutes />
        </main>
      </BrowserRouter>
      
      <Toaster position="bottom-right" />
    </div>
  );
}

export default App;
