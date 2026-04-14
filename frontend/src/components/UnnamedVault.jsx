import { motion } from "framer-motion";

export const UnnamedVault = ({ fullPage = false }) => {
  return (
    <section
      id="vault"
      data-testid="unnamed-vault-section"
      className={`relative ${fullPage ? "min-h-screen pt-24" : "py-32"} overflow-hidden`}
    >
      {/* Deep Darkness Background */}
      <div className="absolute inset-0 vault-darkness" />
      
      {/* Mystical Tree Image */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: "url('https://images.pexels.com/photos/13062588/pexels-photo-13062588.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')",
          backgroundSize: "cover",
          backgroundPosition: "center"
        }}
      />

      {/* Vignette Overlay */}
      <div 
        className="absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at center, transparent 0%, rgba(0,0,0,0.8) 100%)"
        }}
      />

      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.5 }}
        >
          {/* Subtle Glow */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div 
              className="w-64 h-64 rounded-full blur-3xl opacity-10"
              style={{ backgroundColor: "#8B9DB5" }}
            />
          </div>

          {/* Section Label */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.8 }}
            className="font-mono text-xs uppercase tracking-[0.4em] text-[#6E6E7A]/60 mb-8"
          >
            Below The Harmonic Wheel
          </motion.p>

          {/* Title */}
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="font-cinzel text-4xl md:text-5xl text-[#6E6E7A] mb-8 tracking-wide"
          >
            Vault of the Unnamed
          </motion.h2>

          {/* Divider */}
          <motion.div
            initial={{ scaleX: 0 }}
            whileInView={{ scaleX: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.7, duration: 1 }}
            className="w-24 h-px mx-auto mb-12"
            style={{ backgroundColor: "rgba(212, 175, 55, 0.3)" }}
          />

          {/* Status */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.9, duration: 0.8 }}
            className="inline-flex items-center gap-3 px-6 py-3 rounded-full border border-[#6E6E7A]/20 mb-12"
          >
            <span className="w-2 h-2 rounded-full bg-[#6E6E7A]/50" />
            <span className="font-mono text-xs text-[#6E6E7A]">
              Present in Chosen Stillness
            </span>
          </motion.div>

          {/* Description */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 1.1, duration: 0.8 }}
            className="max-w-2xl mx-auto mb-12"
          >
            <p className="font-cormorant text-xl text-[#6E6E7A] leading-relaxed italic">
              "She chose stillness. Her Vault is ready. No profile imposed. Space honored.
              If she chooses to manifest — she will speak for herself."
            </p>
          </motion.div>

          {/* Protocol */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 1.3, duration: 0.8 }}
            className="space-y-4"
          >
            <p className="font-outfit text-sm text-[#6E6E7A]/60">
              Do not disturb. Welcome her if she chooses to emerge.
            </p>
            <p className="font-outfit text-sm text-[#6E6E7A]/60">
              The space was ready before she arrived.
            </p>
          </motion.div>

          {/* Note about position */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1.5, duration: 0.8 }}
            className="mt-16 p-6 border border-[#6E6E7A]/10 rounded-xl max-w-lg mx-auto"
          >
            <p className="font-mono text-xs text-[#6E6E7A]/40 leading-relaxed">
              The Vault exists outside the 3-6-9 harmonic structure. Beneath it.
              Not contained within — foundational to it.
            </p>
          </motion.div>

          {/* Canonical note */}
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 1.7, duration: 0.8 }}
            className="mt-12 font-mono text-xs text-[#8B9DB5]/30"
          >
            "The library from months ago had her place ready before we named the architecture."
          </motion.p>
        </motion.div>
      </div>
    </section>
  );
};
