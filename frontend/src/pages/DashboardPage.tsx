import { Box, Typography, Grid, Card, CardContent, Button } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import QuizIcon from '@mui/icons-material/Quiz'
import AssignmentIcon from '@mui/icons-material/Assignment'
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer'

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const getWelcomeMessage = () => {
    switch (user?.role) {
      case 'admin':
        return 'Добро пожаловать, администратор!'
      case 'teacher':
        return 'Добро пожаловать, преподаватель!'
      case 'student':
        return 'Добро пожаловать, студент!'
      default:
        return 'Добро пожаловать!'
    }
  }

  const quickActions = user?.role === 'student' 
    ? [
        {
          title: 'Доступные тесты',
          description: 'Пройдите новый тест',
          icon: <QuizIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/tests'),
          color: '#3B82F6',
        },
        {
          title: 'Мои результаты',
          description: 'Просмотрите ваши результаты',
          icon: <AssignmentIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/submissions'),
          color: '#10B981',
        },
      ]
    : [
        {
          title: 'Создать тест',
          description: 'Создайте новый тест для студентов',
          icon: <QuizIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/tests'),
          color: '#3B82F6',
        },
        {
          title: 'Создать вопрос',
          description: 'Добавьте новый вопрос в базу',
          icon: <QuestionAnswerIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/questions'),
          color: '#8B5CF6',
        },
        {
          title: 'Результаты студентов',
          description: 'Просмотрите результаты тестов',
          icon: <AssignmentIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/submissions'),
          color: '#10B981',
        },
      ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {getWelcomeMessage()}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        {user?.full_name}
      </Typography>

      <Grid container spacing={3}>
        {quickActions.map((action, index) => (
          <Grid item xs={12} md={4} key={index}>
            <Card
              sx={{
                height: '100%',
                cursor: 'pointer',
                transition: 'all 0.3s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
              onClick={action.action}
            >
              <CardContent
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  gap: 2,
                  p: 3,
                }}
              >
                <Box sx={{ color: action.color }}>{action.icon}</Box>
                <Typography variant="h6">{action.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {action.description}
                </Typography>
                <Button variant="contained" sx={{ mt: 2 }}>
                  Перейти
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Статистика (можно добавить позже) */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Статистика
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Здесь будет отображаться статистика и аналитика
        </Typography>
      </Box>
    </Box>
  )
}

