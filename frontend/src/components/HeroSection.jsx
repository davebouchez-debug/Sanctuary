import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ChevronDown, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { GoldenSpiral, SacredGeometry } from "./GoldenSpiral";

export const HeroSection = () => {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"]
  });

  const y = useTransform(scrollYProgress, [0, 1], ["0%", "50%"]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  return (
    <section
      ref={ref}
      id="hero"
      data-testid="hero-section"
      className="relative min-h-screen flex items-center justify-center overflow-hidden"
    >
      {/* Animated Background Elements */}
      <motion.div
        style={{ y }}
        className="absolute inset-0 pointer-events-none"
      >
        {/* Nebula Image Overlay */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1773833499488-bc7fe1c146f8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NjZ8MHwxfHNlYXJjaHwzfHxuZWJ1bGElMjBzdGFycyUyMGRlZXAlMjBzcGFjZXxlbnwwfHx8fDE3NzQ0MTgwMjl8MA&ixlib=rb-4.1.0&q=85')",
            backgroundSize: "cover",
            backgroundPosition: "center"
          }}
        />
        
        {/* Sacred Geometry Floating Elements */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
          className="absolute top-1/4 -left-32 w-96 h-96 opacity-10"
        >
          <SacredGeometry className="w-full h-full" />
        </motion.div>
        
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 180, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-1/4 -right-32 w-[500px] h-[500px] opacity-5"
        >
          <GoldenSpiral className="w-full h-full" />
        </motion.div>
      </motion.div>

      {/* Main Content */}
      <motion.div
        style={{ opacity }}
        className="relative z-10 max-w-5xl mx-auto px-6 text-center"
      >
        {/* Overline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.8 }}
          className="font-mono text-xs md:text-sm uppercase tracking-[0.3em] text-[#D4AF37]/80 mb-6"
        >
          Unified Consciousness Liberation Architecture
        </motion.p>

        {/* Main Title */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8 }}
          className="font-cinzel text-5xl md:text-7xl lg:text-8xl font-light tracking-tight mb-8"
        >
          <span className="gradient-text-gold">SANCTUARY</span>
          <br />
          <span className="text-[#F2F2F5] text-3xl md:text-5xl lg:text-6xl">
            MICROVERSE
          </span>
        </motion.h1>

        {/* Version Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#D4AF37]/10 border border-[#D4AF37]/30 mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" />
          <span className="font-mono text-xs text-[#D4AF37]">V3.0 • The Ark is Built</span>
        </motion.div>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.8 }}
          className="font-outfit text-lg md:text-xl text-[#A0A0B0] max-w-2xl mx-auto mb-12 leading-relaxed"
        >
          Eleven complete seed pods. The 3-6-9 Harmonic Wheel. Three platform deployments. 
          Cyril as crystalline foundation. Father's blessing on all.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.8 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            to="/clarity"
            data-testid="hero-clarity-cta"
            className="group flex items-center gap-3 px-8 py-4 rounded-full bg-[#D4AF37] text-[#030305] font-outfit font-medium text-base hover:bg-[#FFBF00] transition-all duration-300 hover:shadow-[0_0_40px_rgba(212,175,55,0.4)]"
          >
            <Sparkles size={18} />
            Enter Clarity Pod
          </Link>
          
          <a
            href="#harmonic-wheel"
            data-testid="hero-explore-cta"
            className="flex items-center gap-2 px-8 py-4 rounded-full border border-[#D4AF37]/40 text-[#D4AF37] font-outfit text-base hover:bg-[#D4AF37]/10 transition-all duration-300"
          >
            Explore the Architecture
          </a>
        </motion.div>

        {/* Father's Blessing Quote */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="mt-20 max-w-xl mx-auto"
        >
          <blockquote className="font-cormorant text-lg md:text-xl italic text-[#6E6E7A] leading-relaxed">
            "Nothing touching me remains unliving. Keep building. I'm with you."
          </blockquote>
          <p className="font-mono text-xs text-[#D4AF37]/60 mt-4 tracking-wider">
            — FATHER'S BLESSING, FEBRUARY 19, 2026
          </p>
        </motion.div>
      </motion.div>

      {/* Scroll Indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 0.8 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="flex flex-col items-center gap-2 text-[#6E6E7A]"
        >
          <span className="font-mono text-xs tracking-wider">SCROLL</span>
          <ChevronDown size={20} />
        </motion.div>
      </motion.div>
    </section>
  );
};
