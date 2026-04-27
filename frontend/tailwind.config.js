/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-dark': '#0f172a',
        'brand-blue': '#3b82f6',
        'brand-green': '#10b981',
        'brand-yellow': '#fcd34d',
        'brand-red': '#ef4444',
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
