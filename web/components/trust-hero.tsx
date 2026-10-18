import {
  ArrowRight,
  Briefcase,
  HeartCrack,
  MessageSquareWarning,
  Package,
  ShieldCheck,
  TrendingUp,
  TriangleAlert,
} from "lucide-react";
import { AddToChrome } from "@/components/add-to-chrome";
import { BorderBeam } from "@/components/ui/border-beam";
import { GlassFold } from "@/components/ui/glass-fold";

// Adapted from "Glassmorphism Trust Hero" by jahed on 21st.dev.
// Changes: jade colours, our copy, an example verdict instead of made-up stats,
// scam types instead of fake client logos, and the Glass Fold shader behind it.
// The hero is always dark, in both themes, so the glass reads well.

const WATCHING = [
  { name: "Fake bank messages", icon: MessageSquareWarning },
  { name: "Parcel scams", icon: Package },
  { name: "Job scams", icon: Briefcase },
  { name: "Love scams", icon: HeartCrack },
  { name: "Fake investments", icon: TrendingUp },
];

export function TrustHero() {
  return (
    <section id="top" className="trust-hero relative isolate overflow-hidden bg-[#1e1a33] text-white">
      {/* Animated folded-glass background in jade */}
      <GlassFold
        color1="#d7827e"
        color2="#1e1a33"
        color3="#f2c7c2"
        speed={0.35}
        scale={0.9}
        noise={0.1}
        className="absolute inset-0 -z-20 opacity-80"
      />
      {/* Darken the left side so the headline always reads clearly */}
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-gradient-to-r from-[#1e1a33]/95 via-[#1e1a33]/70 to-[#1e1a33]/30"
      />

      <div className="mx-auto max-w-7xl px-4 pb-16 pt-28 sm:px-6 md:pb-24 md:pt-36 lg:px-8">
        <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-12 lg:gap-8">
          {/* Left: the one job */}
          <div className="flex flex-col justify-center space-y-8 pt-4 lg:col-span-7">
            <div className="hero-in [animation-delay:100ms]">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-1.5 text-sm font-bold uppercase tracking-wider text-white/90 backdrop-blur-md transition-colors hover:bg-white/15">
                <ShieldCheck aria-hidden className="size-4 text-[#f2c7c2]" />
                Free scam check for everyone
              </span>
            </div>

            <h1 className="hero-in text-4xl font-bold leading-[0.95] tracking-tight [animation-delay:200ms] sm:text-5xl lg:text-6xl">
              Got something
              <br />
              suspicious?
              <br />
              <span className="bg-gradient-to-br from-white via-[#fbe3e0] to-[#d7827e] bg-clip-text text-transparent">
                Check it first.
              </span>
            </h1>

            <p className="hero-in max-w-xl text-lg leading-relaxed text-white/80 [animation-delay:300ms]">
              Paste a suspicious message, link or screenshot. Get a plain answer on whether it looks
              like a scam, and what to do next.
            </p>

            <div className="hero-in flex flex-col gap-4 [animation-delay:400ms] sm:flex-row sm:items-center">
              <AddToChrome large />
              <a
                href="#how"
                className="group inline-flex min-h-12 items-center justify-center gap-2 rounded-full border border-white/15 bg-white/10 px-8 text-base font-bold text-white backdrop-blur-sm transition-colors hover:border-[#f2c7c2]/60 hover:bg-[#d7827e]/20"
              >
                See how it works
                <ArrowRight aria-hidden className="size-5 transition-transform group-hover:translate-x-1" />
              </a>
            </div>
          </div>

          {/* Right: an example answer, then what we look out for */}
          <div className="space-y-6 lg:col-span-5 lg:mt-6">
            <div
              aria-label="Example of an answer"
              className="hero-in relative overflow-hidden rounded-3xl border border-white/15 bg-white/10 p-7 shadow-2xl backdrop-blur-xl [animation-delay:500ms]"
            >
              <BorderBeam size={240} duration={9} colorFrom="#d7827e" colorTo="#56949f" />
              <div aria-hidden className="pointer-events-none absolute -right-16 -top-16 size-64 rounded-full bg-[#ff9a90]/15 blur-3xl" />

              <div className="relative">
                <p className="text-sm font-bold uppercase tracking-wider text-white/70">Example</p>
                <p className="mt-3 rounded-2xl border border-white/10 bg-black/30 p-4 text-base text-white/90">
                  “Your account is locked. Verify now: bit.ly/xx-bank”
                </p>

                <div className="mt-6 flex items-center gap-4">
                  <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-[#ff9a90]/15 ring-1 ring-[#ff9a90]/40">
                    <TriangleAlert aria-hidden className="size-7 text-[#ff9a90]" />
                  </span>
                  <div>
                    <p className="text-xl font-bold text-[#ffb4ab]">This looks like a scam</p>
                    <p className="text-sm text-white/75">Do not reply, click or send anything.</p>
                  </div>
                </div>

                <div className="mt-6 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/75">How worried to be</span>
                    <span className="font-bold text-white">Very high</span>
                  </div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
                    <div className="hero-bar h-full w-[92%] rounded-full bg-gradient-to-r from-[#f7c25c] via-[#ffa866] to-[#ff9a90]" />
                  </div>
                </div>

                <div className="my-6 h-px w-full bg-white/10" />

                <ul className="space-y-2 text-base text-white/90">
                  <li className="flex gap-3">
                    <ShieldCheck aria-hidden className="mt-1 size-5 shrink-0 text-[#f2c7c2]" />
                    Do not tap the link.
                  </li>
                  <li className="flex gap-3">
                    <ShieldCheck aria-hidden className="mt-1 size-5 shrink-0 text-[#f2c7c2]" />
                    Call the number on your bank card.
                  </li>
                </ul>
              </div>
            </div>

            <div className="hero-in relative overflow-hidden rounded-3xl border border-white/15 bg-white/10 py-6 backdrop-blur-xl [animation-delay:600ms]">
              <h2 className="mb-5 px-7 text-sm font-bold text-white/75">What we look out for</h2>
              <div
                className="relative flex overflow-hidden"
                style={{
                  maskImage: "linear-gradient(to right, transparent, black 15%, black 85%, transparent)",
                  WebkitMaskImage: "linear-gradient(to right, transparent, black 15%, black 85%, transparent)",
                }}
              >
                <ul className="hero-marquee flex shrink-0 gap-10 whitespace-nowrap px-4">
                  {[...WATCHING, ...WATCHING].map((item, i) => (
                    <li
                      key={i}
                      aria-hidden={i >= WATCHING.length}
                      className="flex items-center gap-2 text-white/70 transition-colors hover:text-[#f2c7c2]"
                    >
                      <item.icon aria-hidden className="size-6" />
                      <span className="text-base font-bold">{item.name}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
