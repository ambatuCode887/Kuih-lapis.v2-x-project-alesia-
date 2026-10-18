import {
  MessageSquareWarning,
  Lock,
  Scale,
  Eye,
  Banknote,
  Package,
  Briefcase,
  HeartCrack,
  TrendingUp,
} from "lucide-react";
import type { ReactNode } from "react";
import { AddToChrome } from "@/components/add-to-chrome";
import { TrustHero } from "@/components/trust-hero";
import { BlurFade } from "@/components/ui/blur-fade";
import { HowItWorks } from "@/components/how-it-works";
import { Backdrop } from "@/components/scroll-effects";
import { SiteHeader } from "@/components/site-header";

function Section({
  id,
  title,
  lead,
  children,
}: {
  id: string;
  title: string;
  lead?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-8">
      <h2 id={`${id}-title`} className="text-2xl font-bold tracking-tight sm:text-3xl">
        {title}
      </h2>
      {lead && <p className="mt-3 max-w-2xl text-lg text-ink-2">{lead}</p>}
      <BlurFade inView delay={0.1} className="mt-10">{children}</BlurFade>
    </section>
  );
}

// `tint` is the colour a card turns to when you hover it.
const SCAMS = [
  {
    icon: MessageSquareWarning,
    tint: "var(--risk-critical)",
    title: "Fake bank message",
    sign: "A text says your account is locked and asks you to click a link.",
    todo: "Do not click. Call the number on the back of your bank card.",
  },
  {
    icon: Package,
    tint: "var(--risk-high)",
    title: "Parcel scam",
    sign: "A delivery you did not order, with a fee to pay or a link to track it.",
    todo: "Check with the courier on their official website or app.",
  },
  {
    icon: Briefcase,
    tint: "var(--risk-moderate)",
    title: "Job scam",
    sign: "Easy money for simple tasks, or a fee you must pay before you start.",
    todo: "A real job never asks you to pay first. Walk away.",
  },
  {
    icon: HeartCrack,
    tint: "var(--risk-high)",
    title: "Love scam",
    sign: "Someone you met online soon asks for money or gift cards.",
    todo: "Do not send money. Talk to a family member or friend you trust.",
  },
  {
    icon: TrendingUp,
    tint: "var(--teal)",
    title: "Fake investment",
    sign: "Big, fast, guaranteed profits, with pressure to join today.",
    todo: "No investment is guaranteed. Check the company with the official regulator.",
  },
];

const PRINCIPLES = [
  { icon: Scale, title: "An estimate, not a final answer", text: "We tell you how worried to be. We cannot be sure, so always confirm through an official number you look up yourself." },
  { icon: Eye, title: "We only look at what you give us", text: "We check the message, link or screenshot you paste, and nothing else on your computer." },
  { icon: Lock, title: "Plain words, no pressure", text: "No jargon. No scary countdowns. You decide what to do next." },
];

export default function Home() {
  return (
    <div className="min-h-screen">
      <Backdrop />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:px-4 focus:py-3"
      >
        Skip to the main content
      </a>

      <SiteHeader />

      <main id="main">
        {/* 1. Hero: dark glass, one job, one button */}
        <TrustHero />

        {/* 2. How it works */}
        <Section id="how" title="How it works" lead="Three steps. Keep scrolling and watch them light up.">
          <HowItWorks />
        </Section>

        {/* 3. Common scams */}
        <Section id="scams" title="Scams to look out for" lead="Five tricks we see most. Each has a warning sign and a safe next step.">
          <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {SCAMS.map((scam, i) => (
              <li key={scam.title}>
                <BlurFade inView delay={0.08 * i} className="h-full">
                  <div
                    style={{ ["--tint" as string]: scam.tint }}
                    className="hover-tint group glass h-full rounded-3xl p-6"
                  >
                    <span className="grid size-14 place-items-center rounded-2xl bg-[color-mix(in_srgb,var(--tint)_16%,transparent)] text-[var(--tint)] transition-all duration-300 group-hover:rotate-6 group-hover:scale-110 group-hover:bg-[var(--tint)] group-hover:text-[var(--card)]">
                      <scam.icon aria-hidden size={30} />
                    </span>
                    <h3 className="mt-4 text-xl font-bold">{scam.title}</h3>
                    <p className="mt-3 text-base"><strong>Warning sign:</strong> {scam.sign}</p>
                    <p className="mt-3 text-base"><strong className="text-jade-text">What to do:</strong> {scam.todo}</p>
                  </div>
                </BlurFade>
              </li>
            ))}
          </ul>
        </Section>

        {/* 4. Honest messaging */}
        <Section id="trust" title="What to expect from us">
          <ul className="grid gap-6 md:grid-cols-3">
            {PRINCIPLES.map((p) => (
              <li key={p.title} className="glass rounded-3xl p-6">
                <p.icon aria-hidden className="text-jade-text" size={32} />
                <h3 className="mt-3 text-xl font-bold">{p.title}</h3>
                <p className="mt-2 text-base text-ink-2">{p.text}</p>
              </li>
            ))}
          </ul>
        </Section>

        {/* 5. Already sent money */}
        <section aria-labelledby="help-title" className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8">
          <div role="note" className="glass flex flex-col gap-4 rounded-3xl border-l-[10px] border-l-warn p-6 sm:flex-row sm:items-center">
            <Banknote aria-hidden className="shrink-0 text-warn" size={44} />
            <div>
              <h2 id="help-title" className="text-xl font-bold">Already sent money?</h2>
              <p className="mt-1 text-lg">
                Call your bank on the number on your card. Then call the National Scam Response Centre on <strong className="text-xl">997</strong>.
              </p>
            </div>
          </div>
        </section>

        {/* 6. Closing call to action */}
        <section className="mx-auto w-full max-w-6xl px-4 py-20 text-center sm:px-8">
          <h2 className="text-3xl font-bold tracking-tight">Got something suspicious?</h2>
          <p className="mx-auto mt-3 max-w-xl text-lg text-ink-2">Check it before you click, reply or pay.</p>
          <div className="mt-8"><AddToChrome large /></div>
        </section>
      </main>

      <footer className="border-t-2 border-line px-4 py-8 text-center text-base text-ink-2">
        <p>Project Alesia gives an estimate, not a final answer. In an emergency, call your bank, then 997.</p>
      </footer>
    </div>
  );
}
