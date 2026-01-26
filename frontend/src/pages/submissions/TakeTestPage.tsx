import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  Divider,
  CircularProgress,
  TextField,
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import { useLocale } from '../../contexts/LocaleContext'
import { useSubmitTest } from '../../lib/api/hooks/useSubmissions'
import { AnnotationEditor } from '../../components/annotation/AnnotationEditor'
import { AnnotationData } from '../../types/annotation'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { MessageDialog } from '../../components/common/MessageDialog'
import { useAnnotationStore } from '../../components/annotation/hooks/useAnnotationStore'

export default function TakeTestPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { t } = useLocale()
  const submitTest = useSubmitTest()
  const { reset: resetAnnotationStore } = useAnnotationStore()
  
  const [submission, setSubmission] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const currentQuestionIndexRef = useRef(currentQuestionIndex)

  const [answers, setAnswers] = useState<Record<string, any>>({})
  const answersRef = useRef(answers)
  
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const isSubmittingRef = useRef(false)
  const [currentLabels, setCurrentLabels] = useState<any[]>([])
  const [timeLeft, setTimeLeft] = useState<number | null>(null)
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false)
  const [isTimeExpiredDialogOpen, setIsTimeExpiredDialogOpen] = useState(false)
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })

  const currentQuestion = questions[currentQuestionIndex]

  useEffect(() => {
    loadSubmission()
  }, [id])

  // Сброс глобального annotation store при загрузке нового теста (submission)
  // Это предотвращает "протекание" аннотаций между разными тестами
  useEffect(() => {
    if (submission?.id) {
      resetAnnotationStore()
    }
  }, [submission?.id, resetAnnotationStore])

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
      const subRes = await api.get(`/submissions/${id}`)
      const subData = subRes.data
      
      // Если тест уже не в процессе, перенаправляем на результаты
      if (subData.status !== 'in_progress') {
        navigate('/submissions', { replace: true })
        return
      }
      
      setSubmission(subData)

      const variantRes = await api.get(`/tests/variants/${subData.variant_id}`)
      const variantData = variantRes.data
      
      const questionPromises = variantData.question_order.map((qId: string) => 
        api.get(`/questions/${qId}`)
      )
      const questionResponses = await Promise.all(questionPromises)
      setQuestions(questionResponses.map(r => r.data))
      
      const initialAnswers: Record<string, any> = {}
      if (subData.answers) {
        subData.answers.forEach((a: any) => {
          initialAnswers[a.question_id] = a.student_answer || a.annotation_data
        })
      }
      // #region agent log
      console.log('[DEBUG H1,H3] loadSubmission: initialAnswers built', {
        answers_keys: Object.keys(initialAnswers),
        first_answer_sample: Object.values(initialAnswers)[0]
      })
      // #endregion
      setAnswers(initialAnswers)
      
    } catch (err: any) {
      console.error('Failed to load test:', err)
      setError(err.response?.data?.detail || t('tests.error.load'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleAnswerChange = (questionId: string, value: any) => {
    setAnswers(prev => {
      const next = { ...prev, [questionId]: value }
      answersRef.current = next
      return next
    })
  }

  const saveAnswer = async (questionId: string) => {
    if (submission?.status !== 'in_progress' && !isSubmittingRef.current) return;
    
    try {
      const answer = answersRef.current[questionId]
      await api.post(`/submissions/${id}/answers`, {
        question_id: questionId,
        student_answer: typeof answer === 'string' ? answer : null,
        annotation_data: typeof answer === 'object' ? answer : null,
      })
    } catch (err: any) {
      if (err.response?.status === 400 && 
          (err.response?.data?.detail === "Submission is not in progress" || 
           err.response?.data?.detail?.includes("Time limit exceeded"))) {
        return;
      }
      console.error('Failed to save answer:', err)
    }
  }

  const handleNext = async () => {
    if (isSubmittingRef.current) return
    try {
      isSubmittingRef.current = true
      setIsSubmitting(true)
      if (currentQuestion) {
        await saveAnswer(currentQuestion.id)
      }
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(prev => {
          const next = prev + 1
          currentQuestionIndexRef.current = next
          return next
        })
      }
    } finally {
      isSubmittingRef.current = false
      setIsSubmitting(false)
    }
  }

  const handlePrev = async () => {
    if (isSubmittingRef.current) return
    try {
      isSubmittingRef.current = true
      setIsSubmitting(true)
      if (currentQuestion) {
        await saveAnswer(currentQuestion.id)
      }
      if (currentQuestionIndex > 0) {
        setCurrentQuestionIndex(prev => {
          const next = prev - 1
          currentQuestionIndexRef.current = next
          return next
        })
      }
    } finally {
      isSubmittingRef.current = false
      setIsSubmitting(false)
    }
  }

  const handleSubmitTest = async (isAuto = false) => {
    if (isSubmittingRef.current) return
    
    try {
      isSubmittingRef.current = true
      setIsSubmitting(true)
      setIsConfirmDialogOpen(false)
      
      const qIndex = currentQuestionIndexRef.current
      const q = questions[qIndex]
      
      if (q) {
        await saveAnswer(q.id)
      }
      
      if (id) {
        await submitTest.mutateAsync(id)
      }
      
      if (isAuto) {
        setIsTimeExpiredDialogOpen(true)
      } else {
        navigate('/submissions', { replace: true })
      }
    } catch (err: any) {
      // Инвалидируем кэш в любом случае, так как статус мог измениться на бэкенде даже при ошибке (например, 500 после коммита)
      await queryClient.invalidateQueries({ queryKey: ['submissions'] })

      // Даже если произошла ошибка, связанная с временем или уже отправленным тестом,
      // мы считаем, что тест завершен.
      const isAlreadySubmitted = err.response?.status === 400 && 
          (err.response?.data?.detail === "Submission already submitted" || 
           err.response?.data?.detail === "Submission is not in progress" ||
           err.response?.data?.detail?.includes("Time limit exceeded"))

      if (isAlreadySubmitted) {
        if (isAuto) {
          setIsTimeExpiredDialogOpen(true)
        } else {
          navigate('/submissions', { replace: true })
        }
        return
      }
      
      console.error('Failed to submit test:', err)
      if (isAuto) {
        setIsTimeExpiredDialogOpen(true)
      } else {
        setErrorDialog({
          open: true,
          message: err.response?.data?.detail || t('tests.error.unknown')
        })
      }
    } finally {
      isSubmittingRef.current = false
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!submission || !submission.time_limit || submission.status !== 'in_progress') {
      setTimeLeft(null)
      return
    }

    const calculateTimeLeft = () => {
      const dateStr = submission.started_at;
      const normalizedDateStr = (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) 
        ? `${dateStr}Z` 
        : dateStr;
        
      const startedAt = new Date(normalizedDateStr).getTime()
      const limitMs = (submission.time_limit || 0) * 60 * 1000
      const now = new Date().getTime()
      const remaining = Math.max(0, Math.floor((startedAt + limitMs - now) / 1000))
      
      if (remaining <= 0) {
        return 0
      }
      return remaining
    }

    const initial = calculateTimeLeft()
    setTimeLeft(initial)
    
    if (initial === 0 && submission && submission.status === 'in_progress') {
      setTimeout(() => handleSubmitTest(true), 0)
    }

    const timer = setInterval(() => {
      if (isSubmittingRef.current) return; // Don't tick if we are already submitting

      setTimeLeft((prev) => {
        if (prev === null || prev <= 0) {
          clearInterval(timer)
          return 0
        }
        const next = prev - 1
        if (next <= 0) {
          clearInterval(timer)
          // Defer call to avoid state updates during render if this was called from a render-related logic
          setTimeout(() => handleSubmitTest(true), 0)
          return 0
        }
        return next
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [submission])

  useEffect(() => {
    if (error) {
      setErrorDialog({
        open: true,
        message: error
      })
    }
  }, [error])

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
        <Button onClick={() => navigate('/tests')}>{t('tests.backToTests')}</Button>
      </Box>
    )
  }

  if (questions.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>{t('questions.noResults')}</Typography>
        <Button onClick={() => navigate('/tests')}>{t('tests.backToTests')}</Button>
      </Box>
    )
  }

  return (
    <Box sx={{ width: '100%', px: { xs: 2, md: 4 }, py: 4 }}>
      <Paper sx={{ p: 3, mb: 3, borderRadius: 1, boxShadow: 3, width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2, alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold">
            {t('tests.questionIndex').replace('{current}', (currentQuestionIndex + 1).toString()).replace('{total}', questions.length.toString())}
          </Typography>
          {timeLeft !== null && (
            <Typography 
              color={timeLeft < 60 ? "error" : "primary"} 
              fontWeight="bold"
              sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
            >
              {t('tests.timeLeft')}: {formatTime(timeLeft)}
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
            placeholder={t('questions.enterAnswer')}
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
              key={`${submission?.id}-${currentQuestion?.id}`}
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
          {t('common.back')}
        </Button>
        
        <Box>
          {currentQuestionIndex < questions.length - 1 ? (
            <Button 
              variant="contained" 
              onClick={handleNext}
              sx={{ borderRadius: 2, px: 4 }}
            >
              {t('common.next')}
            </Button>
          ) : (
            <Button 
              variant="contained" 
              color="success" 
              onClick={() => setIsConfirmDialogOpen(true)}
              disabled={isSubmitting}
              sx={{ borderRadius: 2, px: 4 }}
            >
              {isSubmitting ? t('questions.uploading') : t('tests.confirm.finish.confirmText')}
            </Button>
          )}
        </Box>
      </Box>

      <ConfirmDialog
        open={isConfirmDialogOpen}
        title={t('tests.confirm.finish.title')}
        content={t('tests.confirm.finish.content')}
        confirmText={t('tests.confirm.finish.confirmText')}
        cancelText={t('common.cancel')}
        color="success"
        onConfirm={() => handleSubmitTest(false)}
        onCancel={() => setIsConfirmDialogOpen(false)}
        isLoading={isSubmitting}
      />

      <MessageDialog
        open={errorDialog.open}
        title={t('common.error')}
        content={errorDialog.message}
        onClose={() => setErrorDialog({ ...errorDialog, open: false })}
        severity="error"
      />

      <MessageDialog
        open={isTimeExpiredDialogOpen}
        title={t('tests.confirm.timeExpired.title')}
        content={t('tests.confirm.timeExpired.content')}
        buttonText={t('common.ok')}
        onClose={() => navigate('/submissions', { replace: true })}
        severity="warning"
      />
    </Box>
  )
}
