import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Tabs,
  Tab,
  Alert,
  Tooltip,
} from '@mui/material'
import VisibilityIcon from '@mui/icons-material/Visibility'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import RefreshIcon from '@mui/icons-material/Refresh'
import api from '../../lib/api'

interface TeacherApplication {
  id: string
  email: string
  last_name: string
  first_name: string
  middle_name?: string
  phone?: string
  status: 'pending' | 'approved' | 'rejected'
  admin_comment?: string
  reviewed_by?: string
  reviewed_at?: string
  created_at: string
  updated_at: string
}

type StatusFilter = 'all' | 'pending' | 'approved' | 'rejected'

export default function TeacherApplicationsManagement() {
  const [applications, setApplications] = useState<TeacherApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  
  // Диалоги
  const [viewDialog, setViewDialog] = useState<{ open: boolean; application: TeacherApplication | null }>({
    open: false,
    application: null,
  })
  const [approveDialog, setApproveDialog] = useState<{ open: boolean; application: TeacherApplication | null }>({
    open: false,
    application: null,
  })
  const [rejectDialog, setRejectDialog] = useState<{ open: boolean; application: TeacherApplication | null }>({
    open: false,
    application: null,
  })
  
  const [adminComment, setAdminComment] = useState('')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchApplications = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = statusFilter !== 'all' ? { status_filter: statusFilter } : {}
      const response = await api.get('/teacher-applications/', { params })
      setApplications(response.data)
    } catch (err: any) {
      setError('Ошибка загрузки заявок')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchApplications()
  }, [statusFilter])

  const handleApprove = async () => {
    if (!approveDialog.application) return
    
    setProcessing(true)
    try {
      await api.post(`/teacher-applications/${approveDialog.application.id}/approve`, {
        admin_comment: adminComment || undefined,
      })
      
      setApproveDialog({ open: false, application: null })
      setAdminComment('')
      fetchApplications()
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Ошибка при одобрении заявки')
    } finally {
      setProcessing(false)
    }
  }

  const handleReject = async () => {
    if (!rejectDialog.application) return
    
    setProcessing(true)
    try {
      await api.post(`/teacher-applications/${rejectDialog.application.id}/reject`, {
        admin_comment: adminComment || undefined,
      })
      
      setRejectDialog({ open: false, application: null })
      setAdminComment('')
      fetchApplications()
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Ошибка при отклонении заявки')
    } finally {
      setProcessing(false)
    }
  }

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'pending':
        return <Chip label="Ожидает" color="warning" size="small" />
      case 'approved':
        return <Chip label="Одобрена" color="success" size="small" />
      case 'rejected':
        return <Chip label="Отклонена" color="error" size="small" />
      default:
        return <Chip label={status} size="small" />
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getFullName = (app: TeacherApplication) => {
    return `${app.last_name} ${app.first_name}${app.middle_name ? ' ' + app.middle_name : ''}`
  }

  const pendingCount = applications.filter(a => a.status === 'pending').length

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Заявки преподавателей</Typography>
        <Button
          startIcon={<RefreshIcon />}
          onClick={fetchApplications}
          disabled={loading}
        >
          Обновить
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Tabs 
        value={statusFilter} 
        onChange={(_, value) => setStatusFilter(value)} 
        sx={{ mb: 2 }}
      >
        <Tab label={`Ожидают${pendingCount > 0 ? ` (${pendingCount})` : ''}`} value="pending" />
        <Tab label="Все" value="all" />
        <Tab label="Одобренные" value="approved" />
        <Tab label="Отклоненные" value="rejected" />
      </Tabs>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : applications.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            {statusFilter === 'pending' ? 'Нет заявок, ожидающих рассмотрения' : 'Заявки не найдены'}
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ФИО</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Дата подачи</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell align="right">Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {applications.map((app) => (
                <TableRow key={app.id} hover>
                  <TableCell>{getFullName(app)}</TableCell>
                  <TableCell>{app.email}</TableCell>
                  <TableCell>{formatDate(app.created_at)}</TableCell>
                  <TableCell>{getStatusChip(app.status)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Посмотреть">
                      <IconButton
                        size="small"
                        onClick={() => setViewDialog({ open: true, application: app })}
                      >
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {app.status === 'pending' && (
                      <>
                        <Tooltip title="Одобрить">
                          <IconButton
                            size="small"
                            color="success"
                            onClick={() => setApproveDialog({ open: true, application: app })}
                          >
                            <CheckIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Отклонить">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => setRejectDialog({ open: true, application: app })}
                          >
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Диалог просмотра */}
      <Dialog
        open={viewDialog.open}
        onClose={() => setViewDialog({ open: false, application: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Информация о заявке</DialogTitle>
        <DialogContent>
          {viewDialog.application && (
            <Box sx={{ pt: 1 }}>
              <Typography variant="subtitle2" color="text.secondary">ФИО</Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                {getFullName(viewDialog.application)}
              </Typography>

              <Typography variant="subtitle2" color="text.secondary">Email</Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>{viewDialog.application.email}</Typography>

              {viewDialog.application.phone && (
                <>
                  <Typography variant="subtitle2" color="text.secondary">Телефон</Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>{viewDialog.application.phone}</Typography>
                </>
              )}

              <Typography variant="subtitle2" color="text.secondary">Статус</Typography>
              <Box sx={{ mb: 2 }}>{getStatusChip(viewDialog.application.status)}</Box>

              {viewDialog.application.admin_comment && (
                <>
                  <Typography variant="subtitle2" color="text.secondary">Комментарий администратора</Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>{viewDialog.application.admin_comment}</Typography>
                </>
              )}

              <Typography variant="subtitle2" color="text.secondary">Дата подачи</Typography>
              <Typography variant="body1">{formatDate(viewDialog.application.created_at)}</Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialog({ open: false, application: null })}>
            Закрыть
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог одобрения */}
      <Dialog
        open={approveDialog.open}
        onClose={() => !processing && setApproveDialog({ open: false, application: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Одобрить заявку</DialogTitle>
        <DialogContent>
          {approveDialog.application && (
            <>
              <Typography sx={{ mb: 2 }}>
                Вы уверены, что хотите одобрить заявку от <strong>{getFullName(approveDialog.application)}</strong>?
              </Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                Будет создан аккаунт преподавателя, и на email <strong>{approveDialog.application.email}</strong> будет 
                отправлено письмо с временным паролем.
              </Alert>
              <TextField
                fullWidth
                label="Комментарий администратора (необязательно)"
                multiline
                rows={3}
                value={adminComment}
                onChange={(e) => setAdminComment(e.target.value)}
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => {
              setApproveDialog({ open: false, application: null })
              setAdminComment('')
            }}
            disabled={processing}
          >
            Отмена
          </Button>
          <Button 
            onClick={handleApprove} 
            variant="contained" 
            color="success"
            disabled={processing}
          >
            {processing ? <CircularProgress size={24} /> : 'Одобрить'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог отклонения */}
      <Dialog
        open={rejectDialog.open}
        onClose={() => !processing && setRejectDialog({ open: false, application: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Отклонить заявку</DialogTitle>
        <DialogContent>
          {rejectDialog.application && (
            <>
              <Typography sx={{ mb: 2 }}>
                Вы уверены, что хотите отклонить заявку от <strong>{getFullName(rejectDialog.application)}</strong>?
              </Typography>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Преподавателю будет отправлено уведомление об отклонении заявки.
              </Alert>
              <TextField
                fullWidth
                label="Причина отклонения (необязательно)"
                multiline
                rows={3}
                value={adminComment}
                onChange={(e) => setAdminComment(e.target.value)}
                helperText="Этот комментарий увидит преподаватель"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => {
              setRejectDialog({ open: false, application: null })
              setAdminComment('')
            }}
            disabled={processing}
          >
            Отмена
          </Button>
          <Button 
            onClick={handleReject} 
            variant="contained" 
            color="error"
            disabled={processing}
          >
            {processing ? <CircularProgress size={24} /> : 'Отклонить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
