import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorCard } from '@/components/thread/ErrorCard'

test('renders title and message', () => {
  render(<ErrorCard title="We couldn't ground this one" message="Please try again." reference="cue-err-abc123" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.getByText("We couldn't ground this one")).toBeInTheDocument()
  expect(screen.getByText('Please try again.')).toBeInTheDocument()
})

test('renders opaque reference id', () => {
  render(<ErrorCard title="Error" message="msg" reference="cue-err-abc123" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.getByText(/cue-err-abc123/)).toBeInTheDocument()
})

test('calls onRetry when Retry clicked', async () => {
  const onRetry = jest.fn()
  render(<ErrorCard title="Error" message="msg" reference="ref" retryable={true} onRetry={onRetry} time="12:00" />)
  await userEvent.click(screen.getByRole('button', { name: /retry/i }))
  expect(onRetry).toHaveBeenCalled()
})

test('does not render a non-functional Rephrase button', () => {
  render(<ErrorCard title="Error" message="msg" reference="ref" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.queryByRole('button', { name: /rephrase/i })).not.toBeInTheDocument()
})

test('does not surface backend details in message', () => {
  render(<ErrorCard title="Error" message="Service unavailable." reference="ref" retryable={true} onRetry={jest.fn()} time="12:00" />)
  expect(screen.queryByText(/503/)).not.toBeInTheDocument()
  expect(screen.queryByText(/gpt-4o/)).not.toBeInTheDocument()
})
