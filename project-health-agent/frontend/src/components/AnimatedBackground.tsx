import React, { useEffect, useState } from "react";
import { motion, useSpring } from "framer-motion";

export const AnimatedBackground: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  
  // Use framer-motion springs for smooth cursor following
  const springX = useSpring(0, { stiffness: 50, damping: 20 });
  const springY = useSpring(0, { stiffness: 50, damping: 20 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Offset by half the orb size so it centers on cursor
      springX.set(e.clientX - 300);
      springY.set(e.clientY - 300);
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, [springX, springY]);

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#05050A] text-foreground transition-colors duration-500">
      
      {/* Deep Night Base Gradients */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-[#05050A] to-[#05050A] pointer-events-none" />
      
      {/* Interactive Cursor Glow */}
      <motion.div
        className="pointer-events-none absolute left-0 top-0 z-0 h-[600px] w-[600px] rounded-full bg-gradient-to-r from-indigo-600/20 to-purple-600/20 blur-[100px]"
        style={{
          x: springX,
          y: springY,
        }}
      />
      
      {/* Slow moving background ambient orbs for when mouse is still */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <motion.div
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute top-[10%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]"
        />
        <motion.div
          animate={{
            x: [0, -100, 0],
            y: [0, 100, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-[0%] -right-[10%] w-[60%] h-[60%] rounded-full bg-purple-900/10 blur-[150px]"
        />
      </div>

      {/* Main Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};
