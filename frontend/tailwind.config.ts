import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx,mdx}", "./components/**/*.{ts,tsx,mdx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        field: "#f5f7f1",
        line: "#c6d0c4",
        oxide: "#9d2f2f",
        signal: "#c9ff3d",
        moss: "#335f42",
        steel: "#64736a"
      },
      boxShadow: {
        rule: "0 1px 0 rgba(23,32,27,0.16)"
      }
    }
  },
  plugins: []
};

export default config;
