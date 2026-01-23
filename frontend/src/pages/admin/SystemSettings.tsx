import { Box, Typography, Grid, Card, CardContent, Button } from '@mui/material'
import AssessmentIcon from '@mui/icons-material/Assessment'
import PsychologyIcon from '@mui/icons-material/Psychology'
import { useLocale } from '../../contexts/LocaleContext'

export type SettingsSection = 'menu' | 'cv' | 'llm'

interface SystemSettingsProps {
  activeSubSection: SettingsSection
  onSectionChange: (section: SettingsSection) => void
}

export default function SystemSettings({ activeSubSection, onSectionChange }: SystemSettingsProps) {
  const settingsItems = [
    {
      id: 'cv' as SettingsSection,
      title: 'Параметры CV-оценки',
      description: 'Настройка весов IoU, Recall и Precision для графических тестов',
      icon: <AssessmentIcon sx={{ fontSize: 40 }} />,
      color: '#3B82F6',
    },
    {
      id: 'llm' as SettingsSection,
      title: 'Параметры LLM-оценки',
      description: 'Настройка OpenAI/Anthropic, локальных моделей и промптов для проверки текста',
      icon: <PsychologyIcon sx={{ fontSize: 40 }} />,
      color: '#8B5CF6',
    },
  ]

  if (activeSubSection !== 'menu') return null

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Настройки системы
      </Typography>
      <Box sx={{ mb: 4 }} />

      <Grid container spacing={3}>
        {settingsItems.map((item) => (
          <Grid item xs={12} md={4} key={item.id}>
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
              onClick={() => onSectionChange(item.id)}
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
                <Box sx={{ color: item.color }}>{item.icon}</Box>
                <Typography variant="h6">{item.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.description}
                </Typography>
                <Button variant="contained" sx={{ mt: 2 }}>
                  Открыть
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
