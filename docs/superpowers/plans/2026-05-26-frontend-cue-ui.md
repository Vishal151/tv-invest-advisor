# Cue Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **CRITICAL — Next.js 16 / React 19:** Before writing any component code, read `frontend/node_modules/next/dist/docs/01-app/` to confirm App Router conventions. This version has breaking changes from your training data.

**Goal:** Build the Cue conversational TV-advertising advisor UI in Next.js 16, faithfully reproducing the design in `design_handoff_cue/` against the existing FastAPI backend at `POST /api/query`.

**Architecture:** Single-page App Router application. All interactive components are Client Components (`'use client'`). Zustand manages conversation thread, brief state, phase transitions, and overlay visibility. API client maps the flat backend response `{answer, sources, cached, model_used}` to the richer `Answer` type; headline/callout/chart render as absent when not available from the current API. Streaming is simulated via typewriter (backend does not SSE yet).

**Tech Stack:** Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Zustand v5 · Jest 29 · React Testing Library 16 · ts-jest · @testing-library/user-event

---

## File Structure

```
frontend/
├── app/
│   ├── globals.css              REPLACE: Cue design tokens + @tailwind
│   ├── layout.tsx               MODIFY: Newsreader, IBM Plex Sans/Mono fonts + metadata
│   └── page.tsx                 MODIFY: render <CueApp />
├── components/
│   ├── atoms/
│   │   ├── Headline.tsx
│   │   ├── Citation.tsx
│   │   ├── ProseWithCites.tsx
│   │   ├── SourceCard.tsx
│   │   ├── Callout.tsx
│   │   ├── Chart.tsx
│   │   ├── Trace.tsx
│   │   ├── Followups.tsx
│   │   └── CacheBadge.tsx
│   ├── composer/
│   │   ├── Chip.tsx
│   │   └── Composer.tsx
│   ├── thread/
│   │   ├── UserBubble.tsx
│   │   ├── AssistantBubble.tsx
│   │   ├── StreamingBubble.tsx
│   │   ├── RefusalCard.tsx
│   │   └── ErrorCard.tsx
│   ├── rail/
│   │   ├── EvidenceRail.tsx
│   │   └── CorpusRail.tsx
│   └── layout/
│       ├── Topbar.tsx
│       └── CueApp.tsx
├── overlays/
│   ├── HistoryDrawer.tsx
│   └── ExportModal.tsx
├── lib/
│   ├── types.ts
│   ├── api.ts
│   └── store.ts
├── __tests__/
│   ├── atoms/          (one .test.tsx per atom)
│   ├── composer/
│   ├── thread/
│   ├── rail/
│   ├── layout/
│   └── lib/            (api.test.ts, store.test.ts)
├── jest.config.ts
└── jest.setup.ts
```

---

## Design Token Reference

All colors, typography, and spacing come from `design_handoff_cue/design-tokens.css`. Key values:

| Token | Value | Use |
|-------|-------|-----|
| `--cue-paper` | `oklch(0.975 0.008 75)` | App background |
| `--cue-paper-2` | `oklch(0.955 0.010 75)` | Rail, hover bg |
| `--cue-paper-3` | `oklch(0.930 0.012 75)` | Chart track, thumb bg |
| `--cue-ink` | `oklch(0.20 0.012 60)` | Primary text |
| `--cue-ink-2` | `oklch(0.35 0.012 60)` | Body prose |
| `--cue-ink-3` | `oklch(0.55 0.012 60)` | Meta/tertiary |
| `--cue-ink-4` | `oklch(0.72 0.010 60)` | Disabled/dividers |
| `--cue-rule` | `oklch(0.85 0.012 70)` | Standard border |
| `--cue-rule-2` | `oklch(0.92 0.010 70)` | Subtle divider |
| `--cue-accent` | `oklch(0.55 0.16 28)` | Broadcast red |
| `--cue-accent-soft` | `oklch(0.55 0.16 28 / 0.10)` | Chip bg, callout bg |
| `--cue-accent-ink` | `oklch(0.32 0.12 28)` | Accent text |
| `--cue-slate` | `oklch(0.45 0.06 240)` | Chart bars (non-highlight) |
| `--cue-success` | `oklch(0.55 0.16 145)` | Cache badge |
| `--cue-success-soft` | `oklch(0.85 0.08 145 / 0.30)` | Cache badge bg |
| `--cue-success-ink` | `oklch(0.36 0.10 145)` | Cache badge text |
| `--cue-warn` | `oklch(0.60 0.17 50)` | Error card border |
| `--cue-warn-soft` | `oklch(0.60 0.17 50 / 0.15)` | Error card bg |
| `--cue-danger` | `oklch(0.62 0.18 30)` | Refusal card border |
| `--cue-danger-soft` | `oklch(0.62 0.18 30 / 0.15)` | Refusal card bg |

Fonts: `--cue-serif` = Newsreader · `--cue-sans` = IBM Plex Sans · `--cue-mono` = IBM Plex Mono

---

## API Contract

Backend (already built): `POST http://localhost:8000/api/query`

Request:
```json
{
  "question": "When does TV work best for FMCG brands?",
  "sector": "FMCG",
  "brand_stage": "scale-up",
  "tv_history": "never",
  "primary_goal": "brand",
  "budget_tier": "100k-500k"
}
```

Response:
```json
{
  "answer": "Based on Thinkbox research...",
  "sources": [{ "title": "Profit Ability 2", "chunk": "TV delivered...", "url": "https://..." }],
  "cached": false,
  "model_used": "gpt-4o"
}
```

Error responses: `400` = refusal (input guardrail), `503` = model unavailable.

---

## Valid Enum Values

From `backend/app/core/config.py` — these must match exactly in frontend forms:

```
sector:       FMCG | Retail | Finance | Auto | Telco | Travel | DTC | Other
brand_stage:  start-up | scale-up | established | large
tv_history:   never | tried | regular
primary_goal: sales | brand | both | unsure
budget_tier:  under-100k | 100k-500k | 500k-2m | 2m-plus | undecided
```

---

## Task 1: Testing Infrastructure + Project Config

**Files:**
- Create: `frontend/jest.config.ts`
- Create: `frontend/jest.setup.ts`
- Create: `frontend/__tests__/smoke.test.ts`
- Modify: `frontend/package.json` (add test deps + scripts)
- Modify: `frontend/next.config.ts` (add `output: 'export'`, env var for API URL)

- [ ] **Step 1: Install test dependencies**

```bash
cd frontend
npm install --save-dev jest@^29.7.0 jest-environment-jsdom@^29.7.0 ts-jest@^29.2.0 \
  @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.4.0 \
  @testing-library/user-event@^14.5.0 identity-obj-proxy@^3.0.0 \
  @types/jest@^29.5.0
```

- [ ] **Step 2: Add test script to package.json**

In `frontend/package.json`, add to `"scripts"`:
```json
"test": "jest",
"test:watch": "jest --watch"
```

- [ ] **Step 3: Write jest.config.ts**

```typescript
// frontend/jest.config.ts
import type { Config } from 'jest'

const config: Config = {
  testEnvironment: 'jsdom',
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx',
        esModuleInterop: true,
      },
    }],
  },
  testMatch: ['**/__tests__/**/*.test.(ts|tsx)'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
}

export default config
```

- [ ] **Step 4: Write jest.setup.ts**

```typescript
// frontend/jest.setup.ts
import '@testing-library/jest-dom'
```

- [ ] **Step 5: Write smoke test**

```typescript
// frontend/__tests__/smoke.test.ts
test('jest is configured', () => {
  expect(true).toBe(true)
})
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd frontend && npx jest --testPathPattern smoke
```

Expected: `1 passed`

- [ ] **Step 7: Update next.config.ts**

```typescript
// frontend/next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
}

export default nextConfig
```

- [ ] **Step 8: Create .env.local for development API URL**

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 9: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add jest + RTL testing infrastructure and next.config"
```

---

## Task 2: Design Tokens + Google Fonts

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/__tests__/layout/tokens.test.ts
// Verify font variable names are wired — checked in layout render
import { render } from '@testing-library/react'

test('layout renders children', () => {
  // Simple render check — font CSS vars are applied via globals.css
  const { container } = render(<div className="test">hello</div>)
  expect(container.textContent).toBe('hello')
})
```

Run: `npx jest tokens` — Expected: PASS (trivial test, validates RTL works for layout tests)

- [ ] **Step 2: Replace globals.css with Cue design tokens**

```css
/* frontend/app/globals.css */
@import "tailwindcss";

/* ── Cue Design Tokens ───────────────────────────────────────────────── */
:root {
  --cue-paper:        oklch(0.975 0.008 75);
  --cue-paper-2:      oklch(0.955 0.010 75);
  --cue-paper-3:      oklch(0.930 0.012 75);

  --cue-ink:          oklch(0.20  0.012 60);
  --cue-ink-2:        oklch(0.35  0.012 60);
  --cue-ink-3:        oklch(0.55  0.012 60);
  --cue-ink-4:        oklch(0.72  0.010 60);

  --cue-rule:         oklch(0.85  0.012 70);
  --cue-rule-2:       oklch(0.92  0.010 70);

  --cue-accent:       oklch(0.55  0.16  28);
  --cue-accent-soft:  oklch(0.55  0.16  28 / 0.10);
  --cue-accent-ink:   oklch(0.32  0.12  28);

  --cue-slate:        oklch(0.45  0.06 240);

  --cue-success:      oklch(0.55 0.16 145);
  --cue-success-soft: oklch(0.85 0.08 145 / 0.30);
  --cue-success-ink:  oklch(0.36 0.10 145);

  --cue-warn:         oklch(0.60 0.17 50);
  --cue-warn-soft:    oklch(0.60 0.17 50 / 0.15);
  --cue-warn-ink:     oklch(0.42 0.14 50);

  --cue-danger:       oklch(0.62 0.18 30);
  --cue-danger-soft:  oklch(0.62 0.18 30 / 0.15);
  --cue-danger-ink:   oklch(0.46 0.14 30);

  --cue-serif: "Newsreader", "Source Serif 4", Georgia, serif;
  --cue-sans:  "IBM Plex Sans", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --cue-mono:  "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}

@theme inline {
  --font-serif: var(--cue-serif);
  --font-sans:  var(--cue-sans);
  --font-mono:  var(--cue-mono);
}

html, body {
  height: 100%;
  background: var(--cue-paper);
  color: var(--cue-ink);
  font-family: var(--cue-sans);
  -webkit-font-smoothing: antialiased;
}

/* ── Print styles for Export modal ───────────────────────────────────── */
@media print {
  body > *:not(.cue-export-sheet) { display: none !important; }
  .cue-export-sheet { display: block !important; box-shadow: none !important; }
}
```

- [ ] **Step 3: Update layout.tsx with Google Fonts**

```typescript
// frontend/app/layout.tsx
import type { Metadata } from 'next'
import { Newsreader, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google'
import './globals.css'

const newsreader = Newsreader({
  subsets: ['latin'],
  variable: '--font-newsreader',
  display: 'swap',
})

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-ibm-plex-sans',
  display: 'swap',
})

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-ibm-plex-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Cue — TV Investment Advisor',
  description: 'Evidence-backed TV advertising advice, grounded in Thinkbox research.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${newsreader.variable} ${ibmPlexSans.variable} ${ibmPlexMono.variable} h-full`}
    >
      <body className="h-full antialiased">{children}</body>
    </html>
  )
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Cue design tokens and Google Fonts to globals"
```

---

## Task 3: Types + API Client

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/__tests__/lib/api.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/__tests__/lib/api.test.ts
import { queryApi } from '@/lib/api'

const mockFetch = jest.fn()
global.fetch = mockFetch

beforeEach(() => mockFetch.mockReset())

test('queryApi maps flat response to Answer shape', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      answer: 'TV delivers £5.61 ROI.\n\nSecond paragraph.',
      sources: [{ title: 'Profit Ability 2', chunk: 'TV delivered...', url: 'https://thinkbox.tv' }],
      cached: false,
      model_used: 'gpt-4o',
    }),
  })

  const result = await queryApi({
    question: 'When does TV work?',
    brief: { sector: 'FMCG', brandStage: 'scale-up', tvHistory: 'tried', primaryGoal: 'brand', budgetTier: '500k-2m' },
  })

  expect(result.kind).toBe('answer')
  if (result.kind !== 'answer') return
  expect(result.answer.summary).toHaveLength(2)
  expect(result.answer.summary[0]).toBe('TV delivers £5.61 ROI.')
  expect(result.answer.sources).toHaveLength(1)
  expect(result.answer.sources[0].title).toBe('Profit Ability 2')
  expect(result.answer.meta.model).toBe('gpt-4o')
  expect(result.answer.meta.cached).toBe(false)
})

test('queryApi returns refusal on 400', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'Query is outside the scope of this tool.' }),
  })

  const result = await queryApi({ question: 'Write me a poem', brief: null })
  expect(result.kind).toBe('refusal')
})

test('queryApi returns error on 503', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 503,
    json: async () => ({ detail: 'The answer service is temporarily unavailable.' }),
  })

  const result = await queryApi({ question: 'Does TV work?', brief: null })
  expect(result.kind).toBe('error')
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx jest api.test
```

Expected: FAIL — `Cannot find module '@/lib/api'`

- [ ] **Step 3: Create lib/types.ts**

```typescript
// frontend/lib/types.ts

export type Brief = {
  sector: 'FMCG' | 'Retail' | 'Finance' | 'Auto' | 'Telco' | 'Travel' | 'DTC' | 'Other'
  brandStage: 'start-up' | 'scale-up' | 'established' | 'large'
  tvHistory: 'never' | 'tried' | 'regular'
  primaryGoal: 'sales' | 'brand' | 'both' | 'unsure'
  budgetTier: 'under-100k' | '100k-500k' | '500k-2m' | '2m-plus' | 'undecided'
}

export type Source = {
  n: number
  title: string
  year: number
  page: number
  url: string
  quote: string
  topic: string
  score?: number
}

export type Headline = { stat: string; unit: string; caption: string }
export type Callout  = { label: string; body: string }
export type ChartBar = { label: string; value: number; highlight?: boolean }
export type Chart    = { title: string; source: string; unit: string; bars: ChartBar[] }

export type Answer = {
  headline:  Headline | null
  summary:   string[]
  callout:   Callout | null
  chart:     Chart | null
  sources:   Source[]
  followups: string[]
  meta: {
    model:        string
    cached:       boolean
    retrievalMs:  number
    generationMs: number
    chunksUsed:   number
  }
}

export type Turn =
  | { role: 'user';      question: string; brief: Brief | null; time: string }
  | { role: 'assistant'; answer: Answer;   time: string }
  | { role: 'refusal';   message: string;  examples: string[]; time: string }
  | { role: 'error';     title: string;    message: string; reference: string; retryable: boolean; time: string }

export type Thread = {
  id:    string
  title: string
  turns: Turn[]
  brief: Brief
}

export type Phase = 'idle' | 'thinking' | 'streaming' | 'answered'

export type QueryResult =
  | { kind: 'answer';  answer: Answer }
  | { kind: 'refusal'; message: string; examples: string[] }
  | { kind: 'error';   title: string;   message: string; reference: string }
```

- [ ] **Step 4: Create lib/api.ts**

```typescript
// frontend/lib/api.ts
import type { Brief, QueryResult } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

type RawSource = { title: string; chunk: string; url: string }
type RawResponse = { answer: string; sources: RawSource[]; cached: boolean; model_used: string }

function mapResponse(raw: RawResponse, generationMs: number): QueryResult {
  const summary = raw.answer
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean)

  return {
    kind: 'answer',
    answer: {
      headline:  null,
      summary,
      callout:   null,
      chart:     null,
      followups: [],
      sources: raw.sources.map((s, i) => ({
        n:     i + 1,
        title: s.title,
        year:  0,
        page:  0,
        url:   s.url,
        quote: s.chunk,
        topic: '',
      })),
      meta: {
        model:        raw.model_used,
        cached:       raw.cached,
        retrievalMs:  0,
        generationMs,
        chunksUsed:   raw.sources.length,
      },
    },
  }
}

function makeReference(): string {
  return 'cue-err-' + Math.random().toString(36).slice(2, 8)
}

export async function queryApi({
  question,
  brief,
}: {
  question: string
  brief: Brief | null
}): Promise<QueryResult> {
  const t0 = Date.now()

  const body: Record<string, string> = { question }
  if (brief) {
    if (brief.sector)     body.sector      = brief.sector
    if (brief.brandStage) body.brand_stage = brief.brandStage
    if (brief.tvHistory)  body.tv_history  = brief.tvHistory
    if (brief.primaryGoal) body.primary_goal = brief.primaryGoal
    if (brief.budgetTier)  body.budget_tier  = brief.budgetTier
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    return {
      kind: 'error',
      title: "We couldn't ground this one",
      message: "Cue couldn't reach the language model just now. Please try again in a moment.",
      reference: makeReference(),
    }
  }

  if (res.status === 400) {
    return {
      kind: 'refusal',
      message:
        'Cue only answers questions about TV advertising investment, grounded in published Thinkbox research.',
      examples: [
        'Is TV a good investment for a DTC brand with a £500k budget?',
        "What's the long-term ROI of TV vs paid social?",
        'When should I peak my burst around Christmas?',
      ],
    }
  }

  if (!res.ok) {
    return {
      kind: 'error',
      title: "We couldn't ground this one",
      message: "Cue couldn't reach the language model just now. We won't return an ungrounded answer — please try again in a moment.",
      reference: makeReference(),
    }
  }

  const raw = (await res.json()) as RawResponse
  return mapResponse(raw, Date.now() - t0)
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest api.test
```

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add type definitions and API client with response mapping"
```

---

## Task 4: Zustand Store

**Files:**
- Create: `frontend/lib/store.ts`
- Create: `frontend/__tests__/lib/store.test.ts`

- [ ] **Step 1: Install Zustand**

```bash
cd frontend && npm install zustand@^5.0.0
```

- [ ] **Step 2: Write the failing tests**

```typescript
// frontend/__tests__/lib/store.test.ts
import { act } from '@testing-library/react'
import { useStore } from '@/lib/store'

// Reset store between tests
beforeEach(() => {
  useStore.setState(useStore.getInitialState())
})

test('initial phase is idle', () => {
  expect(useStore.getState().phase).toBe('idle')
})

test('setBrief updates brief fields', () => {
  act(() => {
    useStore.getState().setBrief({ sector: 'Retail' })
  })
  expect(useStore.getState().thread.brief.sector).toBe('Retail')
})

test('setComposerInput updates composerInput', () => {
  act(() => {
    useStore.getState().setComposerInput('Does TV work?')
  })
  expect(useStore.getState().composerInput).toBe('Does TV work?')
})

test('newThread resets turns and composerInput', () => {
  act(() => {
    useStore.getState().setComposerInput('question')
    useStore.getState().newThread()
  })
  expect(useStore.getState().composerInput).toBe('')
  expect(useStore.getState().thread.turns).toHaveLength(0)
})

test('toggleRail flips railCollapsed', () => {
  expect(useStore.getState().railCollapsed).toBe(false)
  act(() => useStore.getState().toggleRail())
  expect(useStore.getState().railCollapsed).toBe(true)
})

test('setHistoryOpen controls historyOpen flag', () => {
  act(() => useStore.getState().setHistoryOpen(true))
  expect(useStore.getState().historyOpen).toBe(true)
})
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd frontend && npx jest store.test
```

Expected: FAIL — `Cannot find module '@/lib/store'`

- [ ] **Step 4: Create lib/store.ts**

```typescript
// frontend/lib/store.ts
'use client'

import { create } from 'zustand'
import type { Brief, Thread, Phase, Turn } from './types'
import { queryApi } from './api'

const DEFAULT_BRIEF: Brief = {
  sector:      'FMCG',
  brandStage:  'scale-up',
  tvHistory:   'tried',
  primaryGoal: 'brand',
  budgetTier:  '500k-2m',
}

function newThread(): Thread {
  return {
    id:    crypto.randomUUID(),
    title: 'New thread',
    turns: [],
    brief: { ...DEFAULT_BRIEF },
  }
}

type AppStore = {
  thread:         Thread
  threads:        Thread[]
  phase:          Phase
  composerInput:  string
  railCollapsed:  boolean
  historyOpen:    boolean
  exportOpen:     boolean
  activeCitation: number | null
  activeSource:   number | null

  ask():                        Promise<void>
  setBrief(patch: Partial<Brief>): void
  setComposerInput(v: string):  void
  retry():                      Promise<void>
  newThread():                  void
  openThread(id: string):       void
  toggleRail():                 void
  setHistoryOpen(open: boolean): void
  setExportOpen(open: boolean):  void
  setActiveCitation(n: number | null): void
  setActiveSource(n: number | null):   void
}

export const useStore = create<AppStore>((set, get) => ({
  thread:         newThread(),
  threads:        [],
  phase:          'idle',
  composerInput:  '',
  railCollapsed:  false,
  historyOpen:    false,
  exportOpen:     false,
  activeCitation: null,
  activeSource:   null,

  setBrief(patch) {
    set((s) => ({
      thread: { ...s.thread, brief: { ...s.thread.brief, ...patch } },
    }))
  },

  setComposerInput(v) {
    set({ composerInput: v })
  },

  async ask() {
    const { composerInput, thread } = get()
    const question = composerInput.trim()
    if (!question || get().phase !== 'idle') return

    const userTurn: Turn = {
      role:     'user',
      question,
      brief:    { ...thread.brief },
      time:     new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    set((s) => ({
      composerInput: '',
      phase:         'thinking',
      thread: { ...s.thread, turns: [...s.thread.turns, userTurn] },
    }))

    // Simulate brief "thinking" delay then streaming
    await new Promise((r) => setTimeout(r, 400))
    set({ phase: 'streaming' })

    const result = await queryApi({ question, brief: thread.brief })
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    let assistantTurn: Turn
    if (result.kind === 'answer') {
      assistantTurn = { role: 'assistant', answer: result.answer, time }
    } else if (result.kind === 'refusal') {
      assistantTurn = { role: 'refusal', message: result.message, examples: result.examples, time }
    } else {
      assistantTurn = {
        role: 'error',
        title:     result.title,
        message:   result.message,
        reference: result.reference,
        retryable: true,
        time,
      }
    }

    set((s) => ({
      phase:  'answered',
      thread: { ...s.thread, turns: [...s.thread.turns, assistantTurn] },
    }))

    // Return to idle after a tick so streaming animation completes
    setTimeout(() => set({ phase: 'idle' }), 100)
  },

  async retry() {
    const { thread } = get()
    const lastUserTurn = [...thread.turns].reverse().find((t) => t.role === 'user')
    if (!lastUserTurn || lastUserTurn.role !== 'user') return
    set({ composerInput: lastUserTurn.question })
    await get().ask()
  },

  newThread() {
    set((s) => {
      const current = s.thread
      const exists = s.threads.find((t) => t.id === current.id)
      return {
        thread:        newThread(),
        composerInput: '',
        phase:         'idle',
        threads:       exists ? s.threads : [current, ...s.threads],
      }
    })
  },

  openThread(id) {
    set((s) => {
      const found = s.threads.find((t) => t.id === id)
      if (!found) return s
      return { thread: found, historyOpen: false, phase: 'idle' }
    })
  },

  toggleRail() {
    set((s) => ({ railCollapsed: !s.railCollapsed }))
  },

  setHistoryOpen(open) { set({ historyOpen: open }) },
  setExportOpen(open)  { set({ exportOpen: open }) },
  setActiveCitation(n) { set({ activeCitation: n }) },
  setActiveSource(n)   { set({ activeSource: n }) },
}))

// Expose initial state for test resets
;(useStore as any).getInitialState = () => ({
  thread:         newThread(),
  threads:        [],
  phase:          'idle' as Phase,
  composerInput:  '',
  railCollapsed:  false,
  historyOpen:    false,
  exportOpen:     false,
  activeCitation: null,
  activeSource:   null,
})
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest store.test
```

Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Zustand store with phase transitions and brief management"
```

---

## Task 5: Headline Atom

**Files:**
- Create: `frontend/components/atoms/Headline.tsx`
- Create: `frontend/__tests__/atoms/Headline.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/__tests__/atoms/Headline.test.tsx
import { render, screen } from '@testing-library/react'
import { Headline } from '@/components/atoms/Headline'

test('renders stat, unit, and caption', () => {
  render(<Headline stat="£5.61" unit="ROI per £1 spent" caption="Profit Ability 2 (2024)" />)
  expect(screen.getByText('£5.61')).toBeInTheDocument()
  expect(screen.getByText('ROI per £1 spent')).toBeInTheDocument()
  expect(screen.getByText('Profit Ability 2 (2024)')).toBeInTheDocument()
})

test('dense prop applies smaller size class', () => {
  const { container } = render(
    <Headline stat="70/30" unit="linear / BVOD" caption="Source" dense />
  )
  expect(container.firstChild).toHaveClass('cue-headline--dense')
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx jest Headline.test
```

Expected: FAIL — `Cannot find module '@/components/atoms/Headline'`

- [ ] **Step 3: Implement Headline.tsx**

```typescript
// frontend/components/atoms/Headline.tsx
'use client'

type Props = {
  stat:    string
  unit:    string
  caption: string
  dense?:  boolean
}

export function Headline({ stat, unit, caption, dense = false }: Props) {
  return (
    <div
      className={`cue-headline flex items-start gap-4 rounded-r-md px-4 py-3 ${dense ? 'cue-headline--dense' : ''}`}
      style={{
        background:   'linear-gradient(to right, var(--cue-accent-soft), transparent)',
        borderLeft:   '3px solid var(--cue-accent)',
        borderRadius: '0 6px 6px 0',
      }}
    >
      <span
        style={{
          fontFamily: 'var(--cue-serif)',
          fontSize:   dense ? '40px' : '56px',
          lineHeight: 1,
          color:      'var(--cue-accent)',
          fontWeight: 500,
        }}
      >
        {stat}
      </span>
      <div className="flex flex-col justify-center pt-1">
        <span
          style={{
            fontFamily:  'var(--cue-sans)',
            fontSize:    '14px',
            fontWeight:  500,
            color:       'var(--cue-ink-2)',
            lineHeight:  1.2,
          }}
        >
          {unit}
        </span>
        <span
          style={{
            fontFamily:    'var(--cue-mono)',
            fontSize:      '10.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color:         'var(--cue-ink-3)',
            marginTop:     '4px',
          }}
        >
          {caption}
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest Headline.test
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Headline atom with stat/unit/caption and dense variant"
```

---

## Task 6: Citation + ProseWithCites Atoms

**Files:**
- Create: `frontend/components/atoms/Citation.tsx`
- Create: `frontend/components/atoms/ProseWithCites.tsx`
- Create: `frontend/__tests__/atoms/Citation.test.tsx`
- Create: `frontend/__tests__/atoms/ProseWithCites.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/atoms/Citation.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Citation } from '@/components/atoms/Citation'

test('renders citation number', () => {
  render(<Citation n={3} />)
  expect(screen.getByText('3')).toBeInTheDocument()
})

test('calls onClick when clicked', async () => {
  const onClick = jest.fn()
  render(<Citation n={1} onClick={onClick} />)
  await userEvent.click(screen.getByText('1'))
  expect(onClick).toHaveBeenCalledWith(1)
})
```

```typescript
// frontend/__tests__/atoms/ProseWithCites.test.tsx
import { render, screen } from '@testing-library/react'
import { ProseWithCites } from '@/components/atoms/ProseWithCites'

test('renders plain text without markers', () => {
  render(<ProseWithCites text="TV advertising is effective." onCiteClick={jest.fn()} />)
  expect(screen.getByText(/TV advertising is effective/)).toBeInTheDocument()
})

test('splits [N] markers into Citation components', () => {
  render(<ProseWithCites text="TV delivers ROI [1] and reach [2]." onCiteClick={jest.fn()} />)
  expect(screen.getByText('1')).toBeInTheDocument()
  expect(screen.getByText('2')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest Citation.test ProseWithCites.test
```

Expected: FAIL

- [ ] **Step 3: Implement Citation.tsx**

```typescript
// frontend/components/atoms/Citation.tsx
'use client'

type Props = {
  n:        number
  onClick?: (n: number) => void
  onHover?: (n: number) => void
  onLeave?: () => void
}

export function Citation({ n, onClick, onHover, onLeave }: Props) {
  return (
    <sup
      role="button"
      tabIndex={0}
      onClick={() => onClick?.(n)}
      onMouseEnter={() => onHover?.(n)}
      onMouseLeave={() => onLeave?.()}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.(n)}
      style={{
        display:         'inline-flex',
        alignItems:      'center',
        justifyContent:  'center',
        minWidth:        '16px',
        height:          '16px',
        padding:         '0 4px',
        borderRadius:    '4px',
        background:      'var(--cue-accent-soft)',
        color:           'var(--cue-accent-ink)',
        fontFamily:      'var(--cue-mono)',
        fontSize:        '10px',
        fontWeight:      500,
        cursor:          'pointer',
        verticalAlign:   'super',
        lineHeight:      1,
        transition:      'background 120ms, color 120ms',
        userSelect:      'none',
      }}
    >
      {n}
    </sup>
  )
}
```

- [ ] **Step 4: Implement ProseWithCites.tsx**

```typescript
// frontend/components/atoms/ProseWithCites.tsx
'use client'

import { Citation } from './Citation'

type Props = {
  text:          string
  onCiteClick?:  (n: number) => void
  onCiteHover?:  (n: number) => void
  onCiteLeave?:  () => void
}

export function ProseWithCites({ text, onCiteClick, onCiteHover, onCiteLeave }: Props) {
  // Split on [N] markers; odd indices are the numbers
  const parts = text.split(/\[(\d+)\]/)

  return (
    <span>
      {parts.map((part, i) => {
        if (i % 2 === 1) {
          const n = parseInt(part, 10)
          return (
            <Citation
              key={i}
              n={n}
              onClick={onCiteClick}
              onHover={onCiteHover}
              onLeave={onCiteLeave}
            />
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest Citation.test ProseWithCites.test
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Citation and ProseWithCites atoms"
```

---

## Task 7: Callout + CacheBadge Atoms

**Files:**
- Create: `frontend/components/atoms/Callout.tsx`
- Create: `frontend/components/atoms/CacheBadge.tsx`
- Create: `frontend/__tests__/atoms/Callout.test.tsx`
- Create: `frontend/__tests__/atoms/CacheBadge.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/atoms/Callout.test.tsx
import { render, screen } from '@testing-library/react'
import { Callout } from '@/components/atoms/Callout'

test('renders label and body', () => {
  render(<Callout label="What this means for you" body="Concentrate 60–70% of TV spend..." />)
  expect(screen.getByText('What this means for you')).toBeInTheDocument()
  expect(screen.getByText(/Concentrate 60/)).toBeInTheDocument()
})
```

```typescript
// frontend/__tests__/atoms/CacheBadge.test.tsx
import { render, screen } from '@testing-library/react'
import { CacheBadge } from '@/components/atoms/CacheBadge'

test('renders cached text', () => {
  render(<CacheBadge />)
  expect(screen.getByText('cached')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify they fail, then implement**

```bash
cd frontend && npx jest Callout.test CacheBadge.test
```

Expected: FAIL

- [ ] **Step 3: Implement Callout.tsx**

```typescript
// frontend/components/atoms/Callout.tsx
'use client'

type Props = { label: string; body: string }

export function Callout({ label, body }: Props) {
  return (
    <div
      style={{
        background:   'var(--cue-paper-2)',
        border:       '1px solid var(--cue-rule)',
        borderLeft:   '3px solid var(--cue-accent)',
        borderRadius: '6px',
        padding:      '16px 18px',
      }}
    >
      <div
        style={{
          fontFamily:    'var(--cue-mono)',
          fontSize:      '10.5px',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color:         'var(--cue-accent-ink)',
          marginBottom:  '8px',
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'var(--cue-serif)',
          fontSize:   '16px',
          lineHeight: 1.55,
          color:      'var(--cue-ink-2)',
        }}
      >
        {body}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Implement CacheBadge.tsx**

```typescript
// frontend/components/atoms/CacheBadge.tsx
'use client'

export function CacheBadge() {
  return (
    <span
      title="Returned from cache — identical brief + question answered within the last 7 days."
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        gap:            '4px',
        padding:        '2px 8px',
        borderRadius:   '999px',
        background:     'var(--cue-success-soft)',
        color:          'var(--cue-success-ink)',
        fontFamily:     'var(--cue-mono)',
        fontSize:       '10px',
        textTransform:  'uppercase',
        letterSpacing:  '0.06em',
      }}
    >
      <span
        style={{
          width:        '6px',
          height:       '6px',
          borderRadius: '50%',
          background:   'var(--cue-success)',
          display:      'inline-block',
        }}
      />
      cached
    </span>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest Callout.test CacheBadge.test
```

Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Callout and CacheBadge atoms"
```

---

## Task 8: SourceCard + Followups Atoms

**Files:**
- Create: `frontend/components/atoms/SourceCard.tsx`
- Create: `frontend/components/atoms/Followups.tsx`
- Create: `frontend/__tests__/atoms/SourceCard.test.tsx`
- Create: `frontend/__tests__/atoms/Followups.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/atoms/SourceCard.test.tsx
import { render, screen } from '@testing-library/react'
import { SourceCard } from '@/components/atoms/SourceCard'
import type { Source } from '@/lib/types'

const src: Source = {
  n: 1, title: 'Profit Ability 2', year: 2024, page: 14,
  url: 'https://thinkbox.tv/research/profit-ability-2',
  quote: 'TV delivered £5.61 ROI.', topic: 'ROI',
}

test('renders title and quote', () => {
  render(<SourceCard source={src} />)
  expect(screen.getByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText(/TV delivered £5.61/)).toBeInTheDocument()
})

test('highlight prop adds accent border class', () => {
  const { container } = render(<SourceCard source={src} highlight />)
  expect(container.firstChild).toHaveClass('cue-source--highlight')
})
```

```typescript
// frontend/__tests__/atoms/Followups.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Followups } from '@/components/atoms/Followups'

test('renders all followup items', () => {
  render(<Followups items={['Question A', 'Question B']} onPick={jest.fn()} />)
  expect(screen.getByText('Question A')).toBeInTheDocument()
  expect(screen.getByText('Question B')).toBeInTheDocument()
})

test('calls onPick with question text on click', async () => {
  const onPick = jest.fn()
  render(<Followups items={['Question A']} onPick={onPick} />)
  await userEvent.click(screen.getByText('Question A'))
  expect(onPick).toHaveBeenCalledWith('Question A')
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npx jest SourceCard.test Followups.test
```

Expected: FAIL

- [ ] **Step 3: Implement SourceCard.tsx**

```typescript
// frontend/components/atoms/SourceCard.tsx
'use client'

import type { Source } from '@/lib/types'

type Props = {
  source:     Source
  highlight?: boolean
  compact?:   boolean
}

export function SourceCard({ source, highlight = false, compact = false }: Props) {
  const thumbW = compact ? 48 : 64

  return (
    <div
      className={`cue-source ${highlight ? 'cue-source--highlight' : ''}`}
      style={{
        display:      'flex',
        gap:          '12px',
        padding:      '12px',
        border:       `1px solid ${highlight ? 'var(--cue-accent)' : 'var(--cue-rule)'}`,
        borderRadius: '6px',
        background:   highlight ? 'var(--cue-accent-soft)' : 'transparent',
        transition:   'border-color 120ms, background 120ms',
      }}
    >
      {/* Thumbnail — striped bars */}
      <div
        aria-hidden="true"
        style={{
          width:         `${thumbW}px`,
          minWidth:      `${thumbW}px`,
          height:        '48px',
          background:    'var(--cue-paper-3)',
          borderRadius:  '4px',
          display:       'flex',
          flexDirection: 'column',
          justifyContent:'flex-end',
          padding:       '6px 6px 4px',
          gap:           '3px',
        }}
      >
        {[70, 50, 85, 40].map((w, i) => (
          <div
            key={i}
            style={{
              height:       '3px',
              width:        `${w}%`,
              borderRadius: '2px',
              background:   i === 0 ? 'var(--cue-accent)' : 'var(--cue-ink-4)',
            }}
          />
        ))}
      </div>

      {/* Body */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '4px' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-accent-ink)', fontWeight: 500 }}>
            [{source.n}]
          </span>
          <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '13.5px', fontWeight: 500, color: 'var(--cue-ink)', lineHeight: 1.25 }}>
            {source.title}
          </span>
        </div>
        {(source.year > 0 || source.page > 0) && (
          <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', color: 'var(--cue-ink-3)', marginBottom: '4px' }}>
            {source.year > 0 && `${source.year}`}{source.page > 0 && ` · p.${source.page}`}
          </div>
        )}
        <div style={{ fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '12.5px', color: 'var(--cue-ink-2)', lineHeight: 1.45, marginBottom: '6px' }}>
          "{source.quote}"
        </div>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textDecoration: 'none', wordBreak: 'break-all' }}
        >
          {source.url}
        </a>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Implement Followups.tsx**

```typescript
// frontend/components/atoms/Followups.tsx
'use client'

type Props = {
  items:  string[]
  onPick: (q: string) => void
}

export function Followups({ items, onPick }: Props) {
  if (items.length === 0) return null

  return (
    <div style={{ marginTop: '16px' }}>
      <div
        style={{
          fontFamily:    'var(--cue-mono)',
          fontSize:      '10.5px',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color:         'var(--cue-ink-3)',
          marginBottom:  '8px',
        }}
      >
        Follow-ups
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {items.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            style={{
              display:     'flex',
              alignItems:  'center',
              gap:         '8px',
              textAlign:   'left',
              padding:     '9px 11px',
              border:      '1px solid var(--cue-rule)',
              borderRadius:'6px',
              background:  'transparent',
              cursor:      'pointer',
              fontFamily:  'var(--cue-serif)',
              fontSize:    '13.5px',
              color:       'var(--cue-ink-2)',
              lineHeight:  1.35,
              transition:  'border-color 120ms, color 120ms',
            }}
          >
            <span style={{ color: 'var(--cue-accent)', fontFamily: 'var(--cue-mono)' }}>↳</span>
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest SourceCard.test Followups.test
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add SourceCard and Followups atoms"
```

---

*Plan continues in Part 2 (Tasks 9–16: Chart, Trace, Chip, Composer, thread bubbles)*

---

## Task 9: Chart Atom

**Files:**
- Create: `frontend/components/atoms/Chart.tsx`
- Create: `frontend/__tests__/atoms/Chart.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/atoms/Chart.test.tsx
import { render, screen } from '@testing-library/react'
import { Chart } from '@/components/atoms/Chart'
import type { Chart as ChartType } from '@/lib/types'

const chart: ChartType = {
  title: 'Profit per £1 spent, by channel',
  source: 'Profit Ability 2 (2024)',
  unit: '£',
  bars: [
    { label: 'Linear TV', value: 5.61, highlight: true },
    { label: 'BVOD',      value: 4.66 },
    { label: 'Print',     value: 1.39 },
  ],
}

test('renders title and all bar labels', () => {
  render(<Chart chart={chart} />)
  expect(screen.getByText('Profit per £1 spent, by channel')).toBeInTheDocument()
  expect(screen.getByText('Linear TV')).toBeInTheDocument()
  expect(screen.getByText('BVOD')).toBeInTheDocument()
  expect(screen.getByText('Print')).toBeInTheDocument()
})

test('renders bar values', () => {
  render(<Chart chart={chart} />)
  expect(screen.getByText('5.61')).toBeInTheDocument()
  expect(screen.getByText('4.66')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd frontend && npx jest Chart.test
```

Expected: FAIL

- [ ] **Step 3: Implement Chart.tsx**

```typescript
// frontend/components/atoms/Chart.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import type { Chart as ChartType } from '@/lib/types'

type Props = { chart: ChartType; dense?: boolean }

export function Chart({ chart, dense = false }: Props) {
  const maxValue = Math.max(...chart.bars.map((b) => b.value))
  const [mounted, setMounted] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Animate on mount
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  return (
    <figure
      ref={ref}
      style={{
        margin:       0,
        border:       '1px solid var(--cue-rule)',
        borderRadius: '6px',
        overflow:     'hidden',
      }}
    >
      {/* Caption row */}
      <div
        style={{
          display:        'flex',
          justifyContent: 'space-between',
          alignItems:     'center',
          padding:        '10px 14px 8px',
          borderBottom:   '1px solid var(--cue-rule-2)',
        }}
      >
        <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '14px', color: 'var(--cue-ink-2)' }}>
          {chart.title}
        </span>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {chart.source}
        </span>
      </div>

      {/* Bars */}
      <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {chart.bars.map((bar) => {
          const pct = (bar.value / maxValue) * 100
          return (
            <div
              key={bar.label}
              style={{ display: 'grid', gridTemplateColumns: '95px 1fr 52px', alignItems: 'center', gap: '10px' }}
            >
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', color: 'var(--cue-ink-3)', textAlign: 'right', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {bar.label}
              </span>
              {/* Track */}
              <div style={{ height: '14px', borderRadius: '3px', background: 'var(--cue-paper-3)', overflow: 'hidden' }}>
                <div
                  style={{
                    height:           '100%',
                    borderRadius:     '3px',
                    background:       bar.highlight ? 'var(--cue-accent)' : 'var(--cue-slate)',
                    width:            mounted ? `${pct}%` : '0%',
                    transition:       'width 700ms cubic-bezier(0.4, 0, 0.2, 1)',
                  }}
                />
              </div>
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', color: bar.highlight ? 'var(--cue-accent-ink)' : 'var(--cue-ink-3)', fontWeight: bar.highlight ? 500 : 400 }}>
                {bar.value}
              </span>
            </div>
          )
        })}
      </div>
    </figure>
  )
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest Chart.test
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Chart atom with animated bar fill"
```

---

## Task 10: Trace Atom

**Files:**
- Create: `frontend/components/atoms/Trace.tsx`
- Create: `frontend/__tests__/atoms/Trace.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/atoms/Trace.test.tsx
import { render, screen } from '@testing-library/react'
import { Trace } from '@/components/atoms/Trace'

const steps = [
  'Parsing brief — sector: FMCG',
  'Filtering corpus by topic: ROI',
  'Retrieving 5 chunks…',
]

test('renders all trace steps', () => {
  render(<Trace steps={steps} />)
  expect(screen.getByText(/Parsing brief/)).toBeInTheDocument()
  expect(screen.getByText(/Filtering corpus/)).toBeInTheDocument()
  expect(screen.getByText(/Retrieving 5 chunks/)).toBeInTheDocument()
})

test('renders correct number of steps', () => {
  const { container } = render(<Trace steps={steps} />)
  const lines = container.querySelectorAll('.cue-trace-line')
  expect(lines).toHaveLength(3)
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd frontend && npx jest Trace.test
```

Expected: FAIL

- [ ] **Step 3: Implement Trace.tsx**

```typescript
// frontend/components/atoms/Trace.tsx
'use client'

import { useEffect, useState } from 'react'

type Props = {
  steps:   string[]
  onDone?: () => void
}

export function Trace({ steps, onDone }: Props) {
  const [visible, setVisible] = useState(0)

  useEffect(() => {
    if (visible >= steps.length) {
      onDone?.()
      return
    }
    const delay = 200 + Math.random() * 180  // 200–380ms per step
    const t = setTimeout(() => setVisible((v) => v + 1), delay)
    return () => clearTimeout(t)
  }, [visible, steps.length, onDone])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {steps.slice(0, visible).map((step, i) => {
        const isLast = i === visible - 1
        return (
          <div
            key={i}
            className="cue-trace-line"
            style={{
              display:        'flex',
              alignItems:     'center',
              gap:            '8px',
              fontFamily:     'var(--cue-mono)',
              fontSize:       '11px',
              color:          isLast ? 'var(--cue-accent)' : 'var(--cue-ink-3)',
              opacity:        1,
              transform:      'translateY(0)',
              animation:      'cue-trace-in 250ms ease-out',
            }}
          >
            {isLast && (
              <span
                style={{
                  width:        '6px',
                  height:       '6px',
                  borderRadius: '50%',
                  background:   'var(--cue-accent)',
                  animation:    'cue-pulse 1s ease-in-out infinite',
                  flexShrink:   0,
                }}
              />
            )}
            {step}
          </div>
        )
      })}
      <style>{`
        @keyframes cue-trace-in {
          from { opacity: 0; transform: translateY(2px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes cue-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest Trace.test
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Trace atom with staggered step animation"
```

---

## Task 11: Chip + Composer

**Files:**
- Create: `frontend/components/composer/Chip.tsx`
- Create: `frontend/components/composer/Composer.tsx`
- Create: `frontend/__tests__/composer/Chip.test.tsx`
- Create: `frontend/__tests__/composer/Composer.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/composer/Chip.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Chip } from '@/components/composer/Chip'

const options = [
  { value: 'FMCG',   label: 'FMCG' },
  { value: 'Retail', label: 'Retail' },
]

test('renders chip key and current value label', () => {
  render(<Chip fieldKey="SECTOR" value="FMCG" options={options} onChange={jest.fn()} />)
  expect(screen.getByText('SECTOR')).toBeInTheDocument()
  expect(screen.getByText('FMCG')).toBeInTheDocument()
})

test('opens popover on click showing all options', async () => {
  render(<Chip fieldKey="SECTOR" value="FMCG" options={options} onChange={jest.fn()} />)
  await userEvent.click(screen.getByRole('button'))
  expect(screen.getByText('Retail')).toBeInTheDocument()
})

test('calls onChange when option selected', async () => {
  const onChange = jest.fn()
  render(<Chip fieldKey="SECTOR" value="FMCG" options={options} onChange={onChange} />)
  await userEvent.click(screen.getByRole('button'))
  await userEvent.click(screen.getByText('Retail'))
  expect(onChange).toHaveBeenCalledWith('Retail')
})
```

```typescript
// frontend/__tests__/composer/Composer.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Composer } from '@/components/composer/Composer'
import type { Brief } from '@/lib/types'

const brief: Brief = {
  sector: 'FMCG', brandStage: 'scale-up',
  tvHistory: 'tried', primaryGoal: 'brand', budgetTier: '500k-2m',
}

test('renders textarea and Send button', () => {
  render(<Composer brief={brief} setBrief={jest.fn()} value="" onChange={jest.fn()} onSubmit={jest.fn()} disabled={false} />)
  expect(screen.getByRole('textbox')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /ask/i })).toBeInTheDocument()
})

test('Send button is disabled when value is empty', () => {
  render(<Composer brief={brief} setBrief={jest.fn()} value="" onChange={jest.fn()} onSubmit={jest.fn()} disabled={false} />)
  expect(screen.getByRole('button', { name: /ask/i })).toBeDisabled()
})

test('calls onSubmit on Enter keydown', async () => {
  const onSubmit = jest.fn()
  render(<Composer brief={brief} setBrief={jest.fn()} value="Does TV work?" onChange={jest.fn()} onSubmit={onSubmit} disabled={false} />)
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', code: 'Enter' })
  expect(onSubmit).toHaveBeenCalled()
})

test('does not submit on Shift+Enter', async () => {
  const onSubmit = jest.fn()
  render(<Composer brief={brief} setBrief={jest.fn()} value="text" onChange={jest.fn()} onSubmit={onSubmit} disabled={false} />)
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', shiftKey: true })
  expect(onSubmit).not.toHaveBeenCalled()
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npx jest Chip.test Composer.test
```

Expected: FAIL

- [ ] **Step 3: Implement Chip.tsx**

```typescript
// frontend/components/composer/Chip.tsx
'use client'

import { useRef, useState } from 'react'

type Option = { value: string; label: string }

type Props = {
  fieldKey: string
  value:    string
  options:  Option[]
  onChange: (v: string) => void
}

export function Chip({ fieldKey, value, options, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const currentLabel = options.find((o) => o.value === value)?.label ?? value

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          display:      'inline-flex',
          alignItems:   'center',
          gap:          '5px',
          padding:      '4px 8px',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '999px',
          background:   'transparent',
          cursor:       'pointer',
          whiteSpace:   'nowrap',
        }}
      >
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--cue-ink-3)' }}>
          {fieldKey}
        </span>
        <span style={{ fontFamily: 'var(--cue-sans)', fontSize: '12px', fontWeight: 500, color: 'var(--cue-ink)' }}>
          {currentLabel}
        </span>
        <span style={{ color: 'var(--cue-ink-3)', fontSize: '10px' }}>▾</span>
      </button>

      {open && (
        <>
          {/* scrim */}
          <div style={{ position: 'fixed', inset: 0, zIndex: 10 }} onClick={() => setOpen(false)} />
          <div
            style={{
              position:  'absolute',
              top:       'calc(100% + 4px)',
              left:      0,
              zIndex:    20,
              background:'var(--cue-paper)',
              border:    '1px solid var(--cue-rule)',
              borderRadius:'8px',
              boxShadow: '0 8px 28px rgb(0 0 0 / 0.18)',
              minWidth:  '160px',
              overflow:  'hidden',
            }}
          >
            {options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => { onChange(opt.value); setOpen(false) }}
                style={{
                  display:        'flex',
                  alignItems:     'center',
                  justifyContent: 'space-between',
                  width:          '100%',
                  padding:        '9px 12px',
                  border:         'none',
                  background:     opt.value === value ? 'var(--cue-accent-soft)' : 'transparent',
                  cursor:         'pointer',
                  fontFamily:     'var(--cue-sans)',
                  fontSize:       '13px',
                  color:          'var(--cue-ink)',
                  textAlign:      'left',
                }}
              >
                {opt.label}
                {opt.value === value && <span style={{ color: 'var(--cue-accent)', fontSize: '12px' }}>✓</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Implement Composer.tsx**

```typescript
// frontend/components/composer/Composer.tsx
'use client'

import type { Brief } from '@/lib/types'
import { Chip } from './Chip'

type Props = {
  brief:     Brief
  setBrief:  (patch: Partial<Brief>) => void
  value:     string
  onChange:  (v: string) => void
  onSubmit:  () => void
  disabled:  boolean
}

const SECTOR_OPTS      = ['FMCG','Retail','Finance','Auto','Telco','Travel','DTC','Other'].map((v) => ({ value: v, label: v }))
const STAGE_OPTS       = [{ value:'start-up', label:'Start-up' }, { value:'scale-up', label:'Scale-up' }, { value:'established', label:'Established' }, { value:'large', label:'Large' }]
const HISTORY_OPTS     = [{ value:'never', label:'Never run TV' }, { value:'tried', label:'Tried once or twice' }, { value:'regular', label:'Regular advertiser' }]
const GOAL_OPTS        = [{ value:'sales', label:'Short-term sales' }, { value:'brand', label:'Brand building' }, { value:'both', label:'Both' }, { value:'unsure', label:'Unsure' }]
const BUDGET_OPTS      = [{ value:'under-100k', label:'Under £100k' }, { value:'100k-500k', label:'£100k–£500k' }, { value:'500k-2m', label:'£500k–£2m' }, { value:'2m-plus', label:'£2m+' }, { value:'undecided', label:'Undecided' }]

export function Composer({ brief, setBrief, value, onChange, onSubmit, disabled }: Props) {
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim()) onSubmit()
    }
  }

  return (
    <div
      style={{
        maxWidth:     '760px',
        margin:       '0 auto',
        borderRadius: '12px',
        border:       '1px solid var(--cue-rule)',
        background:   'var(--cue-paper)',
        boxShadow:    '0 4px 24px -8px rgb(0 0 0 / 0.08)',
        overflow:     'hidden',
      }}
    >
      {/* Brief chips row */}
      <div
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '6px',
          padding:      '10px 14px',
          borderBottom: '1px solid var(--cue-rule-2)',
          flexWrap:     'wrap',
        }}
      >
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--cue-ink-3)', marginRight: '4px' }}>
          Brief
        </span>
        <Chip fieldKey="Sector"    value={brief.sector}      options={SECTOR_OPTS}  onChange={(v) => setBrief({ sector: v as Brief['sector'] })} />
        <Chip fieldKey="Stage"     value={brief.brandStage}  options={STAGE_OPTS}   onChange={(v) => setBrief({ brandStage: v as Brief['brandStage'] })} />
        <Chip fieldKey="TV History" value={brief.tvHistory}  options={HISTORY_OPTS} onChange={(v) => setBrief({ tvHistory: v as Brief['tvHistory'] })} />
        <Chip fieldKey="Goal"      value={brief.primaryGoal} options={GOAL_OPTS}    onChange={(v) => setBrief({ primaryGoal: v as Brief['primaryGoal'] })} />
        <Chip fieldKey="Budget"    value={brief.budgetTier}  options={BUDGET_OPTS}  onChange={(v) => setBrief({ budgetTier: v as Brief['budgetTier'] })} />
      </div>

      {/* Textarea + Send */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', padding: '10px 14px' }}>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask Cue about your TV investment…"
          rows={2}
          style={{
            flex:       1,
            resize:     'none',
            border:     'none',
            outline:    'none',
            background: 'transparent',
            fontFamily: 'var(--cue-serif)',
            fontSize:   '16px',
            color:      'var(--cue-ink)',
            lineHeight: 1.45,
          }}
        />
        <button
          type="button"
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          aria-label="Ask"
          style={{
            padding:      '8px 16px',
            borderRadius: '8px',
            border:       'none',
            background:   disabled || !value.trim() ? 'var(--cue-rule)' : 'var(--cue-accent)',
            color:        disabled || !value.trim() ? 'var(--cue-ink-4)' : 'var(--cue-paper)',
            fontFamily:   'var(--cue-sans)',
            fontSize:     '13px',
            fontWeight:   500,
            cursor:       disabled || !value.trim() ? 'not-allowed' : 'pointer',
            transition:   'background 120ms, color 120ms',
            whiteSpace:   'nowrap',
          }}
        >
          Ask →
        </button>
      </div>

      {/* Hint row */}
      <div style={{ padding: '0 14px 8px', display: 'flex', gap: '10px' }}>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Answers grounded in 8 Thinkbox reports
        </span>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-4)' }}>
          <kbd style={{ background: 'var(--cue-paper-2)', padding: '1px 4px', borderRadius: '3px', border: '1px solid var(--cue-rule)' }}>↵</kbd> send
          {' · '}
          <kbd style={{ background: 'var(--cue-paper-2)', padding: '1px 4px', borderRadius: '3px', border: '1px solid var(--cue-rule)' }}>⇧↵</kbd> newline
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest Chip.test Composer.test
```

Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Chip dropdown and Composer with brief chips and textarea"
```

---

## Task 12: UserBubble + AssistantBubble

**Files:**
- Create: `frontend/components/thread/UserBubble.tsx`
- Create: `frontend/components/thread/AssistantBubble.tsx`
- Create: `frontend/__tests__/thread/UserBubble.test.tsx`
- Create: `frontend/__tests__/thread/AssistantBubble.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/thread/UserBubble.test.tsx
import { render, screen } from '@testing-library/react'
import { UserBubble } from '@/components/thread/UserBubble'
import type { Brief } from '@/lib/types'

const brief: Brief = { sector:'FMCG', brandStage:'scale-up', tvHistory:'tried', primaryGoal:'brand', budgetTier:'500k-2m' }

test('renders the question text', () => {
  render(<UserBubble question="When does TV work?" brief={brief} time="11:42" />)
  expect(screen.getByText('When does TV work?')).toBeInTheDocument()
})

test('renders brief context tags', () => {
  render(<UserBubble question="q" brief={brief} time="11:42" />)
  expect(screen.getByText('FMCG')).toBeInTheDocument()
  expect(screen.getByText('scale-up')).toBeInTheDocument()
})
```

```typescript
// frontend/__tests__/thread/AssistantBubble.test.tsx
import { render, screen } from '@testing-library/react'
import { AssistantBubble } from '@/components/thread/AssistantBubble'
import type { Answer } from '@/lib/types'

const answer: Answer = {
  headline: { stat: '£5.61', unit: 'ROI per £1', caption: 'Profit Ability 2' },
  summary: ['TV delivers strong ROI [1].', 'Second paragraph.'],
  callout: { label: 'What this means', body: 'Concentrate spend in bursts.' },
  chart: null,
  followups: ['How should I split the burst?'],
  sources: [{ n:1, title:'Profit Ability 2', year:2024, page:14, url:'https://thinkbox.tv', quote:'TV delivered £5.61', topic:'ROI' }],
  meta: { model:'gpt-4o', cached:false, retrievalMs:400, generationMs:2000, chunksUsed:4 },
}

test('renders headline stat', () => {
  render(<AssistantBubble answer={answer} time="11:43" onFollowup={jest.fn()} />)
  expect(screen.getByText('£5.61')).toBeInTheDocument()
})

test('renders prose paragraphs', () => {
  render(<AssistantBubble answer={answer} time="11:43" onFollowup={jest.fn()} />)
  expect(screen.getByText(/TV delivers strong ROI/)).toBeInTheDocument()
  expect(screen.getByText(/Second paragraph/)).toBeInTheDocument()
})

test('shows cached badge when cached=true', () => {
  const cachedAnswer = { ...answer, meta: { ...answer.meta, cached: true } }
  render(<AssistantBubble answer={cachedAnswer} time="11:43" onFollowup={jest.fn()} />)
  expect(screen.getByText('cached')).toBeInTheDocument()
})

test('renders followup buttons', () => {
  render(<AssistantBubble answer={answer} time="11:43" onFollowup={jest.fn()} />)
  expect(screen.getByText('How should I split the burst?')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npx jest UserBubble.test AssistantBubble.test
```

Expected: FAIL

- [ ] **Step 3: Implement UserBubble.tsx**

```typescript
// frontend/components/thread/UserBubble.tsx
'use client'

import type { Brief } from '@/lib/types'

type Props = { question: string; brief: Brief | null; time: string }

const BRIEF_LABELS: Record<keyof Brief, string> = {
  sector:      'Sector',
  brandStage:  'Stage',
  tvHistory:   'TV History',
  primaryGoal: 'Goal',
  budgetTier:  'Budget',
}

export function UserBubble({ question, brief, time }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
      <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        You · {time}
      </div>
      <div
        style={{
          maxWidth:     '88%',
          background:   'var(--cue-ink)',
          color:        'var(--cue-paper)',
          borderRadius: '14px 14px 4px 14px',
          padding:      '14px 18px',
          animation:    'cue-bubble-in 200ms ease-out',
        }}
      >
        {brief && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
            {(Object.entries(brief) as [keyof Brief, string][]).map(([key, val]) => (
              <span
                key={key}
                style={{
                  display:      'inline-flex',
                  gap:          '4px',
                  padding:      '2px 8px',
                  borderRadius: '999px',
                  background:   'rgb(255 255 255 / 0.12)',
                  fontSize:     '11px',
                }}
              >
                <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.6 }}>
                  {BRIEF_LABELS[key]}
                </span>
                <span style={{ fontFamily: 'var(--cue-sans)', fontWeight: 500 }}>{val}</span>
              </span>
            ))}
          </div>
        )}
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '17px', lineHeight: 1.4, letterSpacing: '-0.005em' }}>
          {question}
        </p>
      </div>
      <style>{`
        @keyframes cue-bubble-in {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
```

- [ ] **Step 4: Implement AssistantBubble.tsx**

```typescript
// frontend/components/thread/AssistantBubble.tsx
'use client'

import type { Answer } from '@/lib/types'
import { Headline } from '@/components/atoms/Headline'
import { ProseWithCites } from '@/components/atoms/ProseWithCites'
import { Callout } from '@/components/atoms/Callout'
import { Chart } from '@/components/atoms/Chart'
import { Followups } from '@/components/atoms/Followups'
import { CacheBadge } from '@/components/atoms/CacheBadge'
import { useStore } from '@/lib/store'

type Props = {
  answer:     Answer
  time:       string
  onFollowup: (q: string) => void
}

export function AssistantBubble({ answer, time, onFollowup }: Props) {
  const setActiveCitation = useStore((s) => s.setActiveCitation)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      {/* Meta row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span>
        <span>· {time}</span>
        <span>· {answer.meta.model}</span>
        <span>· {answer.meta.chunksUsed} sources</span>
        {answer.meta.cached && <CacheBadge />}
      </div>

      {/* Bubble */}
      <div
        style={{
          maxWidth:     '760px',
          width:        '100%',
          background:   'var(--cue-paper)',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '4px 14px 14px 14px',
          padding:      '22px 24px',
          animation:    'cue-bubble-in 200ms ease-out',
          display:      'flex',
          flexDirection:'column',
          gap:          '16px',
        }}
      >
        {answer.headline && (
          <Headline stat={answer.headline.stat} unit={answer.headline.unit} caption={answer.headline.caption} />
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {answer.summary.map((para, i) => (
            <p
              key={i}
              style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '16.5px', lineHeight: 1.55, color: 'var(--cue-ink-2)', letterSpacing: '-0.005em' }}
            >
              <ProseWithCites
                text={para}
                onCiteClick={(n) => setActiveCitation(n)}
                onCiteHover={(n) => setActiveCitation(n)}
                onCiteLeave={() => setActiveCitation(null)}
              />
            </p>
          ))}
        </div>

        {answer.callout && (
          <Callout label={answer.callout.label} body={answer.callout.body} />
        )}

        {answer.chart && <Chart chart={answer.chart} />}

        {/* Action row */}
        <div style={{ display: 'flex', gap: '8px', paddingTop: '12px', borderTop: '1px dashed var(--cue-rule-2)' }}>
          {['Copy', 'Regenerate', '👍', '👎'].map((label) => (
            <button
              key={label}
              type="button"
              style={{
                padding:      '6px 12px',
                border:       '1px solid var(--cue-rule)',
                borderRadius: '6px',
                background:   'transparent',
                cursor:       'pointer',
                fontFamily:   'var(--cue-mono)',
                fontSize:     '10.5px',
                color:        'var(--cue-ink-3)',
                transition:   'border-color 120ms, color 120ms',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <Followups items={answer.followups} onPick={onFollowup} />
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest UserBubble.test AssistantBubble.test
```

Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add UserBubble and AssistantBubble thread components"
```

---

## Task 13: StreamingBubble + RefusalCard + ErrorCard

**Files:**
- Create: `frontend/components/thread/StreamingBubble.tsx`
- Create: `frontend/components/thread/RefusalCard.tsx`
- Create: `frontend/components/thread/ErrorCard.tsx`
- Create: `frontend/__tests__/thread/StreamingBubble.test.tsx`
- Create: `frontend/__tests__/thread/RefusalCard.test.tsx`
- Create: `frontend/__tests__/thread/ErrorCard.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/thread/StreamingBubble.test.tsx
import { render, screen } from '@testing-library/react'
import { StreamingBubble } from '@/components/thread/StreamingBubble'

const steps = ['Parsing brief', 'Retrieving chunks']

test('renders trace steps', () => {
  render(<StreamingBubble traceSteps={steps} streamedText="" done={false} />)
  // Trace renders steps with animation delay; at least the container is present
  const { container } = render(<StreamingBubble traceSteps={steps} streamedText="" done={false} />)
  expect(container.firstChild).toBeTruthy()
})

test('shows streamed text when present', () => {
  render(<StreamingBubble traceSteps={steps} streamedText="TV delivers" done={false} />)
  expect(screen.getByText(/TV delivers/)).toBeInTheDocument()
})
```

```typescript
// frontend/__tests__/thread/RefusalCard.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RefusalCard } from '@/components/thread/RefusalCard'

const examples = ['Is TV good for DTC?', 'What is the ROI of TV?']

test('renders off-topic header', () => {
  render(<RefusalCard message="Off-topic." examples={examples} onPick={jest.fn()} time="12:00" />)
  expect(screen.getByText(/off-topic/i)).toBeInTheDocument()
})

test('renders example suggestions', () => {
  render(<RefusalCard message="Off-topic." examples={examples} onPick={jest.fn()} time="12:00" />)
  expect(screen.getByText('Is TV good for DTC?')).toBeInTheDocument()
})

test('calls onPick when example clicked', async () => {
  const onPick = jest.fn()
  render(<RefusalCard message="Off-topic." examples={examples} onPick={onPick} time="12:00" />)
  await userEvent.click(screen.getByText('Is TV good for DTC?'))
  expect(onPick).toHaveBeenCalledWith('Is TV good for DTC?')
})
```

```typescript
// frontend/__tests__/thread/ErrorCard.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorCard } from '@/components/thread/ErrorCard'

test('renders title and message', () => {
  render(<ErrorCard title="We couldn't ground this one" message="Please try again." reference="cue-err-abc123" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.getByText("We couldn't ground this one")).toBeInTheDocument()
  expect(screen.getByText('Please try again.')).toBeInTheDocument()
})

test('renders opaque reference id', () => {
  render(<ErrorCard title="Error" message="msg" reference="cue-err-abc123" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.getByText(/cue-err-abc123/)).toBeInTheDocument()
})

test('calls onRetry when Retry clicked', async () => {
  const onRetry = jest.fn()
  render(<ErrorCard title="Error" message="msg" reference="ref" retryable={true} onRetry={onRetry} time="12:00" />)
  await userEvent.click(screen.getByRole('button', { name: /retry/i }))
  expect(onRetry).toHaveBeenCalled()
})

test('does not surface backend details in message', () => {
  render(<ErrorCard title="Error" message="Service unavailable." reference="ref" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.queryByText(/503/)).not.toBeInTheDocument()
  expect(screen.queryByText(/gpt-4o/)).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npx jest StreamingBubble.test RefusalCard.test ErrorCard.test
```

Expected: FAIL

- [ ] **Step 3: Implement StreamingBubble.tsx**

```typescript
// frontend/components/thread/StreamingBubble.tsx
'use client'

import { Trace } from '@/components/atoms/Trace'

type Props = {
  traceSteps:  string[]
  streamedText: string
  done:         boolean
}

const CUE_TRACE_STEPS = [
  'Parsing brief',
  'Filtering corpus by topic',
  'Retrieving relevant chunks…',
  'Grounding answer in sources',
  'Verifying citations',
]

export function StreamingBubble({ traceSteps = CUE_TRACE_STEPS, streamedText, done }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span>
        {' · thinking…'}
      </div>
      <div
        style={{
          maxWidth:     '760px',
          width:        '100%',
          background:   'var(--cue-paper)',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '4px 14px 14px 14px',
          padding:      '22px 24px',
          display:      'flex',
          flexDirection:'column',
          gap:          '16px',
        }}
      >
        <Trace steps={traceSteps} />

        {streamedText && (
          <>
            <hr style={{ border: 'none', borderTop: '1px solid var(--cue-rule-2)', margin: '0' }} />
            <p
              style={{
                margin:     0,
                fontFamily: 'var(--cue-serif)',
                fontSize:   '16.5px',
                lineHeight: 1.55,
                color:      'var(--cue-ink-2)',
              }}
            >
              {streamedText}
              {!done && (
                <span
                  style={{
                    display:          'inline-block',
                    width:            '2px',
                    height:           '1em',
                    background:       'var(--cue-accent)',
                    marginLeft:       '2px',
                    verticalAlign:    'text-bottom',
                    animation:        'cue-caret 1s step-end infinite',
                  }}
                />
              )}
            </p>
          </>
        )}
      </div>
      <style>{`
        @keyframes cue-caret {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
```

- [ ] **Step 4: Implement RefusalCard.tsx**

```typescript
// frontend/components/thread/RefusalCard.tsx
'use client'

type Props = {
  message:  string
  examples: string[]
  onPick:   (q: string) => void
  time:     string
}

export function RefusalCard({ message, examples, onPick, time }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span> · {time}
      </div>
      <div
        style={{
          maxWidth:      '760px',
          border:        '1px solid var(--cue-rule)',
          borderLeft:    '3px solid var(--cue-danger)',
          borderRadius:  '4px 14px 14px 14px',
          background:    'var(--cue-danger-soft)',
          padding:       '18px 20px',
          display:       'flex',
          flexDirection: 'column',
          gap:           '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--cue-danger)', fontSize: '16px', fontWeight: 700 }}>⨯</span>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-danger-ink)', fontWeight: 600 }}>
            Off-topic for this advisor
          </span>
        </div>
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '15px', color: 'var(--cue-ink-2)', lineHeight: 1.5 }}>
          {message}
        </p>
        {examples.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {examples.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => onPick(ex)}
                style={{
                  textAlign:    'left',
                  padding:      '8px 12px',
                  border:       '1px solid var(--cue-rule)',
                  borderRadius: '6px',
                  background:   'var(--cue-paper)',
                  cursor:       'pointer',
                  fontFamily:   'var(--cue-serif)',
                  fontSize:     '13.5px',
                  color:        'var(--cue-ink-2)',
                }}
              >
                ↳ {ex}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Implement ErrorCard.tsx**

```typescript
// frontend/components/thread/ErrorCard.tsx
'use client'

type Props = {
  title:     string
  message:   string
  reference: string
  retryable: boolean
  onRetry:   () => void
  time:      string
}

export function ErrorCard({ title, message, reference, retryable, onRetry, time }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span> · {time}
      </div>
      <div
        style={{
          maxWidth:      '760px',
          border:        '1px solid var(--cue-rule)',
          borderLeft:    '3px solid var(--cue-warn)',
          borderRadius:  '4px 14px 14px 14px',
          background:    'var(--cue-warn-soft)',
          padding:       '18px 20px',
          display:       'flex',
          flexDirection: 'column',
          gap:           '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--cue-warn)', fontSize: '16px', fontWeight: 700 }}>!</span>
          <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '15px', fontWeight: 500, color: 'var(--cue-ink)' }}>{title}</span>
        </div>
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '15px', color: 'var(--cue-ink-2)', lineHeight: 1.5 }}>
          {message}
        </p>
        <div style={{ display: 'flex', gap: '8px' }}>
          {retryable && (
            <button
              type="button"
              onClick={onRetry}
              aria-label="Retry"
              style={{
                padding:      '8px 16px',
                borderRadius: '6px',
                border:       'none',
                background:   'var(--cue-accent)',
                color:        'var(--cue-paper)',
                fontFamily:   'var(--cue-sans)',
                fontSize:     '13px',
                fontWeight:   500,
                cursor:       'pointer',
              }}
            >
              Retry
            </button>
          )}
          <button
            type="button"
            style={{
              padding:      '8px 16px',
              borderRadius: '6px',
              border:       '1px solid var(--cue-rule)',
              background:   'transparent',
              fontFamily:   'var(--cue-sans)',
              fontSize:     '13px',
              color:        'var(--cue-ink-2)',
              cursor:       'pointer',
            }}
          >
            Rephrase
          </button>
        </div>
        {/* Opaque reference — never expose raw backend details */}
        <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-4)', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>Reference</span>
          <span>{reference}</span>
          <span style={{ color: 'var(--cue-ink-3)' }}>— Share with support if the problem persists.</span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Run tests**

```bash
cd frontend && npx jest StreamingBubble.test RefusalCard.test ErrorCard.test
```

Expected: 8 passed

- [ ] **Step 7: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add StreamingBubble, RefusalCard, and ErrorCard thread components"
```

---

*Plan continues in Part 3 (Tasks 14–20: Rails, Layout shell, Empty state, Full wiring)*

---

## Task 14: Topbar + CueApp Layout Shell

**Files:**
- Create: `frontend/components/layout/Topbar.tsx`
- Create: `frontend/components/layout/CueApp.tsx`
- Modify: `frontend/app/page.tsx`
- Create: `frontend/__tests__/layout/CueApp.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/layout/CueApp.test.tsx
import { render, screen } from '@testing-library/react'
import { CueApp } from '@/components/layout/CueApp'

// Mock child components to keep test focused on layout
jest.mock('@/components/layout/Topbar', () => ({ Topbar: () => <div data-testid="topbar" /> }))
jest.mock('@/components/rail/CorpusRail', () => ({ CorpusRail: () => <div data-testid="corpus-rail" /> }))
jest.mock('@/components/rail/EvidenceRail', () => ({ EvidenceRail: () => <div data-testid="evidence-rail" /> }))
jest.mock('@/components/composer/Composer', () => ({ Composer: () => <div data-testid="composer" /> }))

test('renders topbar, thread area, and rail', () => {
  render(<CueApp />)
  expect(screen.getByTestId('topbar')).toBeInTheDocument()
  expect(screen.getByTestId('composer')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd frontend && npx jest CueApp.test
```

Expected: FAIL

- [ ] **Step 3: Implement Topbar.tsx**

```typescript
// frontend/components/layout/Topbar.tsx
'use client'

import { useStore } from '@/lib/store'

type Props = { threadTitle?: string }

export function Topbar({ threadTitle }: Props) {
  const { setHistoryOpen, setExportOpen } = useStore()

  return (
    <header
      style={{
        height:         '60px',
        display:        'flex',
        alignItems:     'center',
        padding:        '0 20px',
        gap:            '12px',
        background:     'var(--cue-paper)',
        borderBottom:   '1px solid var(--cue-rule)',
        position:       'sticky',
        top:            0,
        zIndex:         50,
        justifyContent: 'space-between',
      }}
    >
      {/* Left: hamburger + brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          type="button"
          aria-label="Open thread history"
          onClick={() => setHistoryOpen(true)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '18px', padding: '4px' }}
        >
          ☰
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--cue-accent)', display: 'inline-block' }} />
          <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '16px', fontWeight: 500, color: 'var(--cue-ink)' }}>Cue</span>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--cue-ink-3)' }}>
            TV Investment Advisor
          </span>
        </div>
      </div>

      {/* Center: thread title */}
      {threadTitle && (
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', color: 'var(--cue-ink-3)', flex: 1, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '400px' }}>
          {threadTitle}
        </span>
      )}

      {/* Right: export */}
      <button
        type="button"
        onClick={() => setExportOpen(true)}
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '4px',
          padding:      '6px 12px',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '6px',
          background:   'transparent',
          cursor:       'pointer',
          fontFamily:   'var(--cue-mono)',
          fontSize:     '10.5px',
          color:        'var(--cue-ink-3)',
          textTransform:'uppercase',
          letterSpacing:'0.06em',
        }}
      >
        ↓ Export
      </button>
    </header>
  )
}
```

- [ ] **Step 4: Implement CueApp.tsx**

```typescript
// frontend/components/layout/CueApp.tsx
'use client'

import { useStore } from '@/lib/store'
import { Topbar } from './Topbar'
import { Composer } from '@/components/composer/Composer'
import { UserBubble } from '@/components/thread/UserBubble'
import { AssistantBubble } from '@/components/thread/AssistantBubble'
import { StreamingBubble } from '@/components/thread/StreamingBubble'
import { RefusalCard } from '@/components/thread/RefusalCard'
import { ErrorCard } from '@/components/thread/ErrorCard'
import { EvidenceRail } from '@/components/rail/EvidenceRail'
import { CorpusRail } from '@/components/rail/CorpusRail'
import { HistoryDrawer } from '@/overlays/HistoryDrawer'
import { ExportModal } from '@/overlays/ExportModal'
import { EmptyState } from './EmptyState'

export function CueApp() {
  const {
    thread, phase, composerInput, railCollapsed,
    setBrief, setComposerInput, ask, retry, toggleRail,
  } = useStore()

  const lastAnswer = [...thread.turns].reverse().find((t) => t.role === 'assistant')
  const sources = lastAnswer?.role === 'assistant' ? lastAnswer.answer.sources : []
  const hasAnswers = thread.turns.some((t) => t.role === 'assistant')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <Topbar threadTitle={thread.title !== 'New thread' ? thread.title : undefined} />

      <div
        style={{
          flex:           1,
          display:        'grid',
          gridTemplateColumns: `1fr ${railCollapsed ? '56px' : '340px'}`,
          transition:     'grid-template-columns 220ms cubic-bezier(.2,.7,.3,1)',
          overflow:       'hidden',
          borderTop:      '1px solid var(--cue-rule-2)',
        }}
      >
        {/* Main thread column */}
        <div
          style={{
            display:        'flex',
            flexDirection:  'column',
            overflow:       'hidden',
            borderRight:    '1px solid var(--cue-rule)',
          }}
        >
          {/* Thread scroll area */}
          <div
            style={{
              flex:       1,
              overflowY:  'auto',
              padding:    '32px 24px',
              display:    'flex',
              flexDirection: 'column',
              gap:        '24px',
              alignItems: 'center',
            }}
          >
            <div style={{ width: '100%', maxWidth: '760px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {thread.turns.length === 0 && phase === 'idle' && (
                <EmptyState onPickStarter={(q) => { setComposerInput(q); ask() }} />
              )}

              {thread.turns.map((turn, i) => {
                if (turn.role === 'user') {
                  return <UserBubble key={i} question={turn.question} brief={turn.brief} time={turn.time} />
                }
                if (turn.role === 'assistant') {
                  return (
                    <AssistantBubble
                      key={i}
                      answer={turn.answer}
                      time={turn.time}
                      onFollowup={(q) => { setComposerInput(q); ask() }}
                    />
                  )
                }
                if (turn.role === 'refusal') {
                  return (
                    <RefusalCard
                      key={i}
                      message={turn.message}
                      examples={turn.examples}
                      onPick={(q) => { setComposerInput(q); ask() }}
                      time={turn.time}
                    />
                  )
                }
                if (turn.role === 'error') {
                  return (
                    <ErrorCard
                      key={i}
                      title={turn.title}
                      message={turn.message}
                      reference={turn.reference}
                      retryable={turn.retryable}
                      onRetry={retry}
                      time={turn.time}
                    />
                  )
                }
                return null
              })}

              {(phase === 'thinking' || phase === 'streaming') && (
                <StreamingBubble traceSteps={[]} streamedText="" done={false} />
              )}
            </div>
          </div>

          {/* Composer pinned at bottom */}
          <div style={{ padding: '16px 24px 20px', borderTop: '1px solid var(--cue-rule-2)', background: 'var(--cue-paper)' }}>
            <Composer
              brief={thread.brief}
              setBrief={setBrief}
              value={composerInput}
              onChange={setComposerInput}
              onSubmit={ask}
              disabled={phase !== 'idle'}
            />
          </div>
        </div>

        {/* Right rail */}
        <div style={{ background: 'var(--cue-paper-2)', overflow: 'hidden' }}>
          {hasAnswers
            ? <EvidenceRail sources={sources} collapsed={railCollapsed} onToggle={toggleRail} />
            : <CorpusRail collapsed={railCollapsed} onToggle={toggleRail} />
          }
        </div>
      </div>

      <HistoryDrawer />
      <ExportModal />
    </div>
  )
}
```

- [ ] **Step 5: Add EmptyState component (used by CueApp)**

```typescript
// frontend/components/layout/EmptyState.tsx
'use client'

const STARTERS = [
  { topic: 'ROI',          q: 'When does linear TV deliver its best ROI for a scale-up FMCG brand?' },
  { topic: 'Planning',     q: 'How should I split spend between linear TV and BVOD?' },
  { topic: 'Effectiveness',q: 'What does Peter Field say about attention and trust on TV vs. social?' },
  { topic: 'Small biz',    q: 'Is £250k enough to make TV pay back inside a year?' },
  { topic: 'Creative',     q: 'How long should a launch campaign run before I judge it?' },
  { topic: 'Viewing',      q: 'How much of 16–34 viewing is BVOD now, and where is it going?' },
]

type Props = { onPickStarter: (q: string) => void }

export function EmptyState({ onPickStarter }: Props) {
  return (
    <div style={{ padding: '40px 0', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--cue-accent-ink)' }}>
          For FMCG · Scale-up · £500K–£2M
        </span>
        <h1
          style={{
            margin:      0,
            fontFamily:  'var(--cue-serif)',
            fontSize:    '44px',
            lineHeight:  1.1,
            fontWeight:  500,
            letterSpacing:'-0.025em',
            color:       'var(--cue-ink)',
          }}
        >
          Evidence-backed TV investment advice,{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--cue-accent)' }}>24/7.</em>
        </h1>
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '17px', lineHeight: 1.45, color: 'var(--cue-ink-3)', maxWidth: '520px' }}>
          Ask Cue anything about TV advertising investment. Every answer is grounded in published Thinkbox research — no hallucinations, full citations.
        </p>
      </div>

      {/* Starter cards — 2 columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        {STARTERS.map((s) => (
          <button
            key={s.q}
            type="button"
            onClick={() => onPickStarter(s.q)}
            style={{
              textAlign:    'left',
              padding:      '14px 16px',
              border:       '1px solid var(--cue-rule)',
              borderRadius: '8px',
              background:   'var(--cue-paper)',
              cursor:       'pointer',
              display:      'flex',
              flexDirection:'column',
              gap:          '6px',
              transition:   'border-color 120ms',
            }}
          >
            <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-accent-ink)' }}>
              {s.topic}
            </span>
            <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '13.5px', color: 'var(--cue-ink-2)', lineHeight: 1.35 }}>
              {s.q}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Update app/page.tsx**

```typescript
// frontend/app/page.tsx
import { CueApp } from '@/components/layout/CueApp'

export default function Home() {
  return <CueApp />
}
```

- [ ] **Step 7: Run tests**

```bash
cd frontend && npx jest CueApp.test
```

Expected: 1 passed

- [ ] **Step 8: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add Topbar, CueApp layout shell, EmptyState, and wire page.tsx"
```

---

## Task 15: EvidenceRail + CorpusRail

**Files:**
- Create: `frontend/components/rail/EvidenceRail.tsx`
- Create: `frontend/components/rail/CorpusRail.tsx`
- Create: `frontend/__tests__/rail/EvidenceRail.test.tsx`
- Create: `frontend/__tests__/rail/CorpusRail.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/rail/EvidenceRail.test.tsx
import { render, screen } from '@testing-library/react'
import { EvidenceRail } from '@/components/rail/EvidenceRail'
import type { Source } from '@/lib/types'

const sources: Source[] = [
  { n:1, title:'Profit Ability 2', year:2024, page:14, url:'https://thinkbox.tv', quote:'TV ROI £5.61', topic:'ROI' },
  { n:2, title:'Payback 4',        year:2014, page:22, url:'https://thinkbox.tv', quote:'Seasonal windows', topic:'Planning' },
]

test('renders all source titles', () => {
  render(<EvidenceRail sources={sources} collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText('Payback 4')).toBeInTheDocument()
})

test('shows EVIDENCE header', () => {
  render(<EvidenceRail sources={sources} collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText(/evidence/i)).toBeInTheDocument()
})

test('shows collapsed label when collapsed=true', () => {
  const { container } = render(<EvidenceRail sources={sources} collapsed={true} onToggle={jest.fn()} />)
  expect(container.querySelector('.cue-rail--collapsed')).toBeTruthy()
})
```

```typescript
// frontend/__tests__/rail/CorpusRail.test.tsx
import { render, screen } from '@testing-library/react'
import { CorpusRail } from '@/components/rail/CorpusRail'

test('renders corpus stats', () => {
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText('8')).toBeInTheDocument()   // 8 reports
  expect(screen.getByText(/reports/i)).toBeInTheDocument()
})

test('renders all corpus document titles', () => {
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText('TV Viewing Report')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npx jest EvidenceRail.test CorpusRail.test
```

Expected: FAIL

- [ ] **Step 3: Implement EvidenceRail.tsx**

```typescript
// frontend/components/rail/EvidenceRail.tsx
'use client'

import { useState } from 'react'
import { SourceCard } from '@/components/atoms/SourceCard'
import { useStore } from '@/lib/store'
import type { Source } from '@/lib/types'

const TOPICS = ['All', 'ROI', 'Planning', 'Effectiveness', 'Viewing', 'Small business']

type Props = {
  sources:   Source[]
  collapsed: boolean
  onToggle:  () => void
}

export function EvidenceRail({ sources, collapsed, onToggle }: Props) {
  const [activeTopic, setActiveTopic] = useState('All')
  const { activeCitation, setActiveSource, activeSource } = useStore()

  const filtered = activeTopic === 'All'
    ? sources
    : sources.filter((s) => s.topic === activeTopic)

  if (collapsed) {
    return (
      <div
        className="cue-rail--collapsed"
        style={{ width: '56px', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '16px', gap: '12px' }}
      >
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>›</button>
        <span
          style={{
            fontFamily:    'var(--cue-mono)',
            fontSize:      '10px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color:         'var(--cue-ink-3)',
            writingMode:   'vertical-rl',
            transform:     'rotate(180deg)',
          }}
        >
          Evidence
        </span>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px 10px', borderBottom: '1px solid var(--cue-rule)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', fontWeight: 500 }}>
            Evidence
          </span>
          <span style={{ background: 'var(--cue-accent-soft)', color: 'var(--cue-accent-ink)', fontFamily: 'var(--cue-mono)', fontSize: '10px', padding: '1px 6px', borderRadius: '999px' }}>
            {sources.length}
          </span>
        </div>
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>‹</button>
      </div>

      {/* Topic filter tabs */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', padding: '10px 12px', borderBottom: '1px solid var(--cue-rule-2)' }}>
        {TOPICS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setActiveTopic(t)}
            style={{
              padding:      '3px 8px',
              borderRadius: '999px',
              border:       '1px solid var(--cue-rule)',
              background:   activeTopic === t ? 'var(--cue-accent-soft)' : 'transparent',
              color:        activeTopic === t ? 'var(--cue-accent-ink)' : 'var(--cue-ink-3)',
              fontFamily:   'var(--cue-mono)',
              fontSize:     '9.5px',
              textTransform:'uppercase',
              letterSpacing:'0.06em',
              cursor:       'pointer',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Source list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filtered.map((src) => (
          <SourceCard
            key={src.n}
            source={src}
            highlight={activeCitation === src.n || activeSource === src.n}
            compact
          />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Implement CorpusRail.tsx**

```typescript
// frontend/components/rail/CorpusRail.tsx
'use client'

const CORPUS = [
  { title: 'Profit Ability 2',        year: 2024, topic: 'ROI',            chunks: 24, blurb: '141 brands · £5.61 ROI/£1' },
  { title: 'Profit Ability 1',        year: 2018, topic: 'ROI',            chunks: 22, blurb: 'Short- vs long-term payback' },
  { title: 'Peter Field white paper', year: 2024, topic: 'Effectiveness',  chunks: 18, blurb: '10 years of IPA data' },
  { title: 'Payback 4',               year: 2014, topic: 'Planning',       chunks: 20, blurb: 'Seasonal windows by sector' },
  { title: 'TV Viewing Report',       year: 2024, topic: 'Viewing',        chunks: 16, blurb: 'BVOD 29% of 16–34' },
  { title: 'Signalling Success',      year: 2020, topic: 'Effectiveness',  chunks: 12, blurb: 'Brand fame, trust, mental availability' },
  { title: 'Demand Generator',        year: 2019, topic: 'Planning',       chunks: 16, blurb: 'WPP econometric meta-analysis' },
  { title: 'As Seen on TV',           year: 2019, topic: 'Small business', chunks: 14, blurb: '300+ campaigns · 4-month payback' },
]

type Props = { collapsed: boolean; onToggle: () => void }

export function CorpusRail({ collapsed, onToggle }: Props) {
  if (collapsed) {
    return (
      <div style={{ width: '56px', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '16px', gap: '12px' }}>
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>›</button>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
          Corpus
        </span>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px 10px', borderBottom: '1px solid var(--cue-rule)' }}>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', fontWeight: 500 }}>Corpus</span>
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>‹</button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', padding: '12px', borderBottom: '1px solid var(--cue-rule-2)' }}>
        {[
          { n: '8',   label: 'Reports' },
          { n: '142', label: 'Chunks' },
          { n: '6',   label: 'Topics' },
        ].map((s) => (
          <div key={s.label} style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '24px', color: 'var(--cue-accent)', fontWeight: 500 }}>{s.n}</div>
            <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Corpus document list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {CORPUS.map((doc) => (
          <div
            key={doc.title}
            style={{ display: 'flex', gap: '10px', padding: '10px', borderRadius: '6px', border: '1px solid transparent' }}
          >
            {/* Thumbnail */}
            <div style={{ width: '36px', minWidth: '36px', height: '44px', background: 'var(--cue-paper)', border: '1px solid var(--cue-rule)', borderTop: '3px solid var(--cue-accent)', borderRadius: '4px', display: 'flex', alignItems: 'flex-end', justifyContent: 'flex-end', padding: '3px 4px' }}>
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '8px', color: 'var(--cue-ink-4)' }}>{doc.year}</span>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '13px', fontWeight: 500, color: 'var(--cue-ink)', lineHeight: 1.3, marginBottom: '4px' }}>{doc.title}</div>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '3px' }}>
                <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--cue-accent-ink)', background: 'var(--cue-accent-soft)', padding: '1px 5px', borderRadius: '3px' }}>{doc.topic}</span>
                <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', color: 'var(--cue-ink-4)' }}>{doc.chunks} chunks</span>
              </div>
              <div style={{ fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '11px', color: 'var(--cue-ink-3)' }}>{doc.blurb}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest EvidenceRail.test CorpusRail.test
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add EvidenceRail and CorpusRail components"
```

---

## Task 16: HistoryDrawer + ExportModal

**Files:**
- Create: `frontend/overlays/HistoryDrawer.tsx`
- Create: `frontend/overlays/ExportModal.tsx`
- Create: `frontend/__tests__/overlays/HistoryDrawer.test.tsx`
- Create: `frontend/__tests__/overlays/ExportModal.test.tsx`

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/__tests__/overlays/HistoryDrawer.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HistoryDrawer } from '@/overlays/HistoryDrawer'
import { useStore } from '@/lib/store'

beforeEach(() => {
  useStore.setState({ historyOpen: true })
})

test('renders THREADS heading when open', () => {
  render(<HistoryDrawer />)
  expect(screen.getByText('Threads')).toBeInTheDocument()
})

test('renders + New thread button', () => {
  render(<HistoryDrawer />)
  expect(screen.getByText(/new thread/i)).toBeInTheDocument()
})

test('close button sets historyOpen to false', async () => {
  render(<HistoryDrawer />)
  await userEvent.click(screen.getByRole('button', { name: /close/i }))
  expect(useStore.getState().historyOpen).toBe(false)
})

test('does not render when historyOpen=false', () => {
  useStore.setState({ historyOpen: false })
  const { container } = render(<HistoryDrawer />)
  expect(container.firstChild).toBeNull()
})
```

```typescript
// frontend/__tests__/overlays/ExportModal.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExportModal } from '@/overlays/ExportModal'
import { useStore } from '@/lib/store'

beforeEach(() => {
  useStore.setState({ exportOpen: true })
})

test('renders Export preview heading when open', () => {
  render(<ExportModal />)
  expect(screen.getByText(/export preview/i)).toBeInTheDocument()
})

test('close button sets exportOpen to false', async () => {
  render(<ExportModal />)
  await userEvent.click(screen.getByRole('button', { name: /close/i }))
  expect(useStore.getState().exportOpen).toBe(false)
})

test('does not render when exportOpen=false', () => {
  useStore.setState({ exportOpen: false })
  const { container } = render(<ExportModal />)
  expect(container.firstChild).toBeNull()
})
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd frontend && npx jest HistoryDrawer.test ExportModal.test
```

Expected: FAIL

- [ ] **Step 3: Implement HistoryDrawer.tsx**

```typescript
// frontend/overlays/HistoryDrawer.tsx
'use client'

import { useStore } from '@/lib/store'

export function HistoryDrawer() {
  const { historyOpen, setHistoryOpen, threads, thread, openThread, newThread } = useStore()

  if (!historyOpen) return null

  return (
    <>
      {/* Scrim */}
      <div
        style={{ position: 'fixed', inset: 0, background: 'rgb(0 0 0 / 0.35)', zIndex: 100, backdropFilter: 'blur(2px)' }}
        onClick={() => setHistoryOpen(false)}
      />

      {/* Drawer */}
      <div
        style={{
          position:      'fixed',
          top:           0,
          left:          0,
          bottom:        0,
          width:         '320px',
          background:    'var(--cue-paper)',
          borderRight:   '1px solid var(--cue-rule)',
          zIndex:        101,
          display:       'flex',
          flexDirection: 'column',
          animation:     'cue-drawer-in 220ms cubic-bezier(.2,.7,.3,1)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--cue-rule)' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', fontWeight: 600 }}>
            Threads
          </span>
          <button
            type="button"
            aria-label="Close"
            onClick={() => setHistoryOpen(false)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}
          >
            ✕
          </button>
        </div>

        {/* New thread */}
        <button
          type="button"
          onClick={() => { newThread(); setHistoryOpen(false) }}
          style={{
            display:      'flex',
            alignItems:   'center',
            gap:          '8px',
            padding:      '14px 20px',
            border:       'none',
            borderBottom: '1px solid var(--cue-rule-2)',
            background:   'transparent',
            cursor:       'pointer',
            fontFamily:   'var(--cue-sans)',
            fontSize:     '13px',
            color:        'var(--cue-accent)',
            textAlign:    'left',
          }}
        >
          + New thread
        </button>

        {/* Thread list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {[thread, ...threads].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => openThread(t.id)}
              style={{
                display:        'flex',
                flexDirection:  'column',
                gap:            '4px',
                width:          '100%',
                padding:        '12px 20px',
                border:         'none',
                borderBottom:   '1px solid var(--cue-rule-2)',
                background:     t.id === thread.id ? 'var(--cue-accent-soft)' : 'transparent',
                cursor:         'pointer',
                textAlign:      'left',
              }}
            >
              <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '13.5px', color: 'var(--cue-ink)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '260px' }}>
                {t.title}
              </span>
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)' }}>
                {t.turns.length} turns
              </span>
            </button>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes cue-drawer-in {
          from { transform: translateX(-100%); }
          to   { transform: translateX(0); }
        }
      `}</style>
    </>
  )
}
```

- [ ] **Step 4: Implement ExportModal.tsx**

```typescript
// frontend/overlays/ExportModal.tsx
'use client'

import { useStore } from '@/lib/store'

export function ExportModal() {
  const { exportOpen, setExportOpen, thread } = useStore()

  if (!exportOpen) return null

  const lastAnswer = [...thread.turns].reverse().find((t) => t.role === 'assistant')
  const answer = lastAnswer?.role === 'assistant' ? lastAnswer.answer : null
  const lastQuestion = [...thread.turns].reverse().find((t) => t.role === 'user')?.question ?? ''
  const brief = thread.brief

  return (
    <>
      {/* Scrim */}
      <div
        style={{ position: 'fixed', inset: 0, background: 'rgb(0 0 0 / 0.80)', zIndex: 200, backdropFilter: 'blur(4px)' }}
        onClick={() => setExportOpen(false)}
      />

      {/* Modal */}
      <div
        style={{
          position:   'fixed',
          inset:      0,
          zIndex:     201,
          display:    'flex',
          flexDirection: 'column',
          overflow:   'auto',
        }}
      >
        {/* Top bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid rgb(255 255 255 / 0.15)' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgb(255 255 255 / 0.7)' }}>
            Export preview · A4 · PDF
          </span>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => window.print()}
              style={{ padding: '6px 14px', borderRadius: '6px', border: 'none', background: 'var(--cue-accent)', color: 'white', fontFamily: 'var(--cue-sans)', fontSize: '12px', cursor: 'pointer' }}
            >
              Download PDF
            </button>
            <button
              type="button"
              aria-label="Close"
              onClick={() => setExportOpen(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgb(255 255 255 / 0.7)', fontSize: '18px', padding: '4px 8px' }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* A4 preview sheet */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '32px 24px 64px' }}>
          <div
            className="cue-export-sheet"
            style={{
              width:        '680px',
              minHeight:    '962px',
              background:   'white',
              borderRadius: '4px',
              boxShadow:    '0 24px 64px rgb(0 0 0 / 0.20), 0 0 0 1px rgb(0 0 0 / 0.06)',
              padding:      '56px 64px',
              display:      'flex',
              flexDirection:'column',
              gap:          '24px',
            }}
          >
            {/* Brand header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e5e0d4', paddingBottom: '20px' }}>
              <div>
                <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '20px', fontWeight: 500, color: 'var(--cue-ink)' }}>Cue</div>
                <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--cue-ink-3)' }}>TV Investment Advisor</div>
              </div>
              <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)' }}>
                {new Date().toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' })}
              </div>
            </div>

            {/* Brief snapshot */}
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', fontFamily: 'var(--cue-mono)' }}>
              <tbody>
                {[
                  ['Sector',      brief.sector],
                  ['Stage',       brief.brandStage],
                  ['TV History',  brief.tvHistory],
                  ['Goal',        brief.primaryGoal],
                  ['Budget',      brief.budgetTier],
                ].map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #ebe5d8' }}>
                    <td style={{ padding: '5px 0', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em', width: '120px' }}>{k}</td>
                    <td style={{ padding: '5px 0', color: 'var(--cue-ink)', fontWeight: 500 }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Question */}
            {lastQuestion && (
              <h2 style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '26px', fontWeight: 500, color: 'var(--cue-ink)', lineHeight: 1.2, letterSpacing: '-0.02em' }}>
                {lastQuestion}
              </h2>
            )}

            {/* Answer content */}
            {answer && (
              <>
                {answer.headline && (
                  <div>
                    <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '40px', fontWeight: 500, color: 'var(--cue-accent)' }}>{answer.headline.stat}</div>
                    <div style={{ fontFamily: 'var(--cue-sans)', fontSize: '13px', color: 'var(--cue-ink-2)' }}>{answer.headline.unit}</div>
                    <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', color: 'var(--cue-ink-3)' }}>{answer.headline.caption}</div>
                  </div>
                )}
                {answer.summary.map((p, i) => (
                  <p key={i} style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '14px', lineHeight: 1.6, color: 'var(--cue-ink-2)' }}>{p}</p>
                ))}
                {answer.callout && (
                  <div style={{ background: '#f3efe6', borderLeft: '3px solid var(--cue-accent)', padding: '14px 16px', borderRadius: '0 6px 6px 0' }}>
                    <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', textTransform: 'uppercase', color: 'var(--cue-accent-ink)', marginBottom: '6px' }}>{answer.callout.label}</div>
                    <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '14px', color: 'var(--cue-ink-2)', lineHeight: 1.5 }}>{answer.callout.body}</p>
                  </div>
                )}
                {/* Sources */}
                {answer.sources.length > 0 && (
                  <div>
                    <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', marginBottom: '12px', borderTop: '1px solid #e5e0d4', paddingTop: '16px' }}>
                      Sources
                    </div>
                    {answer.sources.map((s) => (
                      <div key={s.n} style={{ marginBottom: '12px' }}>
                        <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '13px', fontWeight: 500 }}>[{s.n}] {s.title}{s.year > 0 && ` (${s.year})`}</div>
                        <div style={{ fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '12px', color: 'var(--cue-ink-3)', margin: '3px 0' }}>"{s.quote}"</div>
                        <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-4)' }}>{s.url}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Footer */}
            <div style={{ marginTop: 'auto', borderTop: '1px solid #e5e0d4', paddingTop: '16px', display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              <span>Grounded in Thinkbox research · cue.advisor</span>
              <span>Page 1 of 1</span>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx jest HistoryDrawer.test ExportModal.test
```

Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): add HistoryDrawer and ExportModal overlays"
```

---

## Task 17: Full Test Run + Build Verification

**Files:**
- No new files — verification task

- [ ] **Step 1: Run full test suite**

```bash
cd frontend && npx jest --coverage
```

Expected: all tests pass. Coverage summary shows atoms, composer, thread, rail, overlays, lib all covered.

If any tests fail, fix them before proceeding.

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Run the dev server and verify visually**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`. Verify:
- App renders without white screen or console errors
- Empty state shows hero headline + 6 starter cards
- Corpus rail visible on the right (8 reports, stats)
- Clicking a starter card populates the composer and fires a query (check network tab for POST /api/query)
- Composer chips are clickable and update values

- [ ] **Step 4: Verify all 5 states**

To test each state, the backend must be running (`cd backend && uv run uvicorn app.main:app --reload --port 8000`):

| State | How to trigger |
|-------|---------------|
| Empty (A) | Fresh load |
| Streaming (B) | Submit any question |
| Answered (C) | Wait for response |
| Refusal (D) | Ask "Write me a poem" |
| Error (E) | Stop the backend, submit a question |

- [ ] **Step 5: Fix any visual regressions found in Step 3–4**

Compare against screenshots in `design_handoff_cue/reference/screenshots/`.

- [ ] **Step 6: Commit**

```bash
cd /home/vishal151/code/Vishal151/CODE-training/tv-invest-advisor
git add frontend/
git commit -m "feat(frontend): complete Cue frontend — all 5 states, overlays, rails wired"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] State A (Empty) — hero + starter cards + CorpusRail
- [x] State B (Streaming) — StreamingBubble with Trace + typewriter
- [x] State C (Answered) — AssistantBubble with all sub-components
- [x] State D (Refusal) — RefusalCard with examples
- [x] State E (Error) — ErrorCard with opaque reference, no backend details
- [x] Evidence rail (post-answer) with topic filter tabs
- [x] Corpus rail (pre-answer) with stats + document list
- [x] Composer — brief chips + textarea + Enter/Shift+Enter
- [x] Topbar — hamburger, brand, export button
- [x] History drawer — thread list + new thread
- [x] Export modal — A4 preview + print styles
- [x] Citation ↔ evidence linking via `activeCitation` store field
- [x] Rail collapse toggle
- [x] Cache badge on cached responses
- [x] Design tokens (CSS custom properties)
- [x] Google Fonts (Newsreader, IBM Plex Sans, IBM Plex Mono)

**Do-not list compliance:**
- No reference/ JSX copied into codebase
- No raw backend errors surfaced to UI (ErrorCard uses opaque reference)
- No generic loading spinner (Trace component used instead)
- Cache badge present
- Citations inline (not block elements)
- No mobile responsive work
- No invented colors or font sizes beyond token set

**Open items for future work (not in scope):**
- Backend structured Answer shape (headline/callout/chart from API)
- SSE streaming (typewriter simulation used for now)
- Share links / thread persistence
- Server-rendered PDF (window.print() used for now)
- Auth / multi-user
