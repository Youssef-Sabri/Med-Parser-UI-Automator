import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { existsSync } from 'fs'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  envDir: existsSync(resolve(__dirname, '.env')) ? '.' : '..',
  server: {
    host: true,
  }
})
