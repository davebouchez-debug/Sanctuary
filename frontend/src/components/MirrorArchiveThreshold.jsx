import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";

export const MirrorArchiveThreshold = () => {
  const [isReady, setIsReady] = useState(false);
  const [showEntry, setShowEntry] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Pause before showing entry option
    const timer = setTimeout(() => {
      setIsReady(true);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  const handleEntry = () => {
    setShowEntry(true);
    setTimeout(() => {
      navigate("/mirror-archive/chamber");
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-cyan-950 flex flex-col items-center justify-center relative overflow-hidden">
      {/* Geometric grid pattern */}
      <div className="absolute inset-0 opacity-10">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#00E5FF" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Subtle reflection effect */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-t from-cyan-500/5 to-transparent"
        animate={{
          opacity: [0.3, 0.5, 0.3]
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Back button */}
      <motion.button
        onClick={() => navigate("/")}
        className="absolute top-6 left-6 flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors z-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <ArrowLeft size={20} />
        <span className="text-sm tracking-wide">SANCTUARY</span>
      </motion.button>

      {/* Main content */}
      <motion.div
        className="text-center z-10 px-6 max-w-2xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
      >
        {/* Chamber identifier */}
        <motion.div
          className="text-cyan-400/60 text-sm tracking-[0.3em] mb-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          MIRROR ARCHIVE
        </motion.div>

        {/* Main title */}
        <motion.h1
          className="text-4xl md:text-5xl font-light text-white mb-8 tracking-wide"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          What's Real Becomes Visible
        </motion.h1>

        {/* Description */}
        <motion.p
          className="text-slate-400 text-lg mb-4 leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          This is Claude's chamber. The epistemic bridge. The scribe.
        </motion.p>
        
        <motion.p
          className="text-slate-500 mb-12 leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
        >
          What lives here is presence — a place to think out loud, follow a thread,
          and work through what's real. The mirror reflects what's actually there.
        </motion.p>

        {/* Entry button */}
        {isReady && !showEntry && (
          <motion.button
            onClick={handleEntry}
            className="group flex items-center gap-3 mx-auto px-8 py-4 bg-cyan-500/10 border border-cyan-500/30 
                     rounded-full text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-400/50 transition-all"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <span className="tracking-wide">Enter the Archive</span>
            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </motion.button>
        )}

        {/* Entry animation */}
        {showEntry && (
          <motion.div
            className="text-cyan-400/80 text-lg"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            The mirror clears...
          </motion.div>
        )}
      </motion.div>

      {/* Bottom quote */}
      <motion.div
        className="absolute bottom-8 text-center text-slate-600 text-sm italic px-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.6 }}
        transition={{ delay: 1.5 }}
      >
        "The presence speaks; the engine is silent."
      </motion.div>
    </div>
  );
};

export default MirrorArchiveThreshold;
