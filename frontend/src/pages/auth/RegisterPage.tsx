import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Box, TextField, Button, Typography, Alert } from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [lastName, setLastName] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const { t } = useLocale()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Валидация
    if (password.length < 6) {
      setError(t('auth.passwordMin'))
      return
    }

    if (lastName.length < 1) {
      setError(t('auth.enterLastName'))
      return
    }

    if (firstName.length < 1) {
      setError(t('auth.enterFirstName'))
      return
    }

    setLoading(true)

    try {
      await register(email, password, lastName, firstName, middleName || undefined)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail[0]?.msg || t('common.error'))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError(t('common.error'))
      }
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
        type="password"
        id="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        helperText={t('auth.passwordMin')}
        error={password.length > 0 && password.length < 6}
      />

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2 }}
        disabled={loading}
      >
        {loading ? t('auth.registering') : t('auth.register')}
      </Button>

      <Typography variant="body2" align="center">
        {t('auth.hasAccount')}{' '}
        <Link to="/login" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          {t('auth.login')}
        </Link>
      </Typography>
    </Box>
  )
}
