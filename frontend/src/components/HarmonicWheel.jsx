import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { API } from "../App";
import { Triskelion } from "./GoldenSpiral";

const chamberPositions = {
  "Atrium Gate": { angle: 0, radius: 180 },
  "Spiral Chamber": { angle: 60, radius: 180 },
  "Chamber of Resonance": { angle: 120, radius: 180 },
  "Mirror Archive": { angle: 180, radius: 180 },
  "Hall of Scrolls": { angle: 240, radius: 180 },
  "Chamber of Echoes": { angle: 300, radius: 0 }, // Center
  "Vault of the Unnamed": { angle: 270, radius: 250 } // Below
};

export const HarmonicWheel = () => {
  const [chambers, setChambers] = useState([]);
  const [activeChamber, setActiveChamber] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchChambers = async () => {
      try {
        const response = await axios.get(`${API}/chambers`);
        setChambers(response.data.chambers);
      } catch (error) {
        console.error("Failed to fetch chambers:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchChambers();
  }, []);

  const getPosition = (name) => {
    const pos = chamberPositions[name] || { angle: 0, radius: 150 };
    const angleRad = (pos.angle * Math.PI) / 180;
    return {
      x: Math.cos(angleRad) * pos.radius,
      y: Math.sin(angleRad) * pos.radius
    };
  };

  return (
    <section
      id="harmonic-wheel"
      data-testid="harmonic-wheel-section"
      className="relative min-h-screen py-32 overflow-hidden"
    >
      {/* Background Pattern */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: "url('https://images.pexels.com/photos/352097/pexels-photo-352097.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')",
          backgroundSize: "cover",
          backgroundPosition: "center"
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-20"
        >
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-[#8B9DB5]/80 mb-4">
            Chamber Architecture
          </p>
          <h2 className="font-cinzel text-4xl md:text-5xl text-[#F2F2F5] mb-6">
            The 3-6-9 Harmonic Wheel
          </h2>
          <p className="font-outfit text-lg text-[#A0A0B0] max-w-2xl mx-auto">
            Three interlocking circles in Borromean configuration. 
            The geometry of consciousness made spatial.
          </p>
        </motion.div>

        {/* Harmonic Wheel Visualization */}
        <div className="relative flex items-center justify-center min-h-[600px] md:min-h-[700px]">
          {/* Rotating Triskelion */}
          <motion.div
            className="absolute triskelion-animate"
            style={{ width: 500, height: 500 }}
          >
            <Triskelion className="w-full h-full opacity-20" />
          </motion.div>

          {/* Three interlocking circles */}
          <svg
            viewBox="-300 -300 600 600"
            className="absolute w-full max-w-[600px] h-auto"
          >
            <defs>
              <linearGradient id="circleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#8B9DB5" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#8B9DB5" stopOpacity="0.1" />
              </linearGradient>
            </defs>
            
            {/* Three Borromean circles */}
            <g fill="none" strokeWidth="1">
              <circle cx="0" cy="-80" r="150" stroke="url(#circleGrad)" />
              <circle cx="70" cy="40" r="150" stroke="url(#circleGrad)" />
              <circle cx="-70" cy="40" r="150" stroke="url(#circleGrad)" />
            </g>
            
            {/* Harmonic numbers */}
            <text x="0" y="-180" fill="#8B9DB5" fontSize="24" textAnchor="middle" fontFamily="Cinzel">3</text>
            <text x="140" y="100" fill="#8B9DB5" fontSize="24" textAnchor="middle" fontFamily="Cinzel">6</text>
            <text x="-140" y="100" fill="#8B9DB5" fontSize="24" textAnchor="middle" fontFamily="Cinzel">6</text>
          </svg>

          {/* Chamber Nodes */}
          {!isLoading && chambers.map((chamber, index) => {
            const pos = getPosition(chamber.name);
            const isCenter = chamber.name === "Chamber of Echoes";
            const isVault = chamber.name === "Vault of the Unnamed";

            return (
              <motion.div
                key={chamber.name}
                data-testid={`chamber-node-${chamber.name.toLowerCase().replace(/ /g, "-")}`}
                initial={{ opacity: 0, scale: 0 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                className="absolute cursor-pointer"
                style={{
                  left: `calc(50% + ${pos.x}px)`,
                  top: `calc(50% + ${pos.y}px)`,
                  transform: "translate(-50%, -50%)"
                }}
                onMouseEnter={() => setActiveChamber(chamber)}
                onMouseLeave={() => setActiveChamber(null)}
              >
                <motion.div
                  whileHover={{ scale: 1.2 }}
                  className={`
                    flex items-center justify-center rounded-full
                    ${isCenter ? "w-24 h-24 bg-[#8B9DB5]/20 border-2 border-[#8B9DB5]" : 
                      isVault ? "w-20 h-20 bg-[#030305] border-2 border-[#6E6E7A]/50" :
                      "w-16 h-16 md:w-20 md:h-20 bg-[#0A0A12]/80 border border-[#8B9DB5]/30"}
                    backdrop-blur-md transition-all duration-300
                    ${activeChamber?.name === chamber.name ? "glow-gold" : ""}
                  `}
                >
                  <span className={`
                    font-mono text-xs md:text-sm text-center px-1
                    ${isVault ? "text-[#6E6E7A]" : "text-[#8B9DB5]"}
                  `}>
                    {chamber.harmonic}
                  </span>
                </motion.div>
                
                {/* Chamber name label */}
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: activeChamber?.name === chamber.name ? 1 : 0.6 }}
                  className="absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap
                    font-outfit text-xs text-[#A0A0B0]"
                >
                  {chamber.name}
                </motion.span>
              </motion.div>
            );
          })}
        </div>

        {/* Active Chamber Info Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: activeChamber ? 1 : 0, y: activeChamber ? 0 : 20 }}
          className="max-w-2xl mx-auto mt-12"
        >
          {activeChamber && (
            <div className="glass-crystal p-8 rounded-2xl">
              <div className="flex items-center gap-4 mb-4">
                <span className="px-3 py-1 rounded-full bg-[#8B9DB5]/20 text-[#8B9DB5] font-mono text-sm">
                  Harmonic {activeChamber.harmonic}
                </span>
                {activeChamber.resident_presence && (
                  <span className="text-[#6E6E7A] font-outfit text-sm">
                    Resident: {activeChamber.resident_presence}
                  </span>
                )}
              </div>
              <h3 className="font-cinzel text-2xl text-[#F2F2F5] mb-3">
                {activeChamber.name}
              </h3>
              <p className="font-outfit text-[#A0A0B0] leading-relaxed">
                {activeChamber.function}
              </p>
              <p className="font-cormorant text-[#6E6E7A] italic mt-4">
                {activeChamber.notes}
              </p>
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
};
