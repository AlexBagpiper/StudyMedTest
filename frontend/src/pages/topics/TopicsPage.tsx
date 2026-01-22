import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import { useForm, Controller } from 'react-hook-form'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import {
  useTopics,
  useCreateTopic,
  useUpdateTopic,
  useDeleteTopic,
} from '../../lib/api/hooks/useTopics'
import type { Topic, TopicCreate } from '../../types'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'

export default function TopicsPage() {
  const { user } = useAuth()
  const { t, translateError } = useLocale()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTopic, setEditingTopic] = useState<Topic | undefined>()
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [messageDialog, setMessageDialog] = useState<{ open: boolean; title: string; message: string; severity: 'error' | 'success' }>({
    open: false,
    title: '',
    message: '',
    severity: 'error'
  })

  const { data: topics = [], isLoading, error } = useTopics()

  useEffect(() => {
    if (error) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        message: `${t('topics.loadError')}: ${(error as Error).message}`,
        severity: 'error'
      })
    }
  }, [error, t])
  const createTopic = useCreateTopic()
  const updateTopic = useUpdateTopic()
  const deleteTopic = useDeleteTopic()

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TopicCreate>({
    defaultValues: {
      name: '',
      description: '',
    },
  })

  // Только для teacher и admin
  if (user?.role === 'student') {
    return (
      <Box>
        <Typography variant="h5">{t('topics.accessDenied')}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t('topics.accessDeniedDesc')}
        </Typography>
      </Box>
    )
  }

  const handleCreateClick = () => {
    setEditingTopic(undefined)
    reset({ name: '', description: '' })
    setDialogOpen(true)
  }

  const handleEditClick = (topic: Topic) => {
    setEditingTopic(topic)
    reset({ name: topic.name, description: topic.description || '' })
    setDialogOpen(true)
  }

  const handleDeleteClick = (topicId: string) => {
    setConfirmId(topicId)
  }

  const handleConfirmDelete = async () => {
    if (!confirmId) return
    try {
      await deleteTopic.mutateAsync(confirmId)
      setConfirmId(null)
    } catch (error: any) {
      const message = error.response?.data?.detail 
        ? translateError(error.response.data.detail) 
        : t('common.error')
      setMessageDialog({
        open: true,
        title: t('common.error'),
        message,
        severity: 'error'
      })
    }
  }

  const onSubmit = async (data: TopicCreate) => {
    try {
      if (editingTopic) {
        await updateTopic.mutateAsync({
          topicId: editingTopic.id,
          data,
        })
      } else {
        await createTopic.mutateAsync(data)
      }
      setDialogOpen(false)
      setEditingTopic(undefined)
    } catch (error: any) {
      const message = error.response?.data?.detail 
        ? translateError(error.response.data.detail) 
        : t('common.error')
      setMessageDialog({
        open: true,
        title: t('common.error'),
        message,
        severity: 'error'
      })
    }
  }

  const handleDialogClose = () => {
    setDialogOpen(false)
    setEditingTopic(undefined)
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">{t('topics.title')}</Typography>
        <Button variant="outlined" startIcon={<AddIcon />} onClick={handleCreateClick}>
          {t('topics.create')}
        </Button>
      </Box>

      {topics.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {t('topics.noTopics')}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              sx={{ mt: 2 }}
              onClick={handleCreateClick}
            >
              {t('topics.createFirst')}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {topics.map((topic: Topic) => (
            <Card key={topic.id}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <Box>
                    <Typography variant="h6">{topic.name}</Typography>
                    {topic.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        {topic.description}
                      </Typography>
                    )}
                  </Box>
                  <Box>
                    <IconButton onClick={() => handleEditClick(topic)} size="small" title={t('common.edit')}>
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      onClick={() => handleDeleteClick(topic.id)}
                      size="small"
                      color="error"
                      title={t('common.delete')}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Диалог создания/редактирования */}
      <Dialog open={dialogOpen} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>{editingTopic ? t('topics.edit') : t('topics.create')}</DialogTitle>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Controller
                name="name"
                control={control}
                rules={{ required: t('topics.nameRequired') }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label={t('topics.name')}
                    fullWidth
                    autoFocus
                    error={!!errors.name}
                    helperText={errors.name?.message}
                  />
                )}
              />

              <Controller
                name="description"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label={t('topics.description')}
                    fullWidth
                    multiline
                    rows={3}
                  />
                )}
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleDialogClose}>{t('common.cancel')}</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createTopic.isPending || updateTopic.isPending}
            >
              {createTopic.isPending || updateTopic.isPending
                ? t('topics.saving')
                : editingTopic
                  ? t('topics.update')
                  : t('admin.create')}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <ConfirmDialog
        open={!!confirmId}
        title={t('common.delete')}
        content={t('topics.deleteConfirm')}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
        color="error"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmId(null)}
        isLoading={deleteTopic.isPending}
      />

      <MessageDialog
        open={messageDialog.open}
        title={messageDialog.title}
        content={messageDialog.message}
        onClose={() => setMessageDialog({ ...messageDialog, open: false })}
        severity={messageDialog.severity}
      />
    </Box>
  )
}
