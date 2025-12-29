import { Outlet } from 'react-router-dom'
import { Box, Container, Paper, Typography } from '@mui/material'

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={3}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Typography variant="h4" component="h1" gutterBottom>
            MedTest Platform
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Система тестирования для медицинских студентов
          </Typography>
          <Outlet />
        </Paper>
      </Container>
    </Box>
  )
}

