import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useTests, useDeleteTest } from '../../lib/api/hooks'
import { useStartTest } from '../../lib/api/hooks/useTests'
import { useSubmissions } from '../../lib/api/hooks/useSubmissions'
import type { Test, TestStatus, Submission } from '../../types'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import AccessTimeIcon from '@mui/icons-material/AccessTime'

export default function TestsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isStudent = user?.role === 'student'

  const { data: tests = [], isLoading, error } = useTests()
  const { data: submissions = [] } = useSubmissions({ student_id: user?.id })
  const deleteTest = useDeleteTest()
  const startTest = useStartTest()

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

    try {
      const submission = await startTest.mutateAsync(testId)
      navigate(`/submissions/${submission.id}`)
    } catch (error: any) {
      console.error('Failed to start test:', error)
      const message = error.response?.data?.detail || 'Не удалось начать тест'
      alert(message)
    }
  }

  const handleDelete = async (testId: string) => {
    if (window.confirm('Вы уверены, что хотите удалить этот тест?')) {
      try {
        await deleteTest.mutateAsync(testId)
      } catch (error) {
        console.error('Failed to delete test:', error)
      }
    }
  }

  const getStatusLabel = (status: TestStatus) => {
    const statusMap: Record<TestStatus, string> = {
      draft: 'Черновик',
      published: 'Опубликован',
      archived: 'Архивирован',
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
            label="В процессе"
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
            label={submission.status === 'completed' ? `Завершено (${submission.result?.total_score || 0})` : 'На проверке'}
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
          {isStudent ? 'Доступные тесты' : 'Управление тестами'}
        </Typography>
        {!isStudent && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/tests/create')}
          >
            Создать тест
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Ошибка загрузки тестов: {error instanceof Error ? error.message : 'Неизвестная ошибка'}
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : tests.length === 0 ? (
        <Card sx={{ borderRadius: 1 }}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {isStudent ? 'Нет доступных тестов' : 'У вас пока нет тестов'}
            </Typography>
            {!isStudent && (
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                sx={{ mt: 2 }}
                onClick={() => navigate('/tests/create')}
              >
                Создать первый тест
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
                        {test.description || 'Описание отсутствует'}
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
                            label={`${test.test_questions.length} вопросов`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {test.settings?.time_limit && (
                          <Chip
                            icon={<AccessTimeIcon sx={{ fontSize: '16px !important' }} />}
                            label={`${test.settings.time_limit} мин`}
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
                          variant="contained"
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
                          {isInProgress ? 'Продолжить' : isCompleted ? 'Завершено' : 'Начать тест'}
                        </Button>
                      </Box>
                    )}
                  </Box>
                </CardContent>
                
                {!isStudent && (
                  <CardActions sx={{ px: 3, pb: 2, pt: 0, justifyContent: 'flex-end' }}>
                    <Button 
                      size="small" 
                      variant="outlined"
                      onClick={() => navigate(`/tests/${test.id}`)}
                    >
                      Просмотр
                    </Button>
                    <Button
                      size="small"
                      startIcon={<EditIcon />}
                      onClick={() => navigate(`/tests/${test.id}/edit`)}
                    >
                      Редактировать
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={() => handleDelete(test.id)}
                      disabled={deleteTest.isPending}
                    >
                      Удалить
                    </Button>
                  </CardActions>
                )}
              </Card>
            )
          })}
        </Box>
      )}
    </Box>
  )
}

