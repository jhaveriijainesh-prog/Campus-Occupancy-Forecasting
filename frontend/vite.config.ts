import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ command, mode }) => {
  const frontendRoot = process.cwd()
  const projectRoot = resolve(frontendRoot, '..')
  const env = {
    ...loadEnv(mode, projectRoot, ''),
    ...loadEnv(mode, frontendRoot, ''),
  }
  const apiTarget = 'http://127.0.0.1:8000'
  let apiReadKey = env.API_READ_KEY || env.FASTAPI_API_KEY

  if (command === 'serve' && !apiReadKey) {
    apiReadKey = execFileSync(
      process.env.PYTHON || 'python',
      [
        '-c',
        'from app.core.config import get_settings; print(get_settings().api_read_key)',
      ],
      { cwd: projectRoot, encoding: 'utf8' },
    ).trim()
  }

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          headers: apiReadKey ? { 'X-API-Key': apiReadKey } : {},
        },
      },
    },
  }
})
