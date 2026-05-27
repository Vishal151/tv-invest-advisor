# Rich Response Design — Spec

## Goal

Upgrade the Cue response display from plain prose paragraphs to an editorial layout where key statistics surface as inline stat pills, comparison charts appear when the data warrants it, source cards show page and topic provenance, and the app chrome carries a subtle broadcast-signal identity. The backend drives this by returning structured JSON; the frontend renders it.

## Architecture

The LLM is prompted to return a JSON object instead of a prose string. The frontend parses the JSON and renders rich components. If parsing fails (e.g. the fallback model ignores the schema), the raw text is wrapped in a single-paragraph fallback. Guardrails continue to operate on the joined prose text.

**Tech stack additions:** none — all changes are to existing files plus one new atom (`StatPill`).

---

## Backend changes

### 1. `generate()` returns structured JSON

**File:** `backend/app/services/generator.py`

The system prompt is updated to instruct the LLM to return a JSON object with this exact schema:

```json
{
  "summary": ["paragraph 1", "paragraph 2"],
  "stats": [
    {
      "value": "£5.61",
      "unit": "ROI per £1 spent",
      "context": "Average across 141 brands and 14 categories",
      "source": "Profit Ability 2",
      "page": 12
    }
  ],
  "chart": {
    "title": "Average ROI per £1 · by channel",
    "source": "Profit Ability 2",
    "unit": "£",
    "bars": [
      { "label": "TV",      "value": 5.61, "highlight": true },
      { "label": "Digital", "value": 3.21 },
      { "label": "Press",   "value": 2.84 },
      { "label": "Radio",   "value": 1.61 }
    ]
  },
  "followups": [
    "How does this change for a DTC brand?",
    "What is the minimum budget to see TV ROI?"
  ]
}
```

**Schema rules for the prompt:**
- `summary`: 2–4 paragraphs of prose. Citation superscripts `[1]`, `[2]` etc. may appear inline.
- `stats`: 1–3 key statistics found verbatim in the research context. Order them to match their first mention in `summary` (stat[0] surfaces after summary[0], stat[1] after summary[1], etc.). Omit if no concrete statistics are available.
- `chart`: include **only** when the answer compares 2+ values across channels, time periods, or categories. Omit (null) for qualitative answers. Bar values must come from the research context — never invented.
- `followups`: 2–3 short follow-up questions a planner might naturally ask next. Omit if none are relevant.

`acompletion` is called with `response_format={"type": "json_object"}` for the GPT-4o call. The Claude fallback relies on the prompt alone (Anthropic's API ignores `response_format`; the prompt is sufficient).

`generate()` signature changes from returning `(str, str)` to `(dict, str)`, where the dict is the parsed JSON. If JSON parsing fails, it returns a fallback dict: `{"summary": [raw_text], "stats": [], "chart": None, "followups": []}`.

### 2. Routes wire-up

**File:** `backend/app/api/routes.py`

- `_answer_contains_statistic()` receives `"\n\n".join(answer["summary"])` (joined prose) instead of the raw string.
- `cache.set()` stores the structured dict as before.
- `QueryResponse.answer` changes from `str` to a new Pydantic model `StructuredAnswer`.

**New Pydantic models in `routes.py`:**

```python
class AnswerStat(BaseModel):
    value: str
    unit: str
    context: str
    source: str
    page: int = 0

class AnswerChart(BaseModel):
    title: str
    source: str
    unit: str
    bars: list[dict]  # {label: str, value: float, highlight?: bool}

class StructuredAnswer(BaseModel):
    summary: list[str]
    stats: list[AnswerStat] = []
    chart: AnswerChart | None = None
    followups: list[str] = []

class QueryResponse(BaseModel):
    answer: StructuredAnswer   # changed from str
    sources: list[Source]
    cached: bool
    model_used: str
```

The `Source` response model already has `page`, `topic`, `distance` fields — these were added in the previous session but `api.ts` was not updated to read them. No backend change needed here.

---

## Frontend changes

### 3. `lib/types.ts` — add `Stat` type, update `Answer`

```typescript
export type Stat = {
  value:   string   // e.g. "£5.61"
  unit:    string   // e.g. "ROI per £1 spent"
  context: string   // e.g. "Average across 141 brands"
  source:  string   // document name
  page:    number   // 0 means unknown
}
```

`Answer` changes:
- Remove `headline: Headline | null`
- Add `stats: Stat[]`

```typescript
export type Answer = {
  stats:     Stat[]          // replaces headline
  summary:   string[]
  callout:   Callout | null  // kept but will be null for now
  chart:     Chart | null
  sources:   Source[]
  followups: string[]
  meta: { model: string; cached: boolean; retrievalMs: number; generationMs: number; chunksUsed: number }
}
```

### 4. `lib/api.ts` — parse structured response, wire source metadata

`RawResponse` changes to match the new backend shape:

```typescript
type RawStat = { value: string; unit: string; context: string; source: string; page: number }
type RawChart = { title: string; source: string; unit: string; bars: { label: string; value: number; highlight?: boolean }[] }
type RawStructuredAnswer = { summary: string[]; stats: RawStat[]; chart: RawChart | null; followups: string[] }
type RawSource = { title: string; chunk: string; url: string; page: number; topic: string; distance: number }
type RawResponse = { answer: RawStructuredAnswer; sources: RawSource[]; cached: boolean; model_used: string }
```

`mapResponse` maps directly:
- `stats` → `Answer.stats` (1:1 mapping)
- `chart` → `Answer.chart` (already matching shape)
- `followups` → `Answer.followups`
- Sources: `page`, `topic`, `score` are now read from `RawSource` instead of hardcoded to `0`/`''`

### 5. New atom: `components/atoms/StatPill.tsx`

Renders a single stat as an inline pill card woven between prose paragraphs.

```
┌──────────────────────────────────────────────────────┐
│  £5.61  │  ROI per £1 spent                          │
│         │  Average across 141 brands and 14 categories│
│         │  PROFIT ABILITY 2 · P.12                    │
└──────────────────────────────────────────────────────┘
```

Props: `{ stat: Stat }`. No onClick or interactivity needed.

Styled using existing CSS vars: `--cue-paper-2`, `--cue-rule`, `--cue-serif`, `--cue-accent`, `--cue-ink-2`, `--cue-ink-3`, `--cue-mono`.

### 6. `components/thread/AssistantBubble.tsx` — interweave stats and chart

Replace the headline block and plain summary map with an interleaved render:

```
summary[0]
stats[0]  ← if exists
summary[1]
stats[1]  ← if exists
summary[2]
...remaining paragraphs (no pill)
chart     ← if present, after last paragraph
```

Remove the `import { Headline }` and its JSX block. Add `import { StatPill }`.

### 7. `components/atoms/SourceCard.tsx` — render topic tag and page badge

Currently renders `year · p.N` only when `year > 0 || page > 0`. Change to:
- Render topic as a small pill/tag when `source.topic` is non-empty (e.g. `ROI`, `effectiveness`)
- Render `p.N` when `source.page > 0`
- Remove year display (year is always 0 from the API; remove the dead code)

Tag styling: small pill, `background: var(--cue-accent-soft)`, `color: var(--cue-accent-ink)`, `border-radius: 10px`, `font-size: 10px`, monospace.

### 8. `components/layout/Topbar.tsx` — signal bars icon

Replace the 8px dot with a `SignalBars` inline component (4 ascending SVG rectangles using `var(--cue-accent)`). Keep all other Topbar markup identical.

```
SVG: 4 bars, heights 4/7/10/14px, width 3px each, 1.5px gap, opacity 0.4→0.6→0.8→1.0
```

### 9. `components/thread/StreamingBubble.tsx` — broadcast rings loading

Replace `<Trace steps={...} />` with a pulsing broadcast animation: three concentric rings expanding outward, a solid dot at centre, and a text label cycling through the trace steps.

Animation: `@keyframes cue-ring-pulse` defined in `app/globals.css`:
```css
@keyframes cue-ring-pulse {
  0%   { transform: scale(0.6); opacity: 0.8; }
  100% { transform: scale(1.4); opacity: 0; }
}
.cue-ring { animation: cue-ring-pulse 2s ease-out infinite; }
.cue-ring-2 { animation-delay: 0.6s; }
.cue-ring-3 { animation-delay: 1.2s; }
```

The trace steps cycle automatically with a 1.2s interval (same logic as the existing Trace component but displayed as a single line below the rings rather than a list).

---

## Data flow summary

```
POST /api/query
  → backend generate() calls LLM with JSON schema prompt
  → LLM returns JSON: { summary, stats, chart, followups }
  → parse JSON, fall back to prose-only if invalid
  → routes.py wraps in QueryResponse { answer: StructuredAnswer, sources, cached, model_used }
  → sources include page, topic, distance from ChromaDB metadata

api.ts mapResponse()
  → stats → Answer.stats
  → chart → Answer.chart  
  → followups → Answer.followups
  → sources[].page, .topic, .score wired from raw response

AssistantBubble renders:
  paragraph → StatPill (if stats[i] exists) → paragraph → StatPill → ... → Chart → sources
```

---

## What is NOT in scope

- Follow-up question auto-submission (Followups component already handles clicks; no change needed)
- `callout` field (kept in type, always null for now)
- Export modal PDF layout (print styles not changed)
- Streaming / SSE (not implemented; loading state remains request/response)
- The `thinking` and `answered` Phase values (defined but unused; no change)

---

## Testing

**Backend:**
- `test_generator.py`: mock `acompletion` to return valid JSON string; assert `generate()` returns parsed dict with expected keys
- `test_generator.py`: mock `acompletion` to return plain prose (no JSON); assert `generate()` returns fallback dict with `summary: [prose]`
- `test_routes.py`: update `generate` mock to return structured dict; assert `QueryResponse.answer` is a dict (not string)

**Frontend:**
- `api.test.ts`: mock fetch to return new `RawResponse` shape; assert `mapResponse` maps `stats`, `chart`, source `page`/`topic`/`score` correctly
- `StatPill.test.tsx`: render with a Stat fixture; assert value, unit, context, source+page all appear
- `AssistantBubble.test.tsx`: render with 2 paragraphs + 1 stat; assert stat pill appears between para 0 and para 1
- `SourceCard.test.tsx`: render with `topic="ROI"` and `page=12`; assert topic tag and page badge appear
