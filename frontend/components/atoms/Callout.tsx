'use client'

type Props = { label: string; body: string }

export function Callout({ label, body }: Props) {
  return (
    <div
      style={{
        background:   'var(--cue-paper-2)',
        border:       '1px solid var(--cue-rule)',
        borderLeft:   '3px solid var(--cue-accent)',
        borderRadius: '6px',
        padding:      '16px 18px',
      }}
    >
      <div
        style={{
          fontFamily:    'var(--cue-mono)',
          fontSize:      '10.5px',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color:         'var(--cue-accent-ink)',
          marginBottom:  '8px',
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'var(--cue-serif)',
          fontSize:   '16px',
          lineHeight: 1.55,
          color:      'var(--cue-ink-2)',
        }}
      >
        {body}
      </div>
    </div>
  )
}
