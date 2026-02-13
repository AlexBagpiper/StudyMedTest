import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  Divider,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Chip,
  Stack
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import { useLocale } from '../../contexts/LocaleContext'
import PersonIcon from '@mui/icons-material/Person'
import TimerIcon from '@mui/icons-material/Timer'
import AssignmentIcon from '@mui/icons-material/Assignment'
import VisibilityIcon from '@mui/icons-material/Visibility'
import EventIcon from '@mui/icons-material/Event'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import { MessageDialog } from '../../components/common/MessageDialog'
import { useSubmissions } from '../../lib/api/hooks/useSubmissions'

export default function SubmissionDetailsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, formatName } = useLocale()
  
  const [submission, setSubmission] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  
  // Получаем историю всех попыток студента по этому тесту
  const { data: allSubmissions = [] } = useSubmissions(
    submission?.test_id ? { 
      student_id: submission.student_id, 
      test_id: submission.test_id 
    } : undefined,
    { enabled: !!submission?.test_id }
  )

  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })

  useEffect(() => {
    loadSubmission()
    
    // Добавляем поллинг если статус "evaluating" или "in_progress"
    let interval: any
    if (submission?.status === 'evaluating' || submission?.status === 'in_progress') {
      interval = setInterval(() => {
        loadSubmission(false)
      }, 3000)
    }
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [id, submission?.status])

  const loadSubmission = async (showLoading = true) => {
    try {
      if (showLoading) setIsLoading(true)
      const subRes = await api.get(`/submissions/${id}`)
      setSubmission(subRes.data)
    } catch (err: any) {
      console.error('Failed to load submission:', err)
      if (showLoading) {
        setErrorDialog({
          open: true,
          message: err.response?.data?.detail || t('submissions.error.load')
        })
      }
    } finally {
      if (showLoading) setIsLoading(false)
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

  const formatDuration = (start: string, end: string | null) => {
    if (!end) return '-'
    const startTime = new Date(start).getTime()
    const endTime = new Date(end).getTime()
    const durationMs = endTime - startTime
    
    const minutes = Math.floor(durationMs / 60000)
    const seconds = Math.floor((durationMs % 60000) / 1000)
    
    return `${minutes} мин ${seconds} сек`
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!submission && !errorDialog.open) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">Данные не найдены</Typography>
        <Button variant="outlined" sx={{ mt: 2 }} onClick={() => navigate('/admin/submissions')}>
          {t('common.back')}
        </Button>
      </Box>
    )
  }

  const studentName = submission?.student 
    ? formatName(submission.student.last_name, submission.student.first_name, submission.student.middle_name)
    : submission?.student_id || '—'

  return (
    <Box sx={{ width: '100%', px: { xs: 2, md: 4 }, py: 4 }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" fontWeight="bold">
          {t('submissions.action.details')}
        </Typography>
        <Button variant="outlined" onClick={() => navigate('/admin/submissions')}>
          {t('common.back')}
        </Button>
      </Box>

      {allSubmissions.length > 1 && (
        <Paper 
          elevation={0}
          sx={{ 
            p: 2, 
            mb: 3, 
            borderRadius: 2, 
            display: 'flex', 
            alignItems: 'center', 
            gap: 2,
            bgcolor: 'action.hover',
            border: '1px solid',
            borderColor: 'divider'
          }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: 'text.secondary' }}>
            История попыток этого студента:
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {allSubmissions
              .sort((a: any, b: any) => (a.attempt_number || 1) - (b.attempt_number || 1))
              .map((sub: any) => (
                <Chip
                  key={sub.id}
                  label={`Попытка №${sub.attempt_number || 1} (${sub.result?.total_score || 0} б.)`}
                  onClick={() => sub.id !== id && navigate(`/admin/submissions/${sub.id}`)}
                  color={sub.id === id ? "primary" : "default"}
                  variant={sub.id === id ? "filled" : "outlined"}
                  sx={{ 
                    cursor: sub.id === id ? 'default' : 'pointer',
                    '&:hover': sub.id === id ? {} : { bgcolor: 'primary.light', color: 'white' }
                  }}
                />
              ))}
          </Box>
        </Paper>
      )}

      {submission && (
        <Grid container spacing={3}>
          {/* Сводка результата */}
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', boxShadow: 3, borderRadius: 2 }}>
              <CardContent>
                <Box sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    {t('submissions.table.result')}
                  </Typography>
                  <Typography variant="h2" fontWeight="bold" color="primary">
                    {submission.result?.total_score !== undefined ? submission.result.total_score : '-'}
                  </Typography>
                  <Typography variant="h6" color="text.secondary">
                    из {submission.result?.max_score || 0} баллов
                  </Typography>
                  
                  <Box sx={{ mt: 3 }}>
                    <Chip 
                      label={t(`submissions.status.${submission.status}` as any) || submission.status} 
                      color={getStatusColor(submission.status) as any}
                      sx={{ px: 2, py: 2, fontWeight: 'bold' }}
                    />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Информация о студенте и тесте */}
          <Grid item xs={12} md={8}>
            <Card sx={{ height: '100%', boxShadow: 3, borderRadius: 2 }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AssignmentIcon color="primary" /> {submission.test_title}
                </Typography>
                <Divider sx={{ my: 2 }} />
                
                <Stack spacing={2}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <PersonIcon color="action" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Студент</Typography>
                      <Typography variant="body1" fontWeight="500">{studentName}</Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <EventIcon color="action" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Дата начала</Typography>
                      <Typography variant="body1">
                        {submission.started_at ? (() => {
                          const d = new Date(submission.started_at);
                          return isNaN(d.getTime()) ? '—' : d.toLocaleString('ru-RU');
                        })() : '—'}
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <AccessTimeIcon color="action" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Дата завершения</Typography>
                      <Typography variant="body1">
                        {submission.submitted_at ? new Date(submission.submitted_at).toLocaleString('ru-RU') : 'В процессе'}
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <TimerIcon color="action" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Затраченное время</Typography>
                      <Typography variant="body1">
                        {formatDuration(submission.started_at, submission.submitted_at)}
                      </Typography>
                    </Box>
                  </Box>
                </Stack>

                <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
                  <Button 
                    variant="contained" 
                    size="large"
                    startIcon={<VisibilityIcon />}
                    onClick={() => navigate(`/admin/submissions/${submission.id}/review`)}
                    sx={{ borderRadius: 2, px: 4 }}
                  >
                    Детальный просмотр теста
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

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
