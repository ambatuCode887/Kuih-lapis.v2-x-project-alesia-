import { DotLottieReact, setWasmUrl } from '@lottiefiles/dotlottie-react';
import { useEffect, useState } from 'react';
import { ShieldCheckIcon } from './Icons';
import { shieldScan } from './lottie/shield-scan';

// Manifest V3 pages cannot fetch the player from a CDN, so use the copy in public/.
// (Copied from node_modules/@lottiefiles/dotlottie-web/dist; refresh it if that package is upgraded.)
setWasmUrl(browser.runtime.getURL('/dotlottie-player.wasm'));

/** Looping "checking" animation. Shows a still shield when motion is reduced. */
export default function ShieldScan({ size = 56 }: { size?: number }) {
  const [still, setStill] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setStill(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  return (
    <span className="shield-scan" style={{ width: size, height: size }} aria-hidden="true">
      {still ? (
        <ShieldCheckIcon width={size * 0.6} height={size * 0.6} />
      ) : (
        <DotLottieReact data={shieldScan} loop autoplay style={{ width: size, height: size }} />
      )}
    </span>
  );
}
