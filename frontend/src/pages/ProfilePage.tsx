import { useState } from 'react'
import { 
  Box, Typography, Card, CardContent, Avatar, Chip, 
  TextField, Button, Alert, Divider, Grid, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import { useAuth } from '../contexts/AuthContext'
import { useLocale } from '../contexts/LocaleContext'
import api from '../lib/api'

export default function ProfilePage() {
  const { user } = useAuth()
  const { t, formatName, formatRole } = useLocale()
  
  // Состояния редактирования профиля
  const [isEditing, setIsEditing] = useState(false)
  const [lastName, setLastName] = useState(user?.last_name || '')
  const [firstName, setFirstName] = useState(user?.first_name || '')
  const [middleName, setMiddleName] = useState(user?.middle_name || '')
  const [email, setEmail] = useState(user?.email || '')
  
  // Состояния смены пароля
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  // UI состояния
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  if (!user) return null

  const displayName = formatName(user.last_name, user.first_name, user.middle_name)
  const displayRole = formatRole(user.role)

  const handleEditToggle = () => {
    if (!isEditing) {
      // Начинаем редактирование - заполняем поля текущими значениями
      setLastName(user.last_name)
      setFirstName(user.first_name)
      setMiddleName(user.middle_name || '')
      setEmail(user.email)
    }
    setIsEditing(!isEditing)
    setError('')
    setSuccess('')
  }

  const handleSaveProfile = async () => {
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      await api.put('/users/me', {
        last_name: lastName,
        first_name: firstName,
        middle_name: middleName || null,
        email: email,
      })
      
      setSuccess(t('profile.saved'))
      setIsEditing(false)
      
      // Перезагружаем страницу для обновления данных
      window.location.reload()
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

  const handlePasswordDialogOpen = () => {
    setPasswordDialogOpen(true)
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
  }

  const handlePasswordDialogClose = () => {
    setPasswordDialogOpen(false)
    setError('')
  }

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setError(t('profile.passwordMismatch'))
      return
    }

    if (newPassword.length < 6) {
      setError(t('auth.passwordMin'))
      return
    }

    setLoading(true)
    setError('')

    try {
      await api.put('/users/me', {
        password: newPassword,
      })
      
      setSuccess(t('profile.passwordChanged'))
      handlePasswordDialogClose()
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

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

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

              <Button 
                variant="outlined" 
                onClick={handlePasswordDialogOpen}
              >
                {t('profile.changePassword')}
              </Button>
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
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label={t('auth.email')}
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
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
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
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
    </Box>
  )
}
