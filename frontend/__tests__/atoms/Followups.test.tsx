import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Followups } from '@/components/atoms/Followups'

test('renders all followup items', () => {
  render(<Followups items={['Question A', 'Question B']} onPick={jest.fn()} />)
  expect(screen.getByText('Question A')).toBeInTheDocument()
  expect(screen.getByText('Question B')).toBeInTheDocument()
})

test('calls onPick with question text on click', async () => {
  const onPick = jest.fn()
  render(<Followups items={['Question A']} onPick={onPick} />)
  await userEvent.click(screen.getByText('Question A'))
  expect(onPick).toHaveBeenCalledWith('Question A')
})
