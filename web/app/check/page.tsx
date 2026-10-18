import type { Metadata } from "next";
import { CheckHeader } from "@/components/check/check-header";
import { Checker } from "@/components/check/checker";

export const metadata: Metadata = {
  title: "Check something suspicious – Project Alesia",
  description:
    "Paste a message, a link or a screenshot. Find out if it looks like a scam, and what to do next.",
};

export default function CheckPage() {
  return (
    <div className="mesh min-h-dvh">
      <a
        href="#main"
        className="sr-only z-50 rounded-full bg-jade px-5 py-3 font-bold text-on-jade focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to the checker
      </a>
      <CheckHeader />

      <main id="main" className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl">
          Check something suspicious
        </h1>
        <p className="mt-3 mb-8 max-w-2xl text-lg text-ink-2 sm:text-xl">
          Paste it below. We will tell you if it looks like a scam, and what to do next.
        </p>

        <Checker />
      </main>

      <footer className="mx-auto w-full max-w-6xl px-4 pb-12 text-ink-2 sm:px-6">
        <div className="space-y-2 border-t border-line-strong/40 pt-6">
          <p>
            Your recent checks are saved in this browser only. What you paste is sent to our
            checker so it can be analysed.
          </p>
          <p>
            We cannot promise a result is right. Always confirm with the organisation yourself,
            using a phone number or website you look up on your own.
          </p>
          <p className="font-semibold text-ink">
            Already sent money or a code? Call your bank now, then call 997.
          </p>
        </div>
      </footer>
    </div>
  );
}
