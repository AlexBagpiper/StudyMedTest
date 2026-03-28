import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  CircularProgress,
  Divider,
  Slider,
  Tooltip,
  IconButton,
  Switch,
  FormControlLabel,
} from '@mui/material'
import InfoIcon from '@mui/icons-material/Info'
import SaveIcon from '@mui/icons-material/Save'
import { adminApi } from '../../lib/api'
import { MessageDialog } from '../../components/common/MessageDialog'

interface CVConfig {
  iou_weight: number
  recall_weight: number
  precision_weight: number
  iou_threshold: number
  inclusion_threshold: number
  min_coverage_threshold: number
  // Loyalty
  loyalty_mode: boolean
  accuracy_grace_threshold: number
  loyalty_boost_enabled: boolean
  loyalty_boost_value: number
  top_off_threshold: number
}

export default function CVSettings() {
  const [cvConfig, setCvConfig] = useState<CVConfig>({
    iou_weight: 0.5,
    recall_weight: 0.3,
    precision_weight: 0.2,
    iou_threshold: 0.5,
    inclusion_threshold: 0.8,
    min_coverage_threshold: 0.05,
    loyalty_mode: false,
    accuracy_grace_threshold: 0.95,
    loyalty_boost_enabled: false,
    loyalty_boost_value: 0.05,
    top_off_threshold: 99.0,
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [messageDialog, setMessageDialog] = useState<{
    open: boolean
    title: string
    content: string
    severity: 'error' | 'success' | 'info' | 'warning'
  }>({
    open: false,
    title: '',
    content: '',
    severity: 'info'
  })

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      setLoading(true)
      const data = await adminApi.getCVConfig()
      // Округляем до 2 знаков для корректной работы с процентами
      const roundedData = {
        ...data,
        iou_weight: Math.round(data.iou_weight * 100) / 100,
        recall_weight: Math.round(data.recall_weight * 100) / 100,
        precision_weight: Math.round(data.precision_weight * 100) / 100,
      }
      setCvConfig(roundedData)
    } catch (err: any) {
      console.error('Error loading config:', err)
      setMessageDialog({
        open: true,
        title: 'Ошибка',
        content: 'Не удалось загрузить системные настройки',
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleWeightChange = (key: 'iou_weight' | 'recall_weight' | 'precision_weight', value: number) => {
    const otherKeys = (['iou_weight', 'recall_weight', 'precision_weight'] as const).filter(k => k !== key);
    const currentSum = cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight;
    const otherSum = currentSum - cvConfig[key];
    
    // Работаем с процентами как с целыми числами для исключения шума плавающей точки
    const newValPercent = Math.round(value * 100);
    let newConfig = { ...cvConfig, [key]: newValPercent / 100 };
    
    const otherSumPercent = Math.round(otherSum * 100);
    const newSumPercent = newValPercent + otherSumPercent;

    // Если новая сумма превышает 100%, пропорционально уменьшаем другие веса
    if (newSumPercent > 100) {
      let excess = newSumPercent - 100;
      
      if (otherSumPercent > 0) {
        // Уменьшаем остальные веса
        let distributedExcess = 0;
        otherKeys.forEach((k, idx) => {
          if (idx === otherKeys.length - 1) {
            // Последнему отдаем остаток избытка для точности
            const finalVal = Math.max(0, Math.round(cvConfig[k] * 100) - (excess - distributedExcess));
            newConfig[k] = finalVal / 100;
          } else {
            const ratio = (cvConfig[k] * 100) / otherSumPercent;
            const reduction = Math.round(excess * ratio);
            const finalVal = Math.max(0, Math.round(cvConfig[k] * 100) - reduction);
            newConfig[k] = finalVal / 100;
            distributedExcess += reduction;
          }
        });
      } else {
        otherKeys.forEach(k => { newConfig[k] = 0; });
      }
    }

    setCvConfig(newConfig);
  };

  const handleSaveCV = async () => {
    // Проверка суммы весов в целых процентах
    const sumPercent = Math.round(cvConfig.iou_weight * 100) + 
                       Math.round(cvConfig.recall_weight * 100) + 
                       Math.round(cvConfig.precision_weight * 100);
    
    if (sumPercent !== 100) {
      setMessageDialog({
        open: true,
        title: 'Ошибка валидации',
        content: `Сумма весов должна быть равна 100% (сейчас она ${sumPercent}%)`,
        severity: 'warning'
      })
      return
    }

    try {
      setSaving(true)
      await adminApi.updateCVConfig(cvConfig)
      setMessageDialog({
        open: true,
        title: 'Успех',
        content: 'Настройки CV-оценки сохранены',
        severity: 'success'
      })
    } catch (err: any) {
      setMessageDialog({
        open: true,
        title: 'Ошибка',
        content: err.response?.data?.detail || 'Не удалось сохранить настройки',
        severity: 'error'
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4">Параметры CV-оценки</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
              <Typography variant="h6">Параметры CV-оценки</Typography>
              <Tooltip title="Настройки алгоритма автоматической проверки графических ответов (IoU)">
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Настройте веса различных метрик для итогового балла. Сумма весов должна быть равна 100%.
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Вес геометрической точности (IoU)</Typography>
                  <Typography variant="body2" color={Math.abs(cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight - 1.0) > 0.001 ? 'error' : 'primary'} fontWeight="bold">
                    {((cvConfig.iou_weight || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.iou_weight}
                  step={0.01}
                  min={0}
                  max={1}
                  track={false}
                  valueLabelDisplay="off"
                  sx={{
                    height: 8,
                    '& .MuiSlider-rail': {
                      opacity: 0.2,
                      background: (theme) => {
                        const sum = cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight;
                        const remaining = 1 - sum;
                        if (remaining > 0) {
                          const start = cvConfig.iou_weight * 100;
                          const end = (cvConfig.iou_weight + remaining) * 100;
                          return `linear-gradient(90deg, 
                            ${theme.palette.primary.main} 0%, 
                            ${theme.palette.primary.main} ${start}%, 
                            ${theme.palette.warning.light} ${start}%, 
                            ${theme.palette.warning.light} ${end}%, 
                            #ccc ${end}%, 
                            #ccc 100%)`;
                        }
                        return theme.palette.grey[300];
                      }
                    },
                    '& .MuiSlider-thumb': {
                      backgroundColor: '#white',
                      border: '2px solid currentColor',
                    }
                  }}
                  onChange={(_, value) => handleWeightChange('iou_weight', value as number)}
                />
                <Typography variant="caption" color="text.secondary">
                  Влияние точности совпадения контуров на итоговый балл.
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Вес полноты (Recall)</Typography>
                  <Typography variant="body2" color={Math.abs(cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight - 1.0) > 0.001 ? 'error' : 'primary'} fontWeight="bold">
                    {((cvConfig.recall_weight || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.recall_weight}
                  step={0.01}
                  min={0}
                  max={1}
                  track={false}
                  valueLabelDisplay="off"
                  sx={{
                    height: 8,
                    '& .MuiSlider-rail': {
                      opacity: 0.2,
                      background: (theme) => {
                        const sum = cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight;
                        const remaining = 1 - sum;
                        if (remaining > 0) {
                          const start = cvConfig.recall_weight * 100;
                          const end = (cvConfig.recall_weight + remaining) * 100;
                          return `linear-gradient(90deg, 
                            ${theme.palette.primary.main} 0%, 
                            ${theme.palette.primary.main} ${start}%, 
                            ${theme.palette.warning.light} ${start}%, 
                            ${theme.palette.warning.light} ${end}%, 
                            #ccc ${end}%, 
                            #ccc 100%)`;
                        }
                        return theme.palette.grey[300];
                      }
                    }
                  }}
                  onChange={(_, value) => handleWeightChange('recall_weight', value as number)}
                />
                <Typography variant="caption" color="text.secondary">
                  Влияние доли найденных объектов на итоговый балл.
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Вес точности (Precision)</Typography>
                  <Typography variant="body2" color={Math.abs(cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight - 1.0) > 0.001 ? 'error' : 'primary'} fontWeight="bold">
                    {((cvConfig.precision_weight || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.precision_weight}
                  step={0.01}
                  min={0}
                  max={1}
                  track={false}
                  valueLabelDisplay="off"
                  sx={{
                    height: 8,
                    '& .MuiSlider-rail': {
                      opacity: 0.2,
                      background: (theme) => {
                        const sum = cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight;
                        const remaining = 1 - sum;
                        if (remaining > 0) {
                          const start = cvConfig.precision_weight * 100;
                          const end = (cvConfig.precision_weight + remaining) * 100;
                          return `linear-gradient(90deg, 
                            ${theme.palette.primary.main} 0%, 
                            ${theme.palette.primary.main} ${start}%, 
                            ${theme.palette.warning.light} ${start}%, 
                            ${theme.palette.warning.light} ${end}%, 
                            #ccc ${end}%, 
                            #ccc 100%)`;
                        }
                        return theme.palette.grey[300];
                      }
                    }
                  }}
                  onChange={(_, value) => handleWeightChange('precision_weight', value as number)}
                />
                <Typography variant="caption" color="text.secondary">
                  Влияние отсутствия лишних (ошибочных) аннотаций на итоговый балл.
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Порог IoU для зачета объекта</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {((cvConfig.iou_threshold || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.iou_threshold}
                  step={0.05}
                  min={0.1}
                  max={0.9}
                  valueLabelDisplay="off"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, iou_threshold: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Минимальное пересечение с эталоном, при котором объект считается найденным верно.
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Минимальный порог включения (Inclusion)</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {((cvConfig.inclusion_threshold || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.inclusion_threshold}
                  step={0.05}
                  min={0.5}
                  max={1.0}
                  valueLabelDisplay="off"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, inclusion_threshold: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Доля ответа студента, которая должна находиться внутри эталона (для частичного зачета).
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Минимальное покрытие (Coverage)</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {((cvConfig.min_coverage_threshold || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.min_coverage_threshold}
                  step={0.01}
                  min={0.01}
                  max={0.5}
                  valueLabelDisplay="off"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, min_coverage_threshold: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Минимальная площадь эталона, которую должен выделить студент (защита от случайных точек).
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1, gap: 1 }}>
                  <Typography variant="h6">Сбалансированная лояльность</Typography>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={cvConfig.loyalty_mode}
                        onChange={(e) => setCvConfig({ ...cvConfig, loyalty_mode: e.target.checked })}
                      />
                    }
                    label={cvConfig.loyalty_mode ? "Включено" : "Выключено"}
                    sx={{ ml: 2 }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                  Набор механизмов для прощения мелких геометрических погрешностей, если клиническая суть задания выполнена верно.
                </Typography>

                {cvConfig.loyalty_mode && (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 2, pl: 2, borderLeft: '2px solid', borderColor: 'primary.light' }}>
                    <Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2">Порог «идеальной точности» (Grace Zone)</Typography>
                        <Typography variant="body2" color="primary" fontWeight="bold">
                          {((cvConfig.accuracy_grace_threshold || 0) * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                      <Slider
                        value={cvConfig.accuracy_grace_threshold}
                        step={0.01}
                        min={0.80}
                        max={0.99}
                        valueLabelDisplay="off"
                        onChange={(_, value) => setCvConfig({ ...cvConfig, accuracy_grace_threshold: value as number })}
                      />
                      <Typography variant="caption" color="text.secondary">
                        Если средняя точность студента выше этого порога, она автоматически приравнивается к 100%.
                      </Typography>
                    </Box>

                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <FormControlLabel
                          control={
                            <Switch
                              size="small"
                              checked={cvConfig.loyalty_boost_enabled}
                              onChange={(e) => setCvConfig({ ...cvConfig, loyalty_boost_enabled: e.target.checked })}
                            />
                          }
                          label={<Typography variant="subtitle2">Бонус за безошибочность (Loyalty Boost)</Typography>}
                        />
                        {cvConfig.loyalty_boost_enabled && (
                          <Typography variant="body2" color="primary" fontWeight="bold">
                            +{((cvConfig.loyalty_boost_value || 0) * 100).toFixed(0)}%
                          </Typography>
                        )}
                      </Box>
                      {cvConfig.loyalty_boost_enabled && (
                        <Box sx={{ px: 1, mt: 1 }}>
                          <Slider
                            value={cvConfig.loyalty_boost_value}
                            step={0.01}
                            min={0.01}
                            max={0.20}
                            valueLabelDisplay="off"
                            onChange={(_, value) => setCvConfig({ ...cvConfig, loyalty_boost_value: value as number })}
                          />
                        </Box>
                      )}
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        Добавляет бонус к точности, если студент нашел все объекты (Recall=100%) и не добавил лишних (Precision=100%).
                      </Typography>
                    </Box>

                    <Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="subtitle2">Порог округления итога (Top-off Rule)</Typography>
                        <Typography variant="body2" color="primary" fontWeight="bold">
                          {cvConfig.top_off_threshold}%
                        </Typography>
                      </Box>
                      <Slider
                        value={cvConfig.top_off_threshold}
                        step={0.5}
                        min={95}
                        max={99.5}
                        valueLabelDisplay="off"
                        onChange={(_, value) => setCvConfig({ ...cvConfig, top_off_threshold: value as number })}
                      />
                      <Typography variant="caption" color="text.secondary">
                        Если итоговый балл за вопрос выше этого порога, он округляется до 100%.
                      </Typography>
                    </Box>
                  </Box>
                )}
              </Box>

              <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSaveCV}
                  disabled={saving}
                >
                  {saving ? 'Сохранение...' : 'Сохранить параметры CV'}
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, bgcolor: '#f8fafc' }}>
            <Typography variant="h6" gutterBottom>Справка</Typography>
            <Typography variant="body2" paragraph>
              <strong>IoU (Intersection over Union)</strong> — основная метрика сравнения двух областей. 
              Рассчитывается как площадь пересечения деленная на площадь объединения (от 0% до 100%).
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Сумма весов</strong> должна быть равна 100%. Если вы хотите оценивать только точность попадания, 
              установите вес IoU на 100%, а остальные на 0%.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Порог IoU</strong> — это «проходной балл» для каждого объекта. Если пересечение области студента с эталоном выше этого порога, объект считается найденным верно.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Inclusion (Включение)</strong> — «Насколько точно студент попал». Показывает, не выходят ли контуры студента за границы эталона. Если нарисовать лишнее вне зоны, этот показатель упадет.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Coverage (Покрытие)</strong> — «Какую часть работы студент сделал». Показывает, какую долю объекта студент выделил. Для зачета объекта достаточно преодолеть минимальный порог.
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" component="div">
              <strong>Режим лояльности:</strong>
              <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
                <li><strong>Grace Zone</strong> — прощает мелкую неточность. Если студент нарисовал контур очень близко к эталону (напр. 95%+), система считает это за 100%.</li>
                <li><strong>Loyalty Boost</strong> — поощряет поиск. Если все объекты найдены верно и нет лишних, точность получает настроенный бонус (напр. +5%).</li>
                <li><strong>Top-off Rule</strong> — финальное округление. Если итоговый балл почти идеален (напр. 99%+), он округляется до 100%.</li>
              </ul>
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" component="div">
              <strong>Как выбрать порог IoU:</strong>
              <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
                <li><strong>Стандарт (50%)</strong> — баланс между точностью и гибкостью.</li>
                <li><strong>Высокий (70%+)</strong> — для задач, где важна точность контуров.</li>
                <li><strong>Низкий (30-40%)</strong> — если объекты мелкие или их сложно выделить точно.</li>
              </ul>
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <MessageDialog
        open={messageDialog.open}
        title={messageDialog.title}
        content={messageDialog.content}
        severity={messageDialog.severity}
        onClose={() => setMessageDialog({ ...messageDialog, open: false })}
      />
    </Box>
  )
}
