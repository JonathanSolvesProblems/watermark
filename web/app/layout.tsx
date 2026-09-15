import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Watermark",
  description: "When a Ring sensor finds water, the camera goes to the water. Evidence your insurer can use.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-line bg-paper">
          <div className="mx-auto max-w-5xl px-5 py-4 flex items-center justify-between gap-6">
            <Link href="/" className="flex items-baseline gap-3">
              <span className="text-2xl font-bold tracking-tight">Watermark</span>
              <span className="label text-muted hidden sm:inline">Ring · evidence pack</span>
            </Link>
            <nav className="flex gap-5 font-sans text-sm">
              <Link href="/dashboard" className="hover:text-water">Dashboard</Link>
              <Link href="/setup" className="hover:text-water">Setup</Link>
              <Link href="/settings" className="hover:text-water">Settings</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-5 py-8">{children}</main>
        <footer className="mx-auto max-w-5xl px-5 py-10 text-xs text-muted font-sans">
          Watermark records what Ring devices saw. It never states a cause. Subscriptions and cancellation are managed in
          Ring &rsaquo; My Apps; device settings such as motion zones live in the Ring app.
        </footer>
      </body>
    </html>
  );
}
