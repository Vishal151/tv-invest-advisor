import { render, screen } from '@testing-library/react'
import { CueApp } from '@/components/layout/CueApp'

jest.mock('@/components/layout/Topbar', () => ({ Topbar: () => <div data-testid="topbar" /> }))
jest.mock('@/components/rail/CorpusRail', () => ({ CorpusRail: () => <div data-testid="corpus-rail" /> }))
jest.mock('@/components/rail/EvidenceRail', () => ({ EvidenceRail: () => <div data-testid="evidence-rail" /> }))
jest.mock('@/components/composer/Composer', () => ({ Composer: () => <div data-testid="composer" /> }))

test('renders topbar, thread area, and rail', () => {
  render(<CueApp />)
  expect(screen.getByTestId('topbar')).toBeInTheDocument()
  expect(screen.getByTestId('composer')).toBeInTheDocument()
})
