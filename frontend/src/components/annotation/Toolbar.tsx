import React from 'react'
import { 
  Paper, 
  ToggleButtonGroup, 
  ToggleButton, 
  Tooltip, 
  IconButton
} from '@mui/material'
import PanToolIcon from '@mui/icons-material/PanTool'
import NearMeIcon from '@mui/icons-material/NearMe'
import PolylineIcon from '@mui/icons-material/Polyline'
import CropSquareIcon from '@mui/icons-material/CropSquare'
import SaveIcon from '@mui/icons-material/Save'
import { useAnnotationStore } from './hooks/useAnnotationStore'
import { EditorMode } from '../../../types/annotation'

interface ToolbarProps {
  onSave?: () => void
  readOnly?: boolean
}

export const Toolbar: React.FC<ToolbarProps> = ({ onSave, readOnly = false }) => {
  const { mode, setMode } = useAnnotationStore()

  const handleModeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newMode: EditorMode | null,
  ) => {
    if (newMode !== null) {
      setMode(newMode)
    }
  }

  return (
    <Paper 
      sx={{ 
        p: 0.5, 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 0.5, 
        bgcolor: 'transparent',
        alignItems: 'center',
        borderRadius: 2,
        boxShadow: 'none'
      }} 
      variant="elevation"
      elevation={0}
    >
      <ToggleButtonGroup
        orientation="vertical"
        value={mode}
        exclusive
        onChange={handleModeChange}
        size="small"
        sx={{
          '& .MuiToggleButton-root': {
            border: '1px solid #e0e0e0',
            borderRadius: '8px !important',
            color: '#666',
            bgcolor: '#ffffff',
            width: 40,
            height: 40,
            margin: '1px 0',
            '&.Mui-selected': {
              bgcolor: '#00d2be',
              color: '#fff',
              borderColor: '#00d2be',
              '&:hover': {
                bgcolor: '#00b3a3',
              }
            },
            '&:hover': {
              bgcolor: '#f5f5f5',
            }
          }
        }}
      >
        <Tooltip title="Выделение (V)" placement="left">
          <ToggleButton value="select">
            <NearMeIcon fontSize="small" />
          </ToggleButton>
        </Tooltip>
        
        <Tooltip title="Рука (H)" placement="left">
          <ToggleButton value="hand">
            <PanToolIcon fontSize="small" />
          </ToggleButton>
        </Tooltip>

        {!readOnly && (
          <>
            <Tooltip title="Полигон" placement="left">
              <ToggleButton value="polygon">
                <PolylineIcon fontSize="small" />
              </ToggleButton>
            </Tooltip>

            <Tooltip title="Прямоугольник" placement="left">
              <ToggleButton value="rectangle">
                <CropSquareIcon fontSize="small" />
              </ToggleButton>
            </Tooltip>
          </>
        )}
      </ToggleButtonGroup>

      {!readOnly && onSave && (
        <Tooltip title="Сохранить" placement="left">
          <IconButton 
            color="primary" 
            onClick={onSave} 
            size="small"
            sx={{ 
              bgcolor: '#ffffff',
              border: '1px solid #e0e0e0',
              borderRadius: '8px',
              '&:hover': {
                bgcolor: '#f5f5f5'
              }
            }}
          >
            <SaveIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Paper>
  )
}
