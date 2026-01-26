import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Box, 
  TextField, 
  Button, 
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert
} from '@mui/material'
import { useLocale } from '../../contexts/LocaleContext'
import { MessageDialog } from '../../components/common/MessageDialog'
import api from '../../lib/api'

export default function TeacherRegisterPage() {
  const [email, setEmail] = useState('')
  const [lastName, setLastName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [phone, setPhone] = useState('')
  
  const [messageDialog, setMessageDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [loading, setLoading] = useState(false)
  const [successDialogOpen, setSuccessDialogOpen] = useState(false)

  const { t } = useLocale()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Валидация
    if (lastName.length < 1) {
      setMessageDialog({ open: true, message: 'Введите фамилию' })
      return
    }

    if (firstName.length < 1) {
      setMessageDialog({ open: true, message: 'Введите имя' })
      return
    }

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setMessageDialog({ open: true, message: 'Введите корректный email' })
      return
    }

    setLoading(true)

    try {
      await api.post('/teacher-applications/', {
        email,
        last_name: lastName,
        first_name: firstName,
        middle_name: middleName || undefined,
        phone: phone || undefined,
      })
      
      setSuccessDialogOpen(true)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      let message = 'Ошибка при отправке заявки'
      if (Array.isArray(detail)) {
        message = detail[0]?.msg || message
      } else if (typeof detail === 'string') {
        message = detail
      }
      setMessageDialog({ open: true, message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%', mt: 1 }}>
      <Alert severity="info" sx={{ mb: 3 }}>
        Заявка на регистрацию преподавателя будет рассмотрена администратором. 
        После одобрения вы получите письмо с данными для входа.
      </Alert>

      <Typography variant="h6" sx={{ mb: 2 }}>
        Личные данные
      </Typography>

      <TextField
        margin="normal"
        required
        fullWidth
        id="lastName"
        label="Фамилия"
        name="lastName"
        autoFocus
        value={lastName}
        onChange={(e) => setLastName(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        id="firstName"
        label="Имя"
        name="firstName"
        value={firstName}
        onChange={(e) => setFirstName(e.target.value)}
      />
      <TextField
        margin="normal"
        fullWidth
        id="middleName"
        label="Отчество"
        name="middleName"
        value={middleName}
        onChange={(e) => setMiddleName(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        id="email"
        label="Email"
        name="email"
        autoComplete="email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <TextField
        margin="normal"
        fullWidth
        id="phone"
        label="Телефон"
        name="phone"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        helperText="Необязательно"
      />

      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
        disabled={loading}
      >
        {loading ? <CircularProgress size={24} color="inherit" /> : 'Отправить заявку'}
      </Button>

      <Typography variant="body2" align="center">
        Уже есть аккаунт?{' '}
        <Link to="/login" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          Войти
        </Link>
      </Typography>

      <Typography variant="body2" align="center" sx={{ mt: 1 }}>
        Студент?{' '}
        <Link to="/register" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          Зарегистрироваться как студент
        </Link>
      </Typography>

      {/* Диалог успешной отправки */}
      <Dialog 
        open={successDialogOpen} 
        onClose={() => setSuccessDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: 'center', pt: 3 }}>
          ✓ Заявка отправлена
        </DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2, textAlign: 'center' }}>
            Ваша заявка успешно отправлена на рассмотрение администратору.
          </Typography>
          <Typography sx={{ textAlign: 'center', color: 'text.secondary' }}>
            После одобрения заявки вы получите письмо с данными для входа на адрес:<br/>
            <strong>{email}</strong>
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, justifyContent: 'center' }}>
          <Button 
            component={Link}
            to="/login"
            variant="contained" 
            size="large"
          >
            Вернуться на страницу входа
          </Button>
        </DialogActions>
      </Dialog>

      <MessageDialog
        open={messageDialog.open}
        title="Ошибка"
        content={messageDialog.message}
        severity="error"
        onClose={() => setMessageDialog({ ...messageDialog, open: false })}
      />
    </Box>
  )
}
