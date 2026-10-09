import type { Config } from "tailwindcss";

// Colours are the theme tokens in globals.css; Tailwind only names them so a
// component can never introduce a value the manifest does not have.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        concrete: "var(--concrete)",
        plate: "var(--plate)",
        raised: "var(--plate-raised)",
        ink: "var(--ink)",
        stencil: "var(--stencil)",
        seam: "var(--seam)",
        line: "var(--line)",
        onLine: "var(--on-line)",
        stain: "var(--stain)",
        staff: "var(--staff)",
        tick: "var(--tick)",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        none: "0",
        sm: "3px",
        DEFAULT: "3px",
      },
    },
  },
  plugins: [],
};

export default config;
