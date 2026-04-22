import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Snackbar,
  TextField,
  Typography,
} from '@mui/material'
import { useLocale } from '../../contexts/LocaleContext'
import api from '../../lib/api'

export default function TeacherRegisterPage() {
  const [email, setEmail] = useState('')
  const [lastName, setLastName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [phone, setPhone] = useState('')
  
  const [snack, setSnack] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [loading, setLoading] = useState(false)
  const [successDialogOpen, setSuccessDialogOpen] = useState(false)

  const { t } = useLocale()
  const showError = (message: string) => setSnack({ open: true, message })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (lastName.length < 1) {
      showError('Введите фамилию')
      return
    }
    if (firstName.length < 1) {
      showError('Введите имя')
      return
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError('Введите корректный email')
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
      showError(message)
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

      <Snackbar
        open={snack.open}
        autoHideDuration={5000}
        onClose={() => setSnack({ ...snack, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity="error"
          onClose={() => setSnack({ ...snack, open: false })}
          sx={{ width: '100%' }}
        >
          {snack.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
