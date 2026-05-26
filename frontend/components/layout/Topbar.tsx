'use client'

import { useStore } from '@/lib/store'

type Props = { threadTitle?: string }

export function Topbar({ threadTitle }: Props) {
  const { setHistoryOpen, setExportOpen } = useStore()

  return (
    <header
      style={{
        height:         '60px',
        display:        'flex',
        alignItems:     'center',
        padding:        '0 20px',
        gap:            '12px',
        background:     'var(--cue-paper)',
        borderBottom:   '1px solid var(--cue-rule)',
        position:       'sticky',
        top:            0,
        zIndex:         50,
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          type="button"
          aria-label="Open thread history"
          onClick={() => setHistoryOpen(true)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--cue-ink-3)', fontSize: '18px', padding: '4px' }}
        >
          ☰
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--cue-accent)', display: 'inline-block' }} />
          <span style={{ fontFamily: 'var(--cue-serif)', fontSize: '16px', fontWeight: 500, color: 'var(--cue-ink)' }}>Cue</span>
          <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--cue-ink-3)' }}>
            TV Investment Advisor
          </span>
        </div>
      </div>

      {threadTitle && (
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '11px', color: 'var(--cue-ink-3)', flex: 1, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '400px' }}>
          {threadTitle}
        </span>
      )}

      <button
        type="button"
        onClick={() => setExportOpen(true)}
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '4px',
          padding:      '6px 12px',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '6px',
          background:   'transparent',
          cursor:       'pointer',
          fontFamily:   'var(--cue-mono)',
          fontSize:     '10.5px',
          color:        'var(--cue-ink-3)',
          textTransform:'uppercase',
          letterSpacing:'0.06em',
        }}
      >
        ↓ Export
      </button>
    </header>
  )
}
