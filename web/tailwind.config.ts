import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1b1f24",
        muted: "#5f6b76",
        line: "#d9dee3",
        paper: "#fbfaf7",
        ground: "#f4f2ec",
        water: "#2a6f9e",
        waterDeep: "#1d4f72",
        warn: "#a14d2b",
        ok: "#2f6b3a",
      },
      fontFamily: {
        serif: ["Georgia", "Times New Roman", "serif"],
        mono: ["ui-monospace", "Cascadia Mono", "Consolas", "monospace"],
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
