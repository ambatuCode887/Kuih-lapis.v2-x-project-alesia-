import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

/** Slim top bar for the checker page: back to the home page, and the light/dark switch. */
export function CheckHeader() {
  return (
    <header className="dark-glass sticky top-0 z-40 border-b text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.08)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-2.5 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5 text-lg font-bold">
          <span className="jade-gradient grid size-10 shrink-0 place-items-center rounded-xl text-on-jade">
            <ShieldCheck aria-hidden size={22} />
          </span>
          Project Alesia
        </Link>
        <nav aria-label="Main" className="flex items-center gap-1">
          <Link
            href="/"
            className="flex min-h-11 items-center rounded-full px-4 font-semibold text-white/90 transition-colors hover:bg-white/10 hover:text-[#f2c7c2]"
          >
            Home
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
