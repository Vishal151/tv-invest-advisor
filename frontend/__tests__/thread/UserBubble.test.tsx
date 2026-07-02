import { render, screen } from '@testing-library/react'
import { UserBubble } from '@/components/thread/UserBubble'
import type { Brief } from '@/lib/types'

const brief: Brief = { sector:'FMCG', brandStage:'scale-up', tvHistory:'tried', primaryGoal:'brand', budgetTier:'500k-2m' }

test('renders the question text', () => {
  render(<UserBubble question="When does TV work?" brief={brief} time="11:42" />)
  expect(screen.getByText('When does TV work?')).toBeInTheDocument()
})

test('renders brief context tags with human-readable labels, not raw enum values', () => {
  render(<UserBubble question="q" brief={brief} time="11:42" />)
  expect(screen.getByText('FMCG')).toBeInTheDocument()
  expect(screen.getByText('Scale-up')).toBeInTheDocument()
  expect(screen.getByText('Tried once or twice')).toBeInTheDocument()
  expect(screen.getByText('Brand building')).toBeInTheDocument()
  expect(screen.getByText('£500k–£2m')).toBeInTheDocument()
  expect(screen.queryByText('scale-up')).toBeNull()
  expect(screen.queryByText('500k-2m')).toBeNull()
})
