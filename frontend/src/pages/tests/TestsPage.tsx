import { Box, Typography, Button, Grid, Card, CardContent, CardActions, Chip } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import AddIcon from '@mui/icons-material/Add'

export default function TestsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isStudent = user?.role === 'student'

  // TODO: Загрузка тестов через React Query
  const tests = [] // Placeholder

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          {isStudent ? 'Доступные тесты' : 'Мои тесты'}
        </Typography>
        {!isStudent && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/tests/create')}
          >
            Создать тест
          </Button>
        )}
      </Box>

      {tests.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {isStudent ? 'Нет доступных тестов' : 'У вас пока нет тестов'}
            </Typography>
            {!isStudent && (
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                sx={{ mt: 2 }}
                onClick={() => navigate('/tests/create')}
              >
                Создать первый тест
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {tests.map((test: any) => (
            <Grid item xs={12} md={6} key={test.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {test.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {test.description}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    <Chip label={test.status} size="small" color="primary" />
                    <Chip label={`${test.questions_count} вопросов`} size="small" variant="outlined" />
                  </Box>
                </CardContent>
                <CardActions>
                  <Button size="small" onClick={() => navigate(`/tests/${test.id}`)}>
                    {isStudent ? 'Начать тест' : 'Просмотр'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  )
}

