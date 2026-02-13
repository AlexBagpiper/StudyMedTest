import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../index'
import type { Test } from '../../../types'

const TESTS_KEY = ['tests']

export function useTests(params?: any) {
  return useQuery({
    queryKey: [...TESTS_KEY, params],
    queryFn: async () => {
      const response = await api.get<Test[]>('/tests', { params })
      return response.data
    },
  })
}

export function useTest(testId: string | undefined) {
  return useQuery({
    queryKey: [...TESTS_KEY, testId],
    queryFn: async () => {
      if (!testId) return null
      const response = await api.get<Test>(`/tests/${testId}`)
      return response.data
    },
    enabled: !!testId,
  })
}

export function useCreateTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post<Test>('/tests', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TESTS_KEY })
    },
  })
}

export function useUpdateTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ testId, data }: { testId: string; data: any }) => {
      const response = await api.put<Test>(`/tests/${testId}`, data)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: TESTS_KEY })
      queryClient.invalidateQueries({ queryKey: [...TESTS_KEY, variables.testId] })
    },
  })
}

export function useDeleteTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (testId: string) => {
      await api.delete(`/tests/${testId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TESTS_KEY })
    },
  })
}

export function useStartTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (testId: string) => {
      const response = await api.post(`/tests/${testId}/start`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] })
    },
  })
}

export function usePublishTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (testId: string) => {
      const response = await api.post(`/tests/${testId}/publish`)
      return response.data
    },
    onSuccess: (_, testId) => {
      queryClient.invalidateQueries({ queryKey: TESTS_KEY })
      queryClient.invalidateQueries({ queryKey: [...TESTS_KEY, testId] })
    },
  })
}

export function useUnpublishTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (testId: string) => {
      const response = await api.post(`/tests/${testId}/unpublish`)
      return response.data
    },
    onSuccess: (_, testId) => {
      queryClient.invalidateQueries({ queryKey: TESTS_KEY })
      queryClient.invalidateQueries({ queryKey: [...TESTS_KEY, testId] })
    },
  })
}

export function useDuplicateTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (testId: string) => {
      const response = await api.post<Test>(`/tests/${testId}/duplicate`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TESTS_KEY })
    },
  })
}
