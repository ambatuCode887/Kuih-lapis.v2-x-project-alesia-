import { useEffect, useRef } from 'react';
import { CloseIcon } from './Icons';

interface LightboxProps {
  src: string;
  onClose: () => void;
}

/** Full-size image preview. Closes on Esc, on the close button, or by clicking outside. */
export default function Lightbox({ src, onClose }: LightboxProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label="Image preview" onClick={onClose}>
      <button
        ref={closeRef}
        type="button"
        className="lightbox-close"
        aria-label="Close preview"
        onClick={onClose}
      >
        <CloseIcon width={20} height={20} />
      </button>
      <img className="lightbox-img" src={src} alt="Full-size preview" onClick={(e) => e.stopPropagation()} />
    </div>
  );
}
