import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../index'
import type { Question, QuestionCreate } from '../../../types'

const QUESTIONS_KEY = ['questions']

export interface QuestionsPaginated {
  items: Question[]
  total: number
  skip: number
  limit: number
}

export function useQuestions(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: [...QUESTIONS_KEY, params],
    queryFn: async () => {
      const response = await api.get<QuestionsPaginated>('/questions', { params })
      return response.data
    },
  })
}

export function useQuestion(questionId: string | undefined) {
  return useQuery({
    queryKey: [...QUESTIONS_KEY, questionId],
    queryFn: async () => {
      if (!questionId) return null
      const response = await api.get<Question>(`/questions/${questionId}`)
      return response.data
    },
    enabled: !!questionId,
  })
}

export function useCreateQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: QuestionCreate) => {
      const response = await api.post<Question>('/questions', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUESTIONS_KEY })
    },
  })
}

export function useUpdateQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ questionId, data }: { questionId: string; data: QuestionCreate }) => {
      const response = await api.put<Question>(`/questions/${questionId}`, data)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUESTIONS_KEY })
      queryClient.invalidateQueries({ queryKey: [...QUESTIONS_KEY, variables.questionId] })
    },
  })
}

export function useDeleteQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (questionId: string) => {
      await api.delete(`/questions/${questionId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUESTIONS_KEY })
    },
  })
}

export function useDuplicateQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (questionId: string) => {
      const response = await api.post<Question>(`/questions/${questionId}/duplicate`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUESTIONS_KEY })
    },
  })
}
