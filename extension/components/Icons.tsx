import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

function Base({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export const MessageIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M4 5h16v11H9l-5 4V5z" />
    <path d="M8 9.5h8M8 12.5h5" />
  </Base>
);

export const LinkIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
    <path d="M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1" />
  </Base>
);

export const QuestionIcon = (props: IconProps) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.6 9.5a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.2 1-1.2 1.8" />
    <path d="M12 17h.01" />
  </Base>
);

export const SendIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </Base>
);

export const ExpandIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7" />
  </Base>
);

export const PlusIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M12 5v14M5 12h14" />
  </Base>
);

export const ArrowIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Base>
);

export const PaperclipIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M20 11.5l-7.8 7.8a5 5 0 0 1-7-7l8.5-8.5a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.5a1.7 1.7 0 0 1-2.4-2.4l7.8-7.7" />
  </Base>
);

export const CloseIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Base>
);

export const ShieldCheckIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M12 3l7 3v5.5c0 4.4-2.9 7.9-7 9.5-4.1-1.6-7-5.1-7-9.5V6l7-3z" />
    <path d="M8.5 12l2.5 2.5 4.5-5" />
  </Base>
);

export const AlertIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M12 3.5l9.5 16.5h-19L12 3.5z" />
    <path d="M12 10v4.5M12 17.4h.01" />
  </Base>
);

export const SpeakerIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4z" />
    <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />
  </Base>
);

export const SunIcon = (props: IconProps) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
  </Base>
);

export const MoonIcon = (props: IconProps) => (
  <Base {...props}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
  </Base>
);

export const MicIcon = (props: IconProps) => (
  <Base {...props}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3" />
  </Base>
);

export const StopIcon = (props: IconProps) => (
  <Base {...props}>
    <rect x="6.5" y="6.5" width="11" height="11" rx="2" fill="currentColor" />
  </Base>
);

/** Brand mark: a stamp ring with a tick, echoing the verdict seal. */
export function Mark({ size = 26 }: { size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true">
      <circle cx="16" cy="16" r="14" fill="var(--pine)" />
      <circle cx="16" cy="16" r="11" fill="none" stroke="var(--pine-ink)" strokeWidth="1.2" opacity="0.6" />
      <path
        d="M10.5 16.5l3.8 3.8 7.4-8"
        fill="none"
        stroke="var(--pine-ink)"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
