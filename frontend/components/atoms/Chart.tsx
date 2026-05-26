'use client'

import { useEffect, useRef, useState } from 'react'
import type { Chart as ChartType } from '@/lib/types'

type Props = { chart: ChartType; dense?: boolean }

export function Chart({ chart, dense = false }: Props) {
  const maxValue = Math.max(...chart.bars.map((b) => b.value))
  const [mounted, setMounted] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50)
    return () => clearTimeout(t)
  }, [])

  return (
    <figure
      ref={ref}
      style={{
        margin:       0,
        border:       '1px solid var(--cue-rule)',
        borderRadius: '6px',
        overflow:     'hidden',
      }}
    >
      <div
        style={{
          display:        'flex',
          justifyContent: 'space-between',
          alignItems:     'center',
          padding:        '10px 14px 8px',
          borderBottom:   '1px solid var(--cue-rule-2)',
        }}
      >
        <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '14px', color: 'var(--cue-ink-2)' }}>
          {chart.title}
        </span>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {chart.source}
        </span>
      </div>

      <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {chart.bars.map((bar) => {
          const pct = (bar.value / maxValue) * 100
          return (
            <div
              key={bar.label}
              style={{ display: 'grid', gridTemplateColumns: '95px 1fr 52px', alignItems: 'center', gap: '10px' }}
            >
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', color: 'var(--cue-ink-3)', textAlign: 'right', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {bar.label}
              </span>
              <div style={{ height: '14px', borderRadius: '3px', background: 'var(--cue-paper-3)', overflow: 'hidden' }}>
                <div
                  style={{
                    height:     '100%',
                    borderRadius:'3px',
                    background: bar.highlight ? 'var(--cue-accent)' : 'var(--cue-slate)',
                    width:      mounted ? `${pct}%` : '0%',
                    transition: 'width 700ms cubic-bezier(0.4, 0, 0.2, 1)',
                  }}
                />
              </div>
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', color: bar.highlight ? 'var(--cue-accent-ink)' : 'var(--cue-ink-3)', fontWeight: bar.highlight ? 500 : 400 }}>
                {bar.value}
              </span>
            </div>
          )
        })}
      </div>
    </figure>
  )
}
