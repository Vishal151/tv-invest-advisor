'use client'

import { useRef, useState } from 'react'

type Option = { value: string; label: string }

type Props = {
  fieldKey: string
  value:    string
  options:  Option[]
  onChange: (v: string) => void
}

export function Chip({ fieldKey, value, options, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const currentLabel = options.find((o) => o.value === value)?.label ?? value

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          display:      'inline-flex',
          alignItems:   'center',
          gap:          '5px',
          padding:      '4px 8px',
          border:       '1px solid var(--cue-rule)',
          borderRadius: '999px',
          background:   'transparent',
          cursor:       'pointer',
          whiteSpace:   'nowrap',
        }}
      >
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--cue-ink-3)' }}>
          {fieldKey}
        </span>
        <span style={{ fontFamily: 'var(--cue-sans)', fontSize: '12px', fontWeight: 500, color: 'var(--cue-ink)' }}>
          {currentLabel}
        </span>
        <span style={{ color: 'var(--cue-ink-3)', fontSize: '10px' }}>▾</span>
      </button>

      {open && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 10 }} onClick={() => setOpen(false)} />
          <div
            style={{
              position:     'absolute',
              top:          'calc(100% + 4px)',
              left:         0,
              zIndex:       20,
              background:   'var(--cue-paper)',
              border:       '1px solid var(--cue-rule)',
              borderRadius: '8px',
              boxShadow:    '0 8px 28px rgb(0 0 0 / 0.18)',
              minWidth:     '160px',
              overflow:     'hidden',
            }}
          >
            {options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => { onChange(opt.value); setOpen(false) }}
                style={{
                  display:        'flex',
                  alignItems:     'center',
                  justifyContent: 'space-between',
                  width:          '100%',
                  padding:        '9px 12px',
                  border:         'none',
                  background:     opt.value === value ? 'var(--cue-accent-soft)' : 'transparent',
                  cursor:         'pointer',
                  fontFamily:     'var(--cue-sans)',
                  fontSize:       '13px',
                  color:          'var(--cue-ink)',
                  textAlign:      'left',
                }}
              >
                {opt.label}
                {opt.value === value && <span style={{ color: 'var(--cue-accent)', fontSize: '12px' }}>✓</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
