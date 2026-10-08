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
        wet: "var(--wet)",
        onwet: "var(--on-wet)",
        staff: "var(--staff)",
        tick: "var(--tick)",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        none: "0",
        sm: "2px",
        DEFAULT: "2px",
      },
    },
  },
  plugins: [],
};

export default config;
