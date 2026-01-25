import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Paper,
  IconButton,
  Chip,
  Grid,
  Divider,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Rating,
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import { useTest } from '../../lib/api/hooks'
import { usePublishTest, useUnpublishTest, useStartTest } from '../../lib/api/hooks/useTests'
import { useTopics } from '../../lib/api/hooks/useTopics'
import type { TestStatus, Question } from '../../types'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import EditIcon from '@mui/icons-material/Edit'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PublishIcon from '@mui/icons-material/Publish'
import UnpublishedIcon from '@mui/icons-material/Unpublished'
import VisibilityIcon from '@mui/icons-material/Visibility'
import TextFieldsIcon from '@mui/icons-material/TextFields'
import ImageIcon from '@mui/icons-material/Image'
import QuestionFormDialog from '../../components/questions/QuestionFormDialog'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'

export default function TestDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t } = useLocale()

  const { data: test, isLoading, error } = useTest(id)
  const { data: topics } = useTopics()
  const publishTest = usePublishTest()
  const unpublishTest = useUnpublishTest()
  const startTest = useStartTest()

  const [viewingQuestion, setViewingQuestion] = useState<Question | undefined>()
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    content: string;
    onConfirm: () => void;
    color: 'primary' | 'error' | 'success' | 'warning';
    isLoading: boolean;
  }>({
    open: false,
    title: '',
    content: '',
    onConfirm: () => {},
    color: 'primary',
    isLoading: false
  })
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })

  const closeConfirm = () => setConfirmDialog(prev => ({ ...prev, open: false }))

  const isStudent = user?.role === 'student'
  const isAuthor = test?.author_id === user?.id

  useEffect(() => {
    if (isStudent) {
      navigate('/tests', { replace: true })
    }
  }, [isStudent, navigate])

  const handlePublish = () => {
    if (!id) return
    setConfirmDialog({
      open: true,
      title: t('tests.action.publish'),
      content: t('tests.confirm.publish'),
      color: 'success',
      isLoading: false,
      onConfirm: async () => {
        try {
          await publishTest.mutateAsync(id)
          closeConfirm()
        } catch (error) {
          console.error('Failed to publish test:', error)
        }
      }
    })
  }

  const handleUnpublish = () => {
    if (!id) return
    setConfirmDialog({
      open: true,
      title: t('tests.action.unpublish'),
      content: t('tests.confirm.unpublish'),
      color: 'warning',
      isLoading: false,
      onConfirm: async () => {
        try {
          await unpublishTest.mutateAsync(id)
          closeConfirm()
        } catch (error) {
          console.error('Failed to unpublish test:', error)
        }
      }
    })
  }

  const handleStartTest = () => {
    if (!id) return

    setConfirmDialog({
      open: true,
      title: t('tests.confirm.start.title'),
      content: t('tests.confirm.start.content'),
      color: 'primary',
      isLoading: false,
      onConfirm: async () => {
        try {
          const submission = await startTest.mutateAsync(id)
          closeConfirm()
          navigate(`/submissions/${submission.id}`)
        } catch (error: any) {
          console.error('Failed to start test:', error)
          const message = error.response?.data?.detail || t('tests.error.unknown')
          setErrorDialog({ open: true, message })
          closeConfirm()
        }
      }
    })
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !test) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/tests')} sx={{ mb: 2 }}>
          {t('tests.backToTests')}
        </Button>
        <Alert severity="error">{t('tests.error.load')}</Alert>
      </Box>
    )
  }

  const getStatusLabel = (status: TestStatus) => {
    const statusMap: Record<TestStatus, string> = {
      draft: t('tests.status.draft'),
      published: t('tests.status.published'),
      archived: t('tests.status.archived'),
    }
    return statusMap[status]
  }

  const getStatusColor = (status: TestStatus): 'default' | 'success' | 'warning' => {
    const colorMap: Record<TestStatus, 'default' | 'success' | 'warning'> = {
      draft: 'default',
      published: 'success',
      archived: 'warning',
    }
    return colorMap[status]
  }

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/tests')} sx={{ mb: 2 }}>
        {t('tests.backToTests')}
      </Button>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {test.title}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip label={getStatusLabel(test.status)} color={getStatusColor(test.status)} />
              {test.test_questions && test.test_questions.length > 0 && (
                <Chip label={`${test.test_questions.length} ${t('tests.fixedQuestions')}`} variant="outlined" />
              )}
              {test.structure && test.structure.length > 0 && (
                <Chip 
                  label={`${test.structure.reduce((acc: number, curr: any) => acc + curr.count, 0)} ${t('tests.dynamicQuestions')}`} 
                  variant="outlined" 
                />
              )}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            {isStudent && test.status === 'published' && (
              <Button
                variant="outlined"
                startIcon={<PlayArrowIcon />}
                onClick={handleStartTest}
                size="large"
              >
                {t('tests.action.start')}
              </Button>
            )}

            {!isStudent && isAuthor && (
              <>
                {test.status === 'draft' && (
                  <>
                    <Button
                      variant="outlined"
                      startIcon={<EditIcon />}
                      onClick={() => navigate(`/tests/${id}/edit`)}
                    >
                      {t('common.edit')}
                    </Button>
                    <Button
                      variant="outlined"
                      color="success"
                      startIcon={<PublishIcon />}
                      onClick={handlePublish}
                      disabled={publishTest.isPending}
                    >
                      {t('tests.action.publish')}
                    </Button>
                  </>
                )}
                {test.status === 'published' && (
                  <Button
                    variant="outlined"
                    color="warning"
                    startIcon={<UnpublishedIcon />}
                    onClick={handleUnpublish}
                    disabled={unpublishTest.isPending}
                  >
                    {t('tests.action.unpublish')}
                  </Button>
                )}
              </>
            )}
          </Box>
        </Box>

        {test.description && (
          <Typography variant="body1" color="text.secondary" paragraph>
            {test.description}
          </Typography>
        )}

        <Divider sx={{ my: 3 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              {t('tests.settings')}
            </Typography>
            <Box sx={{ mt: 1 }}>
              {test.settings?.time_limit && (
                <Typography variant="body2">
                  {t('tests.timeLimitDesc').replace('{count}', test.settings.time_limit.toString())}
                </Typography>
              )}
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              {t('tests.info')}
            </Typography>
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2">
                {t('tests.createdAt')}: {new Date(test.created_at).toLocaleDateString('ru-RU')}
              </Typography>
              {test.published_at && (
                <Typography variant="body2">
                  {t('tests.publishedAt')}: {new Date(test.published_at).toLocaleDateString('ru-RU')}
                </Typography>
              )}
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {test.structure && test.structure.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t('tests.structure')}
          </Typography>
          <Grid container spacing={2}>
            {test.structure.map((rule: any, index: number) => {
              const topic = topics?.find((t) => t.id === rule.topic_id)
              return (
                <Grid item xs={12} key={index}>
                  <Card variant="outlined">
                    <CardContent sx={{ py: 2, '&:last-child': { pb: 2 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {t('tests.topic')}: {topic?.name || rule.topic_id}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                            <Chip label={`${t('tests.type')}: ${rule.question_type}`} size="small" variant="outlined" />
                            <Chip label={`${t('tests.count')}: ${rule.count}`} size="small" color="primary" variant="outlined" />
                            <Chip label={`${t('tests.difficulty')}: ${rule.difficulty}`} size="small" variant="outlined" />
                          </Box>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              )
            })}
          </Grid>
        </Paper>
      )}

      {test.test_questions && test.test_questions.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t('tests.fixedTitle')}
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                  <TableRow>
                    <TableCell width={40}>#</TableCell>
                    <TableCell width={50}>{t('admin.type')}</TableCell>
                    <TableCell>{t('admin.content')}</TableCell>
                    <TableCell width={150}>{t('questions.topic')}</TableCell>
                    <TableCell width={100}>{t('questions.difficulty')}</TableCell>
                    <TableCell width={80} align="right">{t('admin.actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {test.test_questions.map((tq: any, index: number) => (
                    <TableRow key={tq.id} hover>
                      <TableCell>{index + 1}</TableCell>
                      <TableCell>
                        <Tooltip title={tq.question?.type === 'text' ? t('questions.type.text') : t('questions.type.imageAnnotation')}>
                          {tq.question?.type === 'text' ? <TextFieldsIcon fontSize="small" color="primary" /> : <ImageIcon fontSize="small" color="primary" />}
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{
                          display: '-webkit-box',
                          WebkitLineClamp: 1,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          fontWeight: 500
                        }}>
                          {tq.question?.content}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {tq.question?.topic ? (
                          <Chip label={tq.question.topic.name} size="small" variant="outlined" />
                        ) : (
                          <Typography variant="caption" color="text.disabled">{t('questions.noTopic')}</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Rating value={tq.question?.difficulty || 1} readOnly size="small" />
                      </TableCell>
                      <TableCell align="right">
                      <Tooltip title={t('questions.viewTitle')}>
                        <IconButton 
                          size="small" 
                          onClick={() => {
                            setViewingQuestion(tq.question)
                            setViewDialogOpen(true)
                          }}
                        >
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      <QuestionFormDialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        onSubmit={() => {}}
        question={viewingQuestion}
        readOnly
      />

      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.title}
        content={confirmDialog.content}
        confirmText={t('common.confirm')}
        cancelText={t('common.cancel')}
        color={confirmDialog.color}
        onConfirm={confirmDialog.onConfirm}
        onCancel={closeConfirm}
        isLoading={publishTest.isPending || unpublishTest.isPending || startTest.isPending}
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

