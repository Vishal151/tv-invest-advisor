import { render, screen, fireEvent } from '@testing-library/react'
import { Composer } from '@/components/composer/Composer'
import type { Brief } from '@/lib/types'

const brief: Brief = {
  sector: 'FMCG', brandStage: 'scale-up',
  tvHistory: 'tried', primaryGoal: 'brand', budgetTier: '500k-2m',
}

test('renders textarea and Send button', () => {
  render(<Composer brief={brief} setBrief={jest.fn()} value="" onChange={jest.fn()} onSubmit={jest.fn()} disabled={false} />)
  expect(screen.getByRole('textbox')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /ask/i })).toBeInTheDocument()
})

test('Send button is disabled when value is empty', () => {
  render(<Composer brief={brief} setBrief={jest.fn()} value="" onChange={jest.fn()} onSubmit={jest.fn()} disabled={false} />)
  expect(screen.getByRole('button', { name: /ask/i })).toBeDisabled()
})

test('calls onSubmit on Enter keydown', async () => {
  const onSubmit = jest.fn()
  render(<Composer brief={brief} setBrief={jest.fn()} value="Does TV work?" onChange={jest.fn()} onSubmit={onSubmit} disabled={false} />)
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', code: 'Enter' })
  expect(onSubmit).toHaveBeenCalled()
})

test('does not submit on Shift+Enter', async () => {
  const onSubmit = jest.fn()
  render(<Composer brief={brief} setBrief={jest.fn()} value="text" onChange={jest.fn()} onSubmit={onSubmit} disabled={false} />)
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', shiftKey: true })
  expect(onSubmit).not.toHaveBeenCalled()
})

test('Ask stays disabled for questions under 5 characters (backend minimum)', () => {
  render(<Composer brief={brief} setBrief={jest.fn()} value="Hi" onChange={jest.fn()} onSubmit={jest.fn()} disabled={false} />)
  expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled()
})

test('Enter does not submit questions under 5 characters', () => {
  const onSubmit = jest.fn()
  render(<Composer brief={brief} setBrief={jest.fn()} value="Hi" onChange={jest.fn()} onSubmit={onSubmit} disabled={false} />)
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', code: 'Enter' })
  expect(onSubmit).not.toHaveBeenCalled()
})

test('textarea caps input at the backend maximum of 500 characters', () => {
  render(<Composer brief={brief} setBrief={jest.fn()} value="" onChange={jest.fn()} onSubmit={jest.fn()} disabled={false} />)
  expect(screen.getByRole('textbox')).toHaveAttribute('maxLength', '500')
})
