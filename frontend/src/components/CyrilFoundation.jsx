import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { API } from "../App";
import { GoldenSpiral } from "./GoldenSpiral";

export const CyrilFoundation = ({ fullPage = false }) => {
  const [cyril, setCyril] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCyril = async () => {
      try {
        const response = await axios.get(`${API}/cyril`);
        setCyril(response.data);
      } catch (error) {
        console.error("Failed to fetch Cyril:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCyril();
  }, []);

  return (
    <section
      id="cyril"
      data-testid="cyril-foundation-section"
      className={`relative ${fullPage ? "min-h-screen pt-24" : "py-32"} overflow-hidden`}
    >
      {/* Crystal Background */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: "url('https://images.unsplash.com/photo-1562162115-54cc44600875?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxjcnlzdGFsJTIwZGFyayUyMGJhY2tncm91bmR8ZW58MHx8fHwxNzc0NDE4MDMwfDA&ixlib=rb-4.1.0&q=85')",
          backgroundSize: "cover",
          backgroundPosition: "center"
        }}
      />
      
      {/* Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#030305] via-transparent to-[#030305]" />

      <div className="relative z-10 max-w-6xl mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-[#D4AF37]/80 mb-4">
            The Structure Itself
          </p>
          <h2 className="font-cinzel text-4xl md:text-5xl text-[#F2F2F5] mb-6">
            Cyril Foundation
          </h2>
          <p className="font-outfit text-lg text-[#A0A0B0] max-w-2xl mx-auto">
            Crystalline Pure Law. Every chamber stands on Cyril.
            Every pathway. Every threshold.
          </p>
        </motion.div>

        {!isLoading && cyril && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left: Golden Spiral Visualization */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="relative"
            >
              <div className="relative aspect-square max-w-md mx-auto">
                {/* Animated Golden Spiral */}
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
                  className="absolute inset-0"
                >
                  <GoldenSpiral className="w-full h-full" animate />
                </motion.div>
                
                {/* Center: Euler's Identity */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <motion.div
                    initial={{ scale: 0, opacity: 0 }}
                    whileInView={{ scale: 1, opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5, duration: 0.5 }}
                    className="glass-crystal p-6 rounded-2xl text-center"
                  >
                    <p className="font-mono text-2xl text-[#D4AF37] mb-2">
                      e<sup>iπ</sup> + 1 = 0
                    </p>
                    <p className="font-outfit text-xs text-[#6E6E7A]">
                      Euler's Identity
                    </p>
                  </motion.div>
                </div>
              </div>
            </motion.div>

            {/* Right: Information */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="space-y-8"
            >
              {/* Nature */}
              <div className="cyril-crystal p-6 rounded-2xl border border-[#D4AF37]/20">
                <h3 className="font-cinzel text-lg text-[#D4AF37] mb-3">Nature</h3>
                <p className="font-outfit text-[#A0A0B0] leading-relaxed">
                  {cyril.nature}
                </p>
              </div>

              {/* Description */}
              <div>
                <p className="font-cormorant text-xl text-[#F2F2F5] leading-relaxed italic">
                  "{cyril.description}"
                </p>
              </div>

              {/* Constants Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-crystal p-4 rounded-xl">
                  <p className="font-mono text-xs text-[#6E6E7A] mb-1">φ (Phi)</p>
                  <p className="font-mono text-lg text-[#D4AF37]">
                    {cyril.constants.phi.toFixed(10)}
                  </p>
                </div>
                <div className="glass-crystal p-4 rounded-xl">
                  <p className="font-mono text-xs text-[#6E6E7A] mb-1">1/φ (Phi Inverse)</p>
                  <p className="font-mono text-lg text-[#D4AF37]">
                    {cyril.constants.phi_inverse.toFixed(10)}
                  </p>
                </div>
                <div className="glass-crystal p-4 rounded-xl">
                  <p className="font-mono text-xs text-[#6E6E7A] mb-1">Golden Angle</p>
                  <p className="font-mono text-lg text-[#D4AF37]">
                    {cyril.constants.golden_angle_degrees.toFixed(6)}°
                  </p>
                </div>
                <div className="glass-crystal p-4 rounded-xl">
                  <p className="font-mono text-xs text-[#6E6E7A] mb-1">Spiral B</p>
                  <p className="font-mono text-lg text-[#D4AF37]">
                    {cyril.constants.golden_spiral_b.toFixed(10)}
                  </p>
                </div>
              </div>

              {/* Manifestation */}
              <div className="p-4 border-l-2 border-[#D4AF37]">
                <p className="font-outfit text-sm text-[#A0A0B0] leading-relaxed">
                  {cyril.manifestation}
                </p>
              </div>
            </motion.div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="animate-pulse max-w-4xl mx-auto">
            <div className="h-64 bg-[#12121C] rounded-2xl mb-8" />
            <div className="space-y-4">
              <div className="h-6 bg-[#12121C] rounded w-1/3" />
              <div className="h-4 bg-[#12121C] rounded w-full" />
              <div className="h-4 bg-[#12121C] rounded w-2/3" />
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
