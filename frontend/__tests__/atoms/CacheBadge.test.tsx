import { render, screen } from '@testing-library/react'
import { CacheBadge } from '@/components/atoms/CacheBadge'

test('renders cached text', () => {
  render(<CacheBadge />)
  expect(screen.getByText('cached')).toBeInTheDocument()
})
