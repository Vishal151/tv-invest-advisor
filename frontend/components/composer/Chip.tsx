'use client'

import { useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

type Option = { value: string; label: string }

type Props = {
  fieldKey: string
  value:    string
  options:  Option[]
  onChange: (v: string) => void
}

const MENU_MAX_HEIGHT = 240
const MENU_GAP = 4

export function Chip({ fieldKey, value, options, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [menuStyle, setMenuStyle] = useState<React.CSSProperties>({})
  const buttonRef = useRef<HTMLButtonElement>(null)
  const currentLabel = options.find((o) => o.value === value)?.label ?? value

  useLayoutEffect(() => {
    if (!open || !buttonRef.current) return

    const rect = buttonRef.current.getBoundingClientRect()
    const spaceBelow = window.innerHeight - rect.bottom - MENU_GAP
    const spaceAbove = rect.top - MENU_GAP
    const openUp = spaceBelow < 120 && spaceAbove > spaceBelow
    const maxHeight = Math.min(
      MENU_MAX_HEIGHT,
      Math.max(120, openUp ? spaceAbove : spaceBelow),
    )

    setMenuStyle({
      position:     'fixed',
      left:         rect.left,
      minWidth:     Math.max(rect.width, 180),
      maxHeight,
      overflowY:    'auto',
      overflowX:    'hidden',
      top:          openUp ? undefined : rect.bottom + MENU_GAP,
      bottom:       openUp ? window.innerHeight - rect.top + MENU_GAP : undefined,
      zIndex:       1000,
      background:   'var(--cue-paper)',
      border:       '1px solid var(--cue-rule)',
      borderRadius: '8px',
      boxShadow:    '0 8px 28px rgb(0 0 0 / 0.18)',
    })
  }, [open])

  const menu =
    open &&
    createPortal(
      <>
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 999 }}
          onClick={() => setOpen(false)}
          aria-hidden
        />
        <div role="listbox" style={menuStyle}>
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="option"
              aria-selected={opt.value === value}
              onClick={() => {
                onChange(opt.value)
                setOpen(false)
              }}
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
              {opt.value === value && (
                <span style={{ color: 'var(--cue-accent)', fontSize: '12px' }}>✓</span>
              )}
            </button>
          ))}
        </div>
      </>,
      document.body,
    )

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
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
        <span
          style={{
            fontFamily:     'var(--cue-mono)',
            fontSize:       '10px',
            textTransform:  'uppercase',
            letterSpacing:  '0.08em',
            color:          'var(--cue-ink-3)',
          }}
        >
          {fieldKey}
        </span>
        <span
          style={{
            fontFamily: 'var(--cue-sans)',
            fontSize:   '12px',
            fontWeight: 500,
            color:      'var(--cue-ink)',
          }}
        >
          {currentLabel}
        </span>
        <span style={{ color: 'var(--cue-ink-3)', fontSize: '10px' }}>▾</span>
      </button>
      {menu}
    </div>
  )
}
