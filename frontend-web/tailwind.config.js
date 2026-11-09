/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#070a11',
          surface: '#0e1524',
          card: '#131c2e',
          cardHover: '#19253d',
          border: '#1f2d42',
          borderSubtle: '#172336',
          accent: '#00b0ff',
          bullish: '#00e676',
          bearish: '#ff3d57',
          gold: '#ffd600',
        }
      }
    },
  },
  plugins: [],
}
