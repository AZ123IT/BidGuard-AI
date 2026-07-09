import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx,mdx}", "./components/**/*.{ts,tsx,mdx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        cream: "var(--cream)",
        surface: "var(--surface)",
        field: "var(--field)",
        line: "var(--line)",
        oxide: "var(--oxide)",
        signal: "var(--signal)",
        accent: "var(--accent)",
        success: "var(--success)",
        steel: "var(--muted)",
        muted: "var(--muted)"
      },
      boxShadow: {
        rule: "var(--shadow-rule)",
        soft: "var(--shadow-soft)"
      }
    }
  },
  plugins: []
};

export default config;
