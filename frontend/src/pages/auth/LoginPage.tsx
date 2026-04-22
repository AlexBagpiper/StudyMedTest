import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Box, Button, Snackbar, TextField, Typography } from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'

const PENDING_EMAIL_KEY = 'pendingEmail'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [snack, setSnack] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { t, translateError } = useLocale()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const pendingEmail = typeof window !== 'undefined' ? localStorage.getItem(PENDING_EMAIL_KEY) : null
  const justVerifiedParam = searchParams.get('verified') === '1'
  const [verifiedVisible, setVerifiedVisible] = useState(justVerifiedParam)

  // Авто-скрытие success-баннера через 5 секунд.
  useEffect(() => {
    if (!verifiedVisible) return
    const timer = window.setTimeout(() => setVerifiedVisible(false), 5000)
    return () => window.clearTimeout(timer)
  }, [verifiedVisible])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await login(email, password)
    } catch (err: any) {
      setSnack({
        open: true,
        message: translateError(err.response?.data?.detail)
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%', mt: 1 }}>
      {verifiedVisible && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setVerifiedVisible(false)}>
          Email успешно подтверждён. Войдите в систему.
        </Alert>
      )}
      {pendingEmail && !verifiedVisible && (
        <Alert
          severity="info"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => navigate('/verify-email')}>
              Продолжить
            </Button>
          }
        >
          Незавершённая регистрация: <strong>{pendingEmail}</strong>
        </Alert>
      )}
      <TextField
        margin="normal"
        required
        fullWidth
        id="email"
        label={t('auth.email')}
        name="email"
        autoComplete="email"
        autoFocus
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        name="password"
        label={t('auth.password')}
        type="password"
        id="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
        disabled={loading}
      >
        {loading ? t('auth.loading') : t('auth.login')}
      </Button>

      <Typography variant="body2" align="center">
        {t('auth.noAccount')}{' '}
        <Link to="/register" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          {t('auth.register')}
        </Link>
      </Typography>

      <Typography variant="body2" align="center" sx={{ mt: 1 }}>
        Преподаватель?{' '}
        <Link to="/register-teacher" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          Подать заявку на регистрацию
        </Link>
      </Typography>

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
