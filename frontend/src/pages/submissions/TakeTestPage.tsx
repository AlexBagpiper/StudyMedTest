import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  Divider,
  CircularProgress,
  Alert,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  TextField,
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'

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

  useEffect(() => {
    loadSubmission()
  }, [id])

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
      subData.answers.forEach((a: any) => {
        initialAnswers[a.question_id] = a.student_answer || a.annotation_data
      })
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
    await saveAnswer(questions[currentQuestionIndex].id)
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    }
  }

  const handlePrev = async () => {
    await saveAnswer(questions[currentQuestionIndex].id)
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const handleSubmitTest = async () => {
    if (!window.confirm('Вы уверены, что хотите завершить тест?')) return
    
    try {
      setIsSubmitting(true)
      await saveAnswer(questions[currentQuestionIndex].id)
      await api.post(`/submissions/${id}/submit`)
      navigate('/submissions')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Не удалось завершить тест')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  if (questions.length === 0) {
    return <Alert severity="warning">В тесте нет вопросов</Alert>
  }

  const currentQuestion = questions[currentQuestionIndex]

  return (
    <Box maxWidth="md" sx={{ mx: 'auto' }}>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">
            Вопрос {currentQuestionIndex + 1} из {questions.length}
          </Typography>
          {submission?.test?.settings?.time_limit && (
            <Typography color="primary">
              Осталось: --:--
            </Typography>
          )}
        </Box>
        
        <Divider sx={{ mb: 3 }} />

        <Typography variant="body1" sx={{ mb: 4, whiteSpace: 'pre-wrap' }}>
          {currentQuestion.content}
        </Typography>

        {currentQuestion.type === 'text' ? (
          <TextField
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            placeholder="Введите ваш ответ здесь..."
            value={answers[currentQuestion.id] || ''}
            onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
          />
        ) : (
          <Typography color="text.secondary">
            [Здесь будет редактор аннотаций для графического вопроса]
          </Typography>
        )}
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button 
          disabled={currentQuestionIndex === 0} 
          onClick={handlePrev}
        >
          Назад
        </Button>
        
        <Box>
          {currentQuestionIndex < questions.length - 1 ? (
            <Button variant="contained" onClick={handleNext}>
              Далее
            </Button>
          ) : (
            <Button 
              variant="contained" 
              color="success" 
              onClick={handleSubmitTest}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Отправка...' : 'Завершить тест'}
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  )
}
