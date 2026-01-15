import React, { useEffect } from 'react'
import { Box, Paper } from '@mui/material'
import { FabricCanvas } from './FabricCanvas'
import { Toolbar } from './Toolbar'
import { LabelsPanel } from './LabelsPanel'
import { useAnnotationStore } from './hooks/useAnnotationStore'
import { AnnotationData } from '../../../types/annotation'

interface AnnotationEditorProps {
  imageUrl: string
  initialData?: AnnotationData
  onChange?: (data: AnnotationData) => void
  readOnly?: boolean
}

export const AnnotationEditor: React.FC<AnnotationEditorProps> = ({ 
  imageUrl, 
  initialData, 
  onChange,
  readOnly = false 
}) => {
  const { labels, annotations, setData, reset } = useAnnotationStore()

  useEffect(() => {
    if (initialData) {
      setData(initialData)
    } else {
      reset()
    }
  }, [initialData, setData, reset])

  // Сообщаем родителю об изменениях
  useEffect(() => {
    if (onChange && !readOnly) {
      onChange({ labels, annotations })
    }
  }, [labels, annotations, onChange, readOnly])

  return (
    <Box sx={{ display: 'flex', gap: 2, height: '600px', width: '100%' }}>
      <LabelsPanel readOnly={readOnly} />
      
      <Box sx={{ flex: 1, position: 'relative', display: 'flex' }}>
        <FabricCanvas imageUrl={imageUrl} readOnly={readOnly} />
        
        <Box sx={{ position: 'absolute', right: 10, top: 10 }}>
          <Toolbar readOnly={readOnly} />
        </Box>
      </Box>
    </Box>
  )
}
