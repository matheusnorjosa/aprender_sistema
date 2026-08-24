/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Cores de marca via CSS vars (definidas em src/index.css :root, espelho de
      // BRAND_COLORS). Habilita `bg-primary`/`text-primary`/`border-primary` etc.
      // lendo a MESMA fonte que o AntD e o CSS — um SSOT alimentando os três.
      colors: {
        primary: {
          DEFAULT: 'var(--as-primary)',
          dark: 'var(--as-primary-dark)',
          light: 'var(--as-primary-light)',
        },
      },
    },
  },
  plugins: [],
}
