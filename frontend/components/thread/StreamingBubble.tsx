'use client'

import { Trace } from '@/components/atoms/Trace'

type Props = {
  traceSteps:   string[]
  streamedText: string
  done:         boolean
}

const DEFAULT_TRACE_STEPS = [
  'Parsing brief',
  'Filtering corpus by topic',
  'Retrieving relevant chunks…',
  'Grounding answer in sources',
  'Verifying citations',
]

export function StreamingBubble({ traceSteps = DEFAULT_TRACE_STEPS, streamedText, done }: Props) {
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
          padding:       '22px 24px',
          display:       'flex',
          flexDirection: 'column',
          gap:           '16px',
        }}
      >
        <Trace steps={traceSteps} />

        {streamedText && (
          <p
            style={{
              margin:     0,
              fontFamily: 'var(--cue-serif)',
              fontSize:   '16.5px',
              lineHeight: 1.55,
              color:      'var(--cue-ink-2)',
            }}
          >
            {streamedText}
            {!done && (
              <span
                style={{
                  display:       'inline-block',
                  width:         '2px',
                  height:        '1em',
                  background:    'var(--cue-accent)',
                  marginLeft:    '2px',
                  verticalAlign: 'text-bottom',
                }}
              />
            )}
          </p>
        )}
      </div>
    </div>
  )
}
