import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TestFormPage from '../TestFormPage'

vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    user: { id: 'user-1', role: 'teacher' },
  })),
}))

vi.mock('../../../contexts/LocaleContext', () => ({
  useLocale: () => ({
    t: (key: string) => key,
    locale: 'ru',
  }),
}))

const mockTopics = [{ id: 'topic-1', name: 'Topic A' }]
const mockQuestions = [
  {
    id: 'q1',
    content: 'Question one?',
    type: 'text' as const,
    difficulty: 1,
    created_at: '2025-01-02T00:00:00Z',
    topic_id: 'topic-1',
    topic: mockTopics[0],
  },
  {
    id: 'q2',
    content: 'Question two?',
    type: 'text' as const,
    difficulty: 2,
    created_at: '2025-01-01T00:00:00Z',
    topic_id: 'topic-1',
    topic: mockTopics[0],
  },
]

vi.mock('../../../lib/api/hooks/useTopics', () => ({
  useTopics: vi.fn(() => ({ data: mockTopics })),
}))

vi.mock('../../../lib/api/hooks/useQuestions', () => ({
  useQuestions: vi.fn(() => ({
    data: { items: mockQuestions, total: 2, skip: 0, limit: 1000 },
    isLoading: false,
  })),
}))

vi.mock('../../../lib/api/hooks/useTests', () => ({
  useTest: vi.fn(() => ({ data: undefined, isLoading: false })),
  useCreateTest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateTest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  usePublishTest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}))

function renderTestForm(route = '/tests/new') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/tests/new" element={<TestFormPage />} />
          <Route path="/tests/:testId/edit" element={<TestFormPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('TestFormPage — fixed and available questions', () => {
  it('shows fixed questions alert when no questions selected', () => {
    renderTestForm()
    expect(screen.getByText(/Конкретные вопросы не добавлены/)).toBeInTheDocument()
  })

  it('has button to add fixed question', () => {
    renderTestForm()
    expect(screen.getByRole('button', { name: /Добавить конкретный вопрос/ })).toBeInTheDocument()
  })

  it('opens available questions block with filters and pagination when clicking add question', async () => {
    renderTestForm()
    fireEvent.click(screen.getByRole('button', { name: /Добавить конкретный вопрос/ }))
    await waitFor(() => {
      expect(screen.getByText('Доступные вопросы')).toBeInTheDocument()
    })
    expect(screen.getByText('Question one?')).toBeInTheDocument()
    expect(screen.getByText('Question two?')).toBeInTheDocument()
    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes.length).toBeGreaterThanOrEqual(1)
  })

  it('available questions are sorted by created_at (newest first)', async () => {
    renderTestForm()
    fireEvent.click(screen.getByRole('button', { name: /Добавить конкретный вопрос/ }))
    await waitFor(() => {
      expect(screen.getByText('Question one?')).toBeInTheDocument()
    })
    const rows = screen.getAllByRole('row').filter((r) => r.textContent?.includes('Question'))
    expect(rows.length).toBeGreaterThanOrEqual(2)
    const firstRow = rows[0]
    const secondRow = rows[1]
    expect(firstRow.textContent).toMatch(/Question one\?/)
    expect(secondRow.textContent).toMatch(/Question two\?/)
  })

  it('fixed questions table has no pagination when rendered with data', async () => {
    const useTest = await import('../../../lib/api/hooks/useTests').then((m) => m.useTest)
    vi.mocked(useTest).mockReturnValue({
      data: {
        id: 'test-1',
        title: 'Test',
        status: 'draft',
        author_id: 'user-1',
        test_questions: [
          {
            question_id: 'q1',
            order: 0,
            question: { ...mockQuestions[0], content: 'Fixed Q' },
          },
        ],
      },
      isLoading: false,
    } as any)
    renderTestForm('/tests/test-1/edit')
    await waitFor(() => {
      expect(screen.getByText('Fixed Q')).toBeInTheDocument()
    })
    const paginations = document.querySelectorAll('.MuiTablePagination-root')
    expect(paginations.length).toBe(0)
    vi.mocked(useTest).mockReturnValue({ data: undefined, isLoading: false } as any)
  })
})
