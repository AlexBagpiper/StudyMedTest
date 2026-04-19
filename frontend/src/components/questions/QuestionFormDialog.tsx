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
  FormControlLabel,
  Checkbox,
  Divider,
  Grid,
  Tooltip,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import InfoIcon from '@mui/icons-material/Info'
import { useForm, Controller, useWatch } from 'react-hook-form'
import { useTopics } from '../../lib/api/hooks/useTopics'
import { useLocale } from '../../contexts/LocaleContext'
import { questionsApi, adminApi } from '../../lib/api'
import type { Question, QuestionCreate, ImageAsset } from '../../types'
import { AnnotationEditor } from '../annotation/AnnotationEditor'
import { AnnotationData } from '../../types/annotation'
import { useAnnotationStore } from '../annotation/hooks/useAnnotationStore'

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
  const [isLoadingConfig, setIsLoadingConfig] = useState(false)
  const [imageAsset, setImageAsset] = useState<ImageAsset | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [annotationMethod, setAnnotationMethod] = useState<'upload' | 'manual'>('manual')
  const [manualAnnotations, setManualAnnotations] = useState<AnnotationData | null>(null)
  const [showEditor, setShowEditor] = useState(false)
  const { reset: resetAnnotationStore } = useAnnotationStore()
  const [systemCvConfig, setSystemCvConfig] = useState<any>(null)
  
  const {
    control,
    handleSubmit,
    formState: { errors, submitCount },
    reset,
    setValue,
    getValues,
    trigger,
  } = useForm<QuestionCreate>({
    defaultValues: {
      type: 'text',
      content: '',
      topic_id: undefined,
      difficulty: 1,
      reference_data: {
        reference_answer: '',
      },
      scoring_criteria: {
        allow_partial: false,
        use_custom_cv_config: false,
        iou_weight: 0.5,
        recall_weight: 0.3,
        precision_weight: 0.2,
        iou_threshold: 0.5,
        inclusion_threshold: 0.8,
        min_coverage_threshold: 0.05,
      },
      ai_check_enabled: false,
      plagiarism_check_enabled: false,
      event_log_check_enabled: false,
    },
  })

  // Оптимизация: один watch для всего объекта критериев и типа вопроса
  const watchedValues = useWatch({
    control,
    name: ['type', 'scoring_criteria']
  });

  const questionType = watchedValues[0] || 'text';
  const scoringCriteria = watchedValues[1];

  const iouWeight = scoringCriteria?.iou_weight || 0;
  const recallWeight = scoringCriteria?.recall_weight || 0;
  const precisionWeight = scoringCriteria?.precision_weight || 0;
  const useCustomCvConfig = scoringCriteria?.use_custom_cv_config || false;
  const allowPartial = scoringCriteria?.allow_partial || false;
  const labelConfigs = scoringCriteria?.label_configs || {};
  const anyLabelAllowPartial = Object.values(labelConfigs).some((cfg: any) => cfg.allow_partial);
  const showPartialThresholds = allowPartial || anyLabelAllowPartial;

  const iouThreshold = scoringCriteria?.iou_threshold || 0.5;
  const inclusionThreshold = scoringCriteria?.inclusion_threshold || 0.8;
  const coverageThreshold = scoringCriteria?.min_coverage_threshold || 0.05;

  // Подсчет количества аннотаций для каждой метки для ограничения min_count
  const labelAnnotationCounts = (manualAnnotations?.annotations || []).reduce((acc: Record<string, number>, ann: any) => {
    const lid = ann.label_id.toString();
    acc[lid] = (acc[lid] || 0) + 1;
    return acc;
  }, {});

  const weightsSum = Math.round((iouWeight + recallWeight + precisionWeight) * 100);
  const displayWeightsError = useCustomCvConfig && weightsSum !== 100;

  const handleWeightChange = (key: string, value: number) => {
    const currentConfig = getValues('scoring_criteria') || {};
    const keys = ['iou_weight', 'recall_weight', 'precision_weight'];
    const otherKeys = keys.filter(k => k !== key);
    
    // Работаем в целых процентах для исключения ошибок округления JS
    const newValPercent = Math.round(value * 100);
    const otherSumPercent = otherKeys.reduce((acc, k) => acc + Math.round((currentConfig[k as keyof typeof currentConfig] as number || 0) * 100), 0);
    const newSumPercent = newValPercent + otherSumPercent;

    if (newSumPercent > 100) {
      const excess = newSumPercent - 100;
      if (otherSumPercent > 0) {
        let distributedExcess = 0;
        otherKeys.forEach((k, idx) => {
          const currentKPercent = Math.round((currentConfig[k as keyof typeof currentConfig] as number || 0) * 100);
          if (idx === otherKeys.length - 1) {
            // Последнему отдаем весь оставшийся избыток
            const finalVal = Math.max(0, currentKPercent - (excess - distributedExcess));
            setValue(`scoring_criteria.${k}` as any, finalVal / 100, { shouldValidate: true, shouldDirty: true });
          } else {
            const ratio = currentKPercent / otherSumPercent;
            const reduction = Math.round(excess * ratio);
            const finalVal = Math.max(0, currentKPercent - reduction);
            setValue(`scoring_criteria.${k}` as any, finalVal / 100, { shouldValidate: true, shouldDirty: true });
            distributedExcess += reduction;
          }
        });
      } else {
        otherKeys.forEach(k => setValue(`scoring_criteria.${k}` as any, 0, { shouldValidate: true, shouldDirty: true }));
      }
    }
    setValue(`scoring_criteria.${key}` as any, newValPercent / 100, { shouldValidate: true, shouldDirty: true });
  };

  // Сбрасываем форму при открытии диалога
  useEffect(() => {
    const initForm = async () => {
      if (open) {
        setFormError(null)
        setShowEditor(false)
        
        // Явно сбрасываем хранилище при открытии диалога, чтобы не было наложения
        resetAnnotationStore()

        // Загружаем системные настройки, если они еще не загружены
        let currentSystemConfig = systemCvConfig
        if (!currentSystemConfig) {
          try {
            setIsLoadingConfig(true)
            currentSystemConfig = await adminApi.getCVConfig()
            setSystemCvConfig(currentSystemConfig)
          } catch (error) {
            console.error('Failed to fetch system CV config:', error)
            // Хардкодные значения как запасной вариант
            currentSystemConfig = {
              iou_weight: 0.5,
              recall_weight: 0.3,
              precision_weight: 0.2,
              iou_threshold: 0.5,
              inclusion_threshold: 0.8,
              min_coverage_threshold: 0.05
            }
          } finally {
            setIsLoadingConfig(false)
          }
        }

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
            scoring_criteria: {
              ...question.scoring_criteria,
              allow_partial: question.scoring_criteria?.allow_partial || false,
              use_custom_cv_config: question.scoring_criteria?.use_custom_cv_config || false,
              iou_weight: question.scoring_criteria?.iou_weight ?? currentSystemConfig.iou_weight,
              recall_weight: question.scoring_criteria?.recall_weight ?? currentSystemConfig.recall_weight,
              precision_weight: question.scoring_criteria?.precision_weight ?? currentSystemConfig.precision_weight,
              iou_threshold: question.scoring_criteria?.iou_threshold ?? currentSystemConfig.iou_threshold,
              inclusion_threshold: question.scoring_criteria?.inclusion_threshold ?? currentSystemConfig.inclusion_threshold,
              min_coverage_threshold: question.scoring_criteria?.min_coverage_threshold ?? currentSystemConfig.min_coverage_threshold,
              label_configs: question.scoring_criteria?.label_configs || {},
            },
            ai_check_enabled: question.ai_check_enabled || false,
            plagiarism_check_enabled: question.plagiarism_check_enabled || false,
            event_log_check_enabled: question.event_log_check_enabled || false,
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
            scoring_criteria: {
              allow_partial: false,
              use_custom_cv_config: false,
              iou_weight: currentSystemConfig.iou_weight,
              recall_weight: currentSystemConfig.recall_weight,
              precision_weight: currentSystemConfig.precision_weight,
              iou_threshold: currentSystemConfig.iou_threshold,
              inclusion_threshold: currentSystemConfig.inclusion_threshold,
              min_coverage_threshold: currentSystemConfig.min_coverage_threshold,
              label_configs: {},
            },
            ai_check_enabled: false,
            plagiarism_check_enabled: false,
            event_log_check_enabled: false,
            image_id: undefined,
          })
          setImageAsset(null)
          setManualAnnotations(null)
          setAnnotationMethod('manual')
        }
      }
    }
    initForm()
  }, [open, question, reset, resetAnnotationStore])

  const handleImageUpload = async (file: File) => {
    try {
      setIsUploading(true)
      setFormError(null)
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
      setFormError(translateError(error.response?.data?.detail || 'Error uploading image'))
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
    if (questionType === 'image_annotation') {
      trigger('image_id')
    }
  }

  const handleFormSubmit = (data: QuestionCreate) => {
    // Глубокая очистка данных перед отправкой в зависимости от типа вопроса
    const cleanData = { ...data };

    if (questionType === 'text') {
      // Для текстовых вопросов удаляем специфичные для CV поля
      delete cleanData.image_id;
      delete cleanData.scoring_criteria;
      // manualAnnotations нам тоже не нужны
    } else if (questionType === 'image_annotation') {
      // Для графических вопросов удаляем специфичные для текста проверки (LLM/Плагиат)
      delete cleanData.ai_check_enabled;
      delete cleanData.plagiarism_check_enabled;
      delete cleanData.event_log_check_enabled;
      
      // И очищаем эталонный текстовый ответ, если он есть
      if (cleanData.reference_data) {
        delete cleanData.reference_data.reference_answer;
      }

      if (annotationMethod === 'manual' && manualAnnotations) {
        cleanData.reference_data = {
          ...cleanData.reference_data,
          ...manualAnnotations
        };
      }

      // Проверка суммы весов, если кастомная конфигурация включена
      if (cleanData.scoring_criteria?.use_custom_cv_config && weightsSum !== 100) {
        return;
      }

      // Очищаем кастомные настройки CV (веса и пороги), если они не активированы,
      // но оставляем allow_partial и label_configs, так как это относится к логике самого вопроса
      if (cleanData.scoring_criteria && !cleanData.scoring_criteria.use_custom_cv_config) {
        const { allow_partial, label_configs } = cleanData.scoring_criteria;
        cleanData.scoring_criteria = { allow_partial, label_configs };
      }
    }

    onSubmit(cleanData);
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
                onSave={handleAnnotationsChange}
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
                  <Controller
                    name="ai_check_enabled"
                    control={control}
                    render={({ field }) => (
                      <Box>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={!!field.value}
                              onChange={(e) => field.onChange(e.target.checked)}
                              disabled={readOnly}
                            />
                          }
                          label="Включить проверку на применение ИИ"
                        />
                        {field.value && (
                          <Alert severity="warning" sx={{ mt: 0.5, mb: 1 }}>
                            Использует LLM для анализа стиля ответа. Может давать ложные срабатывания.
                          </Alert>
                        )}
                      </Box>
                    )}
                  />
                  <Controller
                    name="plagiarism_check_enabled"
                    control={control}
                    render={({ field }) => (
                      <Box>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={!!field.value}
                              onChange={(e) => field.onChange(e.target.checked)}
                              disabled={readOnly}
                            />
                          }
                          label="Включить проверку на плагиат"
                        />
                        {field.value && (
                          <Alert severity="warning" sx={{ mt: 0.5 }}>
                            Ищет точные совпадения фрагментов ответа в поисковой выдаче Яндекса.
                          </Alert>
                        )}
                      </Box>
                    )}
                  />
                  <Controller
                    name="event_log_check_enabled"
                    control={control}
                    render={({ field }) => (
                      <Box>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={!!field.value}
                              onChange={(e) => field.onChange(e.target.checked)}
                              disabled={readOnly}
                            />
                          }
                          label="Анализ поведения"
                        />
                        {field.value && (
                          <Alert severity="warning" sx={{ mt: 0.5 }}>
                            ИИ проанализирует логи поведения в системе для оценки честности ответа.
                          </Alert>
                        )}
                      </Box>
                    )}
                  />
                </>
              )}

              {questionType === 'image_annotation' && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Controller
                    name="scoring_criteria.allow_partial"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={!!field.value}
                            onChange={(e) => field.onChange(e.target.checked)}
                            disabled={readOnly}
                          />
                        }
                        label={t('questions.allowPartial')}
                      />
                    )}
                  />

                  <Controller
                    name="scoring_criteria.use_custom_cv_config"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={!!field.value}
                            onChange={(e) => field.onChange(e.target.checked)}
                            disabled={readOnly}
                          />
                        }
                        label={t('questions.useCustomCvConfig')}
                      />
                    )}
                  />

                  {useCustomCvConfig && (
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: '#fdfdfd', border: displayWeightsError ? '1px solid #d32f2f' : '1px solid #ccc' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          {t('questions.cvConfigTitle')}
                          <Tooltip title="Настройка весов метрик и порогов обнаружения для этого вопроса">
                            <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                          </Tooltip>
                        </Typography>
                      </Box>
                      
                      <Grid container spacing={2}>
                        {/* Веса */}
                        <Grid item xs={12} sm={6}>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                            <Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  {t('questions.iouWeight')}
                                  <Tooltip title={t('questions.iouWeightDesc')}>
                                    <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
                                  </Tooltip>
                                </Typography>
                                <Typography variant="caption" fontWeight="bold" color={displayWeightsError ? 'error' : 'primary'}>{Math.round(iouWeight * 100)}%</Typography>
                              </Box>
                              <Slider
                                size="small"
                                value={iouWeight}
                                min={0}
                                max={1}
                                step={0.01}
                                onChange={(_, v) => handleWeightChange('iou_weight', v as number)}
                                disabled={readOnly}
                                color={displayWeightsError ? 'error' : 'primary'}
                              />
                            </Box>
                            <Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  {t('questions.recallWeight')}
                                  <Tooltip title={t('questions.recallWeightDesc')}>
                                    <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
                                  </Tooltip>
                                </Typography>
                                <Typography variant="caption" fontWeight="bold" color={displayWeightsError ? 'error' : 'primary'}>{Math.round(recallWeight * 100)}%</Typography>
                              </Box>
                              <Slider
                                size="small"
                                value={recallWeight}
                                min={0}
                                max={1}
                                step={0.01}
                                onChange={(_, v) => handleWeightChange('recall_weight', v as number)}
                                disabled={readOnly}
                                color={displayWeightsError ? 'error' : 'primary'}
                              />
                            </Box>
                            <Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  {t('questions.precisionWeight')}
                                  <Tooltip title={t('questions.precisionWeightDesc')}>
                                    <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
                                  </Tooltip>
                                </Typography>
                                <Typography variant="caption" fontWeight="bold" color={displayWeightsError ? 'error' : 'primary'}>{Math.round(precisionWeight * 100)}%</Typography>
                              </Box>
                              <Slider
                                size="small"
                                value={precisionWeight}
                                min={0}
                                max={1}
                                step={0.01}
                                onChange={(_, v) => handleWeightChange('precision_weight', v as number)}
                                disabled={readOnly}
                                color={displayWeightsError ? 'error' : 'primary'}
                              />
                            </Box>
                          </Box>
                        </Grid>

                        <Divider orientation="vertical" flexItem sx={{ mx: 1, display: { xs: 'none', sm: 'block' } }} />

                        {/* Пороги */}
                        <Grid item xs={12} sm={5}>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                            <Box>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  {t('questions.iouThreshold')}
                                  <Tooltip title={t('questions.iouThresholdDesc')}>
                                    <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
                                  </Tooltip>
                                </Typography>
                                <Typography variant="caption" fontWeight="bold" color="primary">{Math.round(iouThreshold * 100)}%</Typography>
                              </Box>
                              <Slider
                                size="small"
                                value={iouThreshold}
                                min={0.1}
                                max={0.9}
                                step={0.05}
                                onChange={(_, v) => setValue('scoring_criteria.iou_threshold', v as number, { shouldValidate: true })}
                                disabled={readOnly}
                              />
                            </Box>
                            {showPartialThresholds && (
                              <>
                                <Box>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                      {t('questions.inclusionThreshold')}
                                      <Tooltip title={t('questions.inclusionThresholdDesc')}>
                                        <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
                                      </Tooltip>
                                    </Typography>
                                    <Typography variant="caption" fontWeight="bold" color="primary">{Math.round(inclusionThreshold * 100)}%</Typography>
                                  </Box>
                                  <Slider
                                    size="small"
                                    value={inclusionThreshold}
                                    min={0.5}
                                    max={1.0}
                                    step={0.05}
                                    onChange={(_, v) => setValue('scoring_criteria.inclusion_threshold', v as number, { shouldValidate: true })}
                                    disabled={readOnly}
                                  />
                                </Box>
                                <Box>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                      {t('questions.coverageThreshold')}
                                      <Tooltip title={t('questions.coverageThresholdDesc')}>
                                        <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
                                      </Tooltip>
                                    </Typography>
                                    <Typography variant="caption" fontWeight="bold" color="primary">{Math.round(coverageThreshold * 100)}%</Typography>
                                  </Box>
                                  <Slider
                                    size="small"
                                    value={coverageThreshold}
                                    min={0.01}
                                    max={0.5}
                                    step={0.01}
                                    onChange={(_, v) => setValue('scoring_criteria.min_coverage_threshold', v as number, { shouldValidate: true })}
                                    disabled={readOnly}
                                  />
                                </Box>
                              </>
                            )}
                          </Box>
                        </Grid>
                      </Grid>
                      
                      {/* Настройка оценки по меткам */}
                      {(manualAnnotations?.labels?.length || imageAsset?.coco_annotations?.categories?.length) && (
                        <>
                          <Divider sx={{ my: 2 }} />
                          <Typography variant="subtitle2" sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            {t('questions.labelScoringTitle') || 'Настройка оценки по меткам'}
                            <Tooltip title="Выберите, какие метки из эталона будут участвовать в оценке и как">
                              <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                            </Tooltip>
                          </Typography>
                          
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                            {(manualAnnotations?.labels || imageAsset?.coco_annotations?.categories || []).map((label: any) => {
                              const labelId = label.id.toString();
                              const currentLabelConfig = scoringCriteria?.label_configs?.[labelId];
                              const isActive = !!currentLabelConfig;
                              
                              return (
                                <Paper 
                                  key={labelId} 
                                  variant="outlined" 
                                  sx={{ 
                                    p: 1.5, 
                                    border: isActive ? '1px solid #1976d2' : '1px solid #eee',
                                    bgcolor: isActive ? '#f0f7ff' : '#fafafa'
                                  }}
                                >
                                  {/* Первая строка: Активация и Название */}
                                  <Box sx={{ display: 'flex', alignItems: 'center', mb: isActive ? 1.5 : 0 }}>
                                    <FormControlLabel
                                      control={
                                        <Checkbox
                                          size="small"
                                          checked={isActive}
                                          disabled={readOnly}
                                          onChange={(e) => {
                                            const newConfigs = { ...(scoringCriteria?.label_configs || {}) };
                                            if (e.target.checked) {
                                              newConfigs[labelId] = {
                                                mode: 'all',
                                                min_count: 1,
                                                weight: 1.0,
                                                allow_partial: allowPartial // Наследуем глобальный при активации
                                              };
                                            } else {
                                              delete newConfigs[labelId];
                                            }
                                            setValue('scoring_criteria.label_configs', newConfigs, { shouldValidate: true });
                                          }}
                                        />
                                      }
                                      label={
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: label.color || '#ccc', flexShrink: 0 }} />
                                          <Typography variant="body2" fontWeight={isActive ? 'bold' : 'normal'}>
                                            {label.name}
                                          </Typography>
                                        </Box>
                                      }
                                      sx={{ m: 0 }}
                                    />
                                  </Box>

                                  {/* Вторая строка: Настройки (только если активно) */}
                                  {isActive && (
                                    <Grid container spacing={2} alignItems="center">
                                      <Grid item xs={12} sm={3.5}>
                                        <FormControl fullWidth size="small">
                                          <InputLabel sx={{ fontSize: '0.8rem' }}>{t('questions.labelMode') || 'Режим'}</InputLabel>
                                          <Select
                                            value={currentLabelConfig.mode}
                                            label={t('questions.labelMode') || 'Режим'}
                                            disabled={readOnly}
                                            sx={{ fontSize: '0.8rem' }}
                                            onChange={(e) => {
                                              const newConfigs = { ...scoringCriteria.label_configs };
                                              newConfigs[labelId] = { ...currentLabelConfig, mode: e.target.value };
                                              setValue('scoring_criteria.label_configs', newConfigs, { shouldValidate: true });
                                            }}
                                          >
                                            <MenuItem value="all" sx={{ fontSize: '0.8rem' }}>{t('questions.labelModeAll') || 'Все контуры'}</MenuItem>
                                            <MenuItem value="at_least_n" sx={{ fontSize: '0.8rem' }}>{t('questions.labelModeAtLeastN') || 'Не менее N'}</MenuItem>
                                          </Select>
                                        </FormControl>
                                      </Grid>
                                      
                                      <Grid item xs={12} sm={2}>
                                        {currentLabelConfig.mode === 'at_least_n' && (
                                          <TextField
                                            fullWidth
                                            size="small"
                                            type="number"
                                            label="N"
                                            value={currentLabelConfig.min_count}
                                            disabled={readOnly}
                                            InputProps={{
                                              sx: { fontSize: '0.8rem' }
                                            }}
                                            InputLabelProps={{
                                              sx: { fontSize: '0.8rem' }
                                            }}
                                            inputProps={{ 
                                              min: 1, 
                                              max: labelAnnotationCounts[labelId] || 1 
                                            }}
                                            onChange={(e) => {
                                              const maxVal = labelAnnotationCounts[labelId] || 1;
                                              let val = parseInt(e.target.value) || 1;
                                              if (val > maxVal) val = maxVal;
                                              if (val < 1) val = 1;
                                              const newConfigs = { ...scoringCriteria.label_configs };
                                              newConfigs[labelId] = { ...currentLabelConfig, min_count: val };
                                              setValue('scoring_criteria.label_configs', newConfigs, { shouldValidate: true });
                                            }}
                                          />
                                        )}
                                      </Grid>

                                      <Grid item xs={12} sm={4}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 1 }}>
                                          <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
                                            {t('questions.weightShort') || 'Вес'}:
                                          </Typography>
                                          <Slider
                                            size="small"
                                            value={currentLabelConfig.weight || 1}
                                            min={1}
                                            max={5}
                                            step={1}
                                            disabled={readOnly}
                                            marks
                                            onChange={(_, v) => {
                                              const newConfigs = { ...scoringCriteria.label_configs };
                                              newConfigs[labelId] = { ...currentLabelConfig, weight: v as number };
                                              setValue('scoring_criteria.label_configs', newConfigs, { shouldValidate: true });
                                            }}
                                            sx={{ flex: 1 }}
                                          />
                                          <Typography variant="caption" fontWeight="bold" sx={{ minWidth: 10 }}>
                                            {currentLabelConfig.weight || 1}
                                          </Typography>
                                        </Box>
                                      </Grid>

                                      <Grid item xs={12} sm={2.5}>
                                        <FormControlLabel
                                          control={
                                            <Checkbox
                                              size="small"
                                              checked={!!currentLabelConfig.allow_partial}
                                              disabled={readOnly}
                                              onChange={(e) => {
                                                const newConfigs = { ...scoringCriteria.label_configs };
                                                newConfigs[labelId] = { ...currentLabelConfig, allow_partial: e.target.checked };
                                                setValue('scoring_criteria.label_configs', newConfigs, { shouldValidate: true });
                                              }}
                                            />
                                          }
                                          label={
                                            <Typography variant="caption" sx={{ whiteSpace: 'nowrap' }}>
                                              {t('questions.allowPartialShort') || 'Частичный зачет'}
                                            </Typography>
                                          }
                                          sx={{ m: 0 }}
                                        />
                                      </Grid>
                                    </Grid>
                                  )}
                                </Paper>
                              );
                            })}
                          </Box>
                        </>
                      )}
                      
                      {displayWeightsError && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="caption" color="error" sx={{ fontWeight: 'bold', display: 'block', textAlign: 'center' }}>
                            {t('questions.error.weightsSum')} (сейчас {weightsSum}%)
                          </Typography>
                        </Box>
                      )}
                    </Paper>
                  )}

                  {formError && (
                    <Alert severity="error" onClose={() => setFormError(null)}>
                      {formError}
                    </Alert>
                  )}

                  <Box sx={{ border: '1px dashed #ccc', p: 2, borderRadius: 1, textAlign: 'center' }}>
                    {imageAsset ? (
                      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                        {/* Сообщение об ошибке для Image ID прямо здесь */}
                        {errors.image_id?.message && (
                          <Alert severity="error" sx={{ width: '100%', mb: 1 }}>
                            {errors.image_id.message}
                          </Alert>
                        )}
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
                            onChange={(_, v) => {
                              setAnnotationMethod(v)
                              if (questionType === 'image_annotation') {
                                trigger('image_id')
                              }
                            }}
                            variant="fullWidth"
                          >
                            <Tab label={t('questions.uploadJson')} value="upload" disabled={readOnly} />
                            <Tab label={t('questions.manualAnnotation')} value="manual" disabled={readOnly} />
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
                                            setFormError(null)
                                            const updated = await questionsApi.uploadAnnotations(imageAsset.id, file)
                                            setImageAsset(updated)
                                            // Синхронизируем загруженные аннотации с ручным режимом и переключаем метод
                                            if (updated.coco_annotations) {
                                              setAnnotationMethod('manual')
                                              const converted = {
                                                labels: updated.coco_annotations.categories?.map((c: any, index: number) => {
                                                  const colors = ['#3f51b5', '#f44336', '#4caf50', '#ff9800', '#9c27b0', '#795548', '#607d8b'];
                                                  return {
                                                    id: c.id.toString(),
                                                    name: c.name,
                                                    color: c.color || colors[index % colors.length]
                                                  };
                                                }) || [],
                                                annotations: updated.coco_annotations.annotations?.map((a: any) => ({
                                                  id: a.id.toString(),
                                                  label_id: a.category_id.toString(),
                                                  type: 'polygon',
                                                  points: a.segmentation[0] || []
                                                })) || []
                                              }
                                              setManualAnnotations(converted)
                                            }
                                          } catch (err: any) {
                                            setFormError(translateError(err.response?.data?.detail || 'Error uploading annotations'))
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
