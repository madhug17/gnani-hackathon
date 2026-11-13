/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        gnani: {
          blue: '#1E40AF',
          cyan: '#06B6D4',
          orange: '#F97316',
          purple: '#8B5CF6',
          dark: '#0B0F19',
          card: '#111827',
          border: '#1F2937'
        }
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(6, 182, 212, 0.4)' },
          '100%': { boxShadow: '0 0 20px rgba(6, 182, 212, 0.8)' },
        }
      }
    },
  },
  plugins: [],
}
