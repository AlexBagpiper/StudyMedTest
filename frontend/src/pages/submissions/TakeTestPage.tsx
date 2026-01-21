import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  Divider,
  CircularProgress,
  Alert,
  TextField,
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import { AnnotationEditor } from '../../components/annotation/AnnotationEditor'
import { AnnotationData } from '../../types/annotation'

export default function TakeTestPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  
  const [submission, setSubmission] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentLabels, setCurrentLabels] = useState<any[]>([])
  const [timeLeft, setTimeLeft] = useState<number | null>(null)

  const currentQuestion = questions[currentQuestionIndex]

  useEffect(() => {
    loadSubmission()
  }, [id])

  useEffect(() => {
    if (currentQuestion?.type === 'image_annotation') {
      loadLabels(currentQuestion.id)
    }
  }, [currentQuestion])

  const loadLabels = async (questionId: string) => {
    try {
      const res = await api.get(`/questions/${questionId}/labels`)
      setCurrentLabels(res.data)
    } catch (err) {
      console.error('Failed to load labels:', err)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const loadSubmission = async () => {
    try {
      setIsLoading(true)
      // 1. Get submission
      const subRes = await api.get(`/submissions/${id}`)
      const subData = subRes.data
      setSubmission(subData)

      // 2. Get variant to get question order
      const variantRes = await api.get(`/tests/variants/${subData.variant_id}`)
      const variantData = variantRes.data
      
      // 3. Load all questions in the variant
      const questionPromises = variantData.question_order.map((qId: string) => 
        api.get(`/questions/${qId}`)
      )
      const questionResponses = await Promise.all(questionPromises)
      setQuestions(questionResponses.map(r => r.data))
      
      // Initialize answers from existing ones if any
      const initialAnswers: Record<string, any> = {}
      if (subData.answers) {
        subData.answers.forEach((a: any) => {
          initialAnswers[a.question_id] = a.student_answer || a.annotation_data
        })
      }
      setAnswers(initialAnswers)
      
    } catch (err: any) {
      console.error('Failed to load test:', err)
      setError(err.response?.data?.detail || 'Не удалось загрузить тест')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAnswerChange = (questionId: string, value: any) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }))
  }

  const saveAnswer = async (questionId: string) => {
    try {
      const answer = answers[questionId]
      await api.post(`/submissions/${id}/answers`, {
        question_id: questionId,
        student_answer: typeof answer === 'string' ? answer : null,
        annotation_data: typeof answer === 'object' ? answer : null,
      })
    } catch (err) {
      console.error('Failed to save answer:', err)
    }
  }

  const handleNext = async () => {
    if (currentQuestion) {
      await saveAnswer(currentQuestion.id)
    }
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    }
  }

  const handlePrev = async () => {
    if (currentQuestion) {
      await saveAnswer(currentQuestion.id)
    }
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const handleSubmitTest = async (isAuto = false) => {
    if (!isAuto && !window.confirm('Вы уверены, что хотите завершить тест?')) return
    
    try {
      setIsSubmitting(true)
      if (currentQuestion) {
        await saveAnswer(currentQuestion.id)
      }
      await api.post(`/submissions/${id}/submit`, {})
      navigate('/submissions')
    } catch (err: any) {
      if (isAuto) {
        // Если авто-сабмит не удался (например, уже сабмитнуто на бэкенде), просто уходим
        navigate('/submissions')
      } else {
        alert(err.response?.data?.detail || 'Не удалось завершить тест')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!submission || !submission.time_limit || submission.status !== 'in_progress') {
      setTimeLeft(null)
      return
    }

    const calculateTimeLeft = () => {
      const startedAt = new Date(submission.started_at).getTime()
      const limitMs = submission.time_limit * 60 * 1000
      const now = new Date().getTime()
      const remaining = Math.max(0, Math.floor((startedAt + limitMs - now) / 1000))
      
      if (remaining <= 0) {
        handleSubmitTest(true) // Auto-submit
        return 0
      }
      return remaining
    }

    // Initial calculation
    const initial = calculateTimeLeft()
    setTimeLeft(initial)

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev === null || prev <= 0) {
          clearInterval(timer)
          return 0
        }
        const next = prev - 1
        if (next <= 0) {
          handleSubmitTest(true)
          clearInterval(timer)
          return 0
        }
        return next
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [submission])

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button onClick={() => navigate('/tests')}>Назад к тестам</Button>
      </Box>
    )
  }

  if (questions.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>В тесте нет вопросов</Alert>
        <Button onClick={() => navigate('/tests')}>Назад к тестам</Button>
      </Box>
    )
  }

  return (
    <Box sx={{ width: '100%', px: { xs: 2, md: 4 }, py: 4 }}>
      <Paper sx={{ p: 3, mb: 3, borderRadius: 1, boxShadow: 3, width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2, alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold">
            Вопрос {currentQuestionIndex + 1} из {questions.length}
          </Typography>
          {timeLeft !== null && (
            <Typography 
              color={timeLeft < 60 ? "error" : "primary"} 
              fontWeight="bold"
              sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
            >
              Осталось: {formatTime(timeLeft)}
            </Typography>
          )}
        </Box>
        
        <Divider sx={{ mb: 3 }} />

        <Typography variant="body1" sx={{ mb: 4, whiteSpace: 'pre-wrap', fontSize: '1.1rem' }}>
          {currentQuestion?.content}
        </Typography>

        {currentQuestion?.type === 'text' ? (
          <TextField
            fullWidth
            multiline
            rows={6}
            variant="outlined"
            placeholder="Введите ваш ответ здесь..."
            value={answers[currentQuestion.id] || ''}
            onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
            sx={{ bgcolor: 'background.paper' }}
          />
        ) : (
          <Box sx={{ 
            height: 'calc(100vh - 400px)', 
            minHeight: '600px', 
            border: '1px solid', 
            borderColor: '#333', 
            borderRadius: 1, 
            overflow: 'hidden',
            bgcolor: '#1e2125'
          }}>
            <AnnotationEditor
              imageUrl={currentQuestion?.image?.presigned_url || ''}
              initialData={{
                labels: currentLabels,
                annotations: (answers[currentQuestion?.id] as AnnotationData)?.annotations || []
              }}
              onChange={(data) => handleAnswerChange(currentQuestion.id, data)}
              readOnly={false}
              hideLabels={true}
            />
          </Box>
        )}
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button 
          variant="outlined"
          disabled={currentQuestionIndex === 0} 
          onClick={handlePrev}
          sx={{ borderRadius: 2, px: 4 }}
        >
          Назад
        </Button>
        
        <Box>
          {currentQuestionIndex < questions.length - 1 ? (
            <Button 
              variant="contained" 
              onClick={handleNext}
              sx={{ borderRadius: 2, px: 4 }}
            >
              Далее
            </Button>
          ) : (
            <Button 
              variant="contained" 
              color="success" 
              onClick={handleSubmitTest}
              disabled={isSubmitting}
              sx={{ borderRadius: 2, px: 4 }}
            >
              {isSubmitting ? 'Отправка...' : 'Завершить тест'}
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  )
}
