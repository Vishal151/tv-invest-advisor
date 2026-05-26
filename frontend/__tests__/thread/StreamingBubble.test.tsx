import { render, screen } from '@testing-library/react'
import { StreamingBubble } from '@/components/thread/StreamingBubble'

const steps = ['Parsing brief', 'Retrieving chunks']

test('renders trace steps', () => {
  const { container } = render(<StreamingBubble traceSteps={steps} streamedText="" done={false} />)
  expect(container.firstChild).toBeTruthy()
})

test('shows streamed text when present', () => {
  render(<StreamingBubble traceSteps={steps} streamedText="TV delivers" done={false} />)
  expect(screen.getByText(/TV delivers/)).toBeInTheDocument()
})
