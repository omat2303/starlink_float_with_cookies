/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Variante AdminCN: los tokens viejos apuntan a la escala zinc para que
        // el resto de componentes cambie de look sin tocarlos uno por uno.
        dark: {
          900: '#09090b',
          800: '#0f0f12',
          700: '#18181b',
          600: '#27272a',
          500: '#3f3f46',
          400: '#52525b',
        },
        accent: {
          blue: '#e4e4e7',
          green: '#34d399',
          yellow: '#fbbf24',
          red: '#f87171',
          purple: '#a1a1aa',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
