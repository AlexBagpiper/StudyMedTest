import React, { createContext, useContext, useState, useCallback } from 'react'
import { Backdrop, CircularProgress } from '@mui/material'

interface LoadingContextType {
  showLoading: (show: boolean) => void
  isLoading: boolean
}

const LoadingContext = createContext<LoadingContextType | undefined>(undefined)

export function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(false)

  const showLoading = useCallback((show: boolean) => {
    setIsLoading(show)
  }, [])

  return (
    <LoadingContext.Provider value={{ showLoading, isLoading }}>
      {children}
      <Backdrop
        sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 2000 }}
        open={isLoading}
      >
        <CircularProgress color="inherit" />
      </Backdrop>
    </LoadingContext.Provider>
  )
}

export function useLoading() {
  const context = useContext(LoadingContext)
  if (context === undefined) {
    throw new Error('useLoading must be used within a LoadingProvider')
  }
  return context
}
