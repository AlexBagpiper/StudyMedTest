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
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import DeleteIcon from '@mui/icons-material/Delete'
import { useForm, Controller } from 'react-hook-form'
import { useTopics } from '../../lib/api/hooks/useTopics'
import { useLocale } from '../../contexts/LocaleContext'
import { questionsApi } from '../../lib/api'
import type { Question, QuestionCreate, ImageAsset } from '../../types'

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
  
  const {
    control,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
    setValue,
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
      }
    }
  }, [open, question, reset])

  const handleImageAndAnnotationsUpload = async (imageFile: File, annotationFile?: File) => {
    try {
      setIsUploading(true)
      setUploadError(null)
      
      // 1. Сначала загружаем изображение
      const asset = await questionsApi.uploadImage(imageFile)
      setImageAsset(asset)
      setValue('image_id', asset.id, { shouldValidate: true })
      
      // 2. Если есть файл аннотаций, загружаем его отдельно
      if (annotationFile) {
        try {
          const updatedAsset = await questionsApi.uploadAnnotations(asset.id, annotationFile)
          setImageAsset(updatedAsset)
          // Повторно валидируем после загрузки аннотаций
          setValue('image_id', updatedAsset.id, { shouldValidate: true })
        } catch (annoError: any) {
          // Если ошибка в аннотациях, изображение всё равно остается
          const errorMsg = translateError(annoError.response?.data?.detail || 'Error uploading annotations')
          setUploadError(t('questions.imageUploadedAnnotationsRejected').replace('{error}', errorMsg))
        }
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
  }

  const handleFormSubmit = (data: QuestionCreate) => {
    onSubmit(data)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {readOnly ? t('questions.view') : question ? t('questions.edit') : t('questions.create')}
      </DialogTitle>
      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
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
              <>
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
              </>
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
                    <Box sx={{ position: 'relative', display: 'inline-block' }}>
                      <img
                        src={imageAsset.presigned_url || ''}
                        alt={imageAsset.filename}
                        style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '4px' }}
                      />
                      <Typography variant="caption" display="block">
                        {imageAsset.filename} ({imageAsset.width}x{imageAsset.height})
                      </Typography>
                      {imageAsset.coco_annotations ? (
                        <Typography variant="caption" color="success.main" display="block">
                          ✓ {t('questions.annotationsLoaded')}
                        </Typography>
                      ) : (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="caption" color="error" display="block" sx={{ mb: 1 }}>
                            ⚠ {t('questions.annotationsRequired')}
                          </Typography>
                          {!readOnly && (
                            <Button
                              size="small"
                              component="label"
                              variant="contained"
                              color="warning"
                              startIcon={<CloudUploadIcon />}
                              disabled={isUploading}
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
                                      setValue('image_id', updated.id, { shouldValidate: true })
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
                      )}
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
                                await handleImageAndAnnotationsUpload(file)
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
                        if (!imageAsset?.coco_annotations) return t('questions.annotationsRequired')
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
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={isLoading}>
            {readOnly ? t('common.cancel') : t('common.cancel')}
          </Button>
          {!readOnly && (
            <Button type="submit" variant="contained" disabled={isLoading}>
              {isLoading ? t('topics.saving') : question ? t('topics.update') : t('admin.create')}
            </Button>
          )}
        </DialogActions>
      </form>
    </Dialog>
  )
}
