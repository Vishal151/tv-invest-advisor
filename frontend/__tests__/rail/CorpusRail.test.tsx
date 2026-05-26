import { render, screen } from '@testing-library/react'
import { CorpusRail } from '@/components/rail/CorpusRail'

test('renders corpus stats', () => {
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText('8')).toBeInTheDocument()
  expect(screen.getByText(/reports/i)).toBeInTheDocument()
})

test('renders all corpus document titles', () => {
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText('TV Viewing Report')).toBeInTheDocument()
})
