import { queryApi } from '@/lib/api'

const mockFetch = jest.fn()
global.fetch = mockFetch

beforeEach(() => mockFetch.mockReset())

test('queryApi maps flat response to Answer shape', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      answer: 'TV delivers £5.61 ROI.\n\nSecond paragraph.',
      sources: [{ title: 'Profit Ability 2', chunk: 'TV delivered...', url: 'https://thinkbox.tv' }],
      cached: false,
      model_used: 'gpt-4o',
    }),
  })

  const result = await queryApi({
    question: 'When does TV work?',
    brief: { sector: 'FMCG', brandStage: 'scale-up', tvHistory: 'tried', primaryGoal: 'brand', budgetTier: '500k-2m' },
  })

  expect(result.kind).toBe('answer')
  if (result.kind !== 'answer') return
  expect(result.answer.summary).toHaveLength(2)
  expect(result.answer.summary[0]).toBe('TV delivers £5.61 ROI.')
  expect(result.answer.sources).toHaveLength(1)
  expect(result.answer.sources[0].title).toBe('Profit Ability 2')
  expect(result.answer.meta.model).toBe('gpt-4o')
  expect(result.answer.meta.cached).toBe(false)
})

test('queryApi returns refusal on 400', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'Query is outside the scope of this tool.' }),
  })

  const result = await queryApi({ question: 'Write me a poem', brief: null })
  expect(result.kind).toBe('refusal')
})

test('queryApi returns error on 503', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 503,
    json: async () => ({ detail: 'The answer service is temporarily unavailable.' }),
  })

  const result = await queryApi({ question: 'Does TV work?', brief: null })
  expect(result.kind).toBe('error')
})
