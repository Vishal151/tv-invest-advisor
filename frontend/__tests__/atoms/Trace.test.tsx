import { render, screen } from '@testing-library/react'
import { Trace } from '@/components/atoms/Trace'

const steps = [
  'Parsing brief — sector: FMCG',
  'Filtering corpus by topic: ROI',
  'Retrieving 5 chunks…',
]

test('renders all trace steps', () => {
  render(<Trace steps={steps} />)
  expect(screen.getByText(/Parsing brief/)).toBeInTheDocument()
  expect(screen.getByText(/Filtering corpus/)).toBeInTheDocument()
  expect(screen.getByText(/Retrieving 5 chunks/)).toBeInTheDocument()
})

test('renders correct number of steps', () => {
  const { container } = render(<Trace steps={steps} />)
  const lines = container.querySelectorAll('.cue-trace-line')
  expect(lines).toHaveLength(3)
})
