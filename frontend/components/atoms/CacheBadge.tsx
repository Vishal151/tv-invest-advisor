'use client'

export function CacheBadge() {
  return (
    <span
      title="Returned from cache — identical brief + question answered within the last 7 days."
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        gap:            '4px',
        padding:        '2px 8px',
        borderRadius:   '999px',
        background:     'var(--cue-success-soft)',
        color:          'var(--cue-success-ink)',
        fontFamily:     'var(--cue-mono)',
        fontSize:       '10px',
        textTransform:  'uppercase',
        letterSpacing:  '0.06em',
      }}
    >
      <span
        style={{
          width:        '6px',
          height:       '6px',
          borderRadius: '50%',
          background:   'var(--cue-success)',
          display:      'inline-block',
        }}
      />
      cached
    </span>
  )
}
