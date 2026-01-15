import React from 'react'
import { 
  Paper, 
  ToggleButtonGroup, 
  ToggleButton, 
  Tooltip, 
  Divider,
  IconButton
} from '@mui/material'
import PanToolIcon from '@mui/icons-material/PanTool'
import NearMeIcon from '@mui/icons-material/NearMe'
import HexagonIcon from '@mui/icons-material/Hexagon'
import RectangleIcon from '@mui/icons-material/Rectangle'
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord'
import AdjustIcon from '@mui/icons-material/Adjust'
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep'
import SaveIcon from '@mui/icons-material/Save'
import UndoIcon from '@mui/icons-material/Undo'
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
        gap: 1, 
        bgcolor: 'background.paper',
        alignItems: 'center'
      }} 
      variant="outlined"
    >
      <ToggleButtonGroup
        orientation="vertical"
        value={mode}
        exclusive
        onChange={handleModeChange}
        size="small"
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

        <Divider sx={{ my: 0.5, width: '80%' }} />

        {!readOnly && (
          <>
            <Tooltip title="Многоугольник" placement="left">
              <ToggleButton value="polygon">
                <HexagonIcon fontSize="small" />
              </ToggleButton>
            </Tooltip>

            <Tooltip title="Прямоугольник" placement="left">
              <ToggleButton value="rectangle">
                <RectangleIcon fontSize="small" />
              </ToggleButton>
            </Tooltip>

            <Tooltip title="Эллипс" placement="left">
              <ToggleButton value="ellipse">
                <AdjustIcon fontSize="small" />
              </ToggleButton>
            </Tooltip>

            <Tooltip title="Точка" placement="left">
              <ToggleButton value="point">
                <FiberManualRecordIcon fontSize="small" />
              </ToggleButton>
            </Tooltip>

            <Divider sx={{ my: 0.5, width: '80%' }} />

            <Tooltip title="Ластик" placement="left">
              <ToggleButton value="eraser">
                <DeleteSweepIcon fontSize="small" color="error" />
              </ToggleButton>
            </Tooltip>
          </>
        )}
      </ToggleButtonGroup>

      {!readOnly && onSave && (
        <>
          <Divider sx={{ my: 0.5, width: '80%' }} />
          <Tooltip title="Сохранить" placement="left">
            <IconButton color="primary" onClick={onSave} size="small">
              <SaveIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </>
      )}
    </Paper>
  )
}
