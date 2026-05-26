'use client'

import type { Answer } from '@/lib/types'
import { Headline } from '@/components/atoms/Headline'
import { ProseWithCites } from '@/components/atoms/ProseWithCites'
import { Callout } from '@/components/atoms/Callout'
import { Chart } from '@/components/atoms/Chart'
import { Followups } from '@/components/atoms/Followups'
import { CacheBadge } from '@/components/atoms/CacheBadge'
import { useStore } from '@/lib/store'

type Props = {
  answer:     Answer
  time:       string
  onFollowup: (q: string) => void
}

export function AssistantBubble({ answer, time, onFollowup }: Props) {
  const setActiveCitation = useStore((s) => s.setActiveCitation)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        <span style={{ fontWeight: 600, color: 'var(--cue-accent-ink)' }}>Cue</span>
        <span>· {time}</span>
        <span>· {answer.meta.model}</span>
        <span>· {answer.meta.chunksUsed} sources</span>
        {answer.meta.cached && <CacheBadge />}
      </div>

      <div
        style={{
          maxWidth:     '760px',
          width:        '100%',
          background:   'var(--cue-paper)',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '4px 14px 14px 14px',
          padding:      '22px 24px',
          display:      'flex',
          flexDirection:'column',
          gap:          '16px',
        }}
      >
        {answer.headline && (
          <Headline stat={answer.headline.stat} unit={answer.headline.unit} caption={answer.headline.caption} />
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {answer.summary.map((para, i) => (
            <p
              key={i}
              style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '16.5px', lineHeight: 1.55, color: 'var(--cue-ink-2)' }}
            >
              <ProseWithCites
                text={para}
                onCiteClick={(n) => setActiveCitation(n)}
                onCiteHover={(n) => setActiveCitation(n)}
                onCiteLeave={() => setActiveCitation(null)}
              />
            </p>
          ))}
        </div>

        {answer.callout && (
          <Callout label={answer.callout.label} body={answer.callout.body} />
        )}

        {answer.chart && <Chart chart={answer.chart} />}

        <div style={{ display: 'flex', gap: '8px', paddingTop: '12px', borderTop: '1px dashed var(--cue-rule-2)' }}>
          {['Copy', 'Regenerate'].map((label) => (
            <button
              key={label}
              type="button"
              style={{
                padding:      '6px 12px',
                border:       '1px solid var(--cue-rule)',
                borderRadius: '6px',
                background:   'transparent',
                cursor:       'pointer',
                fontFamily:   'var(--cue-mono)',
                fontSize:     '10.5px',
                color:        'var(--cue-ink-3)',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <Followups items={answer.followups} onPick={onFollowup} />
      </div>
    </div>
  )
}
