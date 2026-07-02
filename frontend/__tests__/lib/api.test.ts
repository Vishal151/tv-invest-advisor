import { queryApi } from '@/lib/api'

const mockFetch = jest.fn()
global.fetch = mockFetch

beforeEach(() => mockFetch.mockReset())

test('queryApi maps structured response to Answer shape', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      answer: {
        summary: ['TV delivers £5.61 ROI.', 'Second paragraph.'],
        stats: [{ value: '£5.61', unit: 'ROI per £1 spent', context: 'Average across 141 brands', source: 'Profit Ability 2', page: 12 }],
        chart: null,
        followups: [],
      },
      sources: [{ title: 'Profit Ability 2', chunk: 'TV delivered...', url: 'https://thinkbox.tv', page: 12, topic: 'ROI', distance: 0.12 }],
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
  expect(result.answer.stats).toHaveLength(1)
  expect(result.answer.stats[0].value).toBe('£5.61')
  expect(result.answer.stats[0].unit).toBe('ROI per £1 spent')
  expect(result.answer.stats[0].context).toBe('Average across 141 brands')
  expect(result.answer.stats[0].source).toBe('Profit Ability 2')
  expect(result.answer.stats[0].page).toBe(12)
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

test('queryApi returns a rate-limit message on 429, not a model-failure message', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 429,
    headers: { get: () => null },
    json: async () => ({ detail: 'Rate limit exceeded' }),
  })

  const result = await queryApi({ question: 'Does TV work?', brief: null })
  expect(result.kind).toBe('error')
  if (result.kind !== 'error') return
  expect(result.message).toMatch(/wait/i)
  expect(result.message).not.toMatch(/language model/i)
})

test('queryApi uses the X-Request-ID response header as the error reference', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 503,
    headers: { get: (k: string) => (k.toLowerCase() === 'x-request-id' ? 'req-123' : null) },
    json: async () => ({ detail: 'unavailable' }),
  })

  const result = await queryApi({ question: 'Does TV work?', brief: null })
  expect(result.kind).toBe('error')
  if (result.kind !== 'error') return
  expect(result.reference).toBe('req-123')
})

test('queryApi returns an error result when a 200 body is not valid JSON', async () => {
  // A proxy can return 200 with an HTML error page — this must not reject
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => {
      throw new SyntaxError('Unexpected token < in JSON')
    },
  })

  const result = await queryApi({ question: 'Does TV work?', brief: null })
  expect(result.kind).toBe('error')
})

test('queryApi returns an error result when a 200 body has the wrong shape', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({ unexpected: 'shape' }),
  })

  const result = await queryApi({ question: 'Does TV work?', brief: null })
  expect(result.kind).toBe('error')
})
