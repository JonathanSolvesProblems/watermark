"use client";

import { useEffect, useRef, useState } from "react";

// A readout that rolls to its value in detented steps, like a mechanical counter,
// the first time it is shown. Later updates (the page polls every few seconds) snap
// straight to the new value, and reduced motion always snaps.
export default function Counter({ value, decimals = 0, steps = 10, ms = 600 }: {
  value: number | null | undefined;
  decimals?: number;
  steps?: number;
  ms?: number;
}) {
  const [shown, setShown] = useState<number | null>(null);
  const rolled = useRef(false);

  useEffect(() => {
    if (value == null) return;
    const still = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (rolled.current || still) {
      setShown(value);
      return;
    }
    rolled.current = true;
    let i = 0;
    const t = setInterval(() => {
      i += 1;
      setShown(i >= steps ? value : (value * i) / steps);
      if (i >= steps) clearInterval(t);
    }, ms / steps);
    return () => clearInterval(t);
  }, [value, steps, ms]);

  if (value == null) return <>–</>;
  return <>{(shown ?? 0).toFixed(decimals)}</>;
}
