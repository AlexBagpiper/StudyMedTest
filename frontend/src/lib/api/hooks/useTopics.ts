import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../index'
import type { Topic, TopicCreate } from '../../../types'

const TOPICS_KEY = ['topics']

export function useTopics() {
  return useQuery({
    queryKey: TOPICS_KEY,
    queryFn: async () => {
      const response = await api.get<Topic[]>('/topics')
      return response.data
    },
  })
}

export function useTopic(topicId: string | undefined) {
  return useQuery({
    queryKey: [...TOPICS_KEY, topicId],
    queryFn: async () => {
      if (!topicId) return null
      const response = await api.get<Topic>(`/topics/${topicId}`)
      return response.data
    },
    enabled: !!topicId,
  })
}

export function useCreateTopic() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: TopicCreate) => {
      const response = await api.post<Topic>('/topics', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TOPICS_KEY })
    },
  })
}

export function useUpdateTopic() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ topicId, data }: { topicId: string; data: TopicCreate }) => {
      const response = await api.put<Topic>(`/topics/${topicId}`, data)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: TOPICS_KEY })
      queryClient.invalidateQueries({ queryKey: [...TOPICS_KEY, variables.topicId] })
    },
  })
}

export function useDeleteTopic() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (topicId: string) => {
      await api.delete(`/topics/${topicId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TOPICS_KEY })
    },
  })
}
