import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExportModal } from '@/overlays/ExportModal'
import { useStore } from '@/lib/store'

beforeEach(() => {
  useStore.setState({ exportOpen: true })
})

test('renders Export preview heading when open', () => {
  render(<ExportModal />)
  expect(screen.getByText(/export preview/i)).toBeInTheDocument()
})

test('close button sets exportOpen to false', async () => {
  render(<ExportModal />)
  await userEvent.click(screen.getByRole('button', { name: /close/i }))
  expect(useStore.getState().exportOpen).toBe(false)
})

test('does not render when exportOpen=false', () => {
  useStore.setState({ exportOpen: false })
  const { container } = render(<ExportModal />)
  expect(container.firstChild).toBeNull()
})
