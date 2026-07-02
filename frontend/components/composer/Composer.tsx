'use client'

import type { Brief } from '@/lib/types'
import { BRIEF_VALUE_LABELS } from '@/lib/briefLabels'
import { Chip } from './Chip'

type Props = {
  brief:     Brief
  setBrief:  (patch: Partial<Brief>) => void
  value:     string
  onChange:  (v: string) => void
  onSubmit:  () => void
  disabled:  boolean
}

const opts = (key: keyof typeof BRIEF_VALUE_LABELS) =>
  Object.entries(BRIEF_VALUE_LABELS[key]).map(([value, label]) => ({ value, label }))

const SECTOR_OPTS  = opts('sector')
const STAGE_OPTS   = opts('brandStage')
const HISTORY_OPTS = opts('tvHistory')
const GOAL_OPTS    = opts('primaryGoal')
const BUDGET_OPTS  = opts('budgetTier')

export function Composer({ brief, setBrief, value, onChange, onSubmit, disabled }: Props) {
  // Backend validates question length 5-500 — don't let shorter ones submit
  // only to bounce off a 422.
  const canSubmit = value.trim().length >= 5

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (canSubmit) onSubmit()
    }
  }

  return (
    <div
      style={{
        maxWidth:     '760px',
        margin:       '0 auto',
        borderRadius: '12px',
        border:       '1px solid var(--cue-rule)',
        background:   'var(--cue-paper)',
        boxShadow:    '0 4px 24px -8px rgb(0 0 0 / 0.08)',
        overflow:     'visible',
      }}
    >
      <div
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '6px',
          padding:      '10px 14px',
          borderBottom: '1px solid var(--cue-rule-2)',
          flexWrap:     'wrap',
        }}
      >
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--cue-ink-3)', marginRight: '4px' }}>
          Brief
        </span>
        <Chip fieldKey="Sector"     value={brief.sector}      options={SECTOR_OPTS}  onChange={(v) => setBrief({ sector: v as Brief['sector'] })} />
        <Chip fieldKey="Stage"      value={brief.brandStage}  options={STAGE_OPTS}   onChange={(v) => setBrief({ brandStage: v as Brief['brandStage'] })} />
        <Chip fieldKey="TV History" value={brief.tvHistory}   options={HISTORY_OPTS} onChange={(v) => setBrief({ tvHistory: v as Brief['tvHistory'] })} />
        <Chip fieldKey="Goal"       value={brief.primaryGoal} options={GOAL_OPTS}    onChange={(v) => setBrief({ primaryGoal: v as Brief['primaryGoal'] })} />
        <Chip fieldKey="Budget"     value={brief.budgetTier}  options={BUDGET_OPTS}  onChange={(v) => setBrief({ budgetTier: v as Brief['budgetTier'] })} />
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', padding: '10px 14px' }}>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          maxLength={500}
          placeholder="Ask Cue about your TV investment…"
          rows={2}
          style={{
            flex:       1,
            resize:     'none',
            border:     'none',
            outline:    'none',
            background: 'transparent',
            fontFamily: 'var(--cue-serif)',
            fontSize:   '16px',
            color:      'var(--cue-ink)',
            lineHeight: 1.45,
          }}
        />
        <button
          type="button"
          onClick={onSubmit}
          disabled={disabled || !canSubmit}
          aria-label="Ask"
          style={{
            padding:      '8px 16px',
            borderRadius: '8px',
            border:       'none',
            background:   disabled || !canSubmit ? 'var(--cue-rule)' : 'var(--cue-accent)',
            color:        disabled || !canSubmit ? 'var(--cue-ink-4)' : 'var(--cue-paper)',
            fontFamily:   'var(--cue-sans)',
            fontSize:     '13px',
            fontWeight:   500,
            cursor:       disabled || !canSubmit ? 'not-allowed' : 'pointer',
            transition:   'background 120ms, color 120ms',
            whiteSpace:   'nowrap',
          }}
        >
          Ask →
        </button>
      </div>

      <div style={{ padding: '0 14px 8px', display: 'flex', gap: '10px' }}>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Answers grounded in published Thinkbox research
        </span>
        <span style={{ fontFamily: 'var(--cue-mono)', fontSize: '9.5px', color: 'var(--cue-ink-4)' }}>
          <kbd style={{ background: 'var(--cue-paper-2)', padding: '1px 4px', borderRadius: '3px', border: '1px solid var(--cue-rule)' }}>↵</kbd> send
          {' · '}
          <kbd style={{ background: 'var(--cue-paper-2)', padding: '1px 4px', borderRadius: '3px', border: '1px solid var(--cue-rule)' }}>⇧↵</kbd> newline
        </span>
      </div>
    </div>
  )
}
