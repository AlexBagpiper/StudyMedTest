import axios from 'axios'

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token } = response.data
          localStorage.setItem('access_token', access_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api

// Admin API functions
export const adminApi = {
  // LLM Config
  getLLMConfig: async () => {
    const response = await api.get('/admin/system/llm-config')
    return response.data
  },

  updateLLMConfig: async (config: any) => {
    const response = await api.put('/admin/system/llm-config', config)
    return response.data
  },

  testLLMConfig: async (config: any) => {
    const response = await api.post('/admin/system/llm-config/test', config)
    return response.data
  },

  // CV Config
  getCVConfig: async () => {
    const response = await api.get('/admin/system/cv-config')
    return response.data
  },

  updateCVConfig: async (config: any) => {
    const response = await api.put('/admin/system/cv-config', config)
    return response.data
  },

  // Users Management
  getUsers: async (params?: any) => {
    const response = await api.get('/admin/users', { params })
    return response.data
  },

  updateUser: async (userId: string, data: any) => {
    const response = await api.put(`/admin/users/${userId}`, data)
    return response.data
  },

  deleteUser: async (userId: string) => {
    const response = await api.delete(`/admin/users/${userId}`)
    return response.data
  },

  // Analytics
  getAnalytics: async () => {
    const response = await api.get('/admin/analytics')
    return response.data
  },

  // User Creation
  createUser: async (userData: any) => {
    const response = await api.post('/admin/users', userData)
    return response.data
  },

  // Bulk Delete Users
  bulkDeleteUsers: async (userIds: string[]) => {
    const response = await api.post('/admin/users/bulk-delete', { user_ids: userIds })
    return response.data
  },

  // Revaluate Submission
  revaluateSubmission: async (submissionId: string) => {
    const response = await api.post(`/admin/submissions/${submissionId}/revaluate`)
    return response.data
  },
}

// Questions API
export const questionsApi = {
  uploadImage: async (file: File, annotations?: any) => {
    const formData = new FormData()
    formData.append('file', file)
    if (annotations) {
      formData.append('coco_annotations', JSON.stringify(annotations))
    }
    const response = await api.post('/questions/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  uploadAnnotations: async (imageId: string, annotations: any) => {
    const response = await api.post(`/questions/images/${imageId}/annotations`, {
      coco_annotations: annotations,
    })
    return response.data
  },

  deleteImage: async (imageId: string) => {
    const response = await api.delete(`/questions/images/${imageId}`)
    return response.data
  },
}
