import forms from '@tailwindcss/forms'

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#E63946',
          50:  '#fef2f2',
          100: '#fee2e3',
          200: '#fdc8ca',
          300: '#fba3a7',
          400: '#f77175',
          500: '#E63946',
          600: '#d32433',
          700: '#b11828',
          800: '#931727',
          900: '#7c1926',
        },
        secondary: {
          DEFAULT: '#1D3557',
          700: '#2d43d5',
          800: '#243a6e',
          900: '#0f1f38',
        },
        accent: '#457B9D',
        surface: '#ffffff',
        'app-bg': '#F8F9FA'
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif']
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.05)'
      }
    }
  },
  plugins: [forms]
}
