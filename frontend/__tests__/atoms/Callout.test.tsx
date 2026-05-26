import { render, screen } from '@testing-library/react'
import { Callout } from '@/components/atoms/Callout'

test('renders label and body', () => {
  render(<Callout label="What this means for you" body="Concentrate 60–70% of TV spend..." />)
  expect(screen.getByText('What this means for you')).toBeInTheDocument()
  expect(screen.getByText(/Concentrate 60/)).toBeInTheDocument()
})
