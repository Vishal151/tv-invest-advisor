import type { Brief, QueryResult } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

type RawStat = { value: string; unit: string; context: string; source: string; page: number }
type RawChartBar = { label: string; value: number; highlight?: boolean }
type RawChart = { title: string; source: string; unit: string; bars: RawChartBar[] }
type RawStructuredAnswer = { summary: string[]; stats: RawStat[]; chart: RawChart | null; followups: string[]; checklist: string[] | null }
type RawSource = { title: string; chunk: string; url: string; page: number; topic: string; distance: number }
type RawResponse = { answer: RawStructuredAnswer; sources: RawSource[]; cached: boolean; model_used: string }

function mapResponse(raw: RawResponse, generationMs: number): QueryResult {
  const { answer: a } = raw

  return {
    kind: 'answer',
    answer: {
      stats: (a.stats ?? []).map((s) => ({
        value:   s.value,
        unit:    s.unit,
        context: s.context,
        source:  s.source,
        page:    s.page ?? 0,
      })),
      summary:   a.summary ?? [],
      checklist: a.checklist?.length ? a.checklist : null,
      callout:   null,
      chart:     a.chart
        ? {
            title:  a.chart.title,
            source: a.chart.source,
            unit:   a.chart.unit,
            bars:   (a.chart.bars ?? []).map((b) => ({
              label:     b.label,
              value:     b.value,
              highlight: b.highlight ?? false,
            })),
          }
        : null,
      followups: a.followups ?? [],
      sources: raw.sources.map((s, i) => ({
        n:     i + 1,
        title: s.title,
        year:  0,
        page:  s.page ?? 0,
        url:   s.url,
        quote: s.chunk,
        topic: s.topic ?? '',
        score: s.distance,
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
