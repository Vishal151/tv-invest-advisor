'use client'

const STARTERS = [
  { topic: 'ROI',          q: 'When does linear TV deliver its best ROI for a scale-up FMCG brand?' },
  { topic: 'Planning',     q: 'How should I split spend between linear TV and BVOD?' },
  { topic: 'Effectiveness',q: 'What does Peter Field say about attention and trust on TV vs. social?' },
  { topic: 'Small biz',    q: 'Is £250k enough to make TV pay back inside a year?' },
  { topic: 'Creative',     q: 'How long should a launch campaign run before I judge it?' },
  { topic: 'Viewing',      q: 'How much of 16–34 viewing is BVOD now, and where is it going?' },
]

type Props = { onPickStarter: (q: string) => void }

export function EmptyState({ onPickStarter }: Props) {
  return (
    <div style={{ padding: '40px 0', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10.5px', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--cue-accent-ink)' }}>
          For FMCG · Scale-up · £500K–£2M
        </span>
        <h1
          style={{
            margin:       0,
            fontFamily:   'var(--cue-serif)',
            fontSize:     '44px',
            lineHeight:   1.1,
            fontWeight:   500,
            letterSpacing:'-0.025em',
            color:        'var(--cue-ink)',
          }}
        >
          Evidence-backed TV investment advice,{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--cue-accent)' }}>24/7.</em>
        </h1>
        <p style={{ margin: 0, fontFamily: 'var(--cue-serif)', fontStyle: 'italic', fontSize: '17px', lineHeight: 1.45, color: 'var(--cue-ink-3)', maxWidth: '520px' }}>
          Ask Cue anything about TV advertising investment. Every answer is grounded in published Thinkbox research — no hallucinations, full citations.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        {STARTERS.map((s) => (
          <button
            key={s.q}
            type="button"
            onClick={() => onPickStarter(s.q)}
            style={{
              textAlign:     'left',
              padding:       '14px 16px',
              border:        '1px solid var(--cue-rule)',
              borderRadius:  '8px',
              background:    'var(--cue-paper)',
              cursor:        'pointer',
              display:       'flex',
              flexDirection: 'column',
              gap:           '6px',
              transition:    'border-color 120ms',
            }}
          >
            <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-accent-ink)' }}>
              {s.topic}
            </span>
            <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '13.5px', color: 'var(--cue-ink-2)', lineHeight: 1.35 }}>
              {s.q}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
