import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../LoginPage'
import * as AuthContext from '../../../contexts/AuthContext'

// Моки контекстов
vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    login: vi.fn(),
  })),
}))

vi.mock('../../../contexts/LocaleContext', () => ({
  useLocale: () => ({
    t: (key: string) => key,
    translateError: (err: any) => err,
  }),
}))

describe('LoginPage', () => {
  it('renders login form', () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LoginPage />
      </MemoryRouter>
    )
    expect(screen.getByLabelText(/auth.email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/auth.password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /auth.login/i })).toBeInTheDocument()
  })

  it('submits login data', async () => {
    const loginMock = vi.fn().mockResolvedValue({})
    
    // Переопределяем мок для конкретного теста через типизированный AuthContext
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      login: loginMock,
    } as any)

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LoginPage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/auth.email/i), { target: { value: 'test@example.com' } })
    fireEvent.change(screen.getByLabelText(/auth.password/i), { target: { value: 'password' } })
    fireEvent.click(screen.getByRole('button', { name: /auth.login/i }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('test@example.com', 'password')
    })
  })
})
