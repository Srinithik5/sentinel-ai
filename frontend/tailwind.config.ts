import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

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
  plugins: [animate],
} satisfies Config;