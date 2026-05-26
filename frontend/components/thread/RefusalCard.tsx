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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} aria-label="Off-topic for this advisor">
          <span aria-hidden="true" style={{ color: 'var(--cue-danger)', fontSize: '16px', fontWeight: 700 }}>⨯</span>
          <span aria-hidden="true" style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-danger-ink)', fontWeight: 600 }}>
            Out of scope
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
                <span aria-hidden="true">↳</span> {ex}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
