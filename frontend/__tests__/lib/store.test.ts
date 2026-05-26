import { act } from '@testing-library/react'
import { useStore } from '@/lib/store'

// Reset store between tests
beforeEach(() => {
  useStore.setState(useStore.getInitialState())
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
