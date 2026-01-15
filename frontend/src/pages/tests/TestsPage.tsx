import {
  Box,
  Typography,
  Button,
  Grid,
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
import type { Test, TestStatus } from '../../types'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'

export default function TestsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isStudent = user?.role === 'student'

  const { data: tests = [], isLoading, error } = useTests()
  const deleteTest = useDeleteTest()

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

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          {isStudent ? 'Доступные тесты' : 'Мои тесты'}
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
        <Alert severity="error" sx={{ mb: 2 }}>
          Ошибка загрузки тестов: {error instanceof Error ? error.message : 'Неизвестная ошибка'}
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : tests.length === 0 ? (
        <Card>
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
        <Grid container spacing={3}>
          {tests.map((test: Test) => (
            <Grid item xs={12} md={6} key={test.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {test.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {test.description || 'Без описания'}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    <Chip
                      label={getStatusLabel(test.status)}
                      size="small"
                      color={getStatusColor(test.status)}
                    />
                    {test.test_questions && (
                      <Chip
                        label={`${test.test_questions.length} вопросов`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </CardContent>
                <CardActions>
                  <Button size="small" onClick={() => navigate(`/tests/${test.id}`)}>
                    {isStudent ? 'Начать тест' : 'Просмотр'}
                  </Button>
                  {!isStudent && (
                    <>
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
                    </>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  )
}

