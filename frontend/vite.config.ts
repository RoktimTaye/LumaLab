import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    proxy: {
      '/api': loadEnv(mode, '.', 'LUMALAB_TEST_').LUMALAB_TEST_API ?? 'http://127.0.0.1:8000',
    },
  },
}))
