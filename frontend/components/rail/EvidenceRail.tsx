'use client'

import { useState } from 'react'
import { SourceCard } from '@/components/atoms/SourceCard'
import { useStore } from '@/lib/store'
import type { Source } from '@/lib/types'

const TOPICS = ['All', 'ROI', 'Planning', 'Effectiveness', 'Viewing', 'Small business']

type Props = {
  sources:   Source[]
  collapsed: boolean
  onToggle:  () => void
}

export function EvidenceRail({ sources, collapsed, onToggle }: Props) {
  const [activeTopic, setActiveTopic] = useState('All')
  const { activeCitation, setActiveSource, activeSource } = useStore()

  const filtered = activeTopic === 'All'
    ? sources
    : sources.filter((s) => s.topic === activeTopic)

  if (collapsed) {
    return (
      <div
        className="cue-rail--collapsed"
        style={{ width: '56px', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '16px', gap: '12px' }}
      >
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>›</button>
        <span
          style={{
            fontFamily:    'var(--cue-mono)',
            fontSize:      '10px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color:         'var(--cue-ink-3)',
            writingMode:   'vertical-rl',
            transform:     'rotate(180deg)',
          }}
        >
          Evidence
        </span>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px 10px', borderBottom: '1px solid var(--cue-rule)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', fontWeight: 500 }}>
            Evidence
          </span>
          <span style={{ background: 'var(--cue-accent-soft)', color: 'var(--cue-accent-ink)', fontFamily: 'var(--cue-mono)', fontSize: '10px', padding: '1px 6px', borderRadius: '999px' }}>
            {sources.length}
          </span>
        </div>
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>‹</button>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', padding: '10px 12px', borderBottom: '1px solid var(--cue-rule-2)' }}>
        {TOPICS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setActiveTopic(t)}
            style={{
              padding:       '3px 8px',
              borderRadius:  '999px',
              border:        '1px solid var(--cue-rule)',
              background:    activeTopic === t ? 'var(--cue-accent-soft)' : 'transparent',
              color:         activeTopic === t ? 'var(--cue-accent-ink)' : 'var(--cue-ink-3)',
              fontFamily:    'var(--cue-mono)',
              fontSize:      '9.5px',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              cursor:        'pointer',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filtered.map((src) => (
          <SourceCard
            key={src.n}
            source={src}
            highlight={activeCitation === src.n || activeSource === src.n}
            compact
          />
        ))}
      </div>
    </div>
  )
}
