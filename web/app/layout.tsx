import type { Metadata, Viewport } from "next";
import { Big_Shoulders, Commissioner } from "next/font/google";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import "./globals.css";

// Variable with an optical-size axis: the condensed display cut at readout sizes, the text cut at labels.
const display = Big_Shoulders({ subsets: ["latin"], axes: ["opsz"], variable: "--font-display" });
const body = Commissioner({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Watermark",
  description: "When a Ring sensor finds water, the camera goes to the water. Evidence your insurer can use.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#1a1f1c" },
    { media: "(prefers-color-scheme: light)", color: "#e3e6df" },
  ],
};

// Applied before paint so a stored light preference never flashes dark first.
const themeBoot = `try{var t=localStorage.getItem("wm-theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" className={`${display.variable} ${body.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBoot }} />
      </head>
      <body className="min-h-screen">
        <header className="border-b border-seam">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 py-2 sm:py-0 sm:h-16 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
            <Link href="/" className="flex items-center gap-3" aria-label="Watermark home">
              <Mark />
              <span className="font-display text-[26px] font-extrabold uppercase tracking-[0.04em] leading-none">Watermark</span>
            </Link>
            <nav className="flex w-full sm:w-auto items-center justify-between sm:justify-end -mx-2 sm:mx-0 sm:gap-2">
              <NavLink href="/dashboard">Dashboard</NavLink>
              <NavLink href="/setup">Setup</NavLink>
              <NavLink href="/settings">Settings</NavLink>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 sm:px-6 py-8 sm:py-10">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 sm:px-6 pb-10 text-[13px] text-stencil leading-relaxed">
          Watermark records what your Ring devices saw. It never states a cause. Manage your subscription in Ring
          &rsaquo; My Apps, and device settings such as motion zones in the Ring app.
        </footer>
      </body>
    </html>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="label px-2 py-2 hover:text-ink transition-colors">
      {children}
    </Link>
  );
}

// The mark is a staff-gauge segment: an E-tick with the water line across it.
function Mark() {
  return (
    <svg width="22" height="26" viewBox="0 0 22 26" aria-hidden="true" className="shrink-0">
      <rect x="0.5" y="0.5" width="21" height="25" fill="var(--staff)" stroke="var(--tick)" />
      <rect x="3" y="3" width="3" height="20" fill="var(--tick)" />
      <rect x="6" y="3" width="9" height="3" fill="var(--tick)" />
      <rect x="6" y="11.5" width="6" height="3" fill="var(--tick)" />
      <rect x="1" y="17" width="20" height="8" fill="var(--wet)" />
    </svg>
  );
}
