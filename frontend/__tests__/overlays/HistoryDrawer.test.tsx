import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HistoryDrawer } from '@/overlays/HistoryDrawer'
import { useStore } from '@/lib/store'

beforeEach(() => {
  useStore.setState({ historyOpen: true })
})

test('renders THREADS heading when open', () => {
  render(<HistoryDrawer />)
  expect(screen.getByText('Threads')).toBeInTheDocument()
})

test('renders + New thread button', () => {
  render(<HistoryDrawer />)
  expect(screen.getByText(/new thread/i)).toBeInTheDocument()
})

test('close button sets historyOpen to false', async () => {
  render(<HistoryDrawer />)
  await userEvent.click(screen.getByRole('button', { name: /close/i }))
  expect(useStore.getState().historyOpen).toBe(false)
})

test('does not render when historyOpen=false', () => {
  useStore.setState({ historyOpen: false })
  const { container } = render(<HistoryDrawer />)
  expect(container.firstChild).toBeNull()
})
