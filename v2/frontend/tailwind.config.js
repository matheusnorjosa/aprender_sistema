/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    // Mesmas quebras do AntD (Grid, `responsive` das colunas): `lg:` e as colunas da tabela
    // mudam na mesma largura. Programa C, v2/docs/specs/frontend/pages.spec.md "Padrão responsivo".
    screens: {
      sm: '576px',
      md: '768px',
      lg: '992px',
      xl: '1200px',
      '2xl': '1600px',
    },
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
