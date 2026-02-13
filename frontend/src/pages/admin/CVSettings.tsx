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
  loyalty_factor: number
}

export default function CVSettings() {
  const [cvConfig, setCvConfig] = useState<CVConfig>({
    iou_weight: 0.5,
    recall_weight: 0.3,
    precision_weight: 0.2,
    iou_threshold: 0.5,
    inclusion_threshold: 0.8,
    min_coverage_threshold: 0.05,
    loyalty_factor: 2.0,
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
      setCvConfig(data)
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

  const handleSaveCV = async () => {
    // Проверка суммы весов
    const sum = cvConfig.iou_weight + cvConfig.recall_weight + cvConfig.precision_weight
    if (Math.abs(sum - 1.0) > 0.001) {
      setMessageDialog({
        open: true,
        title: 'Ошибка валидации',
        content: 'Сумма весов (IoU, Recall, Precision) должна быть равна 1.0',
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
              <Tooltip title="Настройки алгоритма автоматической проверки графических ответов (IoU - Intersection over Union)">
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Настройте веса различных метрик для итогового балла. Сумма весов должна быть равна 1.0.
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Вес геометрической точности (IoU)</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {((cvConfig.iou_weight || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.iou_weight}
                  step={0.05}
                  min={0}
                  max={1}
                  valueLabelDisplay="auto"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, iou_weight: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Влияние точности совпадения контуров на итоговый балл.
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Вес полноты (Recall)</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {((cvConfig.recall_weight || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.recall_weight}
                  step={0.05}
                  min={0}
                  max={1}
                  valueLabelDisplay="auto"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, recall_weight: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Влияние доли найденных объектов на итоговый балл.
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Вес точности (Precision)</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {((cvConfig.precision_weight || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.precision_weight}
                  step={0.05}
                  min={0}
                  max={1}
                  valueLabelDisplay="auto"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, precision_weight: value as number })}
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
                    {cvConfig.iou_threshold}
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.iou_threshold}
                  step={0.05}
                  min={0.1}
                  max={0.9}
                  valueLabelDisplay="auto"
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
                  valueLabelDisplay="auto"
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
                  valueLabelDisplay="auto"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, min_coverage_threshold: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Минимальная площадь эталона, которую должен выделить студент (защита от случайных точек).
                </Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2">Коэффициент лояльности (Loyalty Factor)</Typography>
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {(cvConfig.loyalty_factor || 0).toFixed(1)}
                  </Typography>
                </Box>
                <Slider
                  value={cvConfig.loyalty_factor}
                  step={0.5}
                  min={1.0}
                  max={5.0}
                  valueLabelDisplay="auto"
                  onChange={(_, value) => setCvConfig({ ...cvConfig, loyalty_factor: value as number })}
                />
                <Typography variant="caption" color="text.secondary">
                  Степень мягкости оценки при частичном покрытии. Чем выше, тем больше баллов за малую площадь.
                </Typography>
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
              Рассчитывается как площадь пересечения деленная на площадь объединения (от 0.0 до 1.0).
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Сумма весов</strong> должна быть равна 1.0 (100%). Если вы хотите оценивать только точность попадания, 
              установите вес IoU на 1.0, а остальные на 0.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Порог IoU</strong> — это «проходной балл» для каждого объекта. Если пересечение области студента с эталоном выше этого порога, объект считается найденным верно.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Inclusion (Включение)</strong> — «Насколько точно студент попал». Показывает, не выходят ли контуры студента за границы эталона. Если нарисовать лишнее вне зоны, этот показатель упадет.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Coverage (Покрытие)</strong> — «Какую часть работы студент сделал». Показывает, какую долю огромного объекта студент выделил.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Loyalty Factor</strong> — «Коэффициент лояльности». Чем он выше, тем больше баллов система начисляет за частичное выделение сложного объекта.
            </Typography>
            <Typography variant="body2" component="div">
              <strong>Как выбрать порог:</strong>
              <ul style={{ paddingLeft: '20px', marginTop: '8px' }}>
                <li><strong>0.5 (стандарт)</strong> — баланс между точностью и гибкостью.</li>
                <li><strong>Высокий (0.7+)</strong> — для задач, где важна точность контуров.</li>
                <li><strong>Низкий (0.3-0.4)</strong> — если объекты мелкие или их сложно выделить точно.</li>
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
