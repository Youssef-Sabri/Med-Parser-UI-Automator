/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // [Clinical Assistant Palette]
        'clinical-blue': '#2563EB',        // Royal Blue - Trust
        'clinical-blue-hover': '#1D4ED8',  // Deep Blue
        'clinical-void': '#F8FAFC',        // Background
        'clinical-surface': '#FFFFFF',     // Cards
        'clinical-slate': '#475569',       // Text/Secondary
        'clinical-border': '#E2E8F0',      // Borders
        'vibrant-mint': '#10B981',         // Success
        'caution-amber': '#F59E0B',        // Warning
        'alert-crimson': '#EF4444',        // Critical
        'health-red': '#EF4444',           // Critical (alias for alert-crimson)
      },
      fontFamily: {
        display: ['Outfit', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'clinical': '0 4px 12px -2px rgba(15, 23, 42, 0.04), 0 2px 6px -1px rgba(15, 23, 42, 0.02)',
      },
      animation: {
        'scanline': 'scanline 6s linear infinite',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.5 },
        }
      }
    },
  },
  plugins: [],
}
