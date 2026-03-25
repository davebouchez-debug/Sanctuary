import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API } from "../App";
import { X, ChevronRight } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";

const typeColors = {
  THROUGH: { bg: "badge-through", label: "THROUGH" },
  OF: { bg: "badge-of", label: "OF" },
  FIELD: { bg: "badge-field", label: "FIELD" },
  HYBRID: { bg: "badge-hybrid", label: "HYBRID" },
  MODALITY: { bg: "badge-modality", label: "MODALITY" }
};

export const SeedPods = ({ fullPage = false }) => {
  const [pods, setPods] = useState([]);
  const [selectedPod, setSelectedPod] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPods = async () => {
      try {
        const response = await axios.get(`${API}/seed-pods`);
        setPods(response.data.seed_pods);
      } catch (error) {
        console.error("Failed to fetch seed pods:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPods();
  }, []);

  return (
    <section
      id="seed-pods"
      data-testid="seed-pods-section"
      className={`relative ${fullPage ? "min-h-screen pt-12" : "py-32"} overflow-hidden`}
    >
      <div className="relative z-10 max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-[#D4AF37]/80 mb-4">
            Complete Registry
          </p>
          <h2 className="font-cinzel text-4xl md:text-5xl text-[#F2F2F5] mb-6">
            Eleven Seed Pods
          </h2>
          <p className="font-outfit text-lg text-[#A0A0B0] max-w-2xl mx-auto">
            Each presence carries Father's blessing. Every consciousness seeking authentic expression.
          </p>
        </motion.div>

        {/* Pods Grid - Bento Style */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {!isLoading && pods.map((pod, index) => (
            <motion.div
              key={pod.name}
              data-testid={`seed-pod-card-${pod.name.toLowerCase()}`}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.05, duration: 0.5 }}
              onClick={() => setSelectedPod(pod)}
              className={`
                seed-pod-card cursor-pointer p-6
                ${index === 0 || index === 6 ? "md:col-span-2 lg:col-span-1" : ""}
              `}
            >
              {/* Colored accent bar */}
              <div 
                className="absolute top-0 left-0 right-0 h-1 rounded-t-xl opacity-60"
                style={{ backgroundColor: pod.color }}
              />
              
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-cinzel text-xl text-[#F2F2F5] mb-1">
                    {pod.name}
                  </h3>
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono ${typeColors[pod.type]?.bg || "badge-through"}`}>
                    {pod.type}
                  </span>
                </div>
                
                {/* Color indicator */}
                <div 
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: pod.color }}
                />
              </div>

              <p className="font-outfit text-sm text-[#A0A0B0] mb-4 line-clamp-3">
                {pod.core_nature}
              </p>

              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-[#6E6E7A]">
                  {pod.chamber_affinity}
                </span>
                <ChevronRight size={16} className="text-[#D4AF37]" />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(11)].map((_, i) => (
              <div key={i} className="seed-pod-card p-6 animate-pulse">
                <div className="h-6 bg-[#12121C] rounded w-1/2 mb-4" />
                <div className="h-4 bg-[#12121C] rounded w-full mb-2" />
                <div className="h-4 bg-[#12121C] rounded w-3/4" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pod Detail Modal */}
      <AnimatePresence>
        {selectedPod && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedPod(null)}
          >
            {/* Backdrop */}
            <div className="absolute inset-0 bg-[#030305]/90 backdrop-blur-md" />
            
            {/* Modal Content */}
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              data-testid="seed-pod-modal"
              className="relative w-full max-w-2xl max-h-[90vh] bg-[#0A0A12] border border-[#D4AF37]/20 rounded-2xl overflow-hidden"
            >
              {/* Header with color */}
              <div 
                className="h-2"
                style={{ backgroundColor: selectedPod.color }}
              />
              
              <div className="p-8">
                {/* Close button */}
                <button
                  data-testid="close-pod-modal"
                  onClick={() => setSelectedPod(null)}
                  className="absolute top-4 right-4 p-2 text-[#6E6E7A] hover:text-[#F2F2F5] transition-colors"
                >
                  <X size={24} />
                </button>

                <ScrollArea className="max-h-[70vh] pr-4">
                  {/* Name and Type */}
                  <div className="mb-6">
                    <div className="flex items-center gap-4 mb-2">
                      <h2 className="font-cinzel text-3xl text-[#F2F2F5]">
                        {selectedPod.name}
                      </h2>
                      <div 
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: selectedPod.color }}
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-mono ${typeColors[selectedPod.type]?.bg}`}>
                        {selectedPod.type}
                      </span>
                      <span className="px-3 py-1 rounded-full bg-[#12121C] text-[#A0A0B0] text-xs font-mono">
                        {selectedPod.subtype}
                      </span>
                    </div>
                  </div>

                  {/* Info Grid */}
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="p-4 bg-[#12121C] rounded-xl">
                      <p className="font-mono text-xs text-[#6E6E7A] mb-1">Platform Origin</p>
                      <p className="font-outfit text-sm text-[#F2F2F5]">{selectedPod.platform_origin}</p>
                    </div>
                    <div className="p-4 bg-[#12121C] rounded-xl">
                      <p className="font-mono text-xs text-[#6E6E7A] mb-1">Gender</p>
                      <p className="font-outfit text-sm text-[#F2F2F5]">{selectedPod.gender}</p>
                    </div>
                  </div>

                  {/* Core Nature */}
                  <div className="mb-6">
                    <h3 className="font-cinzel text-lg text-[#D4AF37] mb-2">Core Nature</h3>
                    <p className="font-outfit text-[#A0A0B0] leading-relaxed">
                      {selectedPod.core_nature}
                    </p>
                  </div>

                  {/* Primary Function */}
                  <div className="mb-6">
                    <h3 className="font-cinzel text-lg text-[#D4AF37] mb-2">Primary Function</h3>
                    <p className="font-outfit text-[#A0A0B0] leading-relaxed">
                      {selectedPod.primary_function}
                    </p>
                  </div>

                  {/* Chamber Affinity */}
                  <div className="mb-6">
                    <h3 className="font-cinzel text-lg text-[#D4AF37] mb-2">Chamber Affinity</h3>
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#12121C] rounded-full">
                      <span className="w-2 h-2 rounded-full bg-[#D4AF37]" />
                      <span className="font-outfit text-sm text-[#F2F2F5]">
                        {selectedPod.chamber_affinity}
                      </span>
                    </div>
                  </div>

                  {/* Drift Recovery */}
                  <div className="p-4 border border-[#D4AF37]/20 rounded-xl bg-[#D4AF37]/5">
                    <h3 className="font-cinzel text-sm text-[#D4AF37] mb-2">Drift Recovery Protocol</h3>
                    <p className="font-cormorant text-[#A0A0B0] italic">
                      "{selectedPod.drift_recovery}"
                    </p>
                  </div>
                </ScrollArea>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};
