import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Box, TextField, Button, Typography, Alert } from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await register(email, password, fullName)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации.')
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
        id="fullName"
        label="Полное имя"
        name="fullName"
        autoFocus
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
      />
      <TextField
        margin="normal"
        required
        fullWidth
        id="email"
        label="Email"
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
        label="Пароль"
        type="password"
        id="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
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
        {loading ? 'Регистрация...' : 'Зарегистрироваться'}
      </Button>

      <Typography variant="body2" align="center">
        Уже есть аккаунт?{' '}
        <Link to="/login" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          Войти
        </Link>
      </Typography>
    </Box>
  )
}

