import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  TextField,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton as MuiIconButton,
  Chip,
  Tooltip,
  Rating,
  TablePagination,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import SearchIcon from '@mui/icons-material/Search'
import VisibilityIcon from '@mui/icons-material/Visibility'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import TextFieldsIcon from '@mui/icons-material/TextFields'
import ImageIcon from '@mui/icons-material/Image'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import {
  useQuestions,
  useCreateQuestion,
  useUpdateQuestion,
  useDeleteQuestion,
  useDuplicateQuestion,
} from '../../lib/api/hooks/useQuestions'
import { useTopics } from '../../lib/api/hooks/useTopics'
import QuestionFormDialog from '../../components/questions/QuestionFormDialog'
import type { Question, QuestionCreate, QuestionType } from '../../types'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'
import { TablePaginationActions } from '../../components/common/TablePaginationActions'
import { TruncatedContentTooltip } from '../../components/common/TruncatedContentTooltip'

export default function QuestionsPage() {
  const { user } = useAuth()
  const { t, translateError, locale } = useLocale()
  const [typeFilter, setTypeFilter] = useState<QuestionType | ''>('')
  const [topicFilter, setTopicFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] = useState<Question | undefined>()
  const [isViewOnly, setIsViewOnly] = useState(false)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(25)

  const { data: paginated, isLoading, error } = useQuestions({
    skip: page * pageSize,
    limit: pageSize
  })
  const questions = paginated?.items ?? []
  const total = paginated?.total ?? 0
  const { data: topics = [] } = useTopics()

  useEffect(() => {
    if (error) {
      setErrorDialog({
        open: true,
        message: `${t('common.error')}: ${(error as Error).message}`
      })
    }
  }, [error, t])
  const createQuestion = useCreateQuestion()
  const updateQuestion = useUpdateQuestion()
  const deleteQuestion = useDeleteQuestion()
  const duplicateQuestion = useDuplicateQuestion()

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
    setEditingQuestion(undefined)
    setIsViewOnly(false)
    setDialogOpen(true)
  }

  const handleViewClick = (question: Question) => {
    setEditingQuestion(question)
    setIsViewOnly(true)
    setDialogOpen(true)
  }

  const handleEditClick = (question: Question) => {
    setEditingQuestion(question)
    setIsViewOnly(false)
    setDialogOpen(true)
  }

  const handleDuplicateClick = async (questionId: string) => {
    try {
      const newQuestion = await duplicateQuestion.mutateAsync(questionId)
      setEditingQuestion(newQuestion)
      setIsViewOnly(false)
      setDialogOpen(true)
    } catch (error: any) {
      console.error('Failed to duplicate question:', error)
      setErrorDialog({
        open: true,
        message: translateError(error.response?.data?.detail)
      })
    }
  }

  const handleDeleteClick = (questionId: string) => {
    setConfirmId(questionId)
  }

  const handleConfirmDelete = async () => {
    if (!confirmId) return
    try {
      await deleteQuestion.mutateAsync(confirmId)
      setConfirmId(null)
    } catch (error: any) {
      console.error('Failed to delete question:', error)
      setErrorDialog({
        open: true,
        message: translateError(error.response?.data?.detail)
      })
    }
  }

  const handleFormSubmit = async (data: QuestionCreate) => {
    try {
      if (editingQuestion) {
        await updateQuestion.mutateAsync({
          questionId: editingQuestion.id,
          data,
        })
      } else {
        await createQuestion.mutateAsync(data)
      }
      setDialogOpen(false)
      setEditingQuestion(undefined)
    } catch (error: any) {
      console.error('Failed to save question:', error)
      setErrorDialog({
        open: true,
        message: translateError(error.response?.data?.detail)
      })
    }
  }

  const handleDialogClose = () => {
    setDialogOpen(false)
    setEditingQuestion(undefined)
  }

  // Фильтрация вопросов
  const filteredQuestions = questions.filter((q: Question) => {
    const matchesType = !typeFilter || q.type === typeFilter
    const matchesTopic = !topicFilter || q.topic_id === topicFilter
    const matchesSearch =
      !searchQuery ||
      q.content.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesType && matchesTopic && matchesSearch
  })

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
        <Typography variant="h4">{t('questions.bank')}</Typography>
        <Button variant="outlined" startIcon={<AddIcon />} onClick={handleCreateClick}>
          {t('questions.create')}
        </Button>
      </Box>

      {/* Фильтры */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          placeholder={t('questions.searchPlaceholder')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ flex: 1, minWidth: 250 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <FormControl sx={{ minWidth: 180 }}>
          <InputLabel>{t('questions.topic')}</InputLabel>
          <Select
            value={topicFilter}
            label={t('questions.topic')}
            onChange={(e) => setTopicFilter(e.target.value)}
          >
            <MenuItem value="">{t('questions.allTopics')}</MenuItem>
            {topics.map((topic: any) => (
              <MenuItem key={topic.id} value={topic.id}>
                {topic.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl sx={{ minWidth: 180 }}>
          <InputLabel>{t('questions.type')}</InputLabel>
          <Select
            value={typeFilter}
            label={t('questions.type')}
            onChange={(e) => setTypeFilter(e.target.value as QuestionType | '')}
          >
            <MenuItem value="">{t('questions.allTypes')}</MenuItem>
            <MenuItem value="text">{t('questions.type.text')}</MenuItem>
            <MenuItem value="image_annotation">{t('questions.type.imageAnnotation')}</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Список вопросов */}
      {filteredQuestions.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {questions.length === 0 ? t('questions.emptyBank') : t('questions.noResults')}
            </Typography>
            {questions.length === 0 && (
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                sx={{ mt: 2 }}
                onClick={handleCreateClick}
              >
                {t('questions.createFirst')}
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width={50}>{t('admin.type')}</TableCell>
                <TableCell>{t('admin.content')}</TableCell>
                <TableCell width={150}>{t('questions.topic')}</TableCell>
                <TableCell width={100}>Сложность</TableCell>
                <TableCell width={120}>{t('questions.date')}</TableCell>
                <TableCell width={120} align="right">{t('admin.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredQuestions.map((question: Question) => (
                <TableRow key={question.id} hover>
                  <TableCell>
                    <Tooltip title={question.type === 'text' ? t('questions.type.text') : t('questions.type.imageAnnotation')}>
                      {question.type === 'text' ? <TextFieldsIcon fontSize="small" color="primary" /> : <ImageIcon fontSize="small" color="primary" />}
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <TruncatedContentTooltip content={question.content} />
                  </TableCell>
                  <TableCell>
                    {question.topic ? (
                      <Chip label={question.topic.name} size="small" variant="outlined" />
                    ) : (
                      <Typography variant="caption" color="text.disabled">{t('questions.noTopic')}</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Rating value={question.difficulty} readOnly size="small" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {new Date(question.created_at).toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Tooltip title={t('questions.viewTitle')}>
                        <MuiIconButton size="small" onClick={() => handleViewClick(question)}>
                          <VisibilityIcon fontSize="small" />
                        </MuiIconButton>
                      </Tooltip>
                      <Tooltip title={t('questions.duplicateTitle') || 'Duplicate'}>
                        <MuiIconButton 
                          size="small" 
                          onClick={() => handleDuplicateClick(question.id)}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </MuiIconButton>
                      </Tooltip>
                      {/* Teacher can only edit/delete their own questions or if they are admin */}
                      {(user?.role === 'admin' || question.author_id === user?.id) ? (
                        <>
                          <Tooltip title={t('questions.editTitle')}>
                            <MuiIconButton size="small" onClick={() => handleEditClick(question)}>
                              <EditIcon fontSize="small" />
                            </MuiIconButton>
                          </Tooltip>
                          <Tooltip title={t('questions.deleteTitle')}>
                            <MuiIconButton size="small" color="error" onClick={() => handleDeleteClick(question.id)}>
                              <DeleteIcon fontSize="small" />
                            </MuiIconButton>
                          </Tooltip>
                        </>
                      ) : (
                        <Tooltip title={t('questions.adminReadOnly')}>
                          <span>
                            <MuiIconButton size="small" disabled>
                              <EditIcon fontSize="small" />
                            </MuiIconButton>
                          </span>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(e) => {
              setPageSize(Number(e.target.value))
              setPage(0)
            }}
            rowsPerPageOptions={[10, 25, 50, 100, 500]}
            labelRowsPerPage={t('admin.rowsPerPage')}
            labelDisplayedRows={({ from, to, count }) =>
              `${from}–${to} ${locale === 'ru' ? 'из' : 'of'} ${count !== -1 ? count : `>${to}`}`}
            ActionsComponent={TablePaginationActions}
            sx={{
              borderTop: 1,
              borderColor: 'divider',
              alignItems: 'center',
              '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': { mt: 0, mb: 0 },
              '& .MuiTablePagination-toolbar': { minHeight: 52, paddingRight: 2 },
            }}
          />
        </TableContainer>
      )}

      {/* Диалог создания/редактирования/просмотра */}
      <QuestionFormDialog
        open={dialogOpen}
        onClose={handleDialogClose}
        onSubmit={handleFormSubmit}
        question={editingQuestion}
        isLoading={createQuestion.isPending || updateQuestion.isPending}
        readOnly={isViewOnly}
      />

      <ConfirmDialog
        open={!!confirmId}
        title={t('questions.deleteTitle')}
        content={t('questions.deleteConfirm')}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
        color="error"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmId(null)}
        isLoading={deleteQuestion.isPending}
      />

      <MessageDialog
        open={errorDialog.open}
        title={t('common.error')}
        content={errorDialog.message}
        onClose={() => setErrorDialog({ ...errorDialog, open: false })}
        severity="error"
      />
    </Box>
  )
}

