'use client'

type Props = {
  n:        number
  onClick?: (n: number) => void
  onHover?: (n: number) => void
  onLeave?: () => void
}

export function Citation({ n, onClick, onHover, onLeave }: Props) {
  return (
    <sup
      role="button"
      tabIndex={0}
      onClick={() => onClick?.(n)}
      onMouseEnter={() => onHover?.(n)}
      onMouseLeave={() => onLeave?.()}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.(n)}
      style={{
        display:         'inline-flex',
        alignItems:      'center',
        justifyContent:  'center',
        minWidth:        '16px',
        height:          '16px',
        padding:         '0 4px',
        borderRadius:    '4px',
        background:      'var(--cue-accent-soft)',
        color:           'var(--cue-accent-ink)',
        fontFamily:      'var(--cue-mono)',
        fontSize:        '10px',
        fontWeight:      500,
        cursor:          'pointer',
        verticalAlign:   'super',
        lineHeight:      1,
        transition:      'background 120ms, color 120ms',
        userSelect:      'none',
      }}
    >
      {n}
    </sup>
  )
}
