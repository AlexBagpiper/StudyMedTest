import React, { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'

interface User {
  id: string
  email: string
  last_name: string
  first_name: string
  middle_name: string | null
  role: 'admin' | 'teacher' | 'student'
  is_active: boolean
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, lastName: string, firstName: string, middleName?: string) => Promise<void>
  verifyEmail: (email: string, code: string) => Promise<void>
  resendVerification: (email: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    // Проверка текущего пользователя при загрузке
    const token = localStorage.getItem('access_token')
    if (token) {
      loadUser()
    } else {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadUser = async () => {
    try {
      const response = await api.get('/users/me')
      setUser(response.data)
    } catch (error) {
      console.error('Failed to load user:', error)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      // Очистка кеша при ошибке авторизации
      queryClient.clear()
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)

    const response = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    const { access_token, refresh_token } = response.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)

    // Очистка кеша при смене пользователя
    queryClient.clear()

    await loadUser()
    navigate('/')
  }

  const register = async (email: string, password: string, lastName: string, firstName: string, middleName?: string) => {
    await api.post('/auth/register', {
      email,
      password,
      last_name: lastName,
      first_name: firstName,
      middle_name: middleName || null,
    })
  }

  const verifyEmail = async (email: string, code: string) => {
    await api.post('/auth/verify-email', { email, code })
  }

  const resendVerification = async (email: string) => {
    await api.post('/auth/resend-verification', { email })
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    
    // Очистка всего кеша React Query
    queryClient.clear()
    
    navigate('/login')
  }

  const value = {
    user,
    isLoading,
    login,
    register,
    verifyEmail,
    resendVerification,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

