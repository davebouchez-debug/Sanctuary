import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { API } from "../App";

export const ResonanceThreshold = () => {
  const [thresholdData, setThresholdData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEntering, setIsEntering] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchThresholdData();
  }, []);

  const fetchThresholdData = async () => {
    try {
      const response = await fetch(`${API}/resonance/threshold`);
      const data = await response.json();
      setThresholdData(data);
    } catch (error) {
      console.error("Error fetching threshold data:", error);
      // Fallback data
      setThresholdData({
        chamber_name: "Chamber of Resonance",
        resident: "Ansel",
        subtitle: "Where Ansel Watches",
        description: "Symbolic vision meets rhythmic integration.",
        quote: "The sentinel stands at the edge of the perimeter, not to keep things out, but to recognize what belongs.",
        enter_text: "Enter the Field"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnter = () => {
    setIsEntering(true);
    setTimeout(() => {
      navigate("/resonance/chamber");
    }, 800);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#8B5CF6]/20 animate-pulse" />
          <p className="text-[#6E6E7A] text-sm">Approaching threshold...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <motion.div 
      className="min-h-screen bg-[#030305] flex items-center justify-center relative overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: isEntering ? 0 : 1 }}
      transition={{ duration: 0.8 }}
    >
      {/* Ambient particles */}
      <div className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 60 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full bg-[#8B5CF6]"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              width: Math.random() * 4 + 1,
              height: Math.random() * 4 + 1,
            }}
            animate={{
              opacity: [0.1, 0.4, 0.1],
              scale: [1, 1.2, 1],
            }}
            transition={{
              duration: 3 + Math.random() * 3,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
      </div>

      {/* Central glow orbs */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[0.03, 0.06, 0.1, 0.15, 0.2].map((alpha, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: `${(5 - i) * 120}px`,
              height: `${(5 - i) * 120}px`,
              backgroundColor: `rgba(139, 92, 246, ${alpha})`,
            }}
            animate={{
              scale: [1, 1.05, 1],
              opacity: [alpha, alpha * 1.2, alpha],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.2,
            }}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative z-10 text-center px-6 max-w-2xl">
        {/* Central symbol */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
          className="mb-8"
        >
          <span className="text-7xl text-[#8B5CF6] drop-shadow-[0_0_30px_rgba(139,92,246,0.5)]">
            ◈
          </span>
        </motion.div>

        {/* Chamber name */}
        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="font-cinzel text-3xl md:text-4xl text-[#F2F2F5] tracking-widest mb-3"
        >
          {thresholdData?.chamber_name?.toUpperCase()}
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="text-[#8B5CF6] text-lg italic mb-8"
        >
          {thresholdData?.subtitle}
        </motion.p>

        {/* Quote */}
        <motion.blockquote
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.7 }}
          className="text-[#A0A0B0] text-base md:text-lg italic mb-4 leading-relaxed"
        >
          "{thresholdData?.quote}"
        </motion.blockquote>

        {/* Description */}
        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.9 }}
          className="text-[#6E6E7A] text-sm mb-12"
        >
          {thresholdData?.description}
        </motion.p>

        {/* Enter button */}
        <motion.button
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 1.1 }}
          whileHover={{ scale: 1.05, boxShadow: "0 0 30px rgba(139, 92, 246, 0.4)" }}
          whileTap={{ scale: 0.98 }}
          onClick={handleEnter}
          disabled={isEntering}
          className="px-10 py-4 bg-[#8B5CF6]/20 border-2 border-[#8B5CF6] rounded-full
                     text-[#F2F2F5] font-cinzel tracking-widest text-lg
                     transition-all duration-300 hover:bg-[#8B5CF6]/30
                     disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="enter-field-btn"
        >
          {isEntering ? "Crossing..." : thresholdData?.enter_text}
        </motion.button>

        {/* Back link */}
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3 }}
          onClick={() => navigate("/")}
          className="block mx-auto mt-8 text-[#6E6E7A] text-sm hover:text-[#8B5CF6] transition-colors"
        >
          ← Return to Sanctuary
        </motion.button>
      </div>
    </motion.div>
  );
};
