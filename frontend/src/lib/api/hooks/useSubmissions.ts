import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../index'

const SUBMISSIONS_KEY = ['submissions']

export interface SubmissionsPaginated {
  items: any[]
  total: number
  skip: number
  limit: number
}

export function useSubmissions(params?: Record<string, unknown> & { skip?: number; limit?: number }, options?: any) {
  return useQuery<SubmissionsPaginated>({
    queryKey: [...SUBMISSIONS_KEY, params],
    queryFn: async () => {
      const response = await api.get<SubmissionsPaginated>('/submissions', { params })
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

export function useLogSubmissionEvent() {
  return useMutation({
    mutationFn: async ({
      submissionId,
      eventType,
      details,
    }: {
      submissionId: string
      eventType: string
      details?: any
    }) => {
      await api.post(`/submissions/${submissionId}/events`, {
        event_type: eventType,
        details,
      })
    },
  })
}

export function useGrantRetake() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ submissionId, comment }: { submissionId: string, comment?: string }) => {
      const response = await api.post(`/submissions/${submissionId}/grant-retake`, null, {
        params: comment ? { comment } : {}
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUBMISSIONS_KEY })
      queryClient.invalidateQueries({ queryKey: ['tests'] })
      queryClient.invalidateQueries({ queryKey: ['retake-permissions'] })
    },
  })
}

export function useMyRetakePermissions() {
  return useQuery<any[]>({
    queryKey: ['retake-permissions', 'my'],
    queryFn: async () => {
      const response = await api.get('/submissions/retake-permissions/my')
      return response.data
    },
  })
}
