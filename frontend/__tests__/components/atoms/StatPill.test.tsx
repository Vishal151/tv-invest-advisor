import { render, screen } from '@testing-library/react'
import { StatPill } from '@/components/atoms/StatPill'
import type { Stat } from '@/lib/types'

const fixture: Stat = {
  value:   '£5.61',
  unit:    'ROI per £1 spent',
  context: 'Average across 141 brands and 14 categories',
  source:  'Profit Ability 2',
  page:    12,
}

describe('StatPill', () => {
  it('renders value, unit, context and attribution', () => {
    render(<StatPill stat={fixture} />)
    expect(screen.getByText('£5.61')).toBeInTheDocument()
    expect(screen.getByText('ROI per £1 spent')).toBeInTheDocument()
    expect(screen.getByText('Average across 141 brands and 14 categories')).toBeInTheDocument()
    expect(screen.getByText(/PROFIT ABILITY 2/i)).toBeInTheDocument()
    expect(screen.getByText(/p\.12/i)).toBeInTheDocument()
  })

  it('omits page when page is 0', () => {
    render(<StatPill stat={{ ...fixture, page: 0 }} />)
    expect(screen.queryByText(/p\.\d/)).toBeNull()
  })
})
