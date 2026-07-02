import { defineConfig } from '@playwright/test'
import path from 'path'

export default defineConfig({
  testDir: './capture',
  timeout: 60_000,
  retries: 0,
  outputDir: path.join(__dirname, '../docs/demo'),
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    viewport: { width: 1400, height: 900 },
    video: { mode: 'on', size: { width: 1400, height: 900 } },
    // Slow down interactions so the video looks deliberate
    launchOptions: { slowMo: 350 },
  },
  webServer: [
    {
      command:
        'cd ../backend && LLM_MOCK=true APP_ENV=development uv run uvicorn app.main:app --host 0.0.0.0 --port 8001',
      url: 'http://localhost:8001/api/health',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: 'cd ../frontend && NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
