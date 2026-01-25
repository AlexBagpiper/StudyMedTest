import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../index'

const SUBMISSIONS_KEY = ['submissions']

export function useSubmissions(params?: any, options?: any) {
  return useQuery<any[]>({
    queryKey: [...SUBMISSIONS_KEY, params],
    queryFn: async () => {
      const response = await api.get('/submissions', { params })
      return response.data
    },
    ...options,
  })
}

export function useSubmission(submissionId: string | undefined) {
  return useQuery({
    queryKey: [...SUBMISSIONS_KEY, submissionId],
    queryFn: async () => {
      if (!submissionId) return null
      const response = await api.get(`/submissions/${submissionId}`)
      return response.data
    },
    enabled: !!submissionId,
  })
}

export function useSubmitAnswer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      submissionId,
      questionId,
      answer,
    }: {
      submissionId: string
      questionId: string
      answer: any
    }) => {
      const response = await api.post(`/submissions/${submissionId}/answers`, {
        question_id: questionId,
        answer,
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [...SUBMISSIONS_KEY, variables.submissionId] })
    },
  })
}

export function useCompleteSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (submissionId: string) => {
      const response = await api.post(`/submissions/${submissionId}/submit`)
      return response.data
    },
    onSuccess: (_, submissionId) => {
      queryClient.invalidateQueries({ queryKey: [...SUBMISSIONS_KEY, submissionId] })
      queryClient.invalidateQueries({ queryKey: SUBMISSIONS_KEY })
    },
  })
}

export function useSubmitTest() {
  return useCompleteSubmission()
}

export function useDeleteSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (submissionId: string) => {
      await api.delete(`/submissions/${submissionId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUBMISSIONS_KEY })
    },
  })
}

export function useBulkDeleteSubmissions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (submissionIds: string[]) => {
      await api.post('/submissions/bulk-delete', { submission_ids: submissionIds })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUBMISSIONS_KEY })
    },
  })
}

export function useHideSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (submissionId: string) => {
      const response = await api.patch(`/submissions/${submissionId}/hide`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUBMISSIONS_KEY })
    },
  })
}

export function useRestoreSubmission() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (submissionId: string) => {
      const response = await api.patch(`/submissions/${submissionId}/restore`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUBMISSIONS_KEY })
    },
  })
}
