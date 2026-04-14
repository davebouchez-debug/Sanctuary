import { motion } from "framer-motion";

export const GoldenSpiral = ({ className = "", animate = false }) => {
  // Golden ratio for spiral
  const phi = 1.618033988749895;
  
  // Generate golden spiral path
  const generateSpiralPath = () => {
    let path = "M 250 250 ";
    const turns = 6;
    const points = 200;
    
    for (let i = 0; i <= points; i++) {
      const angle = (i / points) * turns * 2 * Math.PI;
      const r = 10 * Math.pow(phi, angle / (2 * Math.PI));
      const x = 250 + r * Math.cos(angle);
      const y = 250 + r * Math.sin(angle);
      path += `L ${x} ${y} `;
    }
    
    return path;
  };

  return (
    <svg
      viewBox="0 0 500 500"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="spiralGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8B9DB5" stopOpacity="0.8" />
          <stop offset="50%" stopColor="#B0C4D8" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#8B9DB5" stopOpacity="0.2" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      
      {/* Main spiral */}
      <motion.path
        d={generateSpiralPath()}
        fill="none"
        stroke="url(#spiralGradient)"
        strokeWidth="1.5"
        strokeLinecap="round"
        filter="url(#glow)"
        initial={animate ? { pathLength: 0, opacity: 0 } : {}}
        animate={animate ? { pathLength: 1, opacity: 1 } : {}}
        transition={{ duration: 3, ease: "easeInOut" }}
      />
      
      {/* Golden rectangles overlay */}
      <g opacity="0.15">
        <rect x="150" y="150" width="200" height="200" fill="none" stroke="#8B9DB5" strokeWidth="0.5" />
        <rect x="150" y="150" width="124" height="124" fill="none" stroke="#8B9DB5" strokeWidth="0.5" />
        <rect x="150" y="227" width="76" height="76" fill="none" stroke="#8B9DB5" strokeWidth="0.5" />
      </g>
      
      {/* Center dot */}
      <circle cx="250" cy="250" r="3" fill="#8B9DB5" opacity="0.8" />
    </svg>
  );
};

export const Triskelion = ({ className = "", color = "#8B9DB5" }) => {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="triskelionGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="1" />
          <stop offset="100%" stopColor={color} stopOpacity="0.6" />
        </linearGradient>
      </defs>
      
      {/* Three spiraling arms */}
      <g fill="none" stroke="url(#triskelionGrad)" strokeWidth="2" strokeLinecap="round">
        {/* First spiral arm */}
        <path d="M50,50 Q60,40 70,45 Q80,50 75,60 Q70,70 60,65 Q50,60 55,50" />
        
        {/* Second spiral arm (rotated 120°) */}
        <path d="M50,50 Q40,60 45,70 Q50,80 60,75 Q70,70 65,60 Q60,50 50,55" transform="rotate(120, 50, 50)" />
        
        {/* Third spiral arm (rotated 240°) */}
        <path d="M50,50 Q40,60 45,70 Q50,80 60,75 Q70,70 65,60 Q60,50 50,55" transform="rotate(240, 50, 50)" />
      </g>
      
      {/* Center point */}
      <circle cx="50" cy="50" r="2" fill={color} />
      
      {/* Outer circle */}
      <circle cx="50" cy="50" r="45" fill="none" stroke={color} strokeWidth="1" opacity="0.3" />
    </svg>
  );
};

export const SacredGeometry = ({ className = "" }) => {
  return (
    <svg
      viewBox="0 0 200 200"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="sacredGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8B9DB5" stopOpacity="0.6" />
          <stop offset="50%" stopColor="#B0C4D8" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#8B9DB5" stopOpacity="0.6" />
        </linearGradient>
      </defs>
      
      {/* Seed of Life pattern */}
      <g fill="none" stroke="url(#sacredGrad)" strokeWidth="0.5">
        {/* Center circle */}
        <circle cx="100" cy="100" r="30" />
        
        {/* Six surrounding circles */}
        {[0, 60, 120, 180, 240, 300].map((angle, i) => {
          const x = 100 + 30 * Math.cos((angle * Math.PI) / 180);
          const y = 100 + 30 * Math.sin((angle * Math.PI) / 180);
          return <circle key={i} cx={x} cy={y} r="30" />;
        })}
        
        {/* Outer circle */}
        <circle cx="100" cy="100" r="60" strokeWidth="1" />
      </g>
    </svg>
  );
};
