/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1440px",
      },
    },
    extend: {
      colors: {
        vana: {
          forest: "#183D32",
          ivory: "#F5F3EA",
          sage: "#A8B99B",
          gold: "#D6A76A",
          charcoal: "#29332F",
          white: "#FFFFFF",
          crimson: "#9E3A2B",
        },
        border: "rgba(41, 51, 47, 0.12)",
        input: "rgba(41, 51, 47, 0.15)",
        ring: "#183D32",
        background: "#F5F3EA",
        foreground: "#29332F",
        primary: {
          DEFAULT: "#183D32",
          foreground: "#FFFFFF",
        },
        secondary: {
          DEFAULT: "#A8B99B",
          foreground: "#183D32",
        },
        muted: {
          DEFAULT: "rgba(41, 51, 47, 0.08)",
          foreground: "#5C6E66",
        },
        accent: {
          DEFAULT: "#D6A76A",
          foreground: "#29332F",
        },
        destructive: {
          DEFAULT: "#9E3A2B",
          foreground: "#FFFFFF",
        },
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#29332F",
        },
        popover: {
          DEFAULT: "#FFFFFF",
          foreground: "#29332F",
        },
      },
      fontFamily: {
        heading: ["Manrope", "sans-serif"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px",
      },
      boxShadow: {
        subtle: "0 1px 3px rgba(24, 61, 50, 0.05)",
        floating: "0 4px 12px rgba(24, 61, 50, 0.08)",
      },
    },
  },
  plugins: [],
};
