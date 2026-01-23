import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  CircularProgress,
  Divider,
  TextField,
  Switch,
  FormControlLabel,
  MenuItem,
  Tooltip,
  IconButton,
  Alert,
} from '@mui/material'
import InfoIcon from '@mui/icons-material/Info'
import SaveIcon from '@mui/icons-material/Save'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import { adminApi } from '../../lib/api'
import { MessageDialog } from '../../components/common/MessageDialog'

interface LLMConfig {
  yandex_api_key?: string
  yandex_folder_id?: string
  yandex_model: string
  local_llm_enabled: boolean
  local_llm_url?: string
  local_llm_model?: string
  strategy: 'local' | 'hybrid' | 'yandex'
  fallback_enabled: boolean
  evaluation_prompt?: string
}

interface TestResult {
  status: 'success' | 'error'
  message: string
  provider?: string
  result?: any
}

export default function LLMSettings() {
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    local_llm_enabled: false,
    strategy: 'yandex',
    fallback_enabled: true,
    yandex_model: 'yandexgpt-lite/latest',
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
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
      const data = await adminApi.getLLMConfig()
      // Если стратегия 'cloud' (старое значение), меняем на 'yandex'
      if (data.strategy === 'cloud') {
        data.strategy = 'yandex'
      }
      setLlmConfig(data)
    } catch (err: any) {
      console.error('Error loading config:', err)
      setMessageDialog({
        open: true,
        title: 'Ошибка',
        content: 'Не удалось загрузить настройки LLM',
        severity: 'error'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSaveLLM = async () => {
    try {
      setSaving(true)
      await adminApi.updateLLMConfig(llmConfig)
      setMessageDialog({
        open: true,
        title: 'Успех',
        content: 'Настройки LLM сохранены',
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

  const handleTestLLM = async () => {
    try {
      setTesting(true)
      setTestResult(null)
      const data = await adminApi.testLLMConfig(llmConfig)
      setTestResult(data)
      if (data.status === 'success') {
        setMessageDialog({
          open: true,
          title: 'Тест пройден',
          content: `Связь с ${data.provider || 'провайдером'} установлена. Оценка получена.`,
          severity: 'success'
        })
      } else {
        setMessageDialog({
          open: true,
          title: 'Ошибка теста',
          content: data.message,
          severity: 'error'
        })
      }
    } catch (err: any) {
      setMessageDialog({
        open: true,
        title: 'Ошибка',
        content: err.response?.data?.detail || 'Не удалось выполнить тестовый запрос',
        severity: 'error'
      })
    } finally {
      setTesting(false)
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
        <Typography variant="h4">Параметры LLM-оценки</Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
              <Typography variant="h6">Общие настройки</Typography>
            </Box>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  select
                  fullWidth
                  label="Стратегия работы"
                  value={llmConfig.strategy}
                  onChange={(e) => setLlmConfig({ ...llmConfig, strategy: e.target.value as any })}
                >
                  <MenuItem value="yandex">YandexGPT (Облако)</MenuItem>
                  <MenuItem value="local">Только локально (vLLM/Ollama)</MenuItem>
                  <MenuItem value="hybrid">Гибридная (Yandex для важных, локально для массы)</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={llmConfig.fallback_enabled}
                      onChange={(e) => setLlmConfig({ ...llmConfig, fallback_enabled: e.target.checked })}
                    />
                  }
                  label="Запасной вариант при ошибке"
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" gutterBottom>API Ключи и модель (Yandex Cloud)</Typography>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={4}>
                <TextField
                  select
                  fullWidth
                  label="Модель YandexGPT"
                  value={llmConfig.yandex_model || 'yandexgpt-lite/latest'}
                  onChange={(e) => setLlmConfig({ ...llmConfig, yandex_model: e.target.value })}
                >
                  <MenuItem value="yandexgpt-lite/latest">Lite (Экономная)</MenuItem>
                  <MenuItem value="yandexgpt/latest">Pro (Более точная)</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  type="password"
                  label="Yandex API Key"
                  value={llmConfig.yandex_api_key || ''}
                  onChange={(e) => setLlmConfig({ ...llmConfig, yandex_api_key: e.target.value })}
                  placeholder="AQVN..."
                  error={Boolean(llmConfig.yandex_api_key && !llmConfig.yandex_api_key.startsWith('AQVN') && !llmConfig.yandex_api_key.startsWith('t1.'))}
                  helperText={llmConfig.yandex_api_key && !llmConfig.yandex_api_key.startsWith('AQVN') && !llmConfig.yandex_api_key.startsWith('t1.') 
                    ? "Ключ должен начинаться на 'AQVN' (или 't1.' для IAM-токена)" 
                    : ""}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Yandex Folder ID"
                  value={llmConfig.yandex_folder_id || ''}
                  onChange={(e) => setLlmConfig({ ...llmConfig, yandex_folder_id: e.target.value })}
                  placeholder="b1g..."
                  error={Boolean(llmConfig.yandex_folder_id && !llmConfig.yandex_folder_id.startsWith('b1'))}
                  helperText={llmConfig.yandex_folder_id && !llmConfig.yandex_folder_id.startsWith('b1') 
                    ? "ID каталога обычно начинается на 'b1'" 
                    : ""}
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
              <Typography variant="h6">Локальная модель</Typography>
              <FormControlLabel
                sx={{ ml: 2 }}
                control={
                  <Switch
                    checked={llmConfig.local_llm_enabled}
                    onChange={(e) => setLlmConfig({ ...llmConfig, local_llm_enabled: e.target.checked })}
                  />
                }
                label="Включено"
              />
            </Box>
            
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={8}>
                <TextField
                  fullWidth
                  label="URL локального сервера"
                  disabled={!llmConfig.local_llm_enabled}
                  value={llmConfig.local_llm_url || ''}
                  onChange={(e) => setLlmConfig({ ...llmConfig, local_llm_url: e.target.value })}
                  placeholder="http://localhost:8000/v1"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Название модели"
                  disabled={!llmConfig.local_llm_enabled}
                  value={llmConfig.local_llm_model || ''}
                  onChange={(e) => setLlmConfig({ ...llmConfig, local_llm_model: e.target.value })}
                  placeholder="llama-3.1-70b"
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
              <Typography variant="h6">Промпт оценки</Typography>
              <Tooltip title="Настройте промпт, который будет отправлен LLM для оценки ответов">
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            <TextField
              fullWidth
              multiline
              rows={10}
              label="Системный промпт"
              value={llmConfig.evaluation_prompt || ''}
              onChange={(e) => setLlmConfig({ ...llmConfig, evaluation_prompt: e.target.value })}
              placeholder="Ты эксперт-преподаватель медицины..."
              sx={{ fontFamily: 'monospace' }}
            />

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
              <Button
                variant="outlined"
                startIcon={<PlayArrowIcon />}
                onClick={handleTestLLM}
                disabled={testing || saving}
              >
                {testing ? 'Тестирование...' : 'Проверить соединение'}
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSaveLLM}
                disabled={saving || testing}
              >
                {saving ? 'Сохранение...' : 'Сохранить настройки LLM'}
              </Button>
            </Box>

            {testResult && (
              <Box sx={{ mt: 3 }}>
                <Alert severity={testResult.status === 'success' ? 'success' : 'error'}>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Результат теста ({testResult.provider}):
                  </Typography>
                  <Typography variant="body2">
                    {testResult.message}
                  </Typography>
                  {testResult.result && (
                    <Box sx={{ mt: 1, p: 1, bgcolor: 'rgba(0,0,0,0.05)', borderRadius: 1 }}>
                      <pre style={{ margin: 0, fontSize: '0.75rem', overflow: 'auto' }}>
                        {JSON.stringify(testResult.result, null, 2)}
                      </pre>
                    </Box>
                  )}
                </Alert>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, bgcolor: '#f8fafc', mb: 3 }}>
            <Typography variant="h6" gutterBottom>Информация по стратегиям</Typography>
            <Typography variant="body2" paragraph>
              <strong>YandexGPT:</strong> использует облако Яндекса. Требует Folder ID и API Key.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Только локально:</strong> используется ваша инфраструктура (vLLM/Ollama).
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Гибридная:</strong> система будет использовать локальную модель для большинства тестов, переключаясь на YandexGPT для критически важных экзаменов.
            </Typography>
          </Paper>

          <Alert severity="info">
            Изменения вступят в силу для новых запросов к LLM. Текущие задачи в очереди Celery могут использовать старые настройки.
          </Alert>
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
