import { useEffect, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Slider,
  Box,
  Alert,
  IconButton,
  Tabs,
  Tab,
  Paper,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import { useForm, Controller } from 'react-hook-form'
import { useTopics } from '../../lib/api/hooks/useTopics'
import { useLocale } from '../../contexts/LocaleContext'
import { questionsApi } from '../../lib/api'
import type { Question, QuestionCreate, ImageAsset } from '../../types'
import { AnnotationEditor } from '../annotation/AnnotationEditor'
import { AnnotationData } from '../../types/annotation'

interface QuestionFormDialogProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: QuestionCreate) => void
  question?: Question
  isLoading?: boolean
  readOnly?: boolean
}

export default function QuestionFormDialog({
  open,
  onClose,
  onSubmit,
  question,
  isLoading,
  readOnly = false,
}: QuestionFormDialogProps) {
  const { data: topics = [] } = useTopics()
  const { t, translateError } = useLocale()
  const [isUploading, setIsUploading] = useState(false)
  const [imageAsset, setImageAsset] = useState<ImageAsset | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [annotationMethod, setAnnotationMethod] = useState<'upload' | 'manual'>('manual')
  const [manualAnnotations, setManualAnnotations] = useState<AnnotationData | null>(null)
  const [showEditor, setShowEditor] = useState(false)
  
  const {
    control,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
    setValue,
    getValues,
  } = useForm<QuestionCreate>({
    defaultValues: {
      type: 'text',
      content: '',
      topic_id: undefined,
      difficulty: 1,
      reference_data: {
        reference_answer: '',
      },
      scoring_criteria: {},
    },
  })

  const questionType = watch('type')

  // Сбрасываем форму при открытии диалога
  useEffect(() => {
    if (open) {
      setUploadError(null)
      setShowEditor(false)
      if (question) {
        // Редактирование - загружаем данные вопроса
        reset({
          type: question.type,
          content: question.content,
          topic_id: question.topic_id || undefined,
          difficulty: question.difficulty || 1,
          reference_data: {
            reference_answer: question.reference_data?.reference_answer || '',
            ...question.reference_data,
          },
          scoring_criteria: question.scoring_criteria || {},
          image_id: question.image_id,
        })
        setImageAsset(question.image || null)
        
        // Если есть reference_data с аннотациями, считаем это "ручным" методом или отредактированным
        if (question.reference_data && (question.reference_data.annotations || question.reference_data.labels)) {
          setManualAnnotations({
            labels: question.reference_data.labels || [],
            annotations: question.reference_data.annotations || []
          })
          setAnnotationMethod('manual')
        } else if (question.image?.coco_annotations) {
          setAnnotationMethod('upload')
        }
      } else {
        // Создание - очищаем форму
        reset({
          type: 'text',
          content: '',
          topic_id: undefined,
          difficulty: 1,
          reference_data: {
            reference_answer: '',
          },
          scoring_criteria: {},
          image_id: undefined,
        })
        setImageAsset(null)
        setManualAnnotations(null)
        setAnnotationMethod('manual')
      }
    }
  }, [open, question, reset])

  const handleImageUpload = async (file: File) => {
    try {
      setIsUploading(true)
      setUploadError(null)
      const asset = await questionsApi.uploadImage(file)
      setImageAsset(asset)
      setValue('image_id', asset.id, { shouldValidate: true })
      
      // Если у изображения есть встроенные аннотации, переключаем на upload
      if (asset.coco_annotations) {
        setAnnotationMethod('upload')
      } else {
        setAnnotationMethod('manual')
      }
    } catch (error: any) {
      setUploadError(translateError(error.response?.data?.detail || 'Error uploading image'))
    } finally {
      setIsUploading(false)
    }
  }

  const handleRemoveImage = () => {
    setImageAsset(null)
    setValue('image_id', undefined)
    setManualAnnotations(null)
  }

  const handleAnnotationsChange = (data: AnnotationData) => {
    setManualAnnotations(data)
  }

  const handleFormSubmit = (data: QuestionCreate) => {
    if (questionType === 'image_annotation' && annotationMethod === 'manual' && manualAnnotations) {
      data.reference_data = {
        ...data.reference_data,
        ...manualAnnotations
      }
    }
    onSubmit(data)
  }

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth={showEditor ? "lg" : "md"} 
      fullWidth
      fullScreen={showEditor}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{readOnly ? t('questions.view') : question ? t('questions.edit') : t('questions.create')}</span>
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)} style={{ height: showEditor ? '100%' : 'auto', display: 'flex', flexDirection: 'column' }}>
        <DialogContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', p: showEditor ? 0 : 3 }}>
          {showEditor && imageAsset ? (
            <Box sx={{ flex: 1, minHeight: 0 }}>
              <AnnotationEditor 
                imageUrl={imageAsset.presigned_url || ''}
                initialData={manualAnnotations || undefined}
                onChange={handleAnnotationsChange}
                onFinish={() => setShowEditor(false)}
                onCancel={() => {
                  // При отмене возвращаем предыдущее состояние
                  if (question) {
                    setManualAnnotations(question.reference_data ? {
                      labels: question.reference_data.labels || [],
                      annotations: question.reference_data.annotations || []
                    } : null)
                  } else {
                    setManualAnnotations(null)
                  }
                  setShowEditor(false)
                }}
                readOnly={readOnly}
              />
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Controller
                name="type"
                control={control}
                rules={{ required: t('questions.selectType') }}
                render={({ field }) => (
                  <FormControl fullWidth error={!!errors.type} disabled={readOnly}>
                    <InputLabel>{t('questions.type')}</InputLabel>
                    <Select {...field} label={t('questions.type')}>
                      <MenuItem value="text">{t('questions.type.text')}</MenuItem>
                      <MenuItem value="image_annotation">{t('questions.type.imageAnnotation')}</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />

              <Controller
                name="topic_id"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth disabled={readOnly}>
                    <InputLabel>{t('questions.topic')}</InputLabel>
                    <Select
                      {...field}
                      label={t('questions.topic')}
                      value={field.value || ''}
                      onChange={(e) => field.onChange(e.target.value || undefined)}
                    >
                      <MenuItem value="">
                        <em>{t('questions.noTopic')}</em>
                      </MenuItem>
                      {topics.map((topic: any) => (
                        <MenuItem key={topic.id} value={topic.id}>
                          {topic.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />

              <Box>
                <Typography gutterBottom>{t('questions.difficulty')}</Typography>
                <Controller
                  name="difficulty"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Slider
                      {...field}
                      value={field.value}
                      onChange={(_, value) => field.onChange(value)}
                      step={1}
                      marks
                      min={1}
                      max={5}
                      valueLabelDisplay="auto"
                      disabled={readOnly}
                    />
                  )}
                />
              </Box>

              <Controller
                name="content"
                control={control}
                rules={{ required: t('questions.enterContent') }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label={t('questions.content')}
                    fullWidth
                    multiline
                    rows={4}
                    error={!!errors.content}
                    helperText={errors.content?.message}
                    disabled={readOnly}
                  />
                )}
              />

              {questionType === 'text' && (
                <Controller
                  name="reference_data.reference_answer"
                  control={control}
                  rules={{ required: t('questions.enterReferenceAnswer') }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label={t('questions.referenceAnswer')}
                      fullWidth
                      multiline
                      rows={4}
                      error={!!(errors.reference_data as any)?.reference_answer}
                      helperText={
                        (errors.reference_data as any)?.reference_answer?.message ||
                        t('questions.referenceAnswerDesc')
                      }
                      disabled={readOnly}
                    />
                  )}
                />
              )}

              {questionType === 'image_annotation' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {uploadError && (
                    <Alert severity="error" onClose={() => setUploadError(null)}>
                      {uploadError}
                    </Alert>
                  )}

                  <Box sx={{ border: '1px dashed #ccc', p: 2, borderRadius: 1, textAlign: 'center' }}>
                    {imageAsset ? (
                      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                        <Box sx={{ position: 'relative', display: 'inline-block' }}>
                          <img
                            src={imageAsset.presigned_url || ''}
                            alt={imageAsset.filename}
                            style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '4px' }}
                          />
                          {!readOnly && (
                            <IconButton
                              size="small"
                              color="error"
                              onClick={handleRemoveImage}
                              sx={{ position: 'absolute', top: -10, right: -10, bgcolor: 'background.paper' }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          )}
                        </Box>

                        <Paper sx={{ width: '100%', p: 1 }}>
                          <Tabs 
                            value={annotationMethod} 
                            onChange={(_, v) => setAnnotationMethod(v)}
                            variant="fullWidth"
                            disabled={readOnly}
                          >
                            <Tab label={t('questions.uploadJson')} value="upload" />
                            <Tab label={t('questions.manualAnnotation')} value="manual" />
                          </Tabs>

                          <Box sx={{ p: 2 }}>
                            {annotationMethod === 'upload' ? (
                              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                                {imageAsset.coco_annotations ? (
                                  <Typography variant="body2" color="success.main" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    ✓ {t('questions.annotationsLoaded')}
                                  </Typography>
                                ) : (
                                  <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                                    ⚠ {t('questions.annotationsRequired')}
                                  </Typography>
                                )}
                                {!readOnly && (
                                  <Button
                                    size="medium"
                                    component="label"
                                    variant="contained"
                                    startIcon={<CloudUploadIcon />}
                                    disabled={isUploading}
                                    color="primary"
                                    sx={{ 
                                      minWidth: 200
                                    }}
                                  >
                                    {t('questions.uploadAnnotations')}
                                    <input
                                      type="file"
                                      hidden
                                      accept=".json"
                                      onChange={async (e) => {
                                        const file = e.target.files?.[0]
                                        if (file && imageAsset) {
                                          try {
                                            setIsUploading(true)
                                            setUploadError(null)
                                            const updated = await questionsApi.uploadAnnotations(imageAsset.id, file)
                                            setImageAsset(updated)
                                          } catch (err: any) {
                                            setUploadError(translateError(err.response?.data?.detail || 'Error uploading annotations'))
                                          } finally {
                                            setIsUploading(false)
                                          }
                                        }
                                      }}
                                    />
                                  </Button>
                                )}
                              </Box>
                            ) : (
                              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                                {manualAnnotations ? (
                                  <Typography variant="body2" color="success.main" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    ✓ {t('questions.annotationsSummary')
                                        .replace('{labels}', manualAnnotations.labels.length.toString())
                                        .replace('{annotations}', manualAnnotations.annotations.length.toString())}
                                  </Typography>
                                ) : (
                                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                    {t('questions.noAnnotations')}
                                  </Typography>
                                )}
                                <Button
                                  size="medium"
                                  variant="contained"
                                  startIcon={<EditIcon />}
                                  onClick={() => setShowEditor(true)}
                                  color="primary"
                                  sx={{ 
                                    minWidth: 200
                                  }}
                                >
                                  {readOnly ? t('questions.viewAnnotation') : t('questions.openEditor')}
                                </Button>
                              </Box>
                            )}
                          </Box>
                        </Paper>
                      </Box>
                    ) : (
                      <Box>
                        <Typography gutterBottom>
                          {t('questions.uploadImageAndAnnotations')}
                        </Typography>
                        {errors.image_id?.type === 'validate' && !imageAsset && (
                          <Typography color="error" variant="caption" display="block" sx={{ mb: 1 }}>
                            ⚠ {errors.image_id.message}
                          </Typography>
                        )}
                        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 1 }}>
                          <Button
                            component="label"
                            variant="outlined"
                            startIcon={<CloudUploadIcon />}
                            disabled={isUploading || readOnly}
                          >
                            {isUploading ? t('questions.uploading') : t('questions.chooseFiles')}
                            <input
                              type="file"
                              hidden
                              accept="image/*"
                              onChange={async (e) => {
                                const file = e.target.files?.[0]
                                if (file) {
                                  await handleImageUpload(file)
                                }
                              }}
                            />
                          </Button>
                        </Box>
                      </Box>
                    )}
                  </Box>
                  
                  <Controller
                    name="image_id"
                    control={control}
                    rules={{ 
                      validate: (value) => {
                        if (questionType === 'image_annotation') {
                          if (!value) return t('questions.imageRequired')
                          if (annotationMethod === 'upload' && !imageAsset?.coco_annotations) return t('questions.annotationsRequired')
                        if (annotationMethod === 'manual' && (!manualAnnotations || manualAnnotations.annotations.length === 0)) {
                          return t('questions.atLeastOneAnnotation')
                        }
                        }
                        return true
                      }
                    }}
                    render={({ field }) => (
                      <input type="hidden" {...field} value={field.value || ''} />
                    )}
                  />
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        {!showEditor && (
          <DialogActions>
            <Button onClick={onClose} disabled={isLoading}>
              {t('common.cancel')}
            </Button>
            {!readOnly && (
              <Button type="submit" variant="contained" disabled={isLoading}>
                {isLoading ? t('topics.saving') : question ? t('topics.update') : t('admin.create')}
              </Button>
            )}
          </DialogActions>
        )}
      </form>
    </Dialog>
  )
}
