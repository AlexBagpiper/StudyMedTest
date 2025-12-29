import { Box, Typography, Button, Card, CardContent } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { useAuth } from '../../contexts/AuthContext'

export default function QuestionsPage() {
  const { user } = useAuth()

  // Только для teacher и admin
  if (user?.role === 'student') {
    return (
      <Box>
        <Typography variant="h5">Доступ запрещен</Typography>
        <Typography variant="body2" color="text.secondary">
          Студенты не имеют доступа к этой странице.
        </Typography>
      </Box>
    )
  }

  // TODO: Загрузка вопросов через React Query

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Банк вопросов</Typography>
        <Button variant="contained" startIcon={<AddIcon />}>
          Создать вопрос
        </Button>
      </Box>

      <Card>
        <CardContent sx={{ textAlign: 'center', py: 6 }}>
          <Typography variant="h6" color="text.secondary">
            Банк вопросов пуст
          </Typography>
          <Button variant="outlined" startIcon={<AddIcon />} sx={{ mt: 2 }}>
            Создать первый вопрос
          </Button>
        </CardContent>
      </Card>
    </Box>
  )
}

