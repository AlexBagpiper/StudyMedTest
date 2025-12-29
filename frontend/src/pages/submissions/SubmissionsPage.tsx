import { Box, Typography, Card, CardContent, Chip } from '@mui/material'
import { useAuth } from '../../contexts/AuthContext'

export default function SubmissionsPage() {
  const { user } = useAuth()

  // TODO: Загрузка submissions через React Query
  const submissions = [] // Placeholder

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {user?.role === 'student' ? 'Мои результаты' : 'Результаты студентов'}
      </Typography>

      {submissions.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {user?.role === 'student' 
                ? 'У вас пока нет завершенных тестов' 
                : 'Нет результатов для отображения'}
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Box>
          {/* Таблица с результатами */}
          <Typography variant="body2" color="text.secondary">
            Здесь будет таблица с результатами тестов
          </Typography>
        </Box>
      )}
    </Box>
  )
}

