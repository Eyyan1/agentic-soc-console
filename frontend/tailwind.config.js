/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#050816",
          900: "#0a1020",
          850: "#11182b",
          800: "#172036"
        },
        signal: {
          cyan: "#6ee7f9",
          emerald: "#34d399",
          amber: "#fbbf24",
          orange: "#fb923c",
          red: "#f87171"
        }
      },
      boxShadow: {
        panel: "0 12px 48px rgba(0, 0, 0, 0.28)"
      },
      backgroundImage: {
        "soc-grid":
          "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)"
      }
    }
  },
  plugins: []
};
