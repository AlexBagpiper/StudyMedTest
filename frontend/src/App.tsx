import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { useLocale } from './contexts/LocaleContext'

// Layouts
import MainLayout from './layouts/MainLayout'
import AuthLayout from './layouts/AuthLayout'

// Pages
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import TestsPage from './pages/tests/TestsPage'
import TestDetailPage from './pages/tests/TestDetailPage'
import TestFormPage from './pages/tests/TestFormPage'
import TopicsPage from './pages/topics/TopicsPage'
import QuestionsPage from './pages/questions/QuestionsPage'
import SubmissionsPage from './pages/submissions/SubmissionsPage'
import TakeTestPage from './pages/submissions/TakeTestPage'
import ProfilePage from './pages/ProfilePage'
import AdminPage from './pages/admin/AdminPage'
import AdminSubmissionsPage from './pages/admin/AdminSubmissionsPage'
import SubmissionDetailsPage from './pages/admin/SubmissionDetailsPage'
import SubmissionReviewPage from './pages/admin/SubmissionReviewPage'

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

// Admin or Teacher route wrapper
function StaffRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (user.role !== 'admin' && user.role !== 'teacher') {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

// Admin-only route wrapper
function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (user.role !== 'admin') {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function App() {
  const { user } = useAuth()
  const { t } = useLocale()

  return (
    <Routes>
      {/* Public routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage />} />
        <Route path="/register" element={user ? <Navigate to="/" /> : <RegisterPage />} />
      </Route>

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="/tests" element={<TestsPage />} />
        <Route path="/tests/create" element={<TestFormPage />} />
        <Route path="/tests/:testId/edit" element={<TestFormPage />} />
        <Route path="/tests/:id" element={<TestDetailPage />} />
        <Route path="/topics" element={<TopicsPage />} />
        <Route path="/questions" element={<QuestionsPage />} />
        <Route path="/submissions" element={<SubmissionsPage />} />
        <Route path="/submissions/:id" element={<TakeTestPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route
          path="/admin/submissions"
          element={
            <StaffRoute>
              <AdminSubmissionsPage />
            </StaffRoute>
          }
        />
        <Route
          path="/admin/submissions/:id"
          element={
            <StaffRoute>
              <SubmissionDetailsPage />
            </StaffRoute>
          }
        />
        <Route
          path="/admin/submissions/:id/review"
          element={
            <StaffRoute>
              <SubmissionReviewPage />
            </StaffRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminPage />
            </AdminRoute>
          }
        />
      </Route>

      {/* 404 */}
      <Route path="*" element={<div>{t('common.notFound')}</div>} />
    </Routes>
  )
}

export default App

