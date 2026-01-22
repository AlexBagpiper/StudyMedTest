import { Box, Typography, Grid, Card, CardContent, Button } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLocale } from '../contexts/LocaleContext'
import QuizIcon from '@mui/icons-material/Quiz'
import AssignmentIcon from '@mui/icons-material/Assignment'
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer'

export default function DashboardPage() {
  const { user } = useAuth()
  const { t, formatName } = useLocale()
  const navigate = useNavigate()

  const getWelcomeMessage = () => {
    switch (user?.role) {
      case 'admin':
        return t('dashboard.welcome.admin')
      case 'teacher':
        return t('dashboard.welcome.teacher')
      case 'student':
        return t('dashboard.welcome.student')
      default:
        return t('dashboard.welcome.default')
    }
  }

  const displayName = user 
    ? formatName(user.last_name, user.first_name, user.middle_name)
    : ''

  const quickActions = user?.role === 'student' 
    ? [
        {
          title: t('dashboard.availableTests'),
          description: t('dashboard.takeTest'),
          icon: <QuizIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/tests'),
          color: '#3B82F6',
        },
        {
          title: t('dashboard.myResults'),
          description: t('dashboard.viewResults'),
          icon: <AssignmentIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/submissions'),
          color: '#10B981',
        },
      ]
    : [
        {
          title: t('dashboard.createTest'),
          description: t('dashboard.createTestDesc'),
          icon: <QuizIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/tests'),
          color: '#3B82F6',
        },
        {
          title: t('dashboard.createQuestion'),
          description: t('dashboard.createQuestionDesc'),
          icon: <QuestionAnswerIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/questions'),
          color: '#8B5CF6',
        },
        {
          title: t('dashboard.studentResults'),
          description: t('dashboard.studentResultsDesc'),
          icon: <AssignmentIcon sx={{ fontSize: 40 }} />,
          action: () => navigate('/admin/submissions'),
          color: '#10B981',
        },
      ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {getWelcomeMessage()}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        {displayName}
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
                  {t('dashboard.go')}
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Статистика (можно добавить позже) */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          {t('dashboard.statistics')}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t('dashboard.statisticsDesc')}
        </Typography>
      </Box>
    </Box>
  )
}
