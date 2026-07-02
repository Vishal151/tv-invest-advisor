'use client'

import type { Brief } from '@/lib/types'
import { briefLabel } from '@/lib/briefLabels'

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
                <span style={{ fontFamily: 'var(--cue-sans)', fontWeight: 500 }}>{briefLabel(key, val as never)}</span>
              </span>
            ))}
          </div>
        )}
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '17px', lineHeight: 1.4 }}>
          {question}
        </p>
      </div>
    </div>
  )
}
