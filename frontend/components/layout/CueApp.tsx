'use client'

import { useStore } from '@/lib/store'
import { Topbar } from './Topbar'
import { Composer } from '@/components/composer/Composer'
import { UserBubble } from '@/components/thread/UserBubble'
import { AssistantBubble } from '@/components/thread/AssistantBubble'
import { StreamingBubble } from '@/components/thread/StreamingBubble'
import { RefusalCard } from '@/components/thread/RefusalCard'
import { ErrorCard } from '@/components/thread/ErrorCard'
import { EvidenceRail } from '@/components/rail/EvidenceRail'
import { CorpusRail } from '@/components/rail/CorpusRail'
import { HistoryDrawer } from '@/overlays/HistoryDrawer'
import { ExportModal } from '@/overlays/ExportModal'
import { EmptyState } from './EmptyState'

export function CueApp() {
  const {
    thread, phase, composerInput, railCollapsed,
    setBrief, setComposerInput, ask, retry, toggleRail,
  } = useStore()

  const lastAnswer = [...thread.turns].reverse().find((t) => t.role === 'assistant')
  const sources = lastAnswer?.role === 'assistant' ? lastAnswer.answer.sources : []
  const hasAnswers = thread.turns.some((t) => t.role === 'assistant')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <Topbar threadTitle={thread.title !== 'New thread' ? thread.title : undefined} />

      <div
        style={{
          flex:                '1',
          display:             'grid',
          gridTemplateColumns: `1fr ${railCollapsed ? '56px' : '340px'}`,
          transition:          'grid-template-columns 220ms cubic-bezier(.2,.7,.3,1)',
          overflow:            'hidden',
          borderTop:           '1px solid var(--cue-rule-2)',
        }}
      >
        <div
          style={{
            display:       'flex',
            flexDirection: 'column',
            overflow:      'hidden',
            borderRight:   '1px solid var(--cue-rule)',
          }}
        >
          <div
            style={{
              flex:          '1',
              overflowY:     'auto',
              padding:       '32px 24px',
              display:       'flex',
              flexDirection: 'column',
              gap:           '24px',
              alignItems:    'center',
            }}
          >
            <div style={{ width: '100%', maxWidth: '760px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {thread.turns.length === 0 && phase === 'idle' && (
                <EmptyState onPickStarter={(q) => { setComposerInput(q); ask() }} />
              )}

              {thread.turns.map((turn, i) => {
                if (turn.role === 'user') {
                  return <UserBubble key={i} question={turn.question} brief={turn.brief} time={turn.time} />
                }
                if (turn.role === 'assistant') {
                  return (
                    <AssistantBubble
                      key={i}
                      answer={turn.answer}
                      time={turn.time}
                      onFollowup={(q) => { setComposerInput(q); ask() }}
                    />
                  )
                }
                if (turn.role === 'refusal') {
                  return (
                    <RefusalCard
                      key={i}
                      message={turn.message}
                      examples={turn.examples}
                      onPick={(q) => { setComposerInput(q); ask() }}
                      time={turn.time}
                    />
                  )
                }
                if (turn.role === 'error') {
                  return (
                    <ErrorCard
                      key={i}
                      title={turn.title}
                      message={turn.message}
                      reference={turn.reference}
                      retryable={turn.retryable}
                      onRetry={retry}
                      time={turn.time}
                    />
                  )
                }
                return null
              })}

              {(phase === 'thinking' || phase === 'loading') && (
                <StreamingBubble streamedText="" done={false} />
              )}
            </div>
          </div>

          <div
            style={{
              padding:    '16px 24px 20px',
              borderTop:  '1px solid var(--cue-rule-2)',
              background: 'var(--cue-paper)',
              overflow:   'visible',
              position:   'relative',
              zIndex:     2,
            }}
          >
            <Composer
              brief={thread.brief}
              setBrief={setBrief}
              value={composerInput}
              onChange={setComposerInput}
              onSubmit={ask}
              disabled={phase !== 'idle'}
            />
          </div>
        </div>

        <div style={{ background: 'var(--cue-paper-2)', overflow: 'hidden' }}>
          {hasAnswers
            ? <EvidenceRail sources={sources} collapsed={railCollapsed} onToggle={toggleRail} />
            : <CorpusRail collapsed={railCollapsed} onToggle={toggleRail} />
          }
        </div>
      </div>

      <HistoryDrawer />
      <ExportModal />
    </div>
  )
}
