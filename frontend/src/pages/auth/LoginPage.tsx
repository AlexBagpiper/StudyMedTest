import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Box, TextField, Button, Typography } from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import { MessageDialog } from '../../components/common/MessageDialog'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [messageDialog, setMessageDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { t, translateError } = useLocale()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await login(email, password)
    } catch (err: any) {
      setMessageDialog({
        open: true,
        message: translateError(err.response?.data?.detail)
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%', mt: 1 }}>
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
