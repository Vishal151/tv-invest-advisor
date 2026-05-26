'use client'

import type { Source } from '@/lib/types'

type Props = {
  source:     Source
  highlight?: boolean
  compact?:   boolean
}

export function SourceCard({ source, highlight = false, compact = false }: Props) {
  const thumbW = compact ? 48 : 64

  return (
    <div
      className={`cue-source ${highlight ? 'cue-source--highlight' : ''}`}
      style={{
        display:      'flex',
        gap:          '12px',
        padding:      '12px',
        border:       `1px solid ${highlight ? 'var(--cue-accent)' : 'var(--cue-rule)'}`,
        borderRadius: '6px',
        background:   highlight ? 'var(--cue-accent-soft)' : 'transparent',
        transition:   'border-color 120ms, background 120ms',
      }}
    >
      <div
        aria-hidden="true"
        style={{
          width:         `${thumbW}px`,
          minWidth:      `${thumbW}px`,
          height:        '48px',
          background:    'var(--cue-paper-3)',
          borderRadius:  '4px',
          display:       'flex',
          flexDirection: 'column',
          justifyContent:'flex-end',
          padding:       '6px 6px 4px',
          gap:           '3px',
        }}
      >
        {[70, 50, 85, 40].map((w, i) => (
          <div
            key={i}
            style={{
              height:       '3px',
              width:        `${w}%`,
              borderRadius: '2px',
              background:   i === 0 ? 'var(--cue-accent)' : 'var(--cue-ink-4)',
            }}
          />
        ))}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '4px' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-accent-ink)', fontWeight: 500 }}>
            [{source.n}]
          </span>
          <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '13.5px', fontWeight: 500, color: 'var(--cue-ink)', lineHeight: 1.25 }}>
            {source.title}
          </span>
        </div>
        {(source.year > 0 || source.page > 0) && (
          <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', color: 'var(--cue-ink-3)', marginBottom: '4px' }}>
            {source.year > 0 && `${source.year}`}{source.page > 0 && ` · p.${source.page}`}
          </div>
        )}
        <div style={{ fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '12.5px', color: 'var(--cue-ink-2)', lineHeight: 1.45, marginBottom: '6px' }}>
          "{source.quote}"
        </div>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textDecoration: 'none', wordBreak: 'break-all' }}
        >
          {source.url}
        </a>
      </div>
    </div>
  )
}
