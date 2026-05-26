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

export type Phase = 'idle' | 'thinking' | 'loading' | 'answered'

export type QueryResult =
  | { kind: 'answer';  answer: Answer }
  | { kind: 'refusal'; message: string; examples: string[] }
  | { kind: 'error';   title: string;   message: string; reference: string }
