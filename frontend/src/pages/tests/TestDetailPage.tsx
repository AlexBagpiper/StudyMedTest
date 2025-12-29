import { Box, Typography, Button, Card, CardContent } from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'

export default function TestDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  // TODO: Загрузка теста через React Query

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/tests')}
        sx={{ mb: 2 }}
      >
        Назад к тестам
      </Button>

      <Typography variant="h4" gutterBottom>
        Детали теста
      </Typography>

      <Card>
        <CardContent>
          <Typography variant="body1">
            Тест ID: {id}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Здесь будет отображаться подробная информация о тесте, вопросы и возможность начать прохождение.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}

