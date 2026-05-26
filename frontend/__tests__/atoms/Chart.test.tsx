import { render, screen } from '@testing-library/react'
import { Chart } from '@/components/atoms/Chart'
import type { Chart as ChartType } from '@/lib/types'

const chart: ChartType = {
  title: 'Profit per £1 spent, by channel',
  source: 'Profit Ability 2 (2024)',
  unit: '£',
  bars: [
    { label: 'Linear TV', value: 5.61, highlight: true },
    { label: 'BVOD',      value: 4.66 },
    { label: 'Print',     value: 1.39 },
  ],
}

test('renders title and all bar labels', () => {
  render(<Chart chart={chart} />)
  expect(screen.getByText('Profit per £1 spent, by channel')).toBeInTheDocument()
  expect(screen.getByText('Linear TV')).toBeInTheDocument()
  expect(screen.getByText('BVOD')).toBeInTheDocument()
  expect(screen.getByText('Print')).toBeInTheDocument()
})

test('renders bar values', () => {
  render(<Chart chart={chart} />)
  expect(screen.getByText('5.61')).toBeInTheDocument()
  expect(screen.getByText('4.66')).toBeInTheDocument()
})
