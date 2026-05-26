import { render, screen } from '@testing-library/react'
import { EvidenceRail } from '@/components/rail/EvidenceRail'
import type { Source } from '@/lib/types'

const sources: Source[] = [
  { n:1, title:'Profit Ability 2', year:2024, page:14, url:'https://thinkbox.tv', quote:'TV ROI £5.61', topic:'ROI' },
  { n:2, title:'Payback 4',        year:2014, page:22, url:'https://thinkbox.tv', quote:'Seasonal windows', topic:'Planning' },
]

test('renders all source titles', () => {
  render(<EvidenceRail sources={sources} collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText('Payback 4')).toBeInTheDocument()
})

test('shows EVIDENCE header', () => {
  render(<EvidenceRail sources={sources} collapsed={false} onToggle={jest.fn()} />)
  expect(screen.getByText(/evidence/i)).toBeInTheDocument()
})

test('shows collapsed label when collapsed=true', () => {
  const { container } = render(<EvidenceRail sources={sources} collapsed={true} onToggle={jest.fn()} />)
  expect(container.querySelector('.cue-rail--collapsed')).toBeTruthy()
})
