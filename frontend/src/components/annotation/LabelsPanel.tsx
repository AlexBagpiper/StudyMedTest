import React, { useState } from 'react'
import { 
  Box, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon,
  IconButton, 
  TextField, 
  Button,
  Paper,
  Divider,
  Tooltip
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord'
import { useAnnotationStore } from './hooks/useAnnotationStore'

interface LabelsPanelProps {
  readOnly?: boolean
}

export const LabelsPanel: React.FC<LabelsPanelProps> = ({ readOnly = false }) => {
  const { labels, addLabel, deleteLabel, activeLabelId, setActiveLabelId } = useAnnotationStore()
  const [newLabelName, setNewLabelName] = useState('')

  const handleAddLabel = () => {
    if (!newLabelName.trim()) return
    
    // Генерируем случайный яркий цвет
    const colors = [
      '#FF5733', '#33FF57', '#3357FF', '#F333FF', '#33FFF3', 
      '#F3FF33', '#FF3385', '#33FFBD', '#FF8C33', '#8C33FF'
    ]
    const randomColor = colors[Math.floor(Math.random() * colors.length)]
    
    addLabel(newLabelName, randomColor)
    setNewLabelName('')
  }

  return (
    <Paper sx={{ width: 280, height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper' }} variant="outlined">
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>Структуры</Typography>
        {!readOnly && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              size="small"
              placeholder="Название..."
              value={newLabelName}
              onChange={(e) => setNewLabelName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddLabel()}
              fullWidth
            />
            <IconButton color="primary" onClick={handleAddLabel}>
              <AddIcon />
            </IconButton>
          </Box>
        )}
      </Box>
      <Divider />
      <List sx={{ flex: 1, overflow: 'auto' }}>
        {labels.map((label) => (
          <ListItem 
            key={label.id}
            button
            selected={activeLabelId === label.id}
            onClick={() => setActiveLabelId(label.id)}
            secondaryAction={
              !readOnly && (
                <IconButton edge="end" size="small" onClick={(e) => {
                  e.stopPropagation()
                  deleteLabel(label.id)
                }}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              )
            }
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <FiberManualRecordIcon sx={{ color: label.color }} />
            </ListItemIcon>
            <ListItemText 
              primary={label.name} 
              primaryTypographyProps={{ 
                variant: 'body2',
                sx: { 
                  fontWeight: activeLabelId === label.id ? 700 : 400,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                } 
              }} 
            />
          </ListItem>
        ))}
        {labels.length === 0 && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Нет добавленных структур
            </Typography>
          </Box>
        )}
      </List>
    </Paper>
  )
}
