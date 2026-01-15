import { Box, Typography, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Button, Paper } from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../lib/api'

export default function SubmissionsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [submissions, setSubmissions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSubmissions()
  }, [])

  const loadSubmissions = async () => {
    try {
      const res = await api.get('/submissions')
      setSubmissions(res.data)
    } catch (err) {
      console.error('Failed to load submissions:', err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'evaluating': return 'info'
      case 'in_progress': return 'warning'
      default: return 'default'
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {user?.role === 'student' ? 'Мои результаты' : 'Результаты студентов'}
      </Typography>

      {loading ? (
        <Typography>Загрузка...</Typography>
      ) : submissions.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {user?.role === 'student' 
                ? 'У вас пока нет завершенных тестов' 
                : 'Нет результатов для отображения'}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                {user?.role !== 'student' && <TableCell>Студент</TableCell>}
                <TableCell>Дата начала</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Результат</TableCell>
                <TableCell>Действие</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {submissions.map((sub) => (
                <TableRow key={sub.id}>
                  {user?.role !== 'student' && (
                    <TableCell>{sub.student_id}</TableCell>
                  )}
                  <TableCell>{new Date(sub.started_at).toLocaleString()}</TableCell>
                  <TableCell>
                    <Chip label={sub.status} color={getStatusColor(sub.status) as any} size="small" />
                  </TableCell>
                  <TableCell>
                    {sub.result?.score !== undefined ? `${sub.result.score}%` : '-'}
                  </TableCell>
                  <TableCell>
                    {sub.status === 'in_progress' ? (
                      <Button size="small" onClick={() => navigate(`/submissions/${sub.id}`)}>
                        Продолжить
                      </Button>
                    ) : (
                      <Button size="small" variant="outlined">
                        Детали
                      </Button>
                    )}
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

