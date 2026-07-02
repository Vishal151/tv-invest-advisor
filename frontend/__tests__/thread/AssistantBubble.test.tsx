import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AssistantBubble } from '@/components/thread/AssistantBubble'
import type { Answer } from '@/lib/types'

const answer: Answer = {
  stats: [{ value: '£5.61', unit: 'ROI per £1', context: 'TV advertising', source: 'Profit Ability 2', page: 14 }],
  summary: ['TV delivers strong ROI [1].', 'Second paragraph.'],
  checklist: null,
  callout: { label: 'What this means', body: 'Concentrate spend in bursts.' },
  chart: null,
  followups: ['How should I split the burst?'],
  sources: [{ n:1, title:'Profit Ability 2', year:2024, page:14, url:'https://thinkbox.tv', quote:'TV delivered £5.61', topic:'ROI' }],
  meta: { model:'gpt-4o', cached:false, retrievalMs:400, generationMs:2000, chunksUsed:4 },
}

test('renders first stat value', () => {
  render(<AssistantBubble answer={answer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  expect(screen.getByText('£5.61')).toBeInTheDocument()
})

test('renders prose paragraphs', () => {
  render(<AssistantBubble answer={answer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  expect(screen.getByText(/TV delivers strong ROI/)).toBeInTheDocument()
  expect(screen.getByText(/Second paragraph/)).toBeInTheDocument()
})

test('shows cached badge when cached=true', () => {
  const cachedAnswer = { ...answer, meta: { ...answer.meta, cached: true } }
  render(<AssistantBubble answer={cachedAnswer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  expect(screen.getByText('cached')).toBeInTheDocument()
})

test('renders followup buttons when isLast=true', () => {
  render(<AssistantBubble answer={answer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  expect(screen.getByText('How should I split the burst?')).toBeInTheDocument()
})

test('hides followup buttons when isLast=false', () => {
  render(<AssistantBubble answer={answer} time="11:43" isLast={false} onFollowup={jest.fn()} />)
  expect(screen.queryByText('How should I split the burst?')).not.toBeInTheDocument()
})

test('copies the answer text to the clipboard on Copy click', async () => {
  const writeText = jest.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })

  render(<AssistantBubble answer={answer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: /copy/i }))

  expect(writeText).toHaveBeenCalledWith(expect.stringContaining('TV delivers strong ROI'))
})

test('does not render a non-functional Regenerate button', () => {
  render(<AssistantBubble answer={answer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  expect(screen.queryByRole('button', { name: /regenerate/i })).not.toBeInTheDocument()
})

test('citations in older answers do not drive the evidence rail highlight', async () => {
  // The rail always shows the LAST answer's sources — an older answer's [2]
  // pointing at a different document must not highlight the latest source #2.
  const { useStore } = jest.requireActual('@/lib/store')
  render(<AssistantBubble answer={answer} time="11:43" isLast={false} onFollowup={jest.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: '1' }))
  expect(useStore.getState().activeCitation).toBeNull()
})

test('clicking a citation in the latest answer highlights the source and expands a collapsed rail', async () => {
  const { useStore } = jest.requireActual('@/lib/store')
  useStore.setState({ activeCitation: null, railCollapsed: true })
  render(<AssistantBubble answer={answer} time="11:43" isLast={true} onFollowup={jest.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: '1' }))
  expect(useStore.getState().activeCitation).toBe(1)
  expect(useStore.getState().railCollapsed).toBe(false)
})
