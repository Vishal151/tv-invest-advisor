'use client'

import { useStore } from '@/lib/store'
import type { Turn } from '@/lib/types'

export function ExportModal() {
  const { exportOpen, setExportOpen, thread } = useStore()

  if (!exportOpen) return null

  const answerTurns = thread.turns.filter((t): t is Extract<Turn, { role: 'assistant' | 'user' }> =>
    t.role === 'user' || t.role === 'assistant'
  )
  const brief = thread.brief

  return (
    <>
      <div
        style={{ position: 'fixed', inset: 0, background: 'rgb(0 0 0 / 0.80)', zIndex: 200, backdropFilter: 'blur(4px)' }}
        onClick={() => setExportOpen(false)}
      />

      <div
        style={{
          position:      'fixed',
          inset:         0,
          zIndex:        201,
          display:       'flex',
          flexDirection: 'column',
          overflow:      'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid rgb(255 255 255 / 0.15)' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgb(255 255 255 / 0.7)' }}>
            Export Preview · A4 · PDF
          </span>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => window.print()}
              style={{ padding: '6px 14px', borderRadius: '6px', border: 'none', background: 'var(--cue-accent)', color: 'white', fontFamily: 'var(--cue-sans)', fontSize: '12px', cursor: 'pointer' }}
            >
              Download PDF
            </button>
            <button
              type="button"
              aria-label="Close"
              onClick={() => setExportOpen(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgb(255 255 255 / 0.7)', fontSize: '18px', padding: '4px 8px' }}
            >
              ✕
            </button>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '32px 24px 64px' }}>
          <div
            className="cue-export-sheet"
            style={{
              width:         '680px',
              minHeight:     '962px',
              background:    'white',
              borderRadius:  '4px',
              boxShadow:     '0 24px 64px rgb(0 0 0 / 0.20)',
              padding:       '56px 64px',
              display:       'flex',
              flexDirection: 'column',
              gap:           '24px',
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e5e0d4', paddingBottom: '20px' }}>
              <div>
                <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '20px', fontWeight: 500, color: 'var(--cue-ink)' }}>Cue</div>
                <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--cue-ink-3)' }}>TV Investment Advisor</div>
              </div>
              <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)' }}>
                {new Date().toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' })}
              </div>
            </div>

            {/* Brief */}
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', fontFamily: 'var(--cue-mono)' }}>
              <tbody>
                {[
                  ['Sector',      brief.sector],
                  ['Stage',       brief.brandStage],
                  ['TV History',  brief.tvHistory],
                  ['Goal',        brief.primaryGoal],
                  ['Budget',      brief.budgetTier],
                ].map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #ebe5d8' }}>
                    <td style={{ padding: '5px 0', color: 'var(--cue-ink-3)', textTransform: 'uppercase', letterSpacing: '0.06em', width: '120px' }}>{k}</td>
                    <td style={{ padding: '5px 0', color: 'var(--cue-ink)', fontWeight: 500 }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* All Q&A turns */}
            {answerTurns.map((turn, i) => {
              if (turn.role === 'user') {
                return (
                  <h2 key={i} style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '22px', fontWeight: 500, color: 'var(--cue-ink)', lineHeight: 1.2, borderTop: i > 0 ? '1px solid #e5e0d4' : undefined, paddingTop: i > 0 ? '20px' : undefined }}>
                    {turn.question}
                  </h2>
                )
              }
              if (turn.role === 'assistant') {
                const { answer } = turn
                return (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {answer.stats.length > 0 && (
                      <div>
                        <span style={{ fontSize: '32px', fontWeight: 700, fontFamily: 'var(--cue-serif)', color: 'var(--cue-accent)' }}>
                          {answer.stats[0].value}
                        </span>
                        {' '}
                        <span style={{ fontSize: '14px', color: 'var(--cue-ink-2)' }}>
                          {answer.stats[0].unit}
                        </span>
                      </div>
                    )}
                    {answer.summary.map((p, pi) => (
                      <p key={pi} style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontSize: '14px', lineHeight: 1.6, color: 'var(--cue-ink-2)' }}>{p}</p>
                    ))}
                    {'checklist' in answer && Array.isArray((answer as { checklist?: string[] }).checklist) && (answer as { checklist?: string[] }).checklist!.length > 0 && (
                      <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {(answer as { checklist?: string[] }).checklist!.map((item, ci) => (
                          <li key={ci} style={{ fontFamily: 'var(--cue-serif)', fontSize: '13px', color: 'var(--cue-ink-2)', lineHeight: 1.5 }}>{item}</li>
                        ))}
                      </ul>
                    )}
                    {answer.sources.length > 0 && (
                      <div>
                        <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', marginBottom: '8px', borderTop: '1px solid #e5e0d4', paddingTop: '12px' }}>
                          Sources
                        </div>
                        {answer.sources.map((s) => (
                          <div key={s.n} style={{ marginBottom: '10px' }}>
                            <div style={{ fontFamily: 'var(--cue-serif)', fontSize: '13px', fontWeight: 500 }}>[{s.n}] {s.title}{s.page > 0 ? ` · p.${s.page}` : ''}</div>
                            <div style={{ fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '12px', color: 'var(--cue-ink-3)', margin: '3px 0' }}>"{s.quote}"</div>
                            <div style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-4)' }}>{s.url}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              }
              return null
            })}

            <div style={{ marginTop: 'auto', borderTop: '1px solid #e5e0d4', paddingTop: '16px', display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              <span>Grounded in Thinkbox research · cue.advisor</span>
              <span>Generated {new Date().toLocaleDateString('en-GB')}</span>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
