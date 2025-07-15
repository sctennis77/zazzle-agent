import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    globals: true,
    css: false,
    // Mock environment variables for tests
    env: {
      VITE_STRIPE_PUBLISHABLE_KEY: 'pk_test_mock_key_for_testing',
      VITE_API_BASE: 'http://localhost:8000',
      VITE_WS_BASE: 'ws://localhost:8000'
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})