import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  InputAdornment,
  Snackbar,
  TextField,
  Typography,
} from '@mui/material'
import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'

const PENDING_EMAIL_KEY = 'pendingEmail'
const PENDING_PASSWORD_KEY = 'pendingPassword'
const RESEND_AVAILABLE_AT_KEY = 'pendingResendAvailableAt'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [lastName, setLastName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [snack, setSnack] = useState<{ open: boolean; message: string }>({
    open: false,
    message: '',
  })
  const showError = (message: string) => setSnack({ open: true, message })
  const [loading, setLoading] = useState(false)

  const { register } = useAuth()
  const { t } = useLocale()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (password.length < 6) {
      showError(t('auth.passwordMin'))
      return
    }
    if (password !== confirmPassword) {
      showError(t('auth.passwordsDontMatch'))
      return
    }
    if (lastName.length < 1) {
      showError(t('auth.enterLastName'))
      return
    }
    if (firstName.length < 1) {
      showError(t('auth.enterFirstName'))
      return
    }

    setLoading(true)
    try {
      const res = await register(email, password, lastName, firstName, middleName || undefined)
      // Persist pending state so user can recover on F5.
      // Password is stored in sessionStorage only (cleared on tab close) —
      // used once to auto-login right after verification, then wiped.
      localStorage.setItem(PENDING_EMAIL_KEY, email.trim().toLowerCase())
      sessionStorage.setItem(PENDING_PASSWORD_KEY, password)
      // Save when the next resend will be available so VerifyEmailPage can
      // restore the countdown (survives page reload).
      const cooldownSec = res?.resend_after && res.resend_after > 0 ? res.resend_after : 60
      localStorage.setItem(RESEND_AVAILABLE_AT_KEY, String(Date.now() + cooldownSec * 1000))
      navigate('/verify-email')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      let message = t('common.error')
      if (Array.isArray(detail)) {
        message = detail[0]?.msg || t('common.error')
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
      <TextField margin="normal" required fullWidth id="lastName" label={t('auth.lastName')} name="lastName" autoFocus
        value={lastName} onChange={(e) => setLastName(e.target.value)} />
      <TextField margin="normal" required fullWidth id="firstName" label={t('auth.firstName')} name="firstName"
        value={firstName} onChange={(e) => setFirstName(e.target.value)} />
      <TextField margin="normal" fullWidth id="middleName" label={t('auth.middleName')} name="middleName"
        value={middleName} onChange={(e) => setMiddleName(e.target.value)} />
      <TextField margin="normal" required fullWidth id="email" label={t('auth.email')} name="email" autoComplete="email"
        value={email} onChange={(e) => setEmail(e.target.value)} />
      <TextField
        margin="normal" required fullWidth name="password" label={t('auth.password')}
        type={showPassword ? 'text' : 'password'} id="password" autoComplete="new-password"
        value={password} onChange={(e) => setPassword(e.target.value)}
        helperText={t('auth.passwordMin')}
        error={password.length > 0 && password.length < 6}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton aria-label="toggle password visibility" onClick={() => setShowPassword(!showPassword)} edge="end">
                {showPassword ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
      <TextField
        margin="normal" required fullWidth name="confirmPassword" label={t('auth.confirmPassword')}
        type={showPassword ? 'text' : 'password'} id="confirmPassword" autoComplete="new-password"
        value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
        error={confirmPassword.length > 0 && password !== confirmPassword}
        helperText={confirmPassword.length > 0 && password !== confirmPassword ? t('auth.passwordsDontMatch') : ''}
      />

      <Button type="submit" fullWidth variant="contained" sx={{ mt: 3, mb: 2 }} disabled={loading}>
        {loading ? <CircularProgress size={24} color="inherit" /> : t('auth.register')}
      </Button>

      <Typography variant="body2" align="center">
        {t('auth.hasAccount')}{' '}
        <Link to="/login" style={{ color: '#3B82F6', textDecoration: 'none' }}>{t('auth.login')}</Link>
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
