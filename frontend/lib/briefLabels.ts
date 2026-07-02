import type { Brief } from './types'

/** Human-readable labels for every brief enum value — the single source shared
 *  by the composer chips, user bubbles, empty-state kicker and PDF export. */
export const BRIEF_VALUE_LABELS: { [K in keyof Brief]: Record<Brief[K], string> } = {
  sector: {
    FMCG: 'FMCG', Retail: 'Retail', Finance: 'Finance', Auto: 'Auto',
    Telco: 'Telco', Travel: 'Travel', DTC: 'DTC', Other: 'Other',
  },
  brandStage: {
    'start-up': 'Start-up', 'scale-up': 'Scale-up',
    established: 'Established', large: 'Large',
  },
  tvHistory: {
    never: 'Never run TV', tried: 'Tried once or twice', regular: 'Regular advertiser',
  },
  primaryGoal: {
    sales: 'Short-term sales', brand: 'Brand building', both: 'Both', unsure: 'Unsure',
  },
  budgetTier: {
    'under-100k': 'Under £100k', '100k-500k': '£100k–£500k',
    '500k-2m': '£500k–£2m', '2m-plus': '£2m+', undecided: 'Undecided',
  },
}

export function briefLabel<K extends keyof Brief>(key: K, value: Brief[K]): string {
  return BRIEF_VALUE_LABELS[key][value] ?? value
}
