import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accept: "var(--c-accept)",
        review: "var(--c-review)",
        flag: "var(--c-flag)",
        neutral: "var(--c-neutral)",
      },
    },
  },
  plugins: [],
} satisfies Config;
