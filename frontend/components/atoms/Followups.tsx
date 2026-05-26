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
