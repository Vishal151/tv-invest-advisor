import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Chip } from '@/components/composer/Chip'

const options = [
  { value: 'FMCG',   label: 'FMCG' },
  { value: 'Retail', label: 'Retail' },
]

test('renders chip key and current value label', () => {
  render(<Chip fieldKey="SECTOR" value="FMCG" options={options} onChange={jest.fn()} />)
  expect(screen.getByText('SECTOR')).toBeInTheDocument()
  expect(screen.getByText('FMCG')).toBeInTheDocument()
})

test('opens popover on click showing all options', async () => {
  render(<Chip fieldKey="SECTOR" value="FMCG" options={options} onChange={jest.fn()} />)
  await userEvent.click(screen.getByRole('button'))
  expect(screen.getByText('Retail')).toBeInTheDocument()
})

test('calls onChange when option selected', async () => {
  const onChange = jest.fn()
  render(<Chip fieldKey="SECTOR" value="FMCG" options={options} onChange={onChange} />)
  await userEvent.click(screen.getByRole('button'))
  await userEvent.click(screen.getByText('Retail'))
  expect(onChange).toHaveBeenCalledWith('Retail')
})
