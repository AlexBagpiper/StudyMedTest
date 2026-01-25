import React, { useState } from 'react'
import { 
  Box, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon,
  Paper,
  Divider,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  ListItemSecondaryAction,
  Tooltip
} from '@mui/material'
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import { useAnnotationStore } from './hooks/useAnnotationStore'
import { AnnotationLabel } from '../../types/annotation'
import { ConfirmDialog } from '../common/ConfirmDialog'

interface LabelsPanelProps {
  readOnly?: boolean
}

export const LabelsPanel: React.FC<LabelsPanelProps> = ({ readOnly = false }) => {
  const { labels, activeLabelId, setActiveLabelId, addLabel, updateLabel, deleteLabel } = useAnnotationStore()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingLabel, setEditingLabel] = useState<AnnotationLabel | null>(null)
  const [labelName, setLabelName] = useState('')
  const [labelColor, setLabelColor] = useState('#3B82F6')
  
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [labelToDelete, setLabelToDelete] = useState<string | null>(null)

  const handleOpenDialog = (label?: AnnotationLabel) => {
    if (label) {
      setEditingLabel(label)
      setLabelName(label.name)
      setLabelColor(label.color)
    } else {
      setEditingLabel(null)
      setLabelName('')
      setLabelColor('#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0'))
    }
    setDialogOpen(true)
  }

  const handleSaveLabel = () => {
    if (!labelName.trim()) return

    if (editingLabel) {
      updateLabel(editingLabel.id, labelName.trim(), labelColor)
    } else {
      addLabel(labelName.trim(), labelColor)
    }
    setDialogOpen(false)
  }

  const handleDeleteLabel = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setLabelToDelete(id)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = () => {
    if (labelToDelete) {
      deleteLabel(labelToDelete)
      setLabelToDelete(null)
      setDeleteConfirmOpen(false)
    }
  }

  return (
    <Paper sx={{ width: 280, height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper' }} variant="outlined">
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h6">Структуры</Typography>
          <Typography variant="caption" color="text.secondary">
            Метки для разметки
          </Typography>
        </Box>
        {!readOnly && (
          <Tooltip title="Добавить метку">
            <IconButton onClick={() => handleOpenDialog()} size="small" color="primary">
              <AddIcon />
            </IconButton>
          </Tooltip>
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
            sx={{
              '&.Mui-selected': {
                bgcolor: 'action.selected',
                '&:hover': {
                  bgcolor: 'action.hover',
                }
              }
            }}
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
                  whiteSpace: 'nowrap',
                  pr: readOnly ? 0 : 8
                } 
              }} 
            />
            {!readOnly && (
              <ListItemSecondaryAction>
                <IconButton edge="end" size="small" onClick={() => handleOpenDialog(label)} sx={{ mr: 0.5 }}>
                  <EditIcon fontSize="small" />
                </IconButton>
                <IconButton edge="end" size="small" color="error" onClick={(e) => handleDeleteLabel(e, label.id)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </ListItemSecondaryAction>
            )}
          </ListItem>
        ))}
        {labels.length === 0 && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Нет доступных структур
            </Typography>
            {!readOnly && (
              <Button 
                startIcon={<AddIcon />} 
                size="small" 
                onClick={() => handleOpenDialog()}
                sx={{ mt: 1 }}
              >
                Создать первую
              </Button>
            )}
          </Box>
        )}
      </List>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>{editingLabel ? 'Редактировать метку' : 'Новая метка'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2, minWidth: 300 }}>
            <TextField
              label="Название"
              fullWidth
              value={labelName}
              onChange={(e) => setLabelName(e.target.value)}
              autoFocus
            />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="body2">Цвет:</Typography>
              <input
                type="color"
                value={labelColor}
                onChange={(e) => setLabelColor(e.target.value)}
                style={{ 
                  width: 50, 
                  height: 30, 
                  border: '1px solid #ccc', 
                  borderRadius: 4,
                  cursor: 'pointer'
                }}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Отмена</Button>
          <Button onClick={handleSaveLabel} variant="contained" disabled={!labelName.trim()}>
            Сохранить
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Подтвердите удаление"
        content="Вы уверены, что хотите удалить эту метку и все связанные с ней области?"
        confirmText="Удалить"
        cancelText="Отмена"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirmOpen(false)}
        color="error"
      />
    </Paper>
  )
}
