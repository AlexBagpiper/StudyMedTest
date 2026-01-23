import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  Divider,
  CircularProgress,
  TextField,
  Chip,
  Grid,
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import { useLocale } from '../../contexts/LocaleContext'
import { AnnotationEditor } from '../../components/annotation/AnnotationEditor'
import { AnnotationData } from '../../types/annotation'
import { MessageDialog } from '../../components/common/MessageDialog'

export default function SubmissionReviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, formatName } = useLocale()
  
  const [submission, setSubmission] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [currentLabels, setCurrentLabels] = useState<any[]>([])

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

  const loadSubmission = async () => {
    try {
      setIsLoading(true)
      const subRes = await api.get(`/submissions/${id}`)
      const subData = subRes.data
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
      setAnswers(initialAnswers)
      
    } catch (err: any) {
      console.error('Failed to load submission:', err)
      setErrorDialog({
        open: true,
        message: err.response?.data?.detail || t('submissions.error.load')
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box sx={{ width: '100%', px: { xs: 2, md: 4 }, py: 4 }}>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h5" fontWeight="bold">
            {submission?.test_title}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {t('submissions.table.student')}: {submission?.student ? formatName(submission.student.last_name, submission.student.first_name, submission.student.middle_name) : submission?.student_id}
          </Typography>
        </Box>
        <Button variant="outlined" onClick={() => navigate(`/admin/submissions/${id}`)}>
          {t('common.back')}
        </Button>
      </Box>

      <Paper sx={{ p: 3, mb: 3, borderRadius: 1, boxShadow: 3, width: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2, alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold">
            {t('tests.questionIndex').replace('{current}', (currentQuestionIndex + 1).toString()).replace('{total}', questions.length.toString())}
          </Typography>
          <Chip 
            label={t(`submissions.status.${submission?.status}` as any) || submission?.status} 
            color="primary" 
            variant="outlined" 
            size="small" 
          />
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
            value={answers[currentQuestion.id] || ''}
            InputProps={{ readOnly: true }}
            sx={{ bgcolor: 'action.hover' }}
          />
        ) : (
          <Box sx={{ 
            height: 'calc(100vh - 400px)', 
            minHeight: '600px', 
            border: '1px solid', 
            borderColor: 'divider', 
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
              readOnly={true}
              hideLabels={true}
            />
          </Box>
        )}

        {/* Результаты оценки */}
        {(() => {
          const currentAnswer = submission?.answers?.find((a: any) => a.question_id === currentQuestion?.id);
          const evaluation = currentAnswer?.evaluation;
          
          if (!evaluation) return null;

          if (currentQuestion?.type === 'image_annotation') {
            return (
              <Box sx={{ mt: 4, p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2, bgcolor: 'action.hover' }}>
                <Typography variant="h6" fontWeight="bold" gutterBottom color="primary">
                  Детализация оценки
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Точность
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {evaluation.iou !== undefined ? `${(evaluation.iou * 100).toFixed(0)}%` : '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Вес: 50%</Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Полнота
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {evaluation.recall !== undefined ? `${(evaluation.recall * 100).toFixed(0)}%` : '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Вес: 30%</Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Достоверность
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {evaluation.precision !== undefined ? `${(evaluation.precision * 100).toFixed(0)}%` : '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Вес: 20%</Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="primary" fontWeight="bold" display="block">
                      Итоговый балл
                    </Typography>
                    <Typography variant="h4" fontWeight="bold" color="primary">
                      {currentAnswer.score !== undefined ? currentAnswer.score.toFixed(0) : '—'}
                    </Typography>
                  </Grid>
                </Grid>
              </Box>
            );
          }

          if (currentQuestion?.type === 'text') {
            return (
              <Box sx={{ mt: 4, p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2, bgcolor: 'action.hover' }}>
                <Typography variant="h6" fontWeight="bold" gutterBottom color="primary">
                  Результаты LLM-оценки
                </Typography>
                <Typography variant="body2" sx={{ mb: 2, fontStyle: 'italic' }}>
                  {evaluation.feedback}
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    Модель: {evaluation.llm_provider}
                  </Typography>
                  <Typography variant="h5" fontWeight="bold" color="primary">
                    Балл: {currentAnswer.score !== undefined ? currentAnswer.score.toFixed(0) : '—'}
                  </Typography>
                </Box>
              </Box>
            );
          }

          return null;
        })()}
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
        
        <Button 
          variant="contained" 
          disabled={currentQuestionIndex === questions.length - 1}
          onClick={handleNext}
          sx={{ borderRadius: 2, px: 4 }}
        >
          {t('common.next')}
        </Button>
      </Box>

      <MessageDialog
        open={errorDialog.open}
        title={t('common.error')}
        content={errorDialog.message}
        onClose={() => setErrorDialog({ ...errorDialog, open: false })}
        severity="error"
      />
    </Box>
  )
}
