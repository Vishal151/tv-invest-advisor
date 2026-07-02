import { render, screen } from '@testing-library/react'
import { EmptyState } from '@/components/layout/EmptyState'
import { useStore } from '@/lib/store'

beforeEach(() => {
  useStore.setState(useStore.getInitialState())
})

test('kicker reflects the live brief chips, not a hardcoded one', () => {
  const s = useStore.getState()
  useStore.setState({
    thread: {
      ...s.thread,
      brief: { ...s.thread.brief, sector: 'Retail', brandStage: 'established', budgetTier: 'under-100k' },
    },
  })
  render(<EmptyState onPickStarter={jest.fn()} />)
  expect(screen.getByText(/Retail · Established · Under £100k/)).toBeInTheDocument()
})

test('kicker shows the default brief on first load', () => {
  render(<EmptyState onPickStarter={jest.fn()} />)
  expect(screen.getByText(/FMCG · Scale-up · £500k–£2m/)).toBeInTheDocument()
})
