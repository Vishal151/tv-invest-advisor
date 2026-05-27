import { render, screen } from '@testing-library/react'
import { StreamingBubble } from '@/components/thread/StreamingBubble'

const steps = ['Parsing brief', 'Retrieving chunks']

test('renders with default trace steps', () => {
  const { container } = render(<StreamingBubble />)
  expect(container.firstChild).toBeTruthy()
})

test('renders with custom trace steps', () => {
  render(<StreamingBubble traceSteps={steps} />)
  expect(screen.getByText('Parsing brief')).toBeInTheDocument()
})
