import { Box, Typography, Card, CardContent, Avatar, Chip } from '@mui/material'
import { useAuth } from '../contexts/AuthContext'

export default function ProfilePage() {
  const { user } = useAuth()

  if (!user) return null

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Профиль
      </Typography>

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 3 }}>
            <Avatar sx={{ width: 80, height: 80, fontSize: '2rem' }}>
              {user.full_name.charAt(0).toUpperCase()}
            </Avatar>
            <Box>
              <Typography variant="h5">{user.full_name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {user.email}
              </Typography>
              <Chip 
                label={user.role} 
                size="small" 
                color="primary" 
                sx={{ mt: 1 }} 
              />
            </Box>
          </Box>

          <Typography variant="body2" color="text.secondary">
            Здесь будет возможность редактировать профиль, изменить пароль и другие настройки.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}

