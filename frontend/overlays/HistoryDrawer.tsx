'use client'

import { useStore } from '@/lib/store'

export function HistoryDrawer() {
  const { historyOpen, setHistoryOpen, threads, thread, openThread, newThread } = useStore()

  if (!historyOpen) return null

  return (
    <>
      <div
        style={{ position: 'fixed', inset: 0, background: 'rgb(0 0 0 / 0.35)', zIndex: 100, backdropFilter: 'blur(2px)' }}
        onClick={() => setHistoryOpen(false)}
      />

      <div
        style={{
          position:      'fixed',
          top:           0,
          left:          0,
          bottom:        0,
          width:         '320px',
          background:    'var(--cue-paper)',
          borderRight:   '1px solid var(--cue-rule)',
          zIndex:        101,
          display:       'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--cue-rule)' }}>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--cue-ink-3)', fontWeight: 600 }}>
            Threads
          </span>
          <button
            type="button"
            aria-label="Close"
            onClick={() => setHistoryOpen(false)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '16px' }}
          >
            ✕
          </button>
        </div>

        <button
          type="button"
          onClick={() => { newThread(); setHistoryOpen(false) }}
          style={{
            display:      'flex',
            alignItems:   'center',
            gap:          '8px',
            padding:      '14px 20px',
            border:       'none',
            borderBottom: '1px solid var(--cue-rule-2)',
            background:   'transparent',
            cursor:       'pointer',
            fontFamily:   'var(--cue-sans)',
            fontSize:     '13px',
            color:        'var(--cue-accent)',
            textAlign:    'left',
          }}
        >
          + New thread
        </button>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {threads.filter((t) => t.id !== thread.id).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => openThread(t.id)}
              style={{
                display:       'flex',
                flexDirection: 'column',
                gap:           '4px',
                width:         '100%',
                padding:       '12px 20px',
                border:        'none',
                borderBottom:  '1px solid var(--cue-rule-2)',
                background:    t.id === thread.id ? 'var(--cue-accent-soft)' : 'transparent',
                cursor:        'pointer',
                textAlign:     'left',
              }}
            >
              <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '13.5px', color: 'var(--cue-ink)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '260px' }}>
                {t.title}
              </span>
              <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', color: 'var(--cue-ink-3)' }}>
                {t.turns.length} turns
              </span>
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
