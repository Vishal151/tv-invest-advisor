'use client'

import { useState, useEffect } from 'react'

const DEFAULT_TRACE_STEPS = [
  'Parsing brief',
  'Filtering corpus',
  'Retrieving relevant chunks',
  'Grounding answer in sources',
  'Verifying citations',
]

type Props = {
  traceSteps?: string[]
}

export function StreamingBubble({ traceSteps = DEFAULT_TRACE_STEPS }: Props) {
  const [stepIdx, setStepIdx] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setStepIdx((i) => (i + 1) % traceSteps.length)
    }, 1200)
    return () => clearInterval(id)
  }, [traceSteps])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span>
        {' · thinking…'}
      </div>
      <div
        style={{
          maxWidth:      '760px',
          width:         '100%',
          background:    'var(--cue-paper)',
          border:        '1px solid var(--cue-rule)',
          borderRadius:  '4px 14px 14px 14px',
          padding:       '28px 24px',
          display:       'flex',
          flexDirection: 'column',
          alignItems:    'center',
          gap:           '16px',
        }}
      >
        <div style={{ position: 'relative', width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className={`cue-ring-${n}`}
              style={{
                position:    'absolute',
                width:       `${n * 16}px`,
                height:      `${n * 16}px`,
                border:      '1.5px solid var(--cue-accent)',
                borderRadius:'50%',
              }}
            />
          ))}
          <div style={{ width: '6px', height: '6px', background: 'var(--cue-accent)', borderRadius: '50%', position: 'relative', zIndex: 1 }} />
        </div>
        <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {traceSteps[stepIdx]}
        </div>
      </div>
    </div>
  )
}
