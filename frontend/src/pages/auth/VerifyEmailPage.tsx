import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  CircularProgress,
  LinearProgress,
  Snackbar,
  Alert,
  TextField,
  Typography,
} from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'

const PENDING_EMAIL_KEY = 'pendingEmail'
const PENDING_PASSWORD_KEY = 'pendingPassword'
const RESEND_AVAILABLE_AT_KEY = 'pendingResendAvailableAt'
const DEFAULT_COOLDOWN = 60

function readInitialCooldown(): number {
  const raw = localStorage.getItem(RESEND_AVAILABLE_AT_KEY)
  if (!raw) return 0
  const ts = Number(raw)
  if (!Number.isFinite(ts)) return 0
  const remaining = Math.ceil((ts - Date.now()) / 1000)
  return remaining > 0 ? remaining : 0
}

export default function VerifyEmailPage() {
  const navigate = useNavigate()
  const { verifyEmail, resendVerification, login } = useAuth()

  const [email] = useState<string>(() => localStorage.getItem(PENDING_EMAIL_KEY) ?? '')
  const [code, setCode] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [resending, setResending] = useState(false)
  const [resendAfter, setResendAfter] = useState<number>(() => readInitialCooldown())
  const [cooldownTotal, setCooldownTotal] = useState<number>(() => {
    const initial = readInitialCooldown()
    return initial > 0 ? initial : DEFAULT_COOLDOWN
  })
  const [snack, setSnack] = useState<{ open: boolean; severity: 'error' | 'success' | 'info'; message: string }>({
    open: false, severity: 'info', message: '',
  })

  const tickRef = useRef<number | null>(null)

  const startCooldown = (seconds: number) => {
    if (seconds <= 0) {
      setResendAfter(0)
      return
    }
    setCooldownTotal(seconds)
    setResendAfter(seconds)
    localStorage.setItem(RESEND_AVAILABLE_AT_KEY, String(Date.now() + seconds * 1000))

    if (tickRef.current) window.clearInterval(tickRef.current)
    tickRef.current = window.setInterval(() => {
      setResendAfter((prev) => {
        if (prev <= 1) {
          if (tickRef.current) window.clearInterval(tickRef.current)
          localStorage.removeItem(RESEND_AVAILABLE_AT_KEY)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }

  useEffect(() => {
    if (!email) {
      navigate('/register', { replace: true })
      return
    }
    // Resume countdown saved in localStorage (covers F5 and fresh-arrival from register).
    const remaining = readInitialCooldown()
    if (remaining > 0) {
      startCooldown(remaining)
    }
    return () => { if (tickRef.current) window.clearInterval(tickRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email])

  const pickDetail = (err: any, fallback: string): string => {
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail[0]?.msg ?? fallback
    return fallback
  }

  const handleVerify = async () => {
    if (code.length !== 6) return
    setVerifying(true)
    try {
      await verifyEmail(email, code)
      setSnack({ open: true, severity: 'success', message: 'Email подтверждён' })

      const savedPassword = sessionStorage.getItem(PENDING_PASSWORD_KEY)
      localStorage.removeItem(PENDING_EMAIL_KEY)
      localStorage.removeItem(RESEND_AVAILABLE_AT_KEY)
      sessionStorage.removeItem(PENDING_PASSWORD_KEY)
      if (tickRef.current) { window.clearInterval(tickRef.current); tickRef.current = null }

      if (savedPassword) {
        try {
          await login(email, savedPassword)
          return
        } catch {
          navigate('/login?verified=1', { replace: true })
          return
        }
      }
      navigate('/login?verified=1', { replace: true })
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 410) {
        setSnack({ open: true, severity: 'error', message: 'Срок действия кода истёк. Запросите новый.' })
      } else if (status === 429) {
        setSnack({ open: true, severity: 'error', message: 'Слишком много неверных попыток. Зарегистрируйтесь заново.' })
        localStorage.removeItem(PENDING_EMAIL_KEY)
        localStorage.removeItem(RESEND_AVAILABLE_AT_KEY)
        sessionStorage.removeItem(PENDING_PASSWORD_KEY)
        setTimeout(() => navigate('/register', { replace: true }), 1500)
      } else {
        setSnack({ open: true, severity: 'error', message: pickDetail(err, 'Неверный код подтверждения') })
      }
      setCode('')
    } finally {
      setVerifying(false)
    }
  }

  const handleResend = async () => {
    if (resendAfter > 0) return
    setResending(true)
    try {
      const res = await resendVerification(email)
      setSnack({ open: true, severity: 'success', message: 'Код отправлен повторно' })
      startCooldown(res?.resend_after ?? 60)
    } catch (err: any) {
      setSnack({ open: true, severity: 'error', message: pickDetail(err, 'Не удалось отправить код. Попробуйте позже.') })
    } finally {
      setResending(false)
    }
  }

  return (
    <Box sx={{ width: '100%', mt: 1 }}>
      <Typography variant="h6" align="center" sx={{ mt: 2, mb: 1 }}>
        Подтверждение почты
      </Typography>
      <Typography sx={{ mb: 3, textAlign: 'center', color: 'text.secondary' }}>
        Мы отправили 6-значный код на адрес:<br />
        <strong>{email}</strong>
      </Typography>

      <TextField
        fullWidth
        label="Код подтверждения"
        value={code}
        autoFocus
        onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
        inputProps={{
          inputMode: 'numeric',
          style: { textAlign: 'center', fontSize: '28px', letterSpacing: '8px', fontWeight: 'bold' },
        }}
        placeholder="000000"
      />

      <Button
        onClick={handleVerify}
        variant="contained"
        fullWidth
        size="large"
        sx={{ mt: 3, mb: 1 }}
        disabled={code.length !== 6 || verifying}
      >
        {verifying ? <CircularProgress size={26} color="inherit" /> : 'Подтвердить'}
      </Button>

      {resendAfter > 0 ? (
        <Box sx={{ mt: 1.5, px: 1 }}>
          <LinearProgress
            variant="determinate"
            value={Math.max(0, Math.min(100, ((cooldownTotal - resendAfter) / cooldownTotal) * 100))}
            sx={{ height: 6, borderRadius: 3 }}
          />
          <Typography variant="caption" sx={{ mt: 0.75, display: 'block', textAlign: 'center', color: 'text.secondary' }}>
            Повторная отправка будет доступна через <strong>{resendAfter}</strong> сек
          </Typography>
        </Box>
      ) : (
        <Button
          onClick={handleResend}
          color="primary"
          fullWidth
          disabled={resending || verifying}
          sx={{ textTransform: 'none' }}
        >
          {resending ? 'Отправка...' : 'Отправить код повторно'}
        </Button>
      )}

      <Typography variant="body2" align="center" sx={{ mt: 2 }}>
        <Link to="/register" style={{ color: '#3B82F6', textDecoration: 'none' }}>
          Изменить данные регистрации
        </Link>
      </Typography>

      <Snackbar
        open={snack.open}
        autoHideDuration={5000}
        onClose={() => setSnack({ ...snack, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={snack.severity}
          onClose={() => setSnack({ ...snack, open: false })}
          sx={{ width: '100%' }}
        >
          {snack.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
