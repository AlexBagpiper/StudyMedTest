import { Outlet } from 'react-router-dom'
import { Box, AppBar, Toolbar, Typography, IconButton, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Avatar, Menu, MenuItem } from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/Dashboard'
import QuizIcon from '@mui/icons-material/Quiz'
import TopicIcon from '@mui/icons-material/Topic'
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer'
import AssignmentIcon from '@mui/icons-material/Assignment'
import LanguageIcon from '@mui/icons-material/Language'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import EmailIcon from '@mui/icons-material/Email'
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLocale, Locale } from '../contexts/LocaleContext'
import { APP_CONFIG } from '../config'

const DRAWER_WIDTH = 240

export default function MainLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [langAnchorEl, setLangAnchorEl] = useState<null | HTMLElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { t, formatName, formatRole, locale, setLocale } = useLocale()

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleProfileMenuClose = () => {
    setAnchorEl(null)
  }

  const handleLogout = () => {
    handleProfileMenuClose()
    logout()
  }

  const handleLangMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setLangAnchorEl(event.currentTarget)
  }

  const handleLangMenuClose = () => {
    setLangAnchorEl(null)
  }

  const handleLocaleChange = (newLocale: Locale) => {
    setLocale(newLocale)
    handleLangMenuClose()
  }

  const displayName = user 
    ? formatName(user.last_name, user.first_name, user.middle_name)
    : ''

  const displayRole = user ? formatRole(user.role) : ''

  const menuItems = [
    { text: t('nav.dashboard'), icon: <DashboardIcon />, path: '/' },
    ...(user?.role !== 'student' ? [
      { text: t('nav.topics'), icon: <TopicIcon />, path: '/topics' }
    ] : []),
    { text: t('nav.tests'), icon: <QuizIcon />, path: '/tests' },
    ...(user?.role !== 'student' ? [
      { text: t('nav.questions'), icon: <QuestionAnswerIcon />, path: '/questions' },
    ] : []),
    { 
      text: t('nav.submissions'), 
      icon: <AssignmentIcon />, 
      path: user?.role === 'student' ? '/submissions' : '/admin/submissions' 
    },
    ...(user?.role === 'admin' ? [
      { text: t('nav.admin'), icon: <AdminPanelSettingsIcon />, path: '/admin' },
    ] : []),
    { text: t('nav.mail'), icon: <EmailIcon />, path: 'https://mail.med-testing.ru', isExternal: true },
  ]

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          {APP_CONFIG.APP_NAME}
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton onClick={() => {
              if ('isExternal' in item && item.isExternal) {
                window.open(item.path, '_blank')
                return
              }
              // Если кликаем на /admin и уже на /admin, передаем сигнал сброса через state
              if (location.pathname === item.path && item.path === '/admin') {
                navigate(item.path, { replace: true, state: { reset: true } })
              } else {
                navigate(item.path)
              }
            }}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {APP_CONFIG.APP_FULL_NAME}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Переключатель языка */}
            <IconButton color="inherit" onClick={handleLangMenuOpen} size="small">
              <LanguageIcon />
            </IconButton>
            <Menu
              anchorEl={langAnchorEl}
              open={Boolean(langAnchorEl)}
              onClose={handleLangMenuClose}
            >
              <MenuItem 
                onClick={() => handleLocaleChange('ru')}
                selected={locale === 'ru'}
              >
                Русский
              </MenuItem>
              <MenuItem 
                onClick={() => handleLocaleChange('en')}
                selected={locale === 'en'}
              >
                English
              </MenuItem>
            </Menu>

            <Typography variant="body2">
              {displayName} ({displayRole})
            </Typography>
            <IconButton onClick={handleProfileMenuOpen} size="small">
              <Avatar sx={{ width: 32, height: 32 }}>
                {user?.last_name?.charAt(0).toUpperCase()}
              </Avatar>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleProfileMenuClose}
      >
        <MenuItem onClick={() => { navigate('/profile'); handleProfileMenuClose(); }}>
          {t('nav.profile')}
        </MenuItem>
        <MenuItem onClick={handleLogout}>{t('nav.logout')}</MenuItem>
      </Menu>

      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: 8,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}
