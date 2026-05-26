'use client'

type Props = {
  steps:   string[]
  onDone?: () => void
}

export function Trace({ steps, onDone }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1
        return (
          <div
            key={i}
            className="cue-trace-line"
            style={{
              display:    'flex',
              alignItems: 'center',
              gap:        '8px',
              fontFamily: 'var(--cue-mono)',
              fontSize:   '11px',
              color:      isLast ? 'var(--cue-accent)' : 'var(--cue-ink-3)',
            }}
          >
            {isLast && (
              <span
                style={{
                  width:        '6px',
                  height:       '6px',
                  borderRadius: '50%',
                  background:   'var(--cue-accent)',
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
      `}</style>
    </div>
  )
}
