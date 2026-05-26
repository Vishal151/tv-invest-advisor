import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RefusalCard } from '@/components/thread/RefusalCard'

const examples = ['Is TV good for DTC?', 'What is the ROI of TV?']

test('renders off-topic header', () => {
  render(<RefusalCard message="Off-topic." examples={examples} onPick={jest.fn()} time="12:00" />)
  expect(screen.getByText(/off-topic/i)).toBeInTheDocument()
})

test('renders example suggestions', () => {
  render(<RefusalCard message="Off-topic." examples={examples} onPick={jest.fn()} time="12:00" />)
  expect(screen.getByText('Is TV good for DTC?')).toBeInTheDocument()
})

test('calls onPick when example clicked', async () => {
  const onPick = jest.fn()
  render(<RefusalCard message="Off-topic." examples={examples} onPick={onPick} time="12:00" />)
  await userEvent.click(screen.getByText('Is TV good for DTC?'))
  expect(onPick).toHaveBeenCalledWith('Is TV good for DTC?')
})
