'use client'

type Props = {
  stat:    string
  unit:    string
  caption: string
  dense?:  boolean
}

export function Headline({ stat, unit, caption, dense = false }: Props) {
  return (
    <div
      className={`cue-headline flex items-start gap-4 rounded-r-md px-4 py-3 ${dense ? 'cue-headline--dense' : ''}`}
      style={{
        background:   'linear-gradient(to right, var(--cue-accent-soft), transparent)',
        borderLeft:   '3px solid var(--cue-accent)',
        borderRadius: '0 6px 6px 0',
      }}
    >
      <span
        style={{
          fontFamily: 'var(--cue-serif)',
          fontSize:   dense ? '40px' : '56px',
          lineHeight: 1,
          color:      'var(--cue-accent)',
          fontWeight: 500,
        }}
      >
        {stat}
      </span>
      <div className="flex flex-col justify-center pt-1">
        <span
          style={{
            fontFamily:  'var(--cue-sans)',
            fontSize:    '14px',
            fontWeight:  500,
            color:       'var(--cue-ink-2)',
            lineHeight:  1.2,
          }}
        >
          {unit}
        </span>
        <span
          style={{
            fontFamily:    'var(--cue-mono)',
            fontSize:      '10.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color:         'var(--cue-ink-3)',
            marginTop:     '4px',
          }}
        >
          {caption}
        </span>
      </div>
    </div>
  )
}
