import { render, screen } from '@testing-library/react'
import { Headline } from '@/components/atoms/Headline'

test('renders stat, unit, and caption', () => {
  render(<Headline stat="£5.61" unit="ROI per £1 spent" caption="Profit Ability 2 (2024)" />)
  expect(screen.getByText('£5.61')).toBeInTheDocument()
  expect(screen.getByText('ROI per £1 spent')).toBeInTheDocument()
  expect(screen.getByText('Profit Ability 2 (2024)')).toBeInTheDocument()
})

test('dense prop applies smaller size class', () => {
  const { container } = render(
    <Headline stat="70/30" unit="linear / BVOD" caption="Source" dense />
  )
  expect(container.firstChild).toHaveClass('cue-headline--dense')
})
