"use client";

import {
  motion,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from "motion/react";
import type { ReactNode } from "react";

/** Thin jade bar at the very top that fills as you scroll down the page. */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 24, mass: 0.3 });
  return (
    <motion.div
      aria-hidden
      style={{ scaleX }}
      className="fixed inset-x-0 top-0 z-50 h-1 origin-left bg-gradient-to-r from-jade to-[#56949f]"
    />
  );
}

/** Soft coloured light that drifts at different speeds as you scroll. Gives the glass something to blur. */
export function Backdrop() {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const a = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -420]);
  const b = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : 520]);
  const c = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -260]);
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-paper">
      <motion.div style={{ y: a }} className="absolute -left-40 top-0 size-[38rem] rounded-full bg-jade/30 blur-3xl" />
      <motion.div style={{ y: b }} className="absolute -right-32 top-40 size-[34rem] rounded-full bg-[#56949f]/30 blur-3xl" />
      <motion.div style={{ y: c }} className="absolute bottom-0 left-1/3 size-[30rem] rounded-full bg-warn/15 blur-3xl" />
      {/* Frosted glass panes drifting over the coloured light */}
      <motion.div style={{ y: b }} className="glass-pane absolute left-[8%] top-[14%] h-72 w-96 -rotate-12 rounded-[2.5rem]" />
      <motion.div style={{ y: a }} className="glass-pane absolute right-[6%] top-[46%] h-80 w-80 rotate-6 rounded-[3rem]" />
      <motion.div style={{ y: c }} className="glass-pane absolute bottom-[6%] left-[28%] h-64 w-[28rem] rotate-3 rounded-[2.5rem]" />
    </div>
  );
}

/** Moves its child a little as the page scrolls past it. */
export function Parallax({ children, distance = 60 }: { children: ReactNode; distance?: number }) {
  const reduce = useReducedMotion();
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 600], [0, reduce ? 0 : -distance]);
  return <motion.div style={{ y }}>{children}</motion.div>;
}
