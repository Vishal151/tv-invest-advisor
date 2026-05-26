import { render, screen } from '@testing-library/react'
import { UserBubble } from '@/components/thread/UserBubble'
import type { Brief } from '@/lib/types'

const brief: Brief = { sector:'FMCG', brandStage:'scale-up', tvHistory:'tried', primaryGoal:'brand', budgetTier:'500k-2m' }

test('renders the question text', () => {
  render(<UserBubble question="When does TV work?" brief={brief} time="11:42" />)
  expect(screen.getByText('When does TV work?')).toBeInTheDocument()
})

test('renders brief context tags', () => {
  render(<UserBubble question="q" brief={brief} time="11:42" />)
  expect(screen.getByText('FMCG')).toBeInTheDocument()
  expect(screen.getByText('scale-up')).toBeInTheDocument()
})
