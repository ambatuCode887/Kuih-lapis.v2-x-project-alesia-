"use client";

import { motion, useInView, useReducedMotion, useScroll, useSpring } from "motion/react";
import { ClipboardPaste, ShieldCheck, Sparkles, type LucideIcon } from "lucide-react";
import { useRef } from "react";

const STEPS: { icon: LucideIcon; title: string; text: string }[] = [
  { icon: ClipboardPaste, title: "Paste it", text: "A message, a link or a screenshot." },
  { icon: Sparkles, title: "We check it", text: "We look for the signs scammers leave." },
  { icon: ShieldCheck, title: "You know what to do", text: "A clear answer and up to 3 steps." },
];

function Step({ step, index }: { step: (typeof STEPS)[number]; index: number }) {
  const ref = useRef<HTMLLIElement>(null);
  // "Active" while the step is near the middle of the screen.
  const active = useInView(ref, { margin: "-35% 0px -35% 0px" });
  const reduce = useReducedMotion();
  return (
    <motion.li
      ref={ref}
      initial={reduce ? false : { opacity: 0, x: index % 2 ? 60 : -60 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-10%" }}
      transition={{ type: "spring", stiffness: 90, damping: 18 }}
      className="relative pl-24 sm:pl-28"
    >
      <span
        className={`absolute left-0 top-0 grid size-16 place-items-center rounded-2xl border-2 transition-all duration-500 sm:size-20 ${
          active
            ? "jade-gradient scale-110 border-jade text-on-jade shadow-lg"
            : "border-line-strong bg-card text-jade-text"
        }`}
      >
        <step.icon aria-hidden size={34} />
      </span>
      <div
        className={`glass rounded-3xl p-6 transition-all duration-500 ${
          active ? "border-jade [background:color-mix(in_srgb,var(--pine)_12%,var(--card))]" : ""
        }`}
      >
        <h3 className="text-xl font-bold">{step.title}</h3>
        <p className="mt-1 text-lg text-ink-2">{step.text}</p>
      </div>
    </motion.li>
  );
}

/** Steps along a line that fills with jade as you scroll through them. */
export function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 70%", "end 60%"] });
  const scaleY = useSpring(scrollYProgress, { stiffness: 100, damping: 24, mass: 0.3 });
  return (
    <div ref={ref} className="relative mx-auto max-w-3xl">
      <div aria-hidden className="absolute bottom-8 left-8 top-8 w-1 rounded bg-line sm:left-10">
        <motion.div style={{ scaleY }} className="h-full origin-top rounded bg-gradient-to-b from-jade to-[#56949f]" />
      </div>
      <ol className="flex flex-col gap-10">
        {STEPS.map((step, i) => (
          <Step key={step.title} step={step} index={i} />
        ))}
      </ol>
    </div>
  );
}
