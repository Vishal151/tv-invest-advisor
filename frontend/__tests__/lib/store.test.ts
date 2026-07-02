import { act } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { queryApi } from '@/lib/api'

jest.mock('@/lib/api', () => ({ queryApi: jest.fn() }))
const queryApiMock = queryApi as jest.Mock

// Reset store between tests
beforeEach(() => {
  useStore.setState(useStore.getInitialState())
  queryApiMock.mockReset()
})

test('initial phase is idle', () => {
  expect(useStore.getState().phase).toBe('idle')
})

test('setBrief updates brief fields', () => {
  act(() => {
    useStore.getState().setBrief({ sector: 'Retail' })
  })
  expect(useStore.getState().thread.brief.sector).toBe('Retail')
})

test('setComposerInput updates composerInput', () => {
  act(() => {
    useStore.getState().setComposerInput('Does TV work?')
  })
  expect(useStore.getState().composerInput).toBe('Does TV work?')
})

test('newThread resets turns and composerInput', () => {
  act(() => {
    useStore.getState().setComposerInput('question')
    useStore.getState().newThread()
  })
  expect(useStore.getState().composerInput).toBe('')
  expect(useStore.getState().thread.turns).toHaveLength(0)
})

test('toggleRail flips railCollapsed', () => {
  expect(useStore.getState().railCollapsed).toBe(false)
  act(() => useStore.getState().toggleRail())
  expect(useStore.getState().railCollapsed).toBe(true)
})

test('setHistoryOpen controls historyOpen flag', () => {
  act(() => useStore.getState().setHistoryOpen(true))
  expect(useStore.getState().historyOpen).toBe(true)
})

import type { Answer } from '@/lib/types'

function makeAnswer(summary = 'TV works.'): Answer {
  return {
    stats: [],
    summary: [summary],
    checklist: null,
    callout: null,
    chart: null,
    sources: [],
    followups: [],
    meta: { model: 'gpt-4o', cached: false, retrievalMs: 1, generationMs: 1, chunksUsed: 0 },
  }
}

async function askWith(question: string) {
  useStore.getState().setComposerInput(question)
  await act(async () => {
    await useStore.getState().ask()
  })
}

test('ask() appends user and assistant turns and returns to idle', async () => {
  queryApiMock.mockResolvedValueOnce({ kind: 'answer', answer: makeAnswer() })

  await askWith('Does TV work?')

  const { phase, thread, composerInput } = useStore.getState()
  expect(phase).toBe('idle')
  expect(composerInput).toBe('')
  expect(thread.turns).toHaveLength(2)
  expect(thread.turns[0]).toMatchObject({ role: 'user', question: 'Does TV work?' })
  expect(thread.turns[1]).toMatchObject({ role: 'assistant' })
})

test('ask() maps a refusal result to a refusal turn', async () => {
  queryApiMock.mockResolvedValueOnce({ kind: 'refusal', message: 'Off-topic.', examples: ['Is TV right for DTC?'] })

  await askWith('Write me a poem')

  const last = useStore.getState().thread.turns.at(-1)
  expect(last).toMatchObject({ role: 'refusal', message: 'Off-topic.' })
})

test('ask() maps an error result to a retryable error turn', async () => {
  queryApiMock.mockResolvedValueOnce({ kind: 'error', title: 'Down', message: 'Try later.', reference: 'req-1' })

  await askWith('Does TV work?')

  const last = useStore.getState().thread.turns.at(-1)
  expect(last).toMatchObject({ role: 'error', title: 'Down', retryable: true })
  expect(useStore.getState().phase).toBe('idle')
})

test('ask() ignores a second submission while one is in flight', async () => {
  let resolveFirst!: (v: unknown) => void
  queryApiMock.mockReturnValueOnce(new Promise((r) => (resolveFirst = r)))

  useStore.getState().setComposerInput('First question')
  const first = useStore.getState().ask()

  useStore.getState().setComposerInput('Second question')
  await act(async () => {
    await useStore.getState().ask() // must be a no-op: phase is 'loading'
  })
  expect(queryApiMock).toHaveBeenCalledTimes(1)

  resolveFirst({ kind: 'answer', answer: makeAnswer() })
  await act(async () => {
    await first
  })
  expect(useStore.getState().phase).toBe('idle')
})

test('an answer arriving after newThread() lands in the original thread, not the new one', async () => {
  let resolveQuery!: (v: unknown) => void
  queryApiMock.mockReturnValueOnce(new Promise((r) => (resolveQuery = r)))

  const originalId = useStore.getState().thread.id
  useStore.getState().setComposerInput('Does TV work?')
  const inFlight = useStore.getState().ask()

  act(() => useStore.getState().newThread())

  resolveQuery({ kind: 'answer', answer: makeAnswer('Late answer.') })
  await act(async () => {
    await inFlight
  })

  // The new current thread must not receive the stale answer
  expect(useStore.getState().thread.turns).toHaveLength(0)
  // The original thread in history has both its user turn and the answer
  const original = useStore.getState().threads.find((t) => t.id === originalId)
  expect(original).toBeDefined()
  expect(original!.turns).toHaveLength(2)
  expect(original!.turns[1]).toMatchObject({ role: 'assistant' })
})

test('turns added after reopening a thread survive newThread()', async () => {
  queryApiMock.mockResolvedValue({ kind: 'answer', answer: makeAnswer() })

  await askWith('First question')
  const firstId = useStore.getState().thread.id
  act(() => useStore.getState().newThread())

  act(() => useStore.getState().openThread(firstId))
  await askWith('Follow-up question')
  expect(useStore.getState().thread.turns).toHaveLength(4)

  act(() => useStore.getState().newThread())
  const saved = useStore.getState().threads.find((t) => t.id === firstId)
  expect(saved!.turns).toHaveLength(4) // stale 2-turn copy must not win
})

test('openThread() preserves the current thread turns in history', async () => {
  queryApiMock.mockResolvedValue({ kind: 'answer', answer: makeAnswer() })

  await askWith('Thread A question')
  const aId = useStore.getState().thread.id
  act(() => useStore.getState().newThread())

  await askWith('Thread B question')
  const bId = useStore.getState().thread.id

  act(() => useStore.getState().openThread(aId))

  const savedB = useStore.getState().threads.find((t) => t.id === bId)
  expect(savedB).toBeDefined()
  expect(savedB!.turns).toHaveLength(2)
})

test('retry() re-asks the last user question', async () => {
  queryApiMock.mockResolvedValueOnce({ kind: 'error', title: 'Down', message: 'Try later.', reference: 'r' })
  await askWith('Does TV work for FMCG?')

  queryApiMock.mockResolvedValueOnce({ kind: 'answer', answer: makeAnswer() })
  await act(async () => {
    await useStore.getState().retry()
  })

  expect(queryApiMock).toHaveBeenLastCalledWith(
    expect.objectContaining({ question: 'Does TV work for FMCG?' })
  )
  expect(useStore.getState().thread.turns.at(-1)).toMatchObject({ role: 'assistant' })
})

test('ask() recovers to idle with an error turn if the query rejects', async () => {
  // Even if queryApi throws unexpectedly, the app must never be stuck in 'loading'
  queryApiMock.mockRejectedValueOnce(new Error('boom'))

  useStore.getState().setComposerInput('Does TV work?')
  await act(async () => {
    await useStore.getState().ask()
  })

  const { phase, thread } = useStore.getState()
  expect(phase).toBe('idle')
  const last = thread.turns[thread.turns.length - 1]
  expect(last.role).toBe('error')
})
