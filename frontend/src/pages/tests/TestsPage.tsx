import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import { useTests, useDeleteTest } from '../../lib/api/hooks'
import { useStartTest, usePublishTest, useUnpublishTest } from '../../lib/api/hooks/useTests'
import { useSubmissions } from '../../lib/api/hooks/useSubmissions'
import type { Test, TestStatus, Submission } from '../../types'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'
import { useState, useEffect } from 'react'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import PublishIcon from '@mui/icons-material/Publish'
import UnpublishedIcon from '@mui/icons-material/Unpublished'
import VisibilityIcon from '@mui/icons-material/Visibility'

export default function TestsPage() {
  const { user } = useAuth()
  const { t } = useLocale()
  const navigate = useNavigate()
  const isStudent = user?.role === 'student'

  const { data: tests = [], isLoading, error } = useTests()
  const { data: submissions = [] } = useSubmissions({ student_id: user?.id })

  useEffect(() => {
    if (error) {
      setErrorDialog({
        open: true,
        message: `${t('tests.error.load')}: ${error instanceof Error ? error.message : t('tests.error.unknown')}`
      })
    }
  }, [error, t])
  const deleteTest = useDeleteTest()
  const startTest = useStartTest()
  const publishTest = usePublishTest()
  const unpublishTest = useUnpublishTest()

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

  const handlePublish = (testId: string) => {
    setConfirmDialog({
      open: true,
      title: t('tests.action.publish'),
      content: t('tests.confirm.publish'),
      color: 'success',
      isLoading: false,
      onConfirm: async () => {
        try {
          await publishTest.mutateAsync(testId)
          closeConfirm()
        } catch (error) {
          console.error('Failed to publish test:', error)
        }
      }
    })
  }

  const handleUnpublish = (testId: string) => {
    setConfirmDialog({
      open: true,
      title: t('tests.action.unpublish'),
      content: t('tests.confirm.unpublish'),
      color: 'warning',
      isLoading: false,
      onConfirm: async () => {
        try {
          await unpublishTest.mutateAsync(testId)
          closeConfirm()
        } catch (error) {
          console.error('Failed to unpublish test:', error)
        }
      }
    })
  }

  const handleDelete = (testId: string) => {
    setConfirmDialog({
      open: true,
      title: t('common.delete'),
      content: t('tests.confirm.delete'),
      color: 'error',
      isLoading: false,
      onConfirm: async () => {
        try {
          await deleteTest.mutateAsync(testId)
          closeConfirm()
        } catch (error: any) {
          console.error('Failed to delete test:', error)
          const message = error.response?.data?.detail || t('tests.error.unknown')
          setErrorDialog({ open: true, message })
        }
      }
    })
  }

  const getSubmissionForTest = (testId: string) => {
    // Временный хак: так как Submission связан с Variant, а Variant с Test,
    // на бэкенде в list_submissions мы можем фильтровать по test_id.
    // Пока просто найдем в загруженных сабмишнах.
    // Примечание: на бэкенде сабмишн через джойн TestVariant связан с Test.
    return submissions.find((s: any) => s.test_id === testId || s.variant?.test_id === testId)
  }

  const handleStartTest = async (testId: string) => {
    const existingSubmission = getSubmissionForTest(testId)
    if (existingSubmission && existingSubmission.status === 'in_progress') {
      navigate(`/submissions/${existingSubmission.id}`)
      return
    }

    setConfirmDialog({
      open: true,
      title: t('tests.confirm.start.title'),
      content: t('tests.confirm.start.content'),
      color: 'primary',
      isLoading: false,
      onConfirm: async () => {
        try {
          const submission = await startTest.mutateAsync(testId)
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

  const getStatusLabel = (status: TestStatus) => {
    const statusMap: Record<TestStatus, string> = {
      draft: t('tests.status.draft'),
      published: t('tests.status.published'),
      archived: t('tests.status.archived'),
    }
    return statusMap[status]
  }

  const getStatusColor = (status: TestStatus): 'default' | 'primary' | 'success' | 'warning' => {
    const colorMap: Record<TestStatus, 'default' | 'primary' | 'success' | 'warning'> = {
      draft: 'default',
      published: 'success',
      archived: 'warning',
    }
    return colorMap[status]
  }

  const getSubmissionStatusChip = (testId: string) => {
    const submission = getSubmissionForTest(testId)
    if (!submission) return null

    switch (submission.status) {
      case 'in_progress':
        return (
          <Chip
            icon={<AccessTimeIcon />}
            label={t('tests.submission.inProgress')}
            color="warning"
            variant="outlined"
            size="small"
          />
        )
      case 'completed':
      case 'evaluating':
        return (
          <Chip
            icon={<CheckCircleOutlineIcon />}
            label={submission.status === 'completed' 
              ? `${t('tests.submission.completed')} (${submission.result?.total_score || 0})` 
              : t('tests.submission.evaluating')}
            color="success"
            variant="outlined"
            size="small"
          />
        )
      default:
        return null
    }
  }

  return (
    <Box sx={{ width: '100%', py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" fontWeight="bold">
          {isStudent ? t('tests.title.student') : t('tests.title.admin')}
        </Typography>
        {!isStudent && (
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => navigate('/tests/create')}
          >
            {t('tests.create')}
          </Button>
        )}
      </Box>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : tests.length === 0 ? (
        <Card sx={{ borderRadius: 1 }}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {isStudent ? t('tests.noTests.student') : t('tests.noTests.admin')}
            </Typography>
            {!isStudent && (
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                sx={{ mt: 2 }}
                onClick={() => navigate('/tests/create')}
              >
                {t('tests.createFirst')}
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {tests.map((test: Test) => {
            const submission = getSubmissionForTest(test.id)
            const isCompleted = submission?.status === 'completed' || submission?.status === 'evaluating'
            const isInProgress = submission?.status === 'in_progress'

            return (
              <Card key={test.id} sx={{ borderRadius: 1, transition: '0.3s', '&:hover': { boxShadow: 6 } }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h5" gutterBottom fontWeight="600">
                        {test.title}
                      </Typography>
                      <Typography variant="body1" color="text.secondary" sx={{ mb: 2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {test.description || t('tests.description.empty')}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                        {!isStudent && (
                          <Chip
                            label={getStatusLabel(test.status)}
                            size="small"
                            color={getStatusColor(test.status)}
                            sx={{ fontWeight: '500' }}
                          />
                        )}
                        {test.test_questions && (
                          <Chip
                            label={t('tests.questionsCount').replace('{count}', test.test_questions.length.toString())}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {test.settings?.time_limit && (
                          <Chip
                            icon={<AccessTimeIcon sx={{ fontSize: '16px !important' }} />}
                            label={t('tests.timeLimit').replace('{count}', test.settings.time_limit.toString())}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {isStudent && getSubmissionStatusChip(test.id)}
                      </Box>
                    </Box>

                    {isStudent && (
                      <Box sx={{ ml: 3, display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Button
                          variant="outlined"
                          size="large"
                          onClick={() => handleStartTest(test.id)}
                          disabled={startTest.isPending || (isCompleted && !isInProgress)}
                          sx={{ 
                            px: 4, 
                            py: 1.5, 
                            borderRadius: 1,
                            textTransform: 'none',
                            fontSize: '1.1rem',
                            fontWeight: '600',
                            boxShadow: 2
                          }}
                        >
                          {isInProgress ? t('tests.action.continue') : isCompleted ? t('tests.action.completed') : t('tests.action.start')}
                        </Button>
                      </Box>
                    )}
                  </Box>
                </CardContent>
                
                {!isStudent && (
                  <CardActions sx={{ px: 3, pb: 2, pt: 0, justifyContent: 'flex-end', gap: 1 }}>
                    <Button 
                      size="small" 
                      variant="outlined"
                      startIcon={<VisibilityIcon />}
                      onClick={() => navigate(`/tests/${test.id}`)}
                    >
                      {t('tests.action.view')}
                    </Button>
                    {test.status === 'draft' ? (
                      <Button
                        size="small"
                        variant="outlined"
                        color="success"
                        startIcon={<PublishIcon />}
                        onClick={() => handlePublish(test.id)}
                        disabled={publishTest.isPending}
                      >
                        {t('tests.action.publish')}
                      </Button>
                    ) : test.status === 'published' ? (
                      <Button
                        size="small"
                        variant="outlined"
                        color="warning"
                        startIcon={<UnpublishedIcon />}
                        onClick={() => handleUnpublish(test.id)}
                        disabled={unpublishTest.isPending}
                      >
                        {t('tests.action.unpublish')}
                      </Button>
                    ) : null}
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<EditIcon />}
                      onClick={() => navigate(`/tests/${test.id}/edit`)}
                    >
                      {t('common.edit')}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={() => handleDelete(test.id)}
                      disabled={deleteTest.isPending}
                    >
                      {t('common.delete')}
                    </Button>
                  </CardActions>
                )}
              </Card>
            )
          })}
        </Box>
      )}

      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.title}
        content={confirmDialog.content}
        confirmText={t('common.confirm')}
        cancelText={t('common.cancel')}
        color={confirmDialog.color}
        onConfirm={confirmDialog.onConfirm}
        onCancel={closeConfirm}
        isLoading={publishTest.isPending || unpublishTest.isPending || deleteTest.isPending || startTest.isPending}
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

