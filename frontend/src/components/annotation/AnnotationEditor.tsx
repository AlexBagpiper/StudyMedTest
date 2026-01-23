import React, { useEffect, useRef } from 'react'
import { 
  Box, 
  Typography, 
  IconButton, 
  Divider, 
  Button
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import { FabricCanvas } from './FabricCanvas'
import { Toolbar } from './Toolbar'
import { LabelsPanel } from './LabelsPanel'
import { useAnnotationStore } from './hooks/useAnnotationStore'
import { AnnotationData } from '../../types/annotation'

interface AnnotationEditorProps {
  imageUrl: string
  initialData?: AnnotationData
  referenceData?: AnnotationData | null
  showReference?: boolean
  onChange?: (data: AnnotationData) => void
  readOnly?: boolean
  hideLabels?: boolean
}

export const AnnotationEditor: React.FC<AnnotationEditorProps> = ({ 
  imageUrl, 
  initialData, 
  referenceData = null,
  showReference = false,
  onChange,
  readOnly = false,
  hideLabels = false
}) => {
  const { 
    labels, 
    annotations, 
    setData, 
    reset, 
    activeLabelId, 
    setActiveLabelId,
    zoom,
    zoomIn,
    zoomOut,
    resetZoom,
    setMode
  } = useAnnotationStore()

  useEffect(() => {
    if (readOnly) {
      setMode('hand')
    }
  }, [readOnly, setMode])

  // Track previous data to prevent infinite loops
  const prevInitialDataRef = useRef<string | null>(null)
  const prevOnChangeDataRef = useRef<string | null>(null)
  
  useEffect(() => {
    // Serialize for comparison to detect actual changes (prevents infinite loops)
    const serialized = initialData ? JSON.stringify({
      labels: initialData.labels?.map(l => l.id),
      annotations: initialData.annotations?.map(a => a.id)
    }) : null
    
    if (serialized === prevInitialDataRef.current) {
      return
    }
    prevInitialDataRef.current = serialized
    
    if (initialData) {
      setData(initialData)
      if (hideLabels && !activeLabelId && initialData.labels?.length > 0) {
        setActiveLabelId(initialData.labels[0].id)
      }
    } else {
      reset()
    }
  }, [initialData, setData, reset, hideLabels, setActiveLabelId])

  // Сообщаем родителю об изменениях (с защитой от бесконечных циклов)
  useEffect(() => {
    if (onChange && !readOnly) {
      const serialized = JSON.stringify({
        labels: labels.map(l => ({ id: l.id, name: l.name, color: l.color })),
        annotations: annotations.map(a => ({ id: a.id, label_id: a.label_id, type: a.type, points: a.points }))
      })
      
      if (serialized === prevOnChangeDataRef.current) {
        return
      }
      prevOnChangeDataRef.current = serialized
      
      onChange({ labels, annotations })
    }
  }, [labels, annotations, onChange, readOnly])

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', bgcolor: '#f5f5f5' }}>
      <Box sx={{ display: 'flex', gap: 1, flex: 1, width: '100%', overflow: 'hidden', p: 1 }}>
        {!hideLabels && <LabelsPanel readOnly={readOnly} />}
        
        <Box sx={{ flex: 1, minWidth: 0, position: 'relative', display: 'flex', gap: 1, height: '100%' }}>
          <Box sx={{ flex: 1, minWidth: 0, position: 'relative', overflow: 'hidden', height: '100%' }}>
            <FabricCanvas 
              imageUrl={imageUrl} 
              readOnly={readOnly} 
              referenceData={referenceData}
              showReference={showReference}
            />
          </Box>
          <Toolbar readOnly={readOnly} />
        </Box>
      </Box>

      {/* Футер с инструментами зума */}
      <Box sx={{ 
        height: 56, 
        bgcolor: '#ffffff', 
        display: 'flex', 
        alignItems: 'center', 
        px: 2, 
        gap: 1,
        borderTop: '1px solid #e0e0e0'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, bgcolor: '#f5f5f5', borderRadius: 1.5, px: 1.5, py: 0.5, border: '1px solid #e0e0e0' }}>
          <Typography sx={{ color: '#333', fontSize: '0.875rem', minWidth: 45, textAlign: 'center', fontWeight: 500 }}>
            {Math.round(zoom * 100)}%
          </Typography>
          <Divider orientation="vertical" flexItem sx={{ bgcolor: '#ddd', mx: 0.5 }} />
          <IconButton onClick={zoomOut} size="small" sx={{ color: '#666', '&:hover': { bgcolor: '#e0e0e0' } }}>
            <RemoveIcon fontSize="inherit" />
          </IconButton>
          <IconButton onClick={zoomIn} size="small" sx={{ color: '#666', '&:hover': { bgcolor: '#e0e0e0' } }}>
            <AddIcon fontSize="inherit" />
          </IconButton>
          <Button 
            onClick={resetZoom} 
            size="small" 
            sx={{ 
              color: '#00d2be', 
              fontSize: '0.75rem', 
              minWidth: 'auto',
              ml: 0.5,
              textTransform: 'uppercase',
              fontWeight: 600,
              '&:hover': { bgcolor: 'transparent', color: '#00b3a3' }
            }}
          >
            Reset
          </Button>
        </Box>
      </Box>
    </Box>
  )
}
