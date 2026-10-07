import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// Absolute origin for social-card meta tags in index.html (crawlers ignore
// relative og:image URLs). Override per deployment with VITE_SITE_URL.
const SITE_URL = (process.env.VITE_SITE_URL || 'https://gunaaso.com').replace(/\/$/, '')

const siteUrlPlugin = {
  name: 'gunaso-site-url',
  transformIndexHtml: (html) => html.replaceAll('__SITE_URL__', SITE_URL),
}

export default defineConfig(({ command, mode }) => ({
  // Django serves the built assets under STATIC_URL; the dev server and the
  // native app (vite build --mode mobile) serve from root.
  base: command === 'build' && mode !== 'mobile' ? '/static/' : '/',
  plugins: [vue(), siteUrlPlugin],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
}))