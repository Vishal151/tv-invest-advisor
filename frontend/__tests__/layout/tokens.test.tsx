import { render } from '@testing-library/react'

test('layout renders children', () => {
  const { container } = render(<div className="test">hello</div>)
  expect(container.textContent).toBe('hello')
})
