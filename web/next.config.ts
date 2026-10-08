import type { NextConfig } from "next";

// The server's paths are proxied so a single tunnel (one free ngrok domain) carries
// Ring's webhook, token exchange and the web pages. /link stays a page here: Ring's
// Account Link URL lands directly on the sign-in screen with the nonce intact.
const backend = process.env.BACKEND_URL || "http://127.0.0.1:8765";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // A preview build (design work, mock data) must not overwrite the live build's output.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  images: { unoptimized: true },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/webhooks/:path*", destination: `${backend}/webhooks/:path*` },
      { source: "/oauth/:path*", destination: `${backend}/oauth/:path*` },
      { source: "/rover/:path*", destination: `${backend}/rover/:path*` },
      { source: "/health", destination: `${backend}/health` },
    ];
  },
};

export default nextConfig;
