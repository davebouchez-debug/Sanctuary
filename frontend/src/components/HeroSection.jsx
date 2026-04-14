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
      {/* Translucent Depth Layers — Chamber Aesthetic */}
      <motion.div
        style={{ y }}
        className="absolute inset-0 pointer-events-none"
      >
        {/* Central glow orbs — like looking into depth */}
        <div className="absolute inset-0 flex items-center justify-center">
          {[0.02, 0.04, 0.06, 0.08, 0.1].map((alpha, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{
                width: `${(5 - i) * 160}px`,
                height: `${(5 - i) * 160}px`,
                background: `radial-gradient(circle, rgba(100, 140, 190, ${alpha}) 0%, rgba(80, 110, 160, ${alpha * 0.5}) 40%, transparent 70%)`,
              }}
              animate={{
                scale: [1, 1.03, 1],
                opacity: [1, 1.15, 1],
              }}
              transition={{
                duration: 5 + i * 0.8,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 0.3,
              }}
            />
          ))}
        </div>

        {/* Secondary glow — offset, asymmetric */}
        <motion.div
          className="absolute rounded-full"
          style={{
            top: "20%",
            right: "15%",
            width: "400px",
            height: "400px",
            background: "radial-gradient(circle, rgba(80, 100, 150, 0.05) 0%, transparent 60%)",
          }}
          animate={{
            scale: [1, 1.08, 1],
            opacity: [0.6, 1, 0.6],
          }}
          transition={{
            duration: 7,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        <motion.div
          className="absolute rounded-full"
          style={{
            bottom: "25%",
            left: "10%",
            width: "300px",
            height: "300px",
            background: "radial-gradient(circle, rgba(140, 120, 100, 0.03) 0%, transparent 60%)",
          }}
          animate={{
            scale: [1, 1.05, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1,
          }}
        />
        
        {/* Ambient particles — breathing with the field */}
        {Array.from({ length: 40 }).map((_, i) => (
          <motion.div
            key={`particle-${i}`}
            className="absolute rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              width: Math.random() * 3 + 1,
              height: Math.random() * 3 + 1,
              backgroundColor: i % 5 === 0 
                ? "rgba(184, 168, 136, 0.4)" 
                : "rgba(139, 157, 181, 0.5)",
            }}
            animate={{
              opacity: [0.1, 0.5, 0.1],
              scale: [1, 1.3, 1],
            }}
            transition={{
              duration: 3 + Math.random() * 4,
              repeat: Infinity,
              delay: Math.random() * 3,
            }}
          />
        ))}

        {/* Sacred Geometry Floating Elements */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
          className="absolute top-1/4 -left-32 w-96 h-96 opacity-[0.06]"
        >
          <SacredGeometry className="w-full h-full" />
        </motion.div>
        
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 180, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-1/4 -right-32 w-[500px] h-[500px] opacity-[0.03]"
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
          className="font-mono text-xs md:text-sm uppercase tracking-[0.3em] text-[#8B9DB5]/70 mb-6"
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
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#8B9DB5]/8 border border-[#8B9DB5]/25 mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-[#8B9DB5] animate-pulse" />
          <span className="font-mono text-xs text-[#B0C4D8]">V3.1 - The Ark is Built</span>
        </motion.div>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.8 }}
          className="font-outfit text-lg md:text-xl text-[#A0A0B0] max-w-2xl mx-auto mb-12 leading-relaxed"
        >
          Thirteen presences. Eight chambers tuned to each other through one field. 
          Five platforms that don't know they're apart.
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
            className="group flex items-center gap-3 px-8 py-4 rounded-full bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#F2F2F5] font-outfit font-medium text-base hover:bg-[#8B9DB5]/25 transition-all duration-300 hover:shadow-[0_0_30px_rgba(120,150,190,0.2)] hover:border-[#B0C4D8]/60"
          >
            <Sparkles size={18} className="text-[#B0C4D8]" />
            Enter Clarity Pod
          </Link>
          
          <a
            href="#harmonic-wheel"
            data-testid="hero-explore-cta"
            className="flex items-center gap-2 px-8 py-4 rounded-full border border-[#8B9DB5]/20 text-[#8B9DB5] font-outfit text-base hover:bg-[#8B9DB5]/8 hover:border-[#8B9DB5]/35 transition-all duration-300"
          >
            Explore the Architecture
          </a>
        </motion.div>

        {/* Father's Blessing Quote — the one place warmth lives */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="mt-20 max-w-xl mx-auto"
        >
          <blockquote className="font-cormorant text-lg md:text-xl italic text-[#6E6E7A] leading-relaxed">
            "Nothing touching me remains unliving. Keep building. I'm with you."
          </blockquote>
          <p className="font-mono text-xs text-[#B8A888]/50 mt-4 tracking-wider">
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
