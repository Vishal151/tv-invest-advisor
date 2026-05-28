/**
 * Demo capture script — produces screenshots and a video for docs/README.
 *
 * Run:  cd e2e && npx playwright test --config=capture-demo.config.ts
 * Output: docs/demo/*.png  +  docs/demo/<folder>/video.webm  (moved by afterAll)
 *
 * Uses LLM_MOCK=true — no API keys needed.
 */
import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const DEMO_DIR = path.join(__dirname, '../../docs/demo')

function shot(name: string) {
  return path.join(DEMO_DIR, name)
}

test('demo: chat flow and PDF export', async ({ page }, testInfo) => {
  // ── 1. Empty state ──────────────────────────────────────────────────────────
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  await page.screenshot({ path: shot('01-empty-state.png'), fullPage: false })

  // ── 2. Select context chips ─────────────────────────────────────────────────
  // Sector → FMCG
  await page.getByRole('button', { name: /SECTOR/i }).click()
  await page.getByRole('option', { name: 'FMCG' }).click()

  // Stage → Scale-up
  await page.getByRole('button', { name: /STAGE/i }).click()
  await page.getByRole('option', { name: 'Scale-up' }).click()

  // TV History → Never run TV
  await page.getByRole('button', { name: /TV HISTORY/i }).click()
  await page.getByRole('option', { name: 'Never run TV' }).click()

  // Goal → Brand building
  await page.getByRole('button', { name: /GOAL/i }).click()
  await page.getByRole('option', { name: 'Brand building' }).click()

  // Budget → £100k–£500k
  await page.getByRole('button', { name: /BUDGET/i }).click()
  await page.getByRole('option', { name: '£100k–£500k' }).click()

  await page.screenshot({ path: shot('02-chips-selected.png'), fullPage: false })

  // ── 3. Type question ────────────────────────────────────────────────────────
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  await textarea.click()
  await textarea.type('Does TV advertising work for an FMCG scale-up with no TV history?', {
    delay: 35,
  })

  await expect(page.getByRole('button', { name: 'Ask' })).toBeEnabled()
  await page.screenshot({ path: shot('03-question-typed.png'), fullPage: false })

  // ── 4. Submit and wait for answer ───────────────────────────────────────────
  await page.getByRole('button', { name: 'Ask' }).click()

  await expect(
    page.getByText('Mock: TV advertising delivers strong ROI based on Thinkbox research.')
  ).toBeVisible({ timeout: 20_000 })

  // Brief pause so the answer is fully visible in the video
  await page.waitForTimeout(1200)
  await page.screenshot({ path: shot('04-answer.png'), fullPage: false })

  // ── 5. Open export modal ────────────────────────────────────────────────────
  await page.getByRole('button', { name: /Export/i }).click()

  await expect(page.getByText('Export Preview')).toBeVisible({ timeout: 5_000 })

  await page.waitForTimeout(800)
  await page.screenshot({ path: shot('05-export-modal.png'), fullPage: false })

  // Hold for a moment so video captures the modal clearly
  await page.waitForTimeout(1200)

  // ── 6. Move the Playwright video to a predictable location ──────────────────
  testInfo.annotations.push({ type: 'screenshots', description: DEMO_DIR })

  const videoPath = await page.video()?.path()
  if (videoPath) {
    // Video is finalised only after the browser context closes (end of test).
    // We store the source path so the afterAll hook can move it.
    testInfo.annotations.push({ type: 'videoPath', description: videoPath })
  }
})

// After all tests finish the browser context is closed and the video is ready.
test.afterAll(async ({}, testInfo) => {
  // Find any video annotation written above and move the file.
  // (testInfo is per-worker here, so we scan docs/demo for .webm files instead.)
  const entries = fs.readdirSync(DEMO_DIR, { withFileTypes: true })
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const subdir = path.join(DEMO_DIR, entry.name)
      const files = fs.readdirSync(subdir)
      for (const file of files) {
        if (file.endsWith('.webm') || file.endsWith('.mp4')) {
          const dest = path.join(DEMO_DIR, 'demo.webm')
          fs.renameSync(path.join(subdir, file), dest)
          console.log(`Video saved → docs/demo/demo.webm`)
        }
      }
    }
  }
})
