import {
  Card,
  CardContent,
  Typography,
  Chip,
  Box,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material'
import { useState } from 'react'
import MoreVertIcon from '@mui/icons-material/MoreVert'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import TextFieldsIcon from '@mui/icons-material/TextFields'
import ImageIcon from '@mui/icons-material/Image'
import type { Question } from '../../types'
import { ConfirmDialog } from '../common/ConfirmDialog'
import { useLocale } from '../../contexts/LocaleContext'

interface QuestionCardProps {
  question: Question
  onEdit: (question: Question) => void
  onDelete: (questionId: string) => void
}

export default function QuestionCard({ question, onEdit, onDelete }: QuestionCardProps) {
  const { t } = useLocale()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleEdit = () => {
    handleMenuClose()
    onEdit(question)
  }

  const handleDelete = () => {
    handleMenuClose()
    setConfirmOpen(true)
  }

  const handleConfirmDelete = () => {
    setConfirmOpen(false)
    onDelete(question.id)
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'text':
        return t('questions.type.text')
      case 'image_annotation':
        return t('questions.type.imageAnnotation')
      default:
        return type
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'text':
        return <TextFieldsIcon />
      case 'image_annotation':
        return <ImageIcon />
      default:
        return null
    }
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
              <Chip
                icon={getTypeIcon(question.type) || undefined}
                label={getTypeLabel(question.type)}
                size="small"
                color="primary"
                variant="outlined"
              />
              {question.topic && (
                <Chip
                  label={question.topic.name}
                  size="small"
                  color="secondary"
                  variant="outlined"
                />
              )}
            </Box>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                mb: 1,
              }}
            >
              {question.content}
            </Typography>
            {question.type === 'text' && question.reference_data?.reference_answer && (
              <Box
                sx={{
                  mt: 1,
                  p: 1,
                  bgcolor: 'success.50',
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'success.200',
                }}
              >
                <Typography variant="caption" color="success.700" sx={{ fontWeight: 600 }}>
                  {t('questions.referenceAnswer')}:
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {question.reference_data.reference_answer}
                </Typography>
              </Box>
            )}
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              {t('admin.createdAt')}: {new Date(question.created_at).toLocaleDateString('ru-RU')}
            </Typography>
          </Box>
          <IconButton onClick={handleMenuOpen} size="small">
            <MoreVertIcon />
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
            <MenuItem onClick={handleEdit}>
              <EditIcon sx={{ mr: 1 }} fontSize="small" />
              {t('common.edit')}
            </MenuItem>
            <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
              <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
              {t('common.delete')}
            </MenuItem>
          </Menu>
        </Box>
      </CardContent>

      <ConfirmDialog
        open={confirmOpen}
        title={t('questions.deleteTitle')}
        content={t('questions.deleteConfirm')}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
        color="error"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </Card>
  )
}
