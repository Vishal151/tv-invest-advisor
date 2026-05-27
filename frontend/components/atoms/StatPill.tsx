'use client'

import type { Stat } from '@/lib/types'

type Props = { stat: Stat }

export function StatPill({ stat }: Props) {
  return (
    <div
      style={{
        display:     'flex',
        alignItems:  'center',
        gap:         '12px',
        background:  'var(--cue-paper-2)',
        border:      '1px solid var(--cue-rule)',
        borderRadius:'6px',
        padding:     '10px 14px',
      }}
    >
      <span
        style={{
          fontFamily:  'var(--cue-serif)',
          fontSize:    '28px',
          fontWeight:  500,
          color:       'var(--cue-accent)',
          lineHeight:  1,
          whiteSpace:  'nowrap',
          flexShrink:  0,
        }}
      >
        {stat.value}
      </span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span
          style={{
            fontFamily: 'var(--cue-sans)',
            fontSize:   '13px',
            fontWeight: 500,
            color:      'var(--cue-ink-2)',
            lineHeight: 1.3,
          }}
        >
          {stat.unit}
        </span>
        <span
          style={{
            fontFamily: 'var(--cue-sans)',
            fontSize:   '12px',
            color:      'var(--cue-ink-3)',
            lineHeight: 1.4,
          }}
        >
          {stat.context}
        </span>
        <span
          style={{
            fontFamily:    'var(--cue-mono)',
            fontSize:      '10px',
            color:         'var(--cue-ink-4)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            marginTop:     '1px',
          }}
        >
          {stat.source}{stat.page > 0 ? ` · p.${stat.page}` : ''}
        </span>
      </div>
    </div>
  )
}
