import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { loadEnv } from 'vite'
import { createApiProxy } from './api-proxy'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxy = createApiProxy(process.env.REPOMIND_PYTHON_SERVICE_URL || env.REPOMIND_PYTHON_SERVICE_URL || 'http://127.0.0.1:8000')
  return {
    plugins: [vue()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      // Do not broaden FastAPI's explicit origin allowlist via Vite defaults.
      cors: false,
      proxy,
    },
    preview: { host: '127.0.0.1', cors: false, proxy },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/tests/setup.ts'],
      css: false,
    },
  }
})
