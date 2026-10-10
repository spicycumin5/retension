import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The backend serves its API under /api, same as in production.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
