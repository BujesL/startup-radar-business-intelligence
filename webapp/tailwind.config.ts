import type { Config } from "tailwindcss";

/**
 * Token system do dashboard — direção "painel de operações", não "site
 * institucional". Paleta escura de baixo contraste com um único acento
 * (verde-esmeralda: cor de crescimento/mercado, evitando o terracota
 * associado à Anthropic/Claude e o roxo genérico de SaaS).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: {
          950: "#0A0B0D",
          900: "#111318",
          850: "#161920",
          800: "#1C2029",
          700: "#272C38",
          600: "#3A4152",
          400: "#7B8394",
          200: "#C4C9D4",
          50: "#F5F6F8",
        },
        accent: {
          DEFAULT: "#3ECF8E",
          dim: "#1F5C43",
          bright: "#5FE8AC",
        },
        warn: "#E8A33D",
        danger: "#E8544B",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "10px",
      },
    },
  },
  plugins: [],
};

export default config;
