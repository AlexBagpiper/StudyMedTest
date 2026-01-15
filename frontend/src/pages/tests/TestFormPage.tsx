import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Divider,
  Grid,
  Card,
  CardContent,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
  Slider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Rating,
} from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { useTest, useCreateTest, useUpdateTest, usePublishTest } from '../../lib/api/hooks/useTests'
import { useQuestions } from '../../lib/api/hooks/useQuestions'
import { useTopics } from '../../lib/api/hooks/useTopics'
import { useLocale } from '../../contexts/LocaleContext'
import type { TestSettings, Question, TestStructureItem } from '../../types'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import PublishIcon from '@mui/icons-material/Publish'
import VisibilityIcon from '@mui/icons-material/Visibility'
import TextFieldsIcon from '@mui/icons-material/TextFields'
import ImageIcon from '@mui/icons-material/Image'
import { MenuItem, Select, FormControl, InputLabel } from '@mui/material'
import QuestionFormDialog from '../../components/questions/QuestionFormDialog'

interface TestFormData {
  title: string
  description: string
  settings: TestSettings
  structure: TestStructureItem[]
}

interface SelectedQuestion {
  question_id: string
  question: Question
  order: number
}

export default function TestFormPage() {
  const { testId } = useParams()
  const navigate = useNavigate()
  const { t } = useLocale()
  const isEdit = !!testId

  const { data: test, isLoading: testLoading } = useTest(testId)
  const { data: topics = [] } = useTopics()
  const { data: questions = [], isLoading: questionsLoading } = useQuestions()
  const createTest = useCreateTest()
  const updateTest = useUpdateTest()
  const publishTest = usePublishTest()

  const [selectedQuestions, setSelectedQuestions] = useState<SelectedQuestion[]>([])
  const [structure, setStructure] = useState<TestStructureItem[]>([])
  const [showQuestionPicker, setShowQuestionPicker] = useState(false)
  const [viewingQuestion, setViewingQuestion] = useState<Question | undefined>()
  const [viewDialogOpen, setViewDialogOpen] = useState(false)

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TestFormData>({
    defaultValues: {
      title: '',
      description: '',
      settings: {
        time_limit: 60,
      },
      structure: [],
    },
  })

  useEffect(() => {
    if (test) {
      reset({
        title: test.title,
        description: test.description || '',
        settings: test.settings || {},
        structure: test.structure || [],
      })
      
      setStructure(test.structure || [])

      if (test.test_questions) {
        setSelectedQuestions(
          test.test_questions.map((tq: any, index: number) => ({
            question_id: tq.question_id,
            question: tq.question,
            order: tq.order || index,
          }))
        )
      }
    }
  }, [test, reset])

  const handleAddStructureRule = () => {
    if (topics.length === 0) {
      alert('Сначала создайте хотя бы одну тему')
      return
    }
    
    setStructure([
      ...structure,
      {
        topic_id: topics[0].id,
        question_type: 'text',
        count: 5,
        difficulty: 1,
      },
    ])
  }

  const handleRemoveStructureRule = (index: number) => {
    setStructure(structure.filter((_, i) => i !== index))
  }

  const handleUpdateStructureRule = (index: number, field: keyof TestStructureItem, value: any) => {
    setStructure(
      structure.map((rule, i) => (i === index ? { ...rule, [field]: value } : rule))
    )
  }

  const handleAddQuestion = (question: Question) => {
    setSelectedQuestions([
      ...selectedQuestions,
      {
        question_id: question.id,
        question: question,
        order: selectedQuestions.length,
      },
    ])
    setShowQuestionPicker(false)
  }

  const handleRemoveQuestion = (questionId: string) => {
    setSelectedQuestions(selectedQuestions.filter((sq) => sq.question_id !== questionId))
  }

  const onSubmit = async (data: TestFormData) => {
    if (structure.length === 0 && selectedQuestions.length === 0) {
      alert('Определите структуру теста или добавьте вопросы')
      return
    }

    try {
      const payload = {
        ...data,
        structure: structure,
        questions: selectedQuestions.map((q, index) => ({
          question_id: q.question_id,
          order: index,
        })),
      }
// ... (rest of onSubmit remains similar)
      if (isEdit && testId) {
        await updateTest.mutateAsync({ testId, data: payload })
      } else {
        await createTest.mutateAsync(payload)
      }

      navigate('/tests')
    } catch (error: any) {
      console.error('Failed to save test:', error)
      let message = 'Не удалось сохранить тест'
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          message = error.response.data.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
        } else {
          message = error.response.data.detail
        }
      }
      alert(message)
    }
  }

  const handlePublish = async () => {
    if (!testId) return

    if (
      window.confirm(
        'Вы уверены, что хотите опубликовать тест? После публикации его нельзя будет редактировать.'
      )
    ) {
      try {
        await publishTest.mutateAsync(testId)
        navigate('/tests')
      } catch (error) {
        console.error('Failed to publish test:', error)
      }
    }
  }

  if (testLoading || questionsLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  const availableQuestions = questions.filter(
    (q: any) => !selectedQuestions.find((sq) => sq.question_id === q.id)
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate('/tests')} sx={{ mr: 2 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4">{isEdit ? 'Редактировать тест' : 'Создать тест'}</Typography>
      </Box>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Основная информация
          </Typography>

          <Controller
            name="title"
            control={control}
            rules={{ required: 'Название обязательно' }}
            render={({ field }) => (
              <TextField
                {...field}
                label="Название теста"
                fullWidth
                margin="normal"
                error={!!errors.title}
                helperText={errors.title?.message}
              />
            )}
          />

          <Controller
            name="description"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label="Описание"
                fullWidth
                multiline
                rows={3}
                margin="normal"
              />
            )}
          />

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Настройки
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Controller
                name="settings.time_limit"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Время на тест (минуты)"
                    type="number"
                    fullWidth
                    margin="normal"
                  />
                )}
              />
            </Grid>
          </Grid>
        </Paper>

        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Структура теста (автогенерация)
            </Typography>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={handleAddStructureRule}
            >
              Добавить правило
            </Button>
          </Box>

          {structure.length === 0 ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              Добавьте правила для автоматической генерации вопросов из базы данных
            </Alert>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
              {structure.map((rule, index) => (
                <Card key={index} variant="outlined">
                  <CardContent>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} md={4}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Тема</InputLabel>
                          <Select
                            value={rule.topic_id}
                            label="Тема"
                            onChange={(e) => handleUpdateStructureRule(index, 'topic_id', e.target.value)}
                          >
                            {topics.map((topic: any) => (
                              <MenuItem key={topic.id} value={topic.id}>
                                {topic.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={3}>
                        <FormControl fullWidth size="small">
                          <InputLabel>Тип вопроса</InputLabel>
                          <Select
                            value={rule.question_type}
                            label="Тип вопроса"
                            onChange={(e) => handleUpdateStructureRule(index, 'question_type', e.target.value)}
                          >
                            <MenuItem value="text">Текстовый</MenuItem>
                            <MenuItem value="image_annotation">Аннотация</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={6} md={2}>
                        <TextField
                          label="Кол-во"
                          type="number"
                          size="small"
                          fullWidth
                          value={rule.count}
                          onChange={(e) => handleUpdateStructureRule(index, 'count', parseInt(e.target.value) || 1)}
                        />
                      </Grid>
                      <Grid item xs={6} md={2}>
                        <Typography variant="caption">Сложность: {rule.difficulty}</Typography>
                        <Slider
                          value={rule.difficulty}
                          step={1}
                          marks
                          min={1}
                          max={5}
                          size="small"
                          onChange={(_: any, value: any) => handleUpdateStructureRule(index, 'difficulty', value)}
                        />
                      </Grid>
                      <Grid item xs={12} md={1}>
                        <IconButton color="error" onClick={() => handleRemoveStructureRule(index)}>
                          <DeleteIcon />
                        </IconButton>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}

          <Divider sx={{ my: 3 }} />

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Фиксированные вопросы ({selectedQuestions.length})
            </Typography>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => setShowQuestionPicker(!showQuestionPicker)}
            >
              Добавить конкретный вопрос
            </Button>
          </Box>

          {selectedQuestions.length === 0 ? (
            <Alert severity="info">Конкретные вопросы не добавлены (будет использована только автогенерация)</Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                    <TableRow>
                      <TableCell width={40}>#</TableCell>
                      <TableCell width={50}>{t('admin.type')}</TableCell>
                      <TableCell>{t('admin.content')}</TableCell>
                      <TableCell width={150}>{t('questions.topic')}</TableCell>
                      <TableCell width={100}>Сложность</TableCell>
                      <TableCell width={100} align="right">{t('admin.actions')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedQuestions.map((sq, index) => (
                      <TableRow key={sq.question_id} hover>
                        <TableCell>{index + 1}</TableCell>
                        <TableCell>
                          <Tooltip title={sq.question?.type === 'text' ? t('questions.type.text') : t('questions.type.imageAnnotation')}>
                            {sq.question?.type === 'text' ? <TextFieldsIcon fontSize="small" color="primary" /> : <ImageIcon fontSize="small" color="primary" />}
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{
                            display: '-webkit-box',
                            WebkitLineClamp: 1,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            fontWeight: 500
                          }}>
                            {sq.question?.content}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {sq.question?.topic ? (
                            <Chip label={sq.question.topic.name} size="small" variant="outlined" />
                          ) : (
                            <Typography variant="caption" color="text.disabled">{t('questions.noTopic')}</Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Rating value={sq.question?.difficulty || 1} readOnly size="small" />
                        </TableCell>
                        <TableCell align="right">
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                          <Tooltip title={t('questions.viewTitle')}>
                            <IconButton 
                              size="small" 
                              onClick={() => {
                                setViewingQuestion(sq.question)
                                setViewDialogOpen(true)
                              }}
                            >
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={t('questions.deleteTitle')}>
                            <IconButton 
                              size="small" 
                              color="error" 
                              onClick={() => handleRemoveQuestion(sq.question_id)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {showQuestionPicker && (
            <Box sx={{ mt: 3 }}>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="subtitle1" gutterBottom>
                Доступные вопросы
              </Typography>

              {availableQuestions.length === 0 ? (
                <Alert severity="warning">Все вопросы уже добавлены или нет доступных вопросов</Alert>
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell width={50}>{t('admin.type')}</TableCell>
                        <TableCell>{t('admin.content')}</TableCell>
                        <TableCell width={150}>{t('questions.topic')}</TableCell>
                        <TableCell width={100}>Сложность</TableCell>
                        <TableCell width={100} align="right">{t('admin.actions')}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {availableQuestions.map((question: Question) => (
                        <TableRow key={question.id} hover>
                          <TableCell>
                            <Tooltip title={question.type === 'text' ? t('questions.type.text') : t('questions.type.imageAnnotation')}>
                              {question.type === 'text' ? <TextFieldsIcon fontSize="small" color="primary" /> : <ImageIcon fontSize="small" color="primary" />}
                            </Tooltip>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 1,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              fontWeight: 500
                            }}>
                              {question.content}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {question.topic ? (
                              <Chip label={question.topic.name} size="small" variant="outlined" />
                            ) : (
                              <Typography variant="caption" color="text.disabled">{t('questions.noTopic')}</Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            <Rating value={question.difficulty} readOnly size="small" />
                          </TableCell>
                          <TableCell align="right">
                            <Button size="small" onClick={() => handleAddQuestion(question)}>
                              Добавить
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </Paper>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button type="submit" variant="contained" disabled={createTest.isPending || updateTest.isPending}>
            {isEdit ? 'Сохранить' : 'Создать'}
          </Button>

          {isEdit && test?.status === 'draft' && (
            <Button
              variant="contained"
              color="success"
              startIcon={<PublishIcon />}
              onClick={handlePublish}
              disabled={publishTest.isPending}
            >
              Опубликовать
            </Button>
          )}

          <Button variant="outlined" onClick={() => navigate('/tests')}>
            Отмена
          </Button>
        </Box>
      </form>

      <QuestionFormDialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        onSubmit={() => {}}
        question={viewingQuestion}
        readOnly
      />
    </Box>
  )
}
