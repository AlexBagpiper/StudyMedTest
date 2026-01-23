import { useState } from 'react'
import { Box, Typography, Grid, Card, CardContent, Button, Breadcrumbs, Link } from '@mui/material'
import PeopleIcon from '@mui/icons-material/People'
import SchoolIcon from '@mui/icons-material/School'
import SettingsIcon from '@mui/icons-material/Settings'
import { useLocale } from '../../contexts/LocaleContext'
import UsersManagement from './UsersManagement'
import SystemSettings, { SettingsSection } from './SystemSettings'
import CVSettings from './CVSettings'
import LLMSettings from './LLMSettings'

type AdminSection = 'main' | 'users' | 'schools' | 'settings'

export default function AdminPage() {
  const { t } = useLocale()
  const [activeSection, setActiveSection] = useState<AdminSection>('main')
  const [activeSettingsSection, setActiveSettingsSection] = useState<SettingsSection>('menu')

  const adminSections = [
    {
      id: 'users' as AdminSection,
      title: 'Пользователи',
      description: 'Управление пользователями системы',
      icon: <PeopleIcon sx={{ fontSize: 40 }} />,
      color: '#3B82F6',
    },
    {
      id: 'schools' as AdminSection,
      title: 'Учебные заведения',
      description: 'Управление учебными заведениями',
      icon: <SchoolIcon sx={{ fontSize: 40 }} />,
      color: '#8B5CF6',
    },
    {
      id: 'settings' as AdminSection,
      title: 'Настройки системы',
      description: 'Конфигурация платформы',
      icon: <SettingsIcon sx={{ fontSize: 40 }} />,
      color: '#10B981',
    },
  ]

  const renderBreadcrumbs = () => {
    if (activeSection === 'main') return null

    const sectionTitle = adminSections.find((s) => s.id === activeSection)?.title
    const isSubSetting = activeSection === 'settings' && activeSettingsSection !== 'menu'

    return (
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body1"
          onClick={() => {
            setActiveSection('main')
            setActiveSettingsSection('menu')
          }}
          sx={{ cursor: 'pointer', textDecoration: 'none' }}
        >
          Администрирование
        </Link>
        {isSubSetting ? (
          <Link
            component="button"
            variant="body1"
            onClick={() => setActiveSettingsSection('menu')}
            sx={{ cursor: 'pointer', textDecoration: 'none' }}
          >
            {sectionTitle}
          </Link>
        ) : (
          <Typography color="text.primary">{sectionTitle}</Typography>
        )}
        {isSubSetting && (
          <Typography color="text.primary">
            {activeSettingsSection === 'cv' ? 'Параметры CV-оценки' : 
             activeSettingsSection === 'llm' ? 'Параметры LLM-оценки' : ''}
          </Typography>
        )}
      </Breadcrumbs>
    )
  }

  const renderContent = () => {
    switch (activeSection) {
      case 'users':
        return <UsersManagement />
      
      case 'schools':
        return (
          <Box>
            <Typography variant="h4" gutterBottom>
              Учебные заведения
            </Typography>
            <Typography color="text.secondary">
              Функционал в разработке
            </Typography>
          </Box>
        )
      
      case 'settings':
        if (activeSettingsSection === 'cv') {
          return <CVSettings />
        }
        if (activeSettingsSection === 'llm') {
          return <LLMSettings />
        }
        return (
          <SystemSettings 
            activeSubSection={activeSettingsSection} 
            onSectionChange={setActiveSettingsSection} 
          />
        )
      
      default:
        return (
          <Box>
            <Typography variant="h4" gutterBottom>
              {t('nav.admin')}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
              Административная панель управления системой
            </Typography>

            <Grid container spacing={3}>
              {adminSections.map((section) => (
                <Grid item xs={12} md={4} key={section.id}>
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
                    onClick={() => setActiveSection(section.id)}
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
                      <Box sx={{ color: section.color }}>{section.icon}</Box>
                      <Typography variant="h6">{section.title}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {section.description}
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
  }

  return (
    <Box>
      {renderBreadcrumbs()}
      {renderContent()}
    </Box>
  )
}
