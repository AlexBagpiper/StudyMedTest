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
import { useAuth } from '../../contexts/AuthContext'
import { AnnotationEditor } from '../../components/annotation/AnnotationEditor'
import { AnnotationData } from '../../types/annotation'
import { MessageDialog } from '../../components/common/MessageDialog'
import { adminApi } from '../../lib/api'
import RefreshIcon from '@mui/icons-material/Refresh'

export default function SubmissionReviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, formatName } = useLocale()
  const { user } = useAuth()
  
  const [submission, setSubmission] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isRevaluating, setIsRevaluating] = useState(false)
  const [cvConfig, setCvConfig] = useState<any>(null)
  const [errorDialog, setErrorDialog] = useState<{ open: boolean; message: string }>({
    open: false,
    message: ''
  })
  const [currentLabels, setCurrentLabels] = useState<any[]>([])

  const currentQuestion = questions[currentQuestionIndex]

  useEffect(() => {
    loadSubmission()
    loadCVConfig()
  }, [id])

  useEffect(() => {
    if (currentQuestion?.type === 'image_annotation') {
      loadLabels(currentQuestion.id)
    }
  }, [currentQuestion])

  const loadCVConfig = async () => {
    try {
      const config = await adminApi.getCVConfig()
      setCvConfig(config)
    } catch (err) {
      console.error('Failed to load CV config:', err)
    }
  }

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

      // Проверка прав доступа: студент может видеть только свои результаты
      if (user?.role === 'student' && subData.student_id !== user.id) {
        setErrorDialog({
          open: true,
          message: t('error.notEnoughPermissions')
        })
        setIsLoading(false)
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

  const handleRevaluate = async () => {
    if (!id) return
    try {
      setIsRevaluating(true)
      await adminApi.revaluateSubmission(id)
      await loadSubmission() // Перезагружаем данные для отображения новых баллов
    } catch (err: any) {
      setErrorDialog({
        open: true,
        message: err.response?.data?.detail || 'Ошибка при пересчете оценки'
      })
    } finally {
      setIsRevaluating(false)
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
        <Box sx={{ display: 'flex', gap: 2 }}>
          {user?.role === 'admin' && (
            <Button 
              variant="outlined" 
              startIcon={isRevaluating ? <CircularProgress size={20} /> : <RefreshIcon />}
              onClick={handleRevaluate}
              disabled={isRevaluating}
            >
              {isRevaluating ? 'Пересчет...' : 'Пересчитать оценку'}
            </Button>
          )}
          <Button variant="outlined" onClick={() => navigate(user?.role === 'student' ? '/submissions' : `/admin/submissions/${id}`)}>
            {t('common.back')}
          </Button>
        </Box>
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
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Ответ студента
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={6}
                variant="outlined"
                value={answers[currentQuestion.id] || ''}
                InputProps={{ readOnly: true }}
                sx={{ bgcolor: 'action.hover' }}
              />
            </Box>
            
            {currentQuestion.reference_data?.reference_answer && (
              <Box>
                <Typography variant="subtitle2" color="primary" fontWeight="bold" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {t('questions.referenceAnswer')}
                </Typography>
                <Paper 
                  variant="outlined" 
                  sx={{ 
                    p: 2, 
                    bgcolor: 'success.light', 
                    color: 'success.contrastText', 
                    whiteSpace: 'pre-wrap', 
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'success.main'
                  }}
                >
                  {currentQuestion.reference_data.reference_answer}
                </Paper>
              </Box>
            )}
          </Box>
        ) : currentQuestion?.type === 'choice' ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Ответ студента
              </Typography>
              <TextField
                fullWidth
                variant="outlined"
                value={answers[currentQuestion.id] || ''}
                InputProps={{ readOnly: true }}
                sx={{ bgcolor: 'action.hover' }}
              />
            </Box>
            
            {currentQuestion.reference_data?.correct_answer && (
              <Box>
                <Typography variant="subtitle2" color="primary" fontWeight="bold" gutterBottom>
                  {t('questions.referenceAnswer')}
                </Typography>
                <Paper 
                  variant="outlined" 
                  sx={{ 
                    p: 2, 
                    bgcolor: 'success.light', 
                    color: 'success.contrastText', 
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'success.main'
                  }}
                >
                  {currentQuestion.reference_data.correct_answer}
                </Paper>
              </Box>
            )}
          </Box>
        ) : (
          <Grid container spacing={3}>
            <Grid item xs={12} md={(currentQuestion.reference_data?.annotations || currentQuestion.image?.coco_annotations) ? 6 : 12}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Ответ студента
              </Typography>
              <Box sx={{ 
                height: 'calc(100vh - 500px)', 
                minHeight: '500px', 
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
            </Grid>
            
            {(currentQuestion.reference_data?.annotations || currentQuestion.image?.coco_annotations) && (
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="primary" fontWeight="bold" gutterBottom>
                  {t('questions.referenceAnswer')}
                </Typography>
                <Box sx={{ 
                  height: 'calc(100vh - 500px)', 
                  minHeight: '500px', 
                  border: '1px solid', 
                  borderColor: 'primary.main', 
                  borderRadius: 1, 
                  overflow: 'hidden',
                  bgcolor: '#1e2125'
                }}>
                  <AnnotationEditor
                    imageUrl={currentQuestion?.image?.presigned_url || ''}
                    initialData={{
                      labels: currentLabels,
                      annotations: currentQuestion.reference_data?.annotations || currentQuestion.image?.coco_annotations?.annotations || []
                    }}
                    readOnly={true}
                    hideLabels={true}
                  />
                </Box>
              </Grid>
            )}
          </Grid>
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
                    <Typography variant="caption" color="text.secondary">
                      Вес: {cvConfig ? `${(cvConfig.iou_weight * 100).toFixed(0)}%` : '50%'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Полнота
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {evaluation.recall !== undefined ? `${(evaluation.recall * 100).toFixed(0)}%` : '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Вес: {cvConfig ? `${(cvConfig.recall_weight * 100).toFixed(0)}%` : '30%'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Достоверность
                    </Typography>
                    <Typography variant="h5" fontWeight="bold">
                      {evaluation.precision !== undefined ? `${(evaluation.precision * 100).toFixed(0)}%` : '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Вес: {cvConfig ? `${(cvConfig.precision_weight * 100).toFixed(0)}%` : '20%'}
                    </Typography>
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
            const criteriaLabels: Record<string, string> = {
              factual_correctness: 'Фактическая правильность',
              completeness: 'Полнота ответа',
              terminology: 'Терминология',
              structure: 'Структура и логика'
            };

            return (
              <Box sx={{ mt: 4, p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2, bgcolor: 'action.hover' }}>
                <Typography variant="h6" fontWeight="bold" gutterBottom color="primary">
                  Результаты LLM-оценки
                </Typography>
                
                <Typography variant="body2" sx={{ mb: 3, fontStyle: 'italic', color: 'text.primary', borderLeft: '4px solid', borderColor: 'primary.main', pl: 2, py: 1, bgcolor: 'background.paper' }}>
                  {evaluation.feedback}
                </Typography>

                {evaluation.criteria_scores && (
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    {Object.entries(evaluation.criteria_scores).map(([key, score]: [string, any]) => (
                      <Grid item xs={12} sm={6} md={3} key={key}>
                        <Paper sx={{ p: 1.5, textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', mb: 0.5, display: 'block', lineHeight: 1.2 }}>
                            {criteriaLabels[key] || key}
                          </Typography>
                          <Typography variant="h6" fontWeight="bold">
                            {score}
                            <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                              / {currentQuestion.scoring_criteria?.[key] || ''}
                            </Typography>
                          </Typography>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                )}

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="body2" color="text.secondary">
                    Модель: {evaluation.llm_provider || 'YandexGPT'}
                  </Typography>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Итоговый балл
                    </Typography>
                    <Typography variant="h4" fontWeight="bold" color="primary">
                      {currentAnswer.score !== undefined ? currentAnswer.score.toFixed(0) : '—'}
                    </Typography>
                  </Box>
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
