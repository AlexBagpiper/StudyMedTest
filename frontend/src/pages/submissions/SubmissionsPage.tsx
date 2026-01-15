import { 
  Box, 
  Typography, 
  Card, 
  CardContent, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Chip, 
  Button, 
  IconButton,
  Tooltip,
  Paper, 
  CircularProgress,
  Alert
} from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useSubmissions, useDeleteSubmission } from '../../lib/api/hooks/useSubmissions'
import DeleteIcon from '@mui/icons-material/Delete'

export default function SubmissionsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const deleteSubmission = useDeleteSubmission()
  
  const { data: submissions = [], isLoading: loading, error } = useSubmissions({ 
    student_id: user?.role === 'student' ? user.id : undefined 
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'evaluating': return 'info'
      case 'in_progress': return 'warning'
      default: return 'default'
    }
  }

  const getStatusLabel = (status: string) => {
    const statusMap: Record<string, string> = {
      'completed': 'Завершено',
      'evaluating': 'На проверке',
      'in_progress': 'В процессе',
      'submitted': 'Отправлено'
    }
    return statusMap[status] || status
  }

  const handleDelete = async (id: string) => {
    if (window.confirm('Вы уверены, что хотите удалить эту попытку?')) {
      try {
        await deleteSubmission.mutateAsync(id)
      } catch (err) {
        console.error('Failed to delete submission:', err)
        alert('Не удалось удалить попытку')
      }
    }
  }

  return (
    <Box sx={{ width: '100%', py: 4 }}>
      <Typography variant="h4" fontWeight="bold" gutterBottom>
        {user?.role === 'student' ? 'Мои результаты' : 'Результаты студентов'}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Ошибка загрузки результатов
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : submissions.length === 0 ? (
        <Card sx={{ borderRadius: 1 }}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {user?.role === 'student' 
                ? 'У вас пока нет завершенных тестов' 
                : 'Нет результатов для отображения'}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 1, boxShadow: 3 }}>
          <Table>
            <TableHead sx={{ bgcolor: 'action.hover' }}>
              <TableRow>
                {user?.role !== 'student' && <TableCell sx={{ fontWeight: 'bold' }}>Студент</TableCell>}
                <TableCell sx={{ fontWeight: 'bold' }}>Тест</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Дата начала</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Статус</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Результат</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }} align="right">Действие</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {submissions.map((sub) => (
                <TableRow key={sub.id} hover>
                  {user?.role !== 'student' && (
                    <TableCell>{sub.student_id}</TableCell>
                  )}
                  <TableCell sx={{ fontWeight: '500' }}>{sub.test_title || 'Загрузка...'}</TableCell>
                  <TableCell>{new Date(sub.started_at).toLocaleString('ru-RU')}</TableCell>
                  <TableCell>
                    <Chip 
                      label={getStatusLabel(sub.status)} 
                      color={getStatusColor(sub.status) as any} 
                      size="small" 
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>
                    {sub.result?.total_score !== undefined ? `${sub.result.total_score} / ${sub.result.max_score}` : '-'}
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                      {sub.status === 'in_progress' ? (
                        <Button 
                          size="small" 
                          variant="contained" 
                          onClick={() => navigate(`/submissions/${sub.id}`)}
                        >
                          Продолжить
                        </Button>
                      ) : (
                        <Button size="small" variant="outlined">
                          Детали
                        </Button>
                      )}
                      {user?.role === 'admin' && (
                        <Tooltip title="Удалить попытку">
                          <IconButton 
                            size="small" 
                            color="error" 
                            onClick={() => handleDelete(sub.id)}
                            disabled={deleteSubmission.isPending}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  )
}
