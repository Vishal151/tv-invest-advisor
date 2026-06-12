'use client'

import { useEffect, useState } from 'react'
import { fetchCorpus, type CorpusDoc } from '@/lib/api'

type Props = { collapsed: boolean; onToggle: () => void }

export function CorpusRail({ collapsed, onToggle }: Props) {
  const [docs, setDocs] = useState<CorpusDoc[]>([])

  useEffect(() => {
    fetchCorpus().then(setDocs)
  }, [])

  if (collapsed) {
    return (
      <div style={{ width: '56px', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '16px', gap: '12px' }}>
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>›</button>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
          Corpus
        </span>
      </div>
    )
  }

  const totalChunks = docs.reduce((sum, d) => sum + d.chunks, 0)
  const topics = new Set(docs.map((d) => d.topic)).size
  const stats = [
    { n: String(docs.length), label: 'Reports' },
    { n: String(totalChunks), label: 'Chunks' },
    { n: String(topics),      label: 'Topics' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px 10px', borderBottom: '1px solid var(--cue-rule)' }}>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', fontWeight: 500 }}>Corpus</span>
        <button type="button" onClick={onToggle} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}>‹</button>
      </div>

      {docs.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', padding: '12px', borderBottom: '1px solid var(--cue-rule-2)' }}>
          {stats.map((s) => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '24px', color: 'var(--cue-accent)', fontWeight: 500 }}>{s.n}</div>
              <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {docs.map((doc) => (
          <div
            key={doc.source_title}
            style={{ display: 'flex', gap: '10px', padding: '10px', borderRadius: '6px', border: '1px solid transparent' }}
          >
            <div style={{ width: '36px', minWidth: '36px', height: '44px', background: 'var(--cue-paper)', border: '1px solid var(--cue-rule)', borderTop: '3px solid var(--cue-accent)', borderRadius: '4px' }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '13px', fontWeight: 500, color: 'var(--cue-ink)', lineHeight: 1.3, marginBottom: '4px' }}>{doc.source_title}</div>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                {doc.topic && (
                  <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--cue-accent-ink)', background: 'var(--cue-accent-soft)', padding: '1px 5px', borderRadius: '3px' }}>{doc.topic}</span>
                )}
                <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', color: 'var(--cue-ink-4)' }}>{doc.chunks} chunks</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
