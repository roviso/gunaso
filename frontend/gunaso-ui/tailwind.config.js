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
        sans: ['"Public Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Bricolage Grotesque"', '"Public Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif']
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.05)',
        'card-hover': '0 10px 30px -8px rgb(15 31 56 / 0.16), 0 4px 10px -6px rgb(15 31 56 / 0.08)',
        glow: '0 0 0 1px rgb(230 57 70 / 0.12), 0 12px 32px -8px rgb(230 57 70 / 0.35)'
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(18px)' },
          to: { opacity: '1', transform: 'translateY(0)' }
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' }
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.92)' },
          to: { opacity: '1', transform: 'scale(1)' }
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' }
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.55', transform: 'scale(0.85)' }
        },
        'float-slow': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-12px)' }
        },
        'draw-line': {
          from: { transform: 'scaleX(0)' },
          to: { transform: 'scaleX(1)' }
        }
      },
      animation: {
        'fade-up': 'fade-up 0.6s cubic-bezier(0.22, 1, 0.36, 1) both',
        'fade-in': 'fade-in 0.5s ease-out both',
        'scale-in': 'scale-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) both',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'float-slow': 'float-slow 7s ease-in-out infinite',
        'draw-line': 'draw-line 0.8s cubic-bezier(0.22, 1, 0.36, 1) both'
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.22, 1, 0.36, 1)'
      }
    }
  },
  plugins: [forms]
}
