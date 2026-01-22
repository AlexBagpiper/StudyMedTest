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
  Paper, 
  CircularProgress,
  Alert,
  FormControlLabel,
  Switch,
  Tooltip,
  IconButton,
  TableSortLabel
} from '@mui/material'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import { useAuth } from '../../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useLocale } from '../../contexts/LocaleContext'
import { 
  useSubmissions, 
  useHideSubmission, 
  useRestoreSubmission 
} from '../../lib/api/hooks/useSubmissions'
import { useState, useMemo } from 'react'

export default function SubmissionsPage() {
  const { user } = useAuth()
  
  const { t } = useLocale()
  const navigate = useNavigate()
  const [showHidden, setShowHidden] = useState(false)
  const [orderBy, setOrderBy] = useState('started_at')
  const [order, setOrder] = useState<'asc' | 'desc'>('desc')
  
  const { data: submissions = [], isLoading: loading, error } = useSubmissions({ 
    student_id: user?.id,
    include_hidden: user?.role === 'admin' ? true : (showHidden || user?.role === 'student')
  })

  const hideMutation = useHideSubmission()
  const restoreMutation = useRestoreSubmission()

  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc'
    setOrder(isAsc ? 'desc' : 'asc')
    setOrderBy(property)
  }

  const sortedSubmissions = useMemo(() => {
    return [...submissions].sort((a, b) => {
      let comparison = 0
      
      switch (orderBy) {
        case 'test_title':
          comparison = (a.test_title || '').localeCompare(b.test_title || '')
          break
        case 'started_at':
          comparison = new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
          break
        case 'status':
          comparison = (a.status || '').localeCompare(b.status || '')
          break
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
  }, [submissions, order, orderBy])

  const handleHide = async (id: string) => {
    try {
      await hideMutation.mutateAsync(id)
    } catch (err) {
      console.error('Failed to hide submission:', err)
    }
  }

  const handleRestore = async (id: string) => {
    try {
      await restoreMutation.mutateAsync(id)
    } catch (err) {
      console.error('Failed to restore submission:', err)
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

  const getStatusLabel = (status: string) => {
    const statusMap: Record<string, string> = {
      'completed': t('submissions.status.completed'),
      'evaluating': t('submissions.status.evaluating'),
      'in_progress': t('submissions.status.inProgress'),
      'submitted': t('submissions.status.submitted')
    }
    return statusMap[status] || status
  }

  return (
    <Box sx={{ width: '100%', py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="bold">
          {t('submissions.title.my')}
        </Typography>
        
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

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {t('submissions.error.load')}
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
              {t('submissions.noResults.my')}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 1, boxShadow: 3 }}>
          <Table>
            <TableHead sx={{ bgcolor: 'action.hover' }}>
              <TableRow>
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
                  sx={{ 
                    opacity: sub.is_hidden ? 0.6 : 1,
                    bgcolor: sub.is_hidden ? 'action.hover' : 'inherit'
                  }}
                >
                  <TableCell sx={{ fontWeight: '500' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {sub.test_title || 'Загрузка...'}
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
                      {sub.status === 'in_progress' ? (
                        <Button 
                          size="small" 
                          variant="outlined" 
                          onClick={() => navigate(`/submissions/${sub.id}`)}
                        >
                          {t('tests.action.continue')}
                        </Button>
                      ) : (
                        <>
                          {user?.role === 'teacher' && (
                            <>
                              {sub.is_hidden ? (
                                <Tooltip title={t('submissions.action.restore')}>
                                  <IconButton 
                                    size="small" 
                                    color="primary" 
                                    onClick={() => handleRestore(sub.id)}
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
                                    onClick={() => handleHide(sub.id)}
                                    disabled={hideMutation.isPending}
                                  >
                                    <VisibilityOffIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                            </>
                          )}
                        </>
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
