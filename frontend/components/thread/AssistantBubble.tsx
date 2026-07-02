'use client'

import { Fragment } from 'react'
import type { Answer } from '@/lib/types'
import { StatPill } from '@/components/atoms/StatPill'
import { ProseWithCites } from '@/components/atoms/ProseWithCites'
import { Callout } from '@/components/atoms/Callout'
import { Chart } from '@/components/atoms/Chart'
import { Followups } from '@/components/atoms/Followups'
import { CacheBadge } from '@/components/atoms/CacheBadge'
import { useStore } from '@/lib/store'

type Props = {
  answer:     Answer
  time:       string
  isLast:     boolean
  onFollowup: (q: string) => void
}

export function AssistantBubble({ answer, time, isLast, onFollowup }: Props) {
  const setActiveCitation = useStore((s) => s.setActiveCitation)

  // The evidence rail always shows the LAST answer's sources, so only the last
  // bubble's citations may drive its highlight — an older answer's [2] refers
  // to a different source list.
  function handleCiteClick(n: number) {
    setActiveCitation(n)
    const { railCollapsed, toggleRail } = useStore.getState()
    if (railCollapsed) toggleRail()
  }

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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {answer.summary.map((para, i) => (
            <Fragment key={i}>
              <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '16.5px', lineHeight: 1.55, color: 'var(--cue-ink-2)' }}>
                <ProseWithCites
                  text={para}
                  onCiteClick={isLast ? handleCiteClick : undefined}
                  onCiteHover={isLast ? (n) => setActiveCitation(n) : undefined}
                  onCiteLeave={isLast ? () => setActiveCitation(null) : undefined}
                />
              </p>
              {answer.stats[i] && <StatPill stat={answer.stats[i]} />}
            </Fragment>
          ))}
          {answer.chart && <Chart chart={answer.chart} />}
        </div>

        {answer.checklist && answer.checklist.length > 0 && (
          <div style={{ borderTop: '1px solid var(--cue-rule)', paddingTop: '14px' }}>
            <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--cue-ink-3)', marginBottom: '10px' }}>
              Key considerations
            </div>
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {answer.checklist.map((item, i) => (
                <li key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                  <span style={{ color: 'var(--cue-accent)', fontFamily: 'var(--cue-mono)', fontSize: '11px', lineHeight: '1.6', flexShrink: 0 }}>✓</span>
                  <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '14.5px', color: 'var(--cue-ink-2)', lineHeight: 1.5 }}>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {answer.callout && (
          <Callout label={answer.callout.label} body={answer.callout.body} />
        )}

        <div style={{ display: 'flex', gap: '8px', paddingTop: '12px', borderTop: '1px dashed var(--cue-rule-2)' }}>
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(answer.summary.join('\n\n'))}
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
            Copy
          </button>
        </div>

        {isLast && <Followups items={answer.followups} onPick={onFollowup} />}
      </div>
    </div>
  )
}
