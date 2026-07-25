import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#001F3F",
        background: "#F8FAFC",
        accent: "#00C2A8",
      },
    },
  },
  plugins: [],
} satisfies Config;