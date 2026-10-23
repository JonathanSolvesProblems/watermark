import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Watermark",
    short_name: "Watermark",
    description: "When a Ring sensor finds water, the camera records it.",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#1b2a47",
    theme_color: "#1b2a47",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
