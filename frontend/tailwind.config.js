/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: "rgb(var(--paper) / <alpha-value>)",
          soft: "rgb(var(--paper-soft) / <alpha-value>)",
          deep: "rgb(var(--paper-deep) / <alpha-value>)",
        },
        ink: {
          950: "rgb(var(--ink-950) / <alpha-value>)",
          900: "rgb(var(--ink-900) / <alpha-value>)",
          800: "rgb(var(--ink-800) / <alpha-value>)",
          700: "rgb(var(--ink-700) / <alpha-value>)",
          600: "rgb(var(--ink-600) / <alpha-value>)",
        },
        seal: {
          DEFAULT: "rgb(var(--seal) / <alpha-value>)",
          dark: "rgb(var(--seal-dark) / <alpha-value>)",
          soft: "rgb(var(--seal-soft) / <alpha-value>)",
        },
        jade: {
          DEFAULT: "rgb(var(--jade) / <alpha-value>)",
        },
        amber: {
          DEFAULT: "rgb(var(--amber) / <alpha-value>)",
        },
        line: {
          DEFAULT: "rgb(var(--line) / <alpha-value>)",
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "serif"],
        display: ["var(--font-display)", "var(--font-serif)", "serif"],
      },
      backgroundImage: {
        'paper-grain': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.08'/%3E%3C/svg%3E\")",
      }
    },
  },
  plugins: [],
}
