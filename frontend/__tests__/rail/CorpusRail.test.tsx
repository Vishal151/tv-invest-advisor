import { render, screen } from '@testing-library/react'
import { CorpusRail } from '@/components/rail/CorpusRail'

// Both docs share a topic so each stat value (2 reports, 75 chunks, 1 topic) is unique.
const corpus = [
  { source_title: 'Profit Ability 2', chunks: 45, topic: 'ROI' },
  { source_title: 'TV Viewing Report 2025', chunks: 30, topic: 'ROI' },
]

const mockFetch = jest.fn()
global.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
  mockFetch.mockResolvedValue({ ok: true, json: async () => corpus })
})

test('renders live corpus documents from /api/corpus', async () => {
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  expect(await screen.findByText('Profit Ability 2')).toBeInTheDocument()
  expect(screen.getByText('TV Viewing Report 2025')).toBeInTheDocument()
})

test('computes report and chunk stats from live data', async () => {
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  await screen.findByText('Profit Ability 2')
  expect(screen.getByText('2')).toBeInTheDocument() // reports
  expect(screen.getByText('75')).toBeInTheDocument() // total chunks
  expect(screen.getByText(/reports/i)).toBeInTheDocument()
})

test('still renders the rail header when the corpus fetch fails', async () => {
  mockFetch.mockReset()
  mockFetch.mockRejectedValue(new Error('network down'))
  render(<CorpusRail collapsed={false} onToggle={jest.fn()} />)
  expect(await screen.findByText('Corpus')).toBeInTheDocument()
})
