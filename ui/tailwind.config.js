/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          dark: '#030712',
          card: '#081226',
          border: '#1e293b',
          cyan: '#06b6d4',
          blue: '#3b82f6',
          glow: 'rgba(6, 182, 212, 0.35)',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 12s linear infinite',
        'spin-reverse': 'spin 8s linear infinite reverse',
      }
    },
  },
  plugins: [],
}
