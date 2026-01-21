import React from 'react'
import { 
  Box, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon,
  Paper,
  Divider
} from '@mui/material'
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord'
import { useAnnotationStore } from './hooks/useAnnotationStore'

interface LabelsPanelProps {
  readOnly?: boolean
}

export const LabelsPanel: React.FC<LabelsPanelProps> = ({ readOnly = false }) => {
  const { labels, activeLabelId, setActiveLabelId } = useAnnotationStore()

  return (
    <Paper sx={{ width: 280, height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper' }} variant="outlined">
      <Box sx={{ p: 2 }}>
        <Typography variant="h6">Структуры</Typography>
        <Typography variant="caption" color="text.secondary">
          Выбор из существующих категорий
        </Typography>
      </Box>
      <Divider />
      <List sx={{ flex: 1, overflow: 'auto' }}>
        {labels.map((label) => (
          <ListItem 
            key={label.id}
            button
            selected={activeLabelId === label.id}
            onClick={() => setActiveLabelId(label.id)}
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
              Нет доступных структур
            </Typography>
          </Box>
        )}
      </List>
    </Paper>
  )
}
