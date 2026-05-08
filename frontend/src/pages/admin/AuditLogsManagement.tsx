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
  TextField,
  InputAdornment,
  IconButton,
  TablePagination,
  CircularProgress,
  alpha,
  useTheme,
  Tooltip,
  Collapse,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import ClearIcon from '@mui/icons-material/Clear'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp'
import { adminApi } from '../../lib/api'
import { useLocale } from '../../contexts/LocaleContext'
import { TablePaginationActions } from '../../components/common/TablePaginationActions'

interface AuditLog {
  id: string
  user_id?: string
  user?: {
    email: string
    last_name?: string
    first_name?: string
  }
  action: string
  resource_type?: string
  resource_id?: string
  ip_address?: string
  user_agent?: string
  details?: any
  timestamp: string
}

function Row(props: { log: AuditLog }) {
  const { log } = props
  const [open, setOpen] = useState(false)

  const getActionColor = (action: string) => {
    if (action.includes('failed') || action.includes('error')) return 'error'
    if (action.includes('success') || action.includes('sent')) return 'success'
    if (action.includes('register') || action.includes('login')) return 'info'
    return 'default'
  }

  return (
    <>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell width="50">
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>
          {new Date(log.timestamp).toLocaleString('ru-RU')}
        </TableCell>
        <TableCell>
          <Chip
            label={log.action}
            color={getActionColor(log.action) as any}
            size="small"
            variant="outlined"
          />
        </TableCell>
        <TableCell>
          {log.user 
            ? `${log.user.last_name || ''} ${log.user.first_name || ''}`.trim() || log.user.email
            : (log.details?.email || 'System')}
        </TableCell>
        <TableCell>{log.ip_address || '-'}</TableCell>
        <TableCell>
          <Tooltip title={log.user_agent || ''}>
            <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
              {log.user_agent || '-'}
            </Typography>
          </Tooltip>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
              <Typography variant="h6" gutterBottom component="div" size="small">
                Детали события
              </Typography>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {JSON.stringify(log.details, null, 2)}
              </pre>
              {log.resource_type && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Ресурс: {log.resource_type} ({log.resource_id})
                </Typography>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  )
}

export default function AuditLogsManagement() {
  const { t, locale } = useLocale()
  const theme = useTheme()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(25)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
    }, 500)
    return () => clearTimeout(timer)
  }, [searchQuery])

  useEffect(() => {
    loadLogs()
  }, [page, pageSize, debouncedSearch])

  const loadLogs = async () => {
    try {
      if (logs.length === 0) setLoading(true)
      else setFetching(true)

      const params: any = {
        skip: page * pageSize,
        limit: pageSize,
      }
      if (debouncedSearch) {
        params.search = debouncedSearch
      }

      const response = await adminApi.getAuditLogs(params)
      setLogs(response.items)
      setTotal(response.total)
    } catch (err) {
      console.error('Failed to load audit logs', err)
    } finally {
      setLoading(false)
      setFetching(false)
    }
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>Журналы аудита</Typography>

      <Paper sx={{ mb: 3, p: 2 }}>
        <TextField
          fullWidth
          placeholder="Поиск по email, IP или действию..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: searchQuery && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchQuery('')}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper} sx={{ position: 'relative' }}>
          {fetching && (
            <Box sx={{
              position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              zIndex: 2, bgcolor: alpha(theme.palette.background.paper, 0.4)
            }}>
              <CircularProgress />
            </Box>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell />
                <TableCell>Время</TableCell>
                <TableCell>Действие</TableCell>
                <TableCell>Пользователь / Email</TableCell>
                <TableCell>IP Адрес</TableCell>
                <TableCell>User Agent</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">Логи не найдены</TableCell>
                </TableRow>
              ) : (
                logs.map((log) => <Row key={log.id} log={log} />)
              )}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(e) => {
              setPageSize(Number(e.target.value))
              setPage(0)
            }}
            rowsPerPageOptions={[10, 25, 50, 100]}
            labelRowsPerPage={t('admin.rowsPerPage')}
            labelDisplayedRows={({ from, to, count }) =>
              `${from}–${to} ${locale === 'ru' ? 'из' : 'of'} ${count !== -1 ? count : `>${to}`}`}
            ActionsComponent={TablePaginationActions}
          />
        </TableContainer>
      )}
    </Box>
  )
}
