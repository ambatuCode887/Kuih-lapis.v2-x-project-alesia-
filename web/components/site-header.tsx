"use client";

import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useSpring,
} from "motion/react";
import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { AddToChrome } from "@/components/add-to-chrome";

const LINKS = [
  { id: "how", label: "How it works" },
  { id: "scams", label: "Scams" },
  { id: "trust", label: "Our promise" },
];

/** Which section is in the middle of the screen right now. */
function useActiveSection(ids: string[]) {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id);
        }
      },
      { rootMargin: "-45% 0px -50% 0px" },
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    // Back at the hero: nothing is active.
    const onScroll = () => {
      if (window.scrollY < 200) setActive(null);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", onScroll);
    };
  }, [ids]);
  return active;
}

/**
 * Morphing glass header:
 * - at the top it is a full-width frosted bar
 * - once you scroll it becomes a floating glass capsule
 * - scrolling down compacts it (logo text hides), scrolling up restores it
 * - a jade line along the bottom shows how far down the page you are
 * - a pill slides to the link of the section you are reading
 */
export function SiteHeader() {
  const reduce = useReducedMotion();
  const { scrollY, scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: 140, damping: 26, mass: 0.3 });
  const [floating, setFloating] = useState(false);
  const [compact, setCompact] = useState(false);
  const active = useActiveSection(LINKS.map((l) => l.id));

  useMotionValueEvent(scrollY, "change", (y) => {
    const previous = scrollY.getPrevious() ?? 0;
    setFloating(y > 24);
    if (y < 240) setCompact(false);
    else if (Math.abs(y - previous) > 4) setCompact(y > previous);
  });

  const spring = reduce ? { duration: 0 } : { type: "spring" as const, stiffness: 260, damping: 32 };

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center">
      <motion.header
        initial={false}
        animate={{
          maxWidth: floating ? 920 : 2400,
          marginTop: floating ? 12 : 0,
          borderRadius: floating ? 999 : 0,
        }}
        transition={spring}
        className={`dark-glass pointer-events-auto relative w-full overflow-hidden text-white ${
          floating
            ? "mx-4 border shadow-[inset_0_1px_0_rgb(255_255_255/0.08),0_20px_50px_rgb(0_0_0/0.45)]"
            : "border-b shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]"
        }`}
      >
        <motion.div
          initial={false}
          animate={{ paddingTop: compact ? 6 : 10, paddingBottom: compact ? 6 : 10 }}
          transition={spring}
          className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 sm:px-6"
        >
          <a href="#top" aria-label="Project Alesia, back to top" className="flex items-center gap-2 font-bold">
            <motion.span
              initial={false}
              animate={{ scale: compact ? 0.85 : 1 }}
              transition={spring}
              className="jade-gradient grid size-10 shrink-0 place-items-center rounded-xl text-on-jade"
            >
              <ShieldCheck aria-hidden size={22} />
            </motion.span>
            <AnimatePresence initial={false}>
              {!compact && (
                <motion.span
                  key="name"
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={spring}
                  className="overflow-hidden whitespace-nowrap text-lg"
                >
                  Project Alesia
                </motion.span>
              )}
            </AnimatePresence>
          </a>

          <nav aria-label="Page sections" className="hidden md:block">
            <ul className="flex items-center gap-1">
              {LINKS.map((link) => {
                const isActive = active === link.id;
                return (
                  <li key={link.id} className="relative">
                    {isActive && (
                      <motion.span
                        layoutId="nav-pill"
                        transition={spring}
                        className="absolute inset-0 rounded-full bg-white/10 ring-1 ring-[#f2c7c2]/40"
                      />
                    )}
                    <a
                      href={`#${link.id}`}
                      aria-current={isActive ? "location" : undefined}
                      className={`relative block rounded-full px-4 py-2 text-sm font-bold transition-colors hover:bg-white/5 hover:text-[#f2c7c2] ${
                        isActive ? "text-[#f2c7c2]" : "text-white/80"
                      }`}
                    >
                      {link.label}
                    </a>
                  </li>
                );
              })}
            </ul>
          </nav>

          <AddToChrome />
        </motion.div>

        {/* Reading progress along the bottom edge */}
        <motion.div
          aria-hidden
          style={{ scaleX: progress }}
          className="absolute inset-x-0 bottom-0 h-[3px] origin-left bg-gradient-to-r from-jade to-[#56949f]"
        />
      </motion.header>
    </div>
  );
}
