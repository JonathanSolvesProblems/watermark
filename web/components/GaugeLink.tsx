"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

type VT = Document & { startViewTransition?: (cb: () => Promise<void>) => unknown };

// Opens an incident so its small gauge on the dashboard grows into the incident
// page's staff (View Transitions, matched by name). Without browser support, or with
// reduced motion, it is an ordinary link.
export default function GaugeLink({ href, view, className, children }: {
  href: string;
  view: string;
  className?: string;
  children: React.ReactNode;
}) {
  const router = useRouter();

  function go(e: React.MouseEvent<HTMLAnchorElement>) {
    const doc = document as VT;
    if (!doc.startViewTransition || e.metaKey || e.ctrlKey || e.shiftKey ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    e.preventDefault();
    doc.startViewTransition(() => new Promise<void>((done) => {
      router.push(href);
      // The incident page renders its staff once its data arrives; wait for it, briefly.
      // Timers, not requestAnimationFrame: the browser suspends rendering (and rAF) until
      // this callback resolves, so an rAF loop here waits on itself and freezes the page.
      const started = Date.now();
      const check = () => {
        if (document.querySelector(`[data-view="${view}"]`) || Date.now() - started > 800) done();
        else setTimeout(check, 16);
      };
      setTimeout(check, 16);
    }));
  }

  return (
    <Link href={href} onClick={go} className={className}>
      {children}
    </Link>
  );
}
