import { render, screen } from '@testing-library/react'
import { SourceCard } from '@/components/atoms/SourceCard'
import type { Source } from '@/lib/types'

const src: Source = {
  n: 1, title: 'Profit Ability 2', year: 2024, page: 14,
  url: 'https://thinkbox.tv/research/profit-ability-2',
  quote: 'TV delivered £5.61 ROI.', topic: 'ROI',
}

test('renders title and quote', () => {
  render(<SourceCard source={src} />)
  expect(screen.getByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText(/TV delivered £5.61/)).toBeInTheDocument()
})

test('highlight prop adds accent border class', () => {
  const { container } = render(<SourceCard source={src} highlight />)
  expect(container.firstChild).toHaveClass('cue-source--highlight')
})
