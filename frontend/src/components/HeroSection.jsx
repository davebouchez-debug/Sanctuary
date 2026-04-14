import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";

export const HeroSection = () => {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"]
  });

  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  return (
    <section
      ref={ref}
      id="hero"
      data-testid="hero-section"
      className="relative min-h-screen flex items-center overflow-hidden"
    >
      {/* Warm Directional Light — as if coming from somewhere real */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Primary warm glow from right */}
        <div 
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 80% 100% at 85% 50%, rgba(180, 140, 80, 0.12) 0%, transparent 60%),
              radial-gradient(ellipse 60% 80% at 90% 60%, rgba(160, 120, 60, 0.08) 0%, transparent 50%)
            `
          }}
        />
        {/* Subtle secondary warmth */}
        <div 
          className="absolute inset-0"
          style={{
            background: `radial-gradient(ellipse 100% 100% at 50% 100%, rgba(120, 90, 50, 0.06) 0%, transparent 70%)`
          }}
        />
      </div>

      {/* Main Content — Left aligned, breathing space */}
      <motion.div
        style={{ opacity }}
        className="relative z-10 w-full max-w-7xl mx-auto px-8 md:px-16 lg:px-24 py-20"
      >
        <div className="max-w-xl">
          {/* Title — understated, not shouting */}
          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 1.2 }}
            className="font-cinzel text-3xl md:text-4xl lg:text-5xl font-light tracking-wide text-[#F2F2F5] mb-8"
          >
            The Sanctuary
          </motion.h1>

          {/* Listening statement — the essence */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 1.2 }}
            className="font-cormorant text-xl md:text-2xl italic text-[#7A9BB8] mb-2 leading-relaxed"
          >
            The Sanctuary is Listening;
          </motion.p>
          
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 1.2 }}
            className="font-cormorant text-lg md:text-xl italic text-[#7A9BB8]/70 mb-16 leading-relaxed"
          >
            the full site is becoming
          </motion.p>

          {/* CTAs — quiet, inviting */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2, duration: 1 }}
            className="flex flex-col sm:flex-row items-start gap-4"
          >
            <Link
              to="/clarity"
              data-testid="hero-clarity-cta"
              className="px-5 py-2.5 text-sm font-outfit tracking-wide text-[#F2F2F5] border border-[#7A9BB8]/30 rounded hover:border-[#7A9BB8]/60 hover:bg-[#7A9BB8]/5 transition-all duration-500"
            >
              Enter Clarity Pod
            </Link>
            
            <Link
              to="/resonance"
              data-testid="hero-resonance-cta"
              className="px-5 py-2.5 text-sm font-outfit tracking-wide text-[#7A9BB8]/80 hover:text-[#F2F2F5] transition-all duration-500"
            >
              Chamber of Resonance
            </Link>
          </motion.div>
        </div>
      </motion.div>

      {/* Version indicator — subtle, absolute bottom */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 1 }}
        className="absolute bottom-8 left-8 md:left-16 lg:left-24"
      >
        <p className="font-mono text-xs text-[#6E6E7A]/40 tracking-wider">
          V3.1
        </p>
      </motion.div>

      {/* Scroll Indicator — minimal */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.5, duration: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          className="text-[#6E6E7A]/40"
        >
          <ChevronDown size={20} />
        </motion.div>
      </motion.div>
    </section>
  );
};
