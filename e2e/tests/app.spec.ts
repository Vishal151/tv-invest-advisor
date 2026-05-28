import { test, expect } from '@playwright/test'

test('health endpoint returns ok', async ({ request }) => {
  const res = await request.get('http://localhost:8001/api/health')
  expect(res.status()).toBe(200)
  const body = await res.json()
  expect(body.status).toBe('ok')
})

test('homepage loads with question input', async ({ page }) => {
  await page.goto('/')
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  await expect(textarea).toBeVisible()
  const submitBtn = page.getByRole('button', { name: 'Ask' })
  await expect(submitBtn).toBeDisabled()
})

test('submit button enables when question is typed', async ({ page }) => {
  await page.goto('/')
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  const submitBtn = page.getByRole('button', { name: 'Ask' })

  await textarea.fill('Does TV advertising work for FMCG brands?')
  await expect(submitBtn).toBeEnabled()
})

test('submitting a question shows a mock answer', async ({ page }) => {
  await page.goto('/')
  const textarea = page.getByPlaceholder('Ask Cue about your TV investment…')
  await textarea.fill('Does TV advertising work for FMCG brands?')

  await page.getByRole('button', { name: 'Ask' }).click()

  // Mock answer text rendered by AssistantBubble
  await expect(
    page.getByText('Mock: TV advertising delivers strong ROI based on Thinkbox research.')
  ).toBeVisible({ timeout: 20_000 })
})
