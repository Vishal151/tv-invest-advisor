'use client'

import { SourceCard } from '@/components/atoms/SourceCard'
import { useStore } from '@/lib/store'
import type { Source } from '@/lib/types'

type Props = {
  sources:   Source[]
  collapsed: boolean
  onToggle:  () => void
}

export function EvidenceRail({ sources, collapsed, onToggle }: Props) {
  const { activeCitation, setActiveSource, activeSource } = useStore()

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

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {sources.map((src) => (
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
