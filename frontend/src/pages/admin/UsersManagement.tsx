import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Tabs,
  Tab,
  InputAdornment,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import SearchIcon from '@mui/icons-material/Search'
import { adminApi } from '../../lib/api'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'
import { useLocale } from '../../contexts/LocaleContext'

interface User {
  id: string
  email: string
  last_name: string
  first_name: string
  middle_name?: string
  role: 'admin' | 'teacher' | 'student'
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login?: string
}

interface UserFormData {
  email: string
  password: string
  last_name: string
  first_name: string
  middle_name?: string
  role: 'admin' | 'teacher' | 'student'
  is_active: boolean
  is_verified: boolean
}

const initialFormData: UserFormData = {
  email: '',
  password: '',
  last_name: '',
  first_name: '',
  middle_name: '',
  role: 'teacher',
  is_active: true,
  is_verified: true,
}

export default function UsersManagement() {
  const { t } = useLocale()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  
  // Dialog states
  const [messageDialog, setMessageDialog] = useState<{
    open: boolean
    title: string
    content: string
    severity: 'error' | 'success' | 'info' | 'warning'
  }>({
    open: false,
    title: '',
    content: '',
    severity: 'info'
  })

  const [confirmDelete, setConfirmDelete] = useState<{
    open: boolean
    userId: string | null
  }>({
    open: false,
    userId: null
  })

  const [openDialog, setOpenDialog] = useState(false)
  const [formData, setFormData] = useState<UserFormData>(initialFormData)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [total, setTotal] = useState(0)

  const roleColors: Record<string, 'error' | 'primary' | 'success'> = {
    admin: 'error',
    teacher: 'primary',
    student: 'success',
  }

  const roleLabels: Record<string, string> = {
    admin: 'Администратор',
    teacher: 'Преподаватель',
    student: 'Студент',
  }

  useEffect(() => {
    loadUsers()
  }, [roleFilter, searchQuery])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const params: any = { limit: 100 }
      
      if (roleFilter !== 'all') {
        params.role = roleFilter
      }
      
      if (searchQuery) {
        params.search = searchQuery
      }

      const response = await adminApi.getUsers(params)
      setUsers(response.items)
      setTotal(response.total)
    } catch (err: any) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: err.response?.data?.detail || 'Ошибка загрузки пользователей',
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleOpenDialog = (user?: User) => {
    if (user) {
      setEditingUser(user)
      setFormData({
        email: user.email,
        password: '',
        last_name: user.last_name,
        first_name: user.first_name,
        middle_name: user.middle_name || '',
        role: user.role,
        is_active: user.is_active,
        is_verified: user.is_verified,
      })
    } else {
      setEditingUser(null)
      setFormData(initialFormData)
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingUser(null)
    setFormData(initialFormData)
  }

  const handleSubmit = async () => {
    try {
      if (editingUser) {
        const updateData: any = { ...formData }
        if (!updateData.password) {
          delete updateData.password
        }
        await adminApi.updateUser(editingUser.id, updateData)
        setMessageDialog({
          open: true,
          title: t('common.success'),
          content: 'Пользователь успешно обновлён',
          severity: 'success'
        })
      } else {
        await adminApi.createUser(formData)
        setMessageDialog({
          open: true,
          title: t('common.success'),
          content: formData.role === 'teacher'
            ? 'Преподаватель успешно создан'
            : 'Пользователь успешно создан',
          severity: 'success'
        })
      }
      
      handleCloseDialog()
      loadUsers()
    } catch (err: any) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: err.response?.data?.detail || 'Ошибка при сохранении',
        severity: 'error'
      })
    }
  }

  const handleDelete = async (userId: string) => {
    setConfirmDelete({ open: true, userId })
  }

  const confirmDeleteAction = async () => {
    if (!confirmDelete.userId) return

    try {
      setLoading(true)
      await adminApi.deleteUser(confirmDelete.userId)
      setMessageDialog({
        open: true,
        title: t('common.success'),
        content: 'Пользователь успешно удалён',
        severity: 'success'
      })
      setConfirmDelete({ open: false, userId: null })
      loadUsers()
    } catch (err: any) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: err.response?.data?.detail || 'Ошибка при удалении',
        severity: 'error'
      })
      setConfirmDelete({ open: false, userId: null })
    } finally {
      setLoading(false)
    }
  }

  const getFullName = (user: User) => {
    const parts = [user.last_name, user.first_name, user.middle_name].filter(Boolean)
    return parts.join(' ')
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Управление пользователями</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Создать преподавателя
        </Button>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Box sx={{ p: 2 }}>
          <TextField
            fullWidth
            placeholder="Поиск по email или ФИО..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        </Box>
        <Tabs
          value={roleFilter}
          onChange={(_, value) => setRoleFilter(value)}
          sx={{ borderTop: 1, borderColor: 'divider' }}
        >
          <Tab label={`Все (${total})`} value="all" />
          <Tab label="Администраторы" value="admin" />
          <Tab label="Преподаватели" value="teacher" />
          <Tab label="Студенты" value="student" />
        </Tabs>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ФИО</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Роль</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Дата создания</TableCell>
                <TableCell align="right">Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    Пользователи не найдены
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{getFullName(user)}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={roleLabels[user.role]}
                        color={roleColors[user.role]}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? 'Активен' : 'Неактивен'}
                        color={user.is_active ? 'success' : 'default'}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {new Date(user.created_at).toLocaleDateString('ru-RU')}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(user)}
                        color="primary"
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(user.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Диалог создания/редактирования */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingUser ? 'Редактировать пользователя' : 'Создать пользователя'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Email"
              type="email"
              fullWidth
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
            
            <TextField
              label="Пароль"
              type="password"
              fullWidth
              required={!editingUser}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              helperText={editingUser ? 'Оставьте пустым, чтобы не менять' : ''}
            />

            <TextField
              label="Фамилия"
              fullWidth
              required
              value={formData.last_name}
              onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            />

            <TextField
              label="Имя"
              fullWidth
              required
              value={formData.first_name}
              onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            />

            <TextField
              label="Отчество"
              fullWidth
              value={formData.middle_name}
              onChange={(e) => setFormData({ ...formData, middle_name: e.target.value })}
            />

            <TextField
              select
              label="Роль"
              fullWidth
              required
              value={formData.role}
              onChange={(e) =>
                setFormData({ ...formData, role: e.target.value as any })
              }
            >
              <MenuItem value="student">Студент</MenuItem>
              <MenuItem value="teacher">Преподаватель</MenuItem>
              <MenuItem value="admin">Администратор</MenuItem>
            </TextField>

            <TextField
              select
              label="Статус"
              fullWidth
              value={formData.is_active ? 'active' : 'inactive'}
              onChange={(e) =>
                setFormData({ ...formData, is_active: e.target.value === 'active' })
              }
            >
              <MenuItem value="active">Активен</MenuItem>
              <MenuItem value="inactive">Неактивен</MenuItem>
            </TextField>

            <TextField
              select
              label="Подтверждён"
              fullWidth
              value={formData.is_verified ? 'verified' : 'unverified'}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  is_verified: e.target.value === 'verified',
                })
              }
            >
              <MenuItem value="verified">Да</MenuItem>
              <MenuItem value="unverified">Нет</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Отмена</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingUser ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={confirmDelete.open}
        title="Удаление пользователя"
        content="Вы уверены, что хотите удалить этого пользователя? Это действие нельзя отменить."
        confirmText="Удалить"
        cancelText="Отмена"
        onConfirm={confirmDeleteAction}
        onCancel={() => setConfirmDelete({ open: false, userId: null })}
        color="error"
        isLoading={loading}
      />

      <MessageDialog
        open={messageDialog.open}
        title={messageDialog.title}
        content={messageDialog.content}
        severity={messageDialog.severity}
        onClose={() => setMessageDialog({ ...messageDialog, open: false })}
      />
    </Box>
  )
}
