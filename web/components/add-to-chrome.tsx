"use client";

import { ShieldCheck } from "lucide-react";
import { ShimmerButton } from "@/components/ui/shimmer-button";

// TODO: replace with the Chrome Web Store link once the extension is published.
const CHROME_URL = "#add-to-chrome";

export function AddToChrome({ large = false }: { large?: boolean }) {
  return (
    <ShimmerButton
      type="button"
      onClick={() => {
        window.location.href = CHROME_URL;
      }}
      background="var(--pine)"
      shimmerColor="rgba(255,255,255,0.85)"
      className={`gap-2 font-bold text-on-jade ${large ? "h-12 px-7 text-base" : "h-11 px-5 text-sm"}`}
    >
      <ShieldCheck aria-hidden size={large ? 26 : 22} />
      Add to Chrome
    </ShimmerButton>
  );
}
