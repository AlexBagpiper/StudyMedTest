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
  FormControlLabel,
  Switch,
  Tooltip,
  Paper, 
  CircularProgress,
  TableSortLabel,
  Checkbox,
  Stack
} from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useLocale } from '../../contexts/LocaleContext'
import { 
  useSubmissions, 
  useDeleteSubmission,
  useHideSubmission,
  useRestoreSubmission,
  useBulkDeleteSubmissions
} from '../../lib/api/hooks/useSubmissions'
import DeleteIcon from '@mui/icons-material/Delete'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'
import { useState, useEffect, useMemo } from 'react'

export default function AdminSubmissionsPage() {
  const { user } = useAuth()
  const { t, formatName } = useLocale()
  const navigate = useNavigate()
  const deleteSubmission = useDeleteSubmission()
  const bulkDeleteSubmissions = useBulkDeleteSubmissions()
  const hideMutation = useHideSubmission()
  const restoreMutation = useRestoreSubmission()
  
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false)
  const [showHidden, setShowHidden] = useState(false)
  const [orderBy, setOrderBy] = useState('started_at')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  
  const { data: submissions = [], isLoading: loading, error } = useSubmissions({
    include_hidden: user?.role === 'admin' ? true : showHidden
  }, {
    refetchInterval: 10000 // Обновлять каждые 10 секунд
  })

  useEffect(() => {
    if (error) {
      setErrorDialog({
        open: true,
        message: t('submissions.error.load')
      })
    }
  }, [error, t])

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc'
    setOrder(isAsc ? 'desc' : 'asc')
    setOrderBy(property)
  }

  const sortedSubmissions = useMemo(() => {
    return [...submissions].sort((a, b) => {
      let comparison = 0
      
      switch (orderBy) {
        case 'student': {
          const nameA = a.student ? formatName(a.student.last_name, a.student.first_name, a.student.middle_name) : ''
          const nameB = b.student ? formatName(b.student.last_name, b.student.first_name, b.student.middle_name) : ''
          comparison = nameA.localeCompare(nameB)
          break
        }
        case 'teacher': {
          const teacherA = a.teacher ? formatName(a.teacher.last_name, a.teacher.first_name, a.teacher.middle_name) : ''
          const teacherB = b.teacher ? formatName(b.teacher.last_name, b.teacher.first_name, b.teacher.middle_name) : ''
          comparison = teacherA.localeCompare(teacherB)
          break
        }
        case 'test_title': {
          comparison = (a.test_title || '').localeCompare(b.test_title || '')
          break
        }
        case 'started_at': {
          comparison = new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
          break
        }
        case 'status': {
          comparison = (a.status || '').localeCompare(b.status || '')
          break
        }
        case 'result': {
          const scoreA = a.result?.total_score ?? -1
          const scoreB = b.result?.total_score ?? -1
          comparison = scoreA - scoreB
          break
        }
        default:
          comparison = 0
      }
      
      return order === 'desc' ? -comparison : comparison
    })
  }, [submissions, order, orderBy, formatName])

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
      'completed': t('submissions.status.completed'),
      'evaluating': t('submissions.status.evaluating'),
      'in_progress': t('submissions.status.inProgress'),
      'submitted': t('submissions.status.submitted')
    }
    return statusMap[status] || status
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteSubmission.mutateAsync(deleteId)
      setDeleteId(null)
    } catch (err) {
      console.error('Failed to delete submission:', err)
      setErrorDialog({
        open: true,
        message: t('submissions.error.delete')
      })
    }
  }

  const handleBulkDelete = async () => {
    try {
      await bulkDeleteSubmissions.mutateAsync(selectedIds)
      setSelectedIds([])
      setShowBulkDeleteConfirm(false)
    } catch (err) {
      console.error('Failed to bulk delete submissions:', err)
      setErrorDialog({
        open: true,
        message: t('submissions.error.delete')
      })
    }
  }

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedIds(submissions.map((sub: any) => sub.id))
    } else {
      setSelectedIds([])
    }
  }

  const handleSelectOne = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  return (
    <Box sx={{ width: '100%', py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="h4" fontWeight="bold">
            {t('submissions.title.all')}
          </Typography>
          {selectedIds.length > 0 && user?.role === 'admin' && (
            <Button
              variant="contained"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={() => setShowBulkDeleteConfirm(true)}
              size="small"
            >
              {t('common.delete')} ({selectedIds.length})
            </Button>
          )}
        </Stack>
        
        {user?.role === 'teacher' && (
          <FormControlLabel
            control={
              <Switch 
                checked={showHidden} 
                onChange={(e) => setShowHidden(e.target.checked)} 
                color="primary"
              />
            }
            label={t('submissions.showHidden')}
          />
        )}
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : submissions.length === 0 ? (
        <Card sx={{ borderRadius: 1 }}>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {t('submissions.noResults.all')}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 1, boxShadow: 3 }}>
          <Table>
            <TableHead sx={{ bgcolor: 'action.hover' }}>
              <TableRow>
                {user?.role === 'admin' && (
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={selectedIds.length > 0 && selectedIds.length < submissions.length}
                      checked={submissions.length > 0 && selectedIds.length === submissions.length}
                      onChange={handleSelectAll}
                    />
                  </TableCell>
                )}
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={orderBy === 'student'}
                    direction={orderBy === 'student' ? order : 'asc'}
                    onClick={() => handleRequestSort('student')}
                  >
                    {t('submissions.table.student')}
                  </TableSortLabel>
                </TableCell>
                {user?.role === 'admin' && (
                  <TableCell sx={{ fontWeight: 'bold' }}>
                    <TableSortLabel
                      active={orderBy === 'teacher'}
                      direction={orderBy === 'teacher' ? order : 'asc'}
                      onClick={() => handleRequestSort('teacher')}
                    >
                      {t('submissions.table.teacher')}
                    </TableSortLabel>
                  </TableCell>
                )}
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={orderBy === 'test_title'}
                    direction={orderBy === 'test_title' ? order : 'asc'}
                    onClick={() => handleRequestSort('test_title')}
                  >
                    {t('submissions.table.test')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={orderBy === 'started_at'}
                    direction={orderBy === 'started_at' ? order : 'asc'}
                    onClick={() => handleRequestSort('started_at')}
                  >
                    {t('submissions.table.date')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={orderBy === 'status'}
                    direction={orderBy === 'status' ? order : 'asc'}
                    onClick={() => handleRequestSort('status')}
                  >
                    {t('submissions.table.status')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <TableSortLabel
                    active={orderBy === 'result'}
                    direction={orderBy === 'result' ? order : 'asc'}
                    onClick={() => handleRequestSort('result')}
                  >
                    {t('submissions.table.result')}
                  </TableSortLabel>
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold' }} align="right">{t('submissions.table.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedSubmissions.map((sub: any) => (
                <TableRow 
                  key={sub.id} 
                  hover
                  selected={selectedIds.includes(sub.id)}
                  sx={{ 
                    opacity: sub.is_hidden ? 0.6 : 1,
                    bgcolor: sub.is_hidden ? 'action.hover' : 'inherit'
                  }}
                >
                  {user?.role === 'admin' && (
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selectedIds.includes(sub.id)}
                        onChange={() => handleSelectOne(sub.id)}
                      />
                    </TableCell>
                  )}
                  <TableCell>
                    {sub.student 
                      ? formatName(sub.student.last_name, sub.student.first_name, sub.student.middle_name)
                      : sub.student_id}
                  </TableCell>
                  {user?.role === 'admin' && (
                    <TableCell>
                      {sub.teacher 
                        ? formatName(sub.teacher.last_name, sub.teacher.first_name, sub.teacher.middle_name)
                        : '-'}
                    </TableCell>
                  )}
                  <TableCell sx={{ fontWeight: '500' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {sub.test_title || t('submissions.loading')}
                      {sub.is_hidden && (
                        <Chip 
                          label={t('submissions.hidden')} 
                          size="small" 
                          variant="outlined" 
                          sx={{ height: 20, fontSize: '0.65rem' }} 
                        />
                      )}
                    </Box>
                  </TableCell>
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
                      {user?.role === 'teacher' && (
                        <>
                          {sub.is_hidden ? (
                            <Tooltip title={t('submissions.action.restore')}>
                              <IconButton 
                                size="small" 
                                color="primary" 
                                onClick={() => restoreMutation.mutate(sub.id)}
                                disabled={restoreMutation.isPending}
                              >
                                <VisibilityIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : (
                            <Tooltip title={t('submissions.action.hide')}>
                              <IconButton 
                                size="small" 
                                color="default" 
                                onClick={() => hideMutation.mutate(sub.id)}
                                disabled={hideMutation.isPending}
                              >
                                <VisibilityOffIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </>
                      )}
                      {sub.status !== 'in_progress' && (
                        <Button 
                          size="small" 
                          variant="outlined" 
                          onClick={() => navigate(`/admin/submissions/${sub.id}`)}
                        >
                          {t('submissions.action.details')}
                        </Button>
                      )}
                      {user?.role === 'admin' && (
                        <Tooltip title={t('submissions.action.delete')}>
                          <IconButton 
                            size="small" 
                            color="error" 
                            onClick={() => setDeleteId(sub.id)}
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

      <ConfirmDialog
        open={!!deleteId}
        title={t('submissions.action.delete')}
        content={t('submissions.confirm.delete')}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
        color="error"
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
        isLoading={deleteSubmission.isPending}
      />

      <ConfirmDialog
        open={showBulkDeleteConfirm}
        title={t('submissions.action.delete')}
        content={`${t('submissions.confirm.delete')} (${selectedIds.length})`}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
        color="error"
        onConfirm={handleBulkDelete}
        onCancel={() => setShowBulkDeleteConfirm(false)}
        isLoading={bulkDeleteSubmissions.isPending}
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
