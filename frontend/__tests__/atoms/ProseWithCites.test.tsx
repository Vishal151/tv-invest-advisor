import { render, screen } from '@testing-library/react'
import { ProseWithCites } from '@/components/atoms/ProseWithCites'

test('renders plain text without markers', () => {
  render(<ProseWithCites text="TV advertising is effective." onCiteClick={jest.fn()} />)
  expect(screen.getByText(/TV advertising is effective/)).toBeInTheDocument()
})

test('splits [N] markers into Citation components', () => {
  render(<ProseWithCites text="TV delivers ROI [1] and reach [2]." onCiteClick={jest.fn()} />)
  expect(screen.getByText('1')).toBeInTheDocument()
  expect(screen.getByText('2')).toBeInTheDocument()
})
