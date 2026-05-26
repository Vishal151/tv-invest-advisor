import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Citation } from '@/components/atoms/Citation'

test('renders citation number', () => {
  render(<Citation n={3} />)
  expect(screen.getByText('3')).toBeInTheDocument()
})

test('calls onClick when clicked', async () => {
  const onClick = jest.fn()
  render(<Citation n={1} onClick={onClick} />)
  await userEvent.click(screen.getByText('1'))
  expect(onClick).toHaveBeenCalledWith(1)
})
