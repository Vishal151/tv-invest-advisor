'use client'

type Props = {
  title:     string
  message:   string
  reference: string
  retryable: boolean
  onRetry:   () => void
  time:      string
}

export function ErrorCard({ title, message, reference, retryable, onRetry, time }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span> · {time}
      </div>
      <div
        style={{
          maxWidth:      '760px',
          border:        '1px solid var(--cue-rule)',
          borderLeft:    '3px solid var(--cue-warn)',
          borderRadius:  '4px 14px 14px 14px',
          background:    'var(--cue-warn-soft)',
          padding:       '18px 20px',
          display:       'flex',
          flexDirection: 'column',
          gap:           '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--cue-warn)', fontSize: '16px', fontWeight: 700 }}>!</span>
          <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '15px', fontWeight: 500, color: 'var(--cue-ink)' }}>{title}</span>
        </div>
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '15px', color: 'var(--cue-ink-2)', lineHeight: 1.5 }}>
          {message}
        </p>
        <div style={{ display: 'flex', gap: '8px' }}>
          {retryable && (
            <button
              type="button"
              onClick={onRetry}
              aria-label="Retry"
              style={{
                padding:      '8px 16px',
                borderRadius: '6px',
                border:       'none',
                background:   'var(--cue-accent)',
                color:        'var(--cue-paper)',
                fontFamily:   'var(--cue-sans)',
                fontSize:     '13px',
                fontWeight:   500,
                cursor:       'pointer',
              }}
            >
              Retry
            </button>
          )}
          <button
            type="button"
            style={{
              padding:      '8px 16px',
              borderRadius: '6px',
              border:       '1px solid var(--cue-rule)',
              background:   'transparent',
              fontFamily:   'var(--cue-sans)',
              fontSize:     '13px',
              color:        'var(--cue-ink-2)',
              cursor:       'pointer',
            }}
          >
            Rephrase
          </button>
        </div>
        <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-4)', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>Reference</span>
          <span>{reference}</span>
          <span style={{ color: 'var(--cue-ink-3)' }}>— Share with support if the problem persists.</span>
        </div>
      </div>
    </div>
  )
}
