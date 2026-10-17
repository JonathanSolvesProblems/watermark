import type { Metadata, Viewport } from "next";
import { Big_Shoulders, Commissioner } from "next/font/google";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import Wordmark from "@/components/Wordmark";
import "./globals.css";

// Variable with an optical-size axis: the condensed display cut at readout sizes, the text cut at labels.
const display = Big_Shoulders({ subsets: ["latin"], axes: ["opsz"], variable: "--font-display" });
const body = Commissioner({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Watermark",
  description: "When a Ring sensor finds water, the camera goes to the water. Evidence your insurer can use.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#16213a" },
    { media: "(prefers-color-scheme: light)", color: "#f0f1ee" },
  ],
};

// Applied before paint so a stored dark preference never flashes light first.
const themeBoot = `try{var t=localStorage.getItem("wm-theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" className={`${display.variable} ${body.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBoot }} />
      </head>
      <body className="min-h-screen">
        <header className="border-b border-seam">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 py-3 sm:py-0 sm:h-16 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <Link href="/" className="text-ink" aria-label="Watermark home">
              <Wordmark height={26} />
            </Link>
            <nav className="flex w-full sm:w-auto items-center justify-between sm:justify-end -mx-2 sm:mx-0 sm:gap-1">
              <NavLink href="/dashboard">Dashboard</NavLink>
              <NavLink href="/setup">Setup</NavLink>
              <NavLink href="/settings">Settings</NavLink>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 sm:px-6 py-8 sm:py-10">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 sm:px-6 pb-10 text-[13px] text-stencil leading-relaxed grid gap-1">
          <p>
            Watermark records what your Ring devices saw. It never states a cause. Manage your subscription in Ring
            &rsaquo; My Apps, and device settings such as motion zones in the Ring app.
          </p>
          <p>
            Built by Jonathan Andrei after two floods in one year. More of what I build at{" "}
            <a href="https://jonathansolvesproblems.com" className="underline decoration-seam underline-offset-2 hover:text-ink hover:decoration-current transition-colors">
              jonathansolvesproblems.com
            </a>
            .
          </p>
        </footer>
      </body>
    </html>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="px-2 py-2 text-[15px] text-stencil hover:text-ink transition-colors">
      {children}
    </Link>
  );
}
