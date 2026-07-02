/**
 * Demo capture script — produces screenshots and a video for docs/README.
 *
 * Run:  cd e2e && npx playwright test --config=capture-demo.config.ts
 * Output: docs/demo/*.png  +  docs/demo/<folder>/video.webm  (moved by afterAll)
 *
 * Uses LLM_MOCK=true — no API keys needed.
 */
import { test, expect, Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const DEMO_DIR = path.join(__dirname, '../../docs/demo')

function shot(name: string) {
  return path.join(DEMO_DIR, name)
}

// Pause between demo beats so viewers can register each step in the video.
const BEAT = 900

/**
 * Signpost banner baked into the recording — the video has no audio, so this
 * narrates each step. Injected into the page (not post-processed) so timing
 * always matches the interactions. Hidden before every README screenshot.
 */
async function caption(page: Page, kicker: string, text: string) {
  await page.evaluate(
    async ({ kicker, text }) => {
      let el = document.getElementById('demo-caption')
      if (!el) {
        el = document.createElement('div')
        el.id = 'demo-caption'
        el.style.cssText = [
          'position: fixed',
          'left: 50%',
          'top: 10px',
          'transform: translateX(-50%)',
          'z-index: 99999',
          'display: flex',
          'align-items: baseline',
          'gap: 14px',
          'max-width: 760px',
          'padding: 13px 24px',
          'border-radius: 8px',
          'background: #17130e',
          'color: #f5f0e8',
          'box-shadow: 0 8px 28px rgba(23, 19, 14, 0.35)',
          'font-family: Georgia, "Times New Roman", serif',
          'font-size: 17px',
          'line-height: 1.35',
          'white-space: nowrap',
          'opacity: 0',
          'transition: opacity 0.35s ease',
          'pointer-events: none',
        ].join(';')
        const kickerEl = document.createElement('span')
        kickerEl.setAttribute('data-kicker', '')
        kickerEl.style.cssText =
          'font-family: ui-monospace, monospace; font-size: 11px;' +
          ' letter-spacing: 0.14em; color: #e05252; text-transform: uppercase;'
        const textEl = document.createElement('span')
        textEl.setAttribute('data-text', '')
        el.append(kickerEl, textEl)
        document.body.appendChild(el)
      }
      if (el.style.opacity === '1') {
        el.style.opacity = '0'
        await new Promise((r) => setTimeout(r, 380))
      }
      el.querySelector('[data-kicker]')!.textContent = kicker
      el.querySelector('[data-text]')!.textContent = text
      // Next frame so the browser registers opacity 0 before fading in
      await new Promise((r) => requestAnimationFrame(() => r(null)))
      el.style.opacity = '1'
    },
    { kicker, text }
  )
}

async function hideCaption(page: Page) {
  await page.evaluate(async () => {
    const el = document.getElementById('demo-caption')
    if (el && el.style.opacity === '1') {
      el.style.opacity = '0'
      await new Promise((r) => setTimeout(r, 380))
    }
  })
}

test('demo: chat flow and PDF export', async ({ page }, testInfo) => {
  // ── 1. Empty state ──────────────────────────────────────────────────────────
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  // Hold the empty state so the video opens on a settled, readable frame
  await page.waitForTimeout(600)
  await page.screenshot({ path: shot('01-empty-state.png'), fullPage: false })

  await caption(page, 'Cue · TV investment advisor', 'Answers grounded in published Thinkbox research')
  await page.waitForTimeout(3000)

  // ── 2. Select context chips ─────────────────────────────────────────────────
  await caption(page, 'Step 1 · Set your context', 'Sector, stage, TV history, goal and budget')

  // Sector → FMCG
  await page.getByRole('button', { name: /SECTOR/i }).click()
  await page.getByRole('option', { name: 'FMCG' }).click()
  await page.waitForTimeout(BEAT)

  // Stage → Scale-up
  await page.getByRole('button', { name: /STAGE/i }).click()
  await page.getByRole('option', { name: 'Scale-up' }).click()
  await page.waitForTimeout(BEAT)

  // TV History → Never run TV
  await page.getByRole('button', { name: /TV HISTORY/i }).click()
  await page.getByRole('option', { name: 'Never run TV' }).click()
  await page.waitForTimeout(BEAT)

  // Goal → Brand building
  await page.getByRole('button', { name: /GOAL/i }).click()
  await page.getByRole('option', { name: 'Brand building' }).click()
  await page.waitForTimeout(BEAT)

  // Budget → £100k–£500k
  await page.getByRole('button', { name: /BUDGET/i }).click()
  await page.getByRole('option', { name: '£100k–£500k' }).click()
  await page.waitForTimeout(BEAT)

  await hideCaption(page)
  await page.screenshot({ path: shot('02-chips-selected.png'), fullPage: false })

  // ── 3. Type question ────────────────────────────────────────────────────────
  await caption(page, 'Step 2 · Ask', 'Any TV investment question, in plain English')

  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  await textarea.click()
  await textarea.type('Does TV advertising work for an FMCG scale-up with no TV history?', {
    delay: 65,
  })

  await expect(page.getByRole('button', { name: 'Ask' })).toBeEnabled()
  await page.waitForTimeout(BEAT)
  await hideCaption(page)
  await page.screenshot({ path: shot('03-question-typed.png'), fullPage: false })

  // ── 4. Submit and wait for answer ───────────────────────────────────────────
  await page.getByRole('button', { name: 'Ask' }).click()

  // Narrate the pipeline while it runs — with DEMO_REAL=1 this is genuinely
  // retrieval + GPT-4o generation + grounding checks, not a canned wait.
  await caption(page, 'Grounded generation', 'Retrieving Thinkbox research · generating a cited answer')

  // The Copy button renders with every assistant answer — mock or real.
  await expect(page.getByRole('button', { name: 'Copy' })).toBeVisible({ timeout: 120_000 })

  // Dwell on the answer long enough to read the summary, stat card and sources
  await caption(page, 'Step 3 · Evidence-backed answer', 'Every stat is cited to its Thinkbox source')
  await page.waitForTimeout(3200)
  await caption(page, 'Step 3 · Evidence rail', 'The retrieved passages appear alongside, with links')
  await page.waitForTimeout(3200)
  await hideCaption(page)
  await page.screenshot({ path: shot('04-answer.png'), fullPage: false })

  // ── 5. Open export modal ────────────────────────────────────────────────────
  await page.getByRole('button', { name: /Export/i }).click()

  await expect(page.getByText('Export Preview')).toBeVisible({ timeout: 5_000 })

  await caption(page, 'Step 4 · Export', 'A client-ready PDF one-pager, cited and dated')
  await page.waitForTimeout(800)
  await hideCaption(page)
  await page.screenshot({ path: shot('05-export-modal.png'), fullPage: false })

  // Hold so the export preview can actually be read
  await caption(page, 'Step 4 · Export', 'A client-ready PDF one-pager, cited and dated')
  await page.waitForTimeout(3500)

  // ── 6. Close the modal for a clean final beat ───────────────────────────────
  await page.getByRole('button', { name: 'Close' }).click()
  await caption(page, 'Cue', 'Grounded. Cited. No hallucinated numbers.')
  await page.waitForTimeout(3000)
  await hideCaption(page)
  await page.waitForTimeout(600)

  // ── 7. Move the Playwright video to a predictable location ──────────────────
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
