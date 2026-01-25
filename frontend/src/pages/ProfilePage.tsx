import { useState } from 'react'
import { 
  Box, Typography, Card, CardContent, Avatar, Chip, 
  TextField, Button, Divider, Grid,
  Dialog, DialogTitle, DialogContent, DialogActions,
  Alert
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import EmailIcon from '@mui/icons-material/Email'
import { useAuth } from '../contexts/AuthContext'
import { useLocale } from '../contexts/LocaleContext'
import api from '../lib/api'
import { MessageDialog } from '../components/common/MessageDialog'

export default function ProfilePage() {
  const { user } = useAuth()
  const { t, formatRole } = useLocale()
  
  // Состояния редактирования профиля
  const [isEditing, setIsEditing] = useState(false)
  const [lastName, setLastName] = useState(user?.last_name || '')
  const [firstName, setFirstName] = useState(user?.first_name || '')
  const [middleName, setMiddleName] = useState(user?.middle_name || '')
  
  // Состояния смены пароля
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  // Состояния смены email
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)
  const [emailStep, setEmailStep] = useState<'request' | 'confirm'>('request')
  const [newEmail, setNewEmail] = useState('')
  const [emailCode, setEmailCode] = useState('')
  const [devCode, setDevCode] = useState('')  // Для режима разработки
  
  // UI состояния
  const [loading, setLoading] = useState(false)
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

  if (!user) return null

  const displayRole = formatRole(user.role)

  const handleEditToggle = () => {
    if (!isEditing) {
      // Начинаем редактирование - заполняем поля текущими значениями
      setLastName(user.last_name)
      setFirstName(user.first_name)
      setMiddleName(user.middle_name || '')
    }
    setIsEditing(!isEditing)
  }

  const handleSaveProfile = async () => {
    setLoading(true)

    try {
      await api.put('/users/me', {
        last_name: lastName,
        first_name: firstName,
        middle_name: middleName || null,
      })
      
      setMessageDialog({
        open: true,
        title: t('common.success'),
        content: t('profile.saved'),
        severity: 'success'
      })
      setIsEditing(false)
      
      // Перезагружаем страницу для обновления данных
      setTimeout(() => window.location.reload(), 1500)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      let content = t('common.error')
      if (Array.isArray(detail)) {
        content = detail[0]?.msg || t('common.error')
      } else if (typeof detail === 'string') {
        content = detail
      }
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content,
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordDialogOpen = () => {
    setPasswordDialogOpen(true)
    setNewPassword('')
    setConfirmPassword('')
  }

  const handlePasswordDialogClose = () => {
    setPasswordDialogOpen(false)
  }

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: t('profile.passwordMismatch'),
        severity: 'error'
      })
      return
    }

    if (newPassword.length < 6) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: t('auth.passwordMin'),
        severity: 'error'
      })
      return
    }

    setLoading(true)

    try {
      await api.put('/users/me', {
        password: newPassword,
      })
      
      setMessageDialog({
        open: true,
        title: t('common.success'),
        content: t('profile.passwordChanged'),
        severity: 'success'
      })
      handlePasswordDialogClose()
    } catch (err: any) {
      const detail = err.response?.data?.detail
      let content = t('common.error')
      if (Array.isArray(detail)) {
        content = detail[0]?.msg || t('common.error')
      } else if (typeof detail === 'string') {
        content = detail
      }
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content,
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleEmailDialogOpen = () => {
    setEmailDialogOpen(true)
    setEmailStep('request')
    setNewEmail('')
    setEmailCode('')
    setDevCode('')
  }

  const handleEmailDialogClose = () => {
    setEmailDialogOpen(false)
  }

  const handleRequestEmailChange = async () => {
    if (!newEmail || !newEmail.includes('@')) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: 'Введите корректный email',
        severity: 'error'
      })
      return
    }

    setLoading(true)

    try {
      const response = await api.post('/users/me/request-email-change', {
        new_email: newEmail,
      })
      
      // Сохраняем dev код если он есть
      if (response.data.dev_code) {
        setDevCode(response.data.dev_code)
      }
      
      setEmailStep('confirm')
      setMessageDialog({
        open: true,
        title: t('common.success'),
        content: 'Код подтверждения отправлен на новый email',
        severity: 'success'
      })
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: typeof detail === 'string' ? detail : 'Ошибка при отправке кода',
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmEmailChange = async () => {
    if (!emailCode || emailCode.length !== 6) {
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: 'Введите 6-значный код',
        severity: 'error'
      })
      return
    }

    setLoading(true)

    try {
      await api.post('/users/me/confirm-email-change', {
        code: emailCode,
      })
      
      setMessageDialog({
        open: true,
        title: t('common.success'),
        content: 'Email успешно изменен',
        severity: 'success'
      })
      handleEmailDialogClose()
      
      // Перезагружаем страницу для обновления данных
      setTimeout(() => {
        window.location.reload()
      }, 1500)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setMessageDialog({
        open: true,
        title: t('common.error'),
        content: typeof detail === 'string' ? detail : 'Неверный код подтверждения',
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCancelEmailChange = async () => {
    try {
      await api.delete('/users/me/cancel-email-change')
      handleEmailDialogClose()
    } catch (err) {
      handleEmailDialogClose()
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          {t('profile.title')}
        </Typography>
        <Button 
          variant={isEditing ? 'outlined' : 'contained'}
          startIcon={<EditIcon />}
          onClick={handleEditToggle}
        >
          {isEditing ? t('profile.cancel') : t('profile.edit')}
        </Button>
      </Box>

      <Card>
        <CardContent>
          {!isEditing ? (
            // Режим просмотра
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 3 }}>
                <Avatar sx={{ width: 80, height: 80, fontSize: '2rem' }}>
                  {user.last_name.charAt(0).toUpperCase()}
                </Avatar>
                <Box>
                  <Typography variant="h5">
                    {user.last_name} {user.first_name} {user.middle_name || ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {user.email}
                  </Typography>
                  <Chip 
                    label={displayRole} 
                    size="small" 
                    color="primary" 
                    sx={{ mt: 1 }} 
                  />
                </Box>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button 
                  variant="outlined" 
                  onClick={handlePasswordDialogOpen}
                >
                  {t('profile.changePassword')}
                </Button>
                <Button 
                  variant="outlined" 
                  startIcon={<EmailIcon />}
                  onClick={handleEmailDialogOpen}
                >
                  {t('profile.changeEmail')}
                </Button>
              </Box>
            </>
          ) : (
            // Режим редактирования
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {t('profile.editDescription')}
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label={t('auth.lastName')}
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label={t('auth.firstName')}
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label={t('auth.middleName')}
                    value={middleName}
                    onChange={(e) => setMiddleName(e.target.value)}
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button 
                  variant="contained" 
                  onClick={handleSaveProfile}
                  disabled={loading}
                >
                  {loading ? t('common.loading') : t('profile.save')}
                </Button>
                <Button 
                  variant="outlined" 
                  onClick={handleEditToggle}
                >
                  {t('profile.cancel')}
                </Button>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Диалог смены пароля */}
      <Dialog open={passwordDialogOpen} onClose={handlePasswordDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>{t('profile.changePassword')}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            margin="normal"
            label={t('profile.newPassword')}
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            helperText={t('auth.passwordMin')}
          />
          <TextField
            fullWidth
            margin="normal"
            label={t('profile.confirmPassword')}
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={confirmPassword.length > 0 && newPassword !== confirmPassword}
            helperText={confirmPassword.length > 0 && newPassword !== confirmPassword ? t('profile.passwordMismatch') : ''}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handlePasswordDialogClose}>
            {t('profile.cancel')}
          </Button>
          <Button 
            onClick={handleChangePassword} 
            variant="contained"
            disabled={loading || !newPassword || !confirmPassword}
          >
            {loading ? t('common.loading') : t('profile.save')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог смены email */}
      <Dialog open={emailDialogOpen} onClose={handleEmailDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>{t('profile.changeEmail')}</DialogTitle>
        <DialogContent>
          {emailStep === 'request' ? (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2, mb: 2 }}>
                Текущий email: <strong>{user?.email}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Введите новый email. На него будет отправлен код подтверждения.
              </Typography>
              <TextField
                fullWidth
                margin="normal"
                label="Новый email"
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                autoFocus
              />
            </>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2, mb: 2 }}>
                Код подтверждения отправлен на: <strong>{newEmail}</strong>
              </Typography>
              {devCode && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  DEV режим - код: <strong>{devCode}</strong>
                </Alert>
              )}
              <TextField
                fullWidth
                margin="normal"
                label="Код подтверждения (6 цифр)"
                value={emailCode}
                onChange={(e) => setEmailCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                inputProps={{ maxLength: 6, pattern: '[0-9]*' }}
                autoFocus
              />
              <Typography variant="caption" color="text.secondary">
                Код действителен 15 минут
              </Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={emailStep === 'confirm' ? handleCancelEmailChange : handleEmailDialogClose}>
            {t('profile.cancel')}
          </Button>
          {emailStep === 'request' ? (
            <Button 
              onClick={handleRequestEmailChange} 
              variant="contained"
              disabled={loading || !newEmail}
            >
              {loading ? t('common.loading') : 'Отправить код'}
            </Button>
          ) : (
            <Button 
              onClick={handleConfirmEmailChange} 
              variant="contained"
              disabled={loading || emailCode.length !== 6}
            >
              {loading ? t('common.loading') : 'Подтвердить'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

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
