import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development (npm run dev) calls to /api are forwarded to the FastAPI server.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': process.env.VITE_API_PROXY || 'http://localhost:8000' },
  },
})
