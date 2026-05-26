# Cue — Frontend

Next.js 16 frontend for the Cue TV Investment Advisor. Builds to a static export served by the FastAPI backend.

## Stack

- **Next.js 16** — App Router, static export (`output: 'export'`)
- **React 19** — client components with `'use client'`
- **TypeScript** — strict mode
- **Tailwind CSS v4** — design tokens via CSS custom properties (oklch)
- **Zustand v5** — global app state (turns, brief, phase)
- **Jest 29 + React Testing Library 16** — 62 tests

## Development

```bash
npm install
npm run dev        # http://localhost:3000
npm test           # run all tests
npm run build      # static export → out/
npm run lint       # eslint
```

## Environment

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In production the frontend is served from the same origin as the API, so relative URLs are used automatically when `NEXT_PUBLIC_API_URL` is unset.

## Structure

```
frontend/
├── app/
│   ├── layout.tsx        # Root layout — Google Fonts, metadata
│   ├── page.tsx          # Entry point — renders <CueApp />
│   └── globals.css       # Cue design tokens + Tailwind import
├── components/
│   ├── atoms/            # Headline, Citation, Chart, Trace, SourceCard …
│   ├── composer/         # Chip (brief selector), Composer (input bar)
│   ├── thread/           # UserBubble, AssistantBubble, RefusalCard, ErrorCard
│   ├── rail/             # EvidenceRail, CorpusRail
│   └── layout/           # Topbar, EmptyState, CueApp (app shell)
├── overlays/             # HistoryDrawer, ExportModal
├── lib/
│   ├── types.ts          # Brief, Answer, Turn, QueryResult types
│   ├── api.ts            # queryApi() — maps backend response to UI types
│   └── store.ts          # Zustand store — turns, brief, phase, overlays
└── __tests__/            # Mirrors component structure
```

## Design Tokens

All colours are defined as CSS custom properties in `app/globals.css` using the oklch colour space:

| Token | Usage |
|-------|-------|
| `--cue-paper` / `--cue-paper-2/3` | Background surfaces |
| `--cue-ink` / `--cue-ink-2/3/4` | Text hierarchy |
| `--cue-accent` / `--cue-accent-soft` | Primary interactive colour (terracotta) |
| `--cue-success` / `--cue-warn` / `--cue-danger` | Status colours |
| `--cue-serif` / `--cue-sans` / `--cue-mono` | Font stacks |

## Build for Production

```bash
npm run build
```

Outputs to `out/`. The FastAPI backend serves this directory as static files. The Docker Compose setup handles this automatically.
