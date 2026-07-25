import type { Config } from "tailwindcss";

import { theme } from "./src/config/theme";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: theme.colors.primary,
        background: theme.colors.background,
        accent: theme.colors.accent,
      },
    },
  },
  plugins: [],
} satisfies Config;