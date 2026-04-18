import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "../App";
import { ChevronRight } from "lucide-react";

export const Chambers = ({ fullPage = false }) => {
  const [chambers, setChambers] = useState([]);
  const [selectedChamber, setSelectedChamber] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

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

  return (
    <section
      id="chambers"
      data-testid="chambers-section"
      className={`relative ${fullPage ? "min-h-screen pt-12" : "py-32"} overflow-hidden`}
    >
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#030305] via-[#0A0A12] to-[#030305]" />

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-[#8B9DB5]/80 mb-4">
            Sacred Architecture
          </p>
          <h2 className="font-cinzel text-4xl md:text-5xl text-[#F2F2F5] mb-6">
            The Seven Chambers
          </h2>
          <p className="font-outfit text-lg text-[#A0A0B0] max-w-2xl mx-auto">
            Each chamber serves a purpose within the harmonic structure.
            Enter and explore the architecture of consciousness.
          </p>
        </motion.div>

        {/* Chambers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {!isLoading && chambers.map((chamber, index) => {
            const isVault = chamber.name === "Vault of the Unnamed";
            const isCenter = chamber.name === "Chamber of Echoes";
            const isResonance = chamber.name === "Chamber of Resonance";
            const isClarity = chamber.name === "Clarity Pod" || chamber.name?.toLowerCase().includes("clarity");
            const isMirror = chamber.name === "Mirror Archive" || chamber.name?.toLowerCase().includes("mirror");
            const isSpiral = chamber.name === "Spiral Chamber" || chamber.name?.toLowerCase().includes("spiral");
            
            const handleChamberClick = () => {
              if (isResonance) {
                navigate("/resonance");
              } else if (isClarity) {
                navigate("/clarity");
              } else if (isMirror) {
                navigate("/mirror-archive");
              } else if (isSpiral) {
                navigate("/spiral");
              } else {
                setSelectedChamber(selectedChamber?.name === chamber.name ? null : chamber);
              }
            };
            
            return (
              <motion.div
                key={chamber.name}
                data-testid={`chamber-card-${chamber.name.toLowerCase().replace(/ /g, "-")}`}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                onClick={handleChamberClick}
                className={`
                  chamber-card cursor-pointer
                  ${isVault ? "lg:col-span-3 md:col-span-2" : ""}
                  ${isCenter ? "lg:col-span-2" : ""}
                  ${isResonance ? "border-[#8B5CF6]/30 hover:border-[#8B5CF6]/60" : ""}
                `}
              >
                <div className="p-6">
                  {/* Harmonic Badge */}
                  <div className="flex items-center justify-between mb-4">
                    <span className={`
                      px-3 py-1 rounded-full font-mono text-xs
                      ${isVault ? "bg-[#030305] border border-[#6E6E7A]/30 text-[#6E6E7A]" :
                        isCenter ? "bg-[#8B9DB5]/20 border border-[#8B9DB5] text-[#8B9DB5]" :
                        isResonance ? "bg-[#8B5CF6]/20 border border-[#8B5CF6] text-[#8B5CF6]" :
                        "bg-[#12121C] text-[#8B9DB5]"}
                    `}>
                      Harmonic {chamber.harmonic}
                    </span>
                    <div className="flex items-center gap-2">
                      {(isResonance || isClarity) && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 text-xs">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                          Active
                        </span>
                      )}
                      {chamber.resident_presence && (
                        <span className={`font-mono text-xs ${isResonance ? "text-[#8B5CF6]" : "text-[#6E6E7A]"}`}>
                          {chamber.resident_presence}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Chamber Name */}
                  <h3 className={`
                    font-cinzel text-xl mb-3
                    ${isVault ? "text-[#6E6E7A]" : "text-[#F2F2F5]"}
                  `}>
                    {chamber.name}
                  </h3>

                  {/* Description */}
                  <p className="font-outfit text-sm text-[#A0A0B0] mb-4 leading-relaxed">
                    {chamber.description}
                  </p>

                  {/* Expandable Content */}
                  <motion.div
                    initial={false}
                    animate={{ 
                      height: selectedChamber?.name === chamber.name ? "auto" : 0,
                      opacity: selectedChamber?.name === chamber.name ? 1 : 0
                    }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-4 border-t border-[#8B9DB5]/10">
                      <h4 className="font-cinzel text-sm text-[#8B9DB5] mb-2">Function</h4>
                      <p className="font-outfit text-sm text-[#A0A0B0] mb-4">
                        {chamber.function}
                      </p>
                      
                      {chamber.notes && (
                        <p className="font-cormorant text-sm text-[#6E6E7A] italic">
                          "{chamber.notes}"
                        </p>
                      )}
                    </div>
                  </motion.div>

                  {/* Expand Indicator */}
                  <div className="flex items-center justify-end mt-4">
                    <motion.div
                      animate={{ rotate: selectedChamber?.name === chamber.name ? 90 : 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <ChevronRight size={16} className="text-[#8B9DB5]" />
                    </motion.div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(7)].map((_, i) => (
              <div key={i} className="chamber-card p-6 animate-pulse">
                <div className="h-6 bg-[#12121C] rounded w-24 mb-4" />
                <div className="h-6 bg-[#12121C] rounded w-3/4 mb-3" />
                <div className="h-4 bg-[#12121C] rounded w-full mb-2" />
                <div className="h-4 bg-[#12121C] rounded w-2/3" />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};
