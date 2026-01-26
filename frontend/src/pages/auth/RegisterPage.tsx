import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Box, 
  TextField, 
  Button, 
  Typography, 
  IconButton, 
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress
} from '@mui/material'
import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import { MessageDialog } from '../../components/common/MessageDialog'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [lastName, setLastName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [messageDialog, setMessageDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [loading, setLoading] = useState(false)
  
  // Состояния для подтверждения почты
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false)
  const [verificationCode, setVerificationCode] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [resending, setResending] = useState(false)

  const { register, verifyEmail, resendVerification, login } = useAuth()
  const { t } = useLocale()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Валидация
    if (password.length < 6) {
      setMessageDialog({ open: true, message: t('auth.passwordMin') })
      return
    }

    if (password !== confirmPassword) {
      setMessageDialog({ open: true, message: t('auth.passwordsDontMatch') })
      return
    }

    if (lastName.length < 1) {
      setMessageDialog({ open: true, message: t('auth.enterLastName') })
      return
    }

    if (firstName.length < 1) {
      setMessageDialog({ open: true, message: t('auth.enterFirstName') })
      return
    }

    setLoading(true)

    try {
      await register(email, password, lastName, firstName, middleName || undefined)
      setVerifyDialogOpen(true)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      let message = t('common.error')
      if (Array.isArray(detail)) {
        message = detail[0]?.msg || t('common.error')
      } else if (typeof detail === 'string') {
        message = detail
      }
      setMessageDialog({ open: true, message })
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyCode = async () => {
    if (verificationCode.length !== 6) return
    
    setVerifying(true)
    try {
      await verifyEmail(email, verificationCode)
      // После успешной верификации — логинимся
      await login(email, password)
      setVerifyDialogOpen(false)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setMessageDialog({ 
        open: true, 
        message: typeof detail === 'string' ? detail : "Неверный код подтверждения" 
      })
    } finally {
      setVerifying(false)
    }
  }

  const handleResendCode = async () => {
    setResending(true)
    try {
      await resendVerification(email)
      // В реальном приложении здесь лучше использовать Snackbar
      alert("Код отправлен повторно")
    } catch (err: any) {
      console.error(err)
    } finally {
      setResending(false)
    }
  }

  const handleCloseVerifyDialog = () => {
    if (!verifying) {
      setVerifyDialogOpen(false)
      setVerificationCode('')
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%', mt: 1 }}>
      <TextField
        margin="normal"
        required
        fullWidth
        id="lastName"
        label={t('auth.lastName')}
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
        label={t('auth.firstName')}
        name="firstName"
        value={firstName}
        onChange={(e) => setFirstName(e.target.value)}
      />
      <TextField
        margin="normal"
        fullWidth
        id="middleName"
        label={t('auth.middleName')}
        name="middleName"
        value={middleName}
        onChange={(e) => setMiddleName(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        id="email"
        label={t('auth.email')}
        name="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        name="password"
        label={t('auth.password')}
        type={showPassword ? 'text' : 'password'}
        id="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        helperText={t('auth.passwordMin')}
        error={password.length > 0 && password.length < 6}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label="toggle password visibility"
                onClick={() => setShowPassword(!showPassword)}
                edge="end"
              >
                {showPassword ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        name="confirmPassword"
        label={t('auth.confirmPassword')}
        type={showPassword ? 'text' : 'password'}
        id="confirmPassword"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        error={confirmPassword.length > 0 && password !== confirmPassword}
        helperText={confirmPassword.length > 0 && password !== confirmPassword ? t('auth.passwordsDontMatch') : ''}
      />

      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
        disabled={loading}
      >
        {loading ? <CircularProgress size={24} color="inherit" /> : t('auth.register')}
      </Button>

      <Typography variant="body2" align="center">
        {t('auth.hasAccount')}{' '}
        <Link to="/login" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          {t('auth.login')}
        </Link>
      </Typography>

      {/* Диалог подтверждения почты */}
      <Dialog 
        open={verifyDialogOpen} 
        onClose={handleCloseVerifyDialog}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: 'center', pt: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ width: 40 }} /> 
          Подтверждение почты
          <IconButton
            onClick={handleCloseVerifyDialog}
            disabled={verifying}
            sx={{ color: 'text.secondary' }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 3, textAlign: 'center', color: 'text.secondary' }}>
            Мы отправили 6-значный код на адрес:<br/>
            <strong>{email}</strong>
          </Typography>
          <TextField
            fullWidth
            label="Код подтверждения"
            value={verificationCode}
            autoFocus
            onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            inputProps={{ 
              style: { 
                textAlign: 'center', 
                fontSize: '28px', 
                letterSpacing: '8px',
                fontWeight: 'bold'
              } 
            }}
            placeholder="000000"
          />
          <Typography variant="caption" sx={{ mt: 1, display: 'block', textAlign: 'center', color: 'text.secondary' }}>
            Код действителен в течение 24 часов
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 4, flexDirection: 'column', gap: 2 }}>
          <Button 
            onClick={handleVerifyCode} 
            variant="contained" 
            fullWidth
            size="large"
            disabled={verificationCode.length !== 6 || verifying}
          >
            {verifying ? <CircularProgress size={26} color="inherit" /> : 'Подтвердить'}
          </Button>
          <Button 
            onClick={handleResendCode} 
            color="primary" 
            disabled={resending || verifying}
            sx={{ textTransform: 'none' }}
          >
            {resending ? 'Отправка...' : 'Отправить код повторно'}
          </Button>
        </DialogActions>
      </Dialog>

      <MessageDialog
        open={messageDialog.open}
        title={t('common.error')}
        content={messageDialog.message}
        severity="error"
        onClose={() => setMessageDialog({ ...messageDialog, open: false })}
      />
    </Box>
  )
}
