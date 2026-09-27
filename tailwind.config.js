var tailwind_config_default = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        forest: {
          950: "var(--forest-950)",
          900: "var(--forest-900)",
          700: "var(--forest-700)",
          600: "var(--forest-600)",
          500: "var(--forest-500)"
        },
        moss: {
          300: "var(--moss-300)",
          100: "var(--moss-100)"
        },
        sage: {
          50: "var(--sage-50)"
        },
        paper: "var(--paper)",
        ink: {
          900: "var(--ink-900)",
          600: "var(--ink-600)",
          400: "var(--ink-400)"
        },
        line: "var(--line)",
        bark: {
          500: "var(--bark-500)"
        }
      },
      borderRadius: {
        control: "6px",
        panel: "10px"
      },
      boxShadow: {
        sm: "0 6px 18px rgba(15,31,23,0.08)",
        md: "0 14px 38px rgba(15,31,23,0.10)"
      },
      fontFamily: {
        ui: ["Inter", "Geist", "system-ui", "sans-serif"],
        display: ["Fraunces", "Source Serif 4", "Georgia", "serif"],
        mono: ["JetBrains Mono", "IBM Plex Mono", "ui-monospace", "monospace"]
      }
    }
  },
  plugins: []
};
export {
  tailwind_config_default as default
};
