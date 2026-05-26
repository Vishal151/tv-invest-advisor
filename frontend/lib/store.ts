'use client'

import { create } from 'zustand'
import type { Brief, Thread, Phase, Turn } from './types'
import { queryApi } from './api'

const DEFAULT_BRIEF: Brief = {
  sector:      'FMCG',
  brandStage:  'scale-up',
  tvHistory:   'tried',
  primaryGoal: 'brand',
  budgetTier:  '500k-2m',
}

function uuid(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

function newThread(): Thread {
  return {
    id:    uuid(),
    title: 'New thread',
    turns: [],
    brief: { ...DEFAULT_BRIEF },
  }
}

type AppStore = {
  thread:         Thread
  threads:        Thread[]
  phase:          Phase
  composerInput:  string
  railCollapsed:  boolean
  historyOpen:    boolean
  exportOpen:     boolean
  activeCitation: number | null
  activeSource:   number | null

  ask():                        Promise<void>
  setBrief(patch: Partial<Brief>): void
  setComposerInput(v: string):  void
  retry():                      Promise<void>
  newThread():                  void
  openThread(id: string):       void
  toggleRail():                 void
  setHistoryOpen(open: boolean): void
  setExportOpen(open: boolean):  void
  setActiveCitation(n: number | null): void
  setActiveSource(n: number | null):   void
}

export const useStore = create<AppStore>((set, get) => ({
  thread:         newThread(),
  threads:        [],
  phase:          'idle',
  composerInput:  '',
  railCollapsed:  false,
  historyOpen:    false,
  exportOpen:     false,
  activeCitation: null,
  activeSource:   null,

  setBrief(patch) {
    set((s) => ({
      thread: { ...s.thread, brief: { ...s.thread.brief, ...patch } },
    }))
  },

  setComposerInput(v) {
    set({ composerInput: v })
  },

  async ask() {
    const { composerInput, thread } = get()
    const question = composerInput.trim()
    if (!question || get().phase !== 'idle') return

    const userTurn: Turn = {
      role:     'user',
      question,
      brief:    { ...thread.brief },
      time:     new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    set((s) => ({
      composerInput: '',
      phase:         'thinking',
      thread: { ...s.thread, turns: [...s.thread.turns, userTurn] },
    }))

    await new Promise((r) => setTimeout(r, 400))
    set({ phase: 'streaming' })

    const result = await queryApi({ question, brief: thread.brief })
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    let assistantTurn: Turn
    if (result.kind === 'answer') {
      assistantTurn = { role: 'assistant', answer: result.answer, time }
    } else if (result.kind === 'refusal') {
      assistantTurn = { role: 'refusal', message: result.message, examples: result.examples, time }
    } else {
      assistantTurn = {
        role: 'error',
        title:     result.title,
        message:   result.message,
        reference: result.reference,
        retryable: true,
        time,
      }
    }

    set((s) => ({
      phase:  'answered',
      thread: { ...s.thread, turns: [...s.thread.turns, assistantTurn] },
    }))

    setTimeout(() => set({ phase: 'idle' }), 100)
  },

  async retry() {
    const { thread } = get()
    const lastUserTurn = [...thread.turns].reverse().find((t) => t.role === 'user')
    if (!lastUserTurn || lastUserTurn.role !== 'user') return
    set({ composerInput: lastUserTurn.question })
    await get().ask()
  },

  newThread() {
    set((s) => {
      const current = s.thread
      const exists = s.threads.find((t) => t.id === current.id)
      return {
        thread:        newThread(),
        composerInput: '',
        phase:         'idle',
        threads:       exists ? s.threads : [current, ...s.threads],
      }
    })
  },

  openThread(id) {
    set((s) => {
      const found = s.threads.find((t) => t.id === id)
      if (!found) return s
      return { thread: found, historyOpen: false, phase: 'idle' }
    })
  },

  toggleRail() {
    set((s) => ({ railCollapsed: !s.railCollapsed }))
  },

  setHistoryOpen(open) { set({ historyOpen: open }) },
  setExportOpen(open)  { set({ exportOpen: open }) },
  setActiveCitation(n) { set({ activeCitation: n }) },
  setActiveSource(n)   { set({ activeSource: n }) },
}))

;(useStore as any).getInitialState = () => ({
  thread:         newThread(),
  threads:        [],
  phase:          'idle' as Phase,
  composerInput:  '',
  railCollapsed:  false,
  historyOpen:    false,
  exportOpen:     false,
  activeCitation: null,
  activeSource:   null,
})
