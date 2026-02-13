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
  yandex_search_api_key?: string
  yandex_search_folder_id?: string
  deepseek_api_key?: string
  qwen_api_key?: string
  gigachat_credentials?: string
  gigachat_scope: string
  local_llm_enabled: boolean
  local_llm_url?: string
  local_llm_model?: string
  strategy: 'local' | 'hybrid' | 'yandex' | 'deepseek' | 'qwen' | 'gigachat'
  hybrid_cloud_provider: string
  evaluation_prompt?: string
  ai_check_prompt?: string
  integrity_check_prompt?: string
  ai_threshold_warning: number
  ai_threshold_error: number
  plagiarism_threshold: number
}

interface TestResult {
  status: 'success' | 'error'
  message: string
  provider?: string
  result?: any
  search_result?: {
    status: 'success' | 'error' | 'skipped' | 'no_results'
    message: string
    score?: number
  }
}

export default function LLMSettings() {
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    local_llm_enabled: false,
    strategy: 'yandex',
    yandex_model: 'yandexgpt-lite/latest',
    gigachat_scope: 'GIGACHAT_API_PERS',
    hybrid_cloud_provider: 'deepseek',
    ai_check_prompt: "\nДОПОЛНИТЕЛЬНО (ИИ):\nОцени вероятность того, что ответ сгенерирован ИИ (0.0 - 1.0). Признаки: идеальная структура, отсутствие опечаток, общие фразы без конкретики.\n",
    integrity_check_prompt: "\nАНАЛИЗ ПОВЕДЕНИЯ (ПРОКТОР):\nВо время ответа на этот вопрос зафиксированы события: {event_log}.\nСуммарное время отсутствия в фокусе: {away_time_seconds} сек.\nОбщее время работы над вопросом: {total_time_seconds} сек.\nЧистое время набора текста (в фокусе): {focus_time_seconds} сек.\n\nОцени 'integrity_score' (коэффициент честности от 0.0 до 1.0).\nКритерии объективности:\n- Кратковременные переключения до 5 сек — допустимо 1 раз.\n- Длительные отсутствия более 10 сек — серьезное подозрение на поиск ответа.\n- Суммарное время вне вкладки {away_time_seconds} сек: если оно превышает 20% от общего времени {total_time_seconds} сек — значительное снижение.\n- Попытки вставки paste_attempted — критическое снижение от 0.0 до 0.3.\n- Если текст ответа большой, а время нахождения в фокусе {focus_time_seconds} сек маленькое — это явное списывание.\n\nВАЖНО: В тексте пояснения ('integrity_feedback') НЕ используй скобки любого типа. Пиши кратко.\n",
    ai_threshold_warning: 0.5,
    ai_threshold_error: 0.8,
    plagiarism_threshold: 0.5,
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
                  <MenuItem value="gigachat">GigaChat (Облако)</MenuItem>
                  <MenuItem value="deepseek">DeepSeek (Облако)</MenuItem>
                  <MenuItem value="qwen">Qwen (Облако)</MenuItem>
                  <MenuItem value="local">Локальная модель (Локально)</MenuItem>
                  <MenuItem value="hybrid">Гибридная стратегия (Облако/Локально)</MenuItem>
                </TextField>
              </Grid>
              {llmConfig.strategy === 'hybrid' && (
                <Grid item xs={12} sm={6}>
                  <TextField
                    select
                    fullWidth
                    label="Облачный провайдер (основной)"
                    value={llmConfig.hybrid_cloud_provider}
                    onChange={(e) => setLlmConfig({ ...llmConfig, hybrid_cloud_provider: e.target.value })}
                    helperText="При сбое этого провайдера будет использована локальная модель"
                  >
                    <MenuItem value="yandex">YandexGPT</MenuItem>
                    <MenuItem value="gigachat">GigaChat</MenuItem>
                    <MenuItem value="deepseek">DeepSeek</MenuItem>
                    <MenuItem value="qwen">Qwen</MenuItem>
                  </TextField>
                </Grid>
              )}
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Yandex Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom color="primary">Yandex GPT (Оценка)</Typography>
              <Grid container spacing={2}>
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
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    label="Yandex Folder ID"
                    value={llmConfig.yandex_folder_id || ''}
                    onChange={(e) => setLlmConfig({ ...llmConfig, yandex_folder_id: e.target.value })}
                    placeholder="b1g..."
                  />
                </Grid>
              </Grid>
            </Box>

            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom color="primary">Yandex Search API (Антиплагиат)</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="password"
                    label="Yandex Search API Key"
                    value={llmConfig.yandex_search_api_key || ''}
                    onChange={(e) => setLlmConfig({ ...llmConfig, yandex_search_api_key: e.target.value })}
                    placeholder="AQVN..."
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Yandex Search Folder ID"
                    value={llmConfig.yandex_search_folder_id || ''}
                    onChange={(e) => setLlmConfig({ ...llmConfig, yandex_search_folder_id: e.target.value })}
                    placeholder="b1g..."
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* GigaChat Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom color="primary">GigaChat (Sber)</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={8}>
                  <TextField
                    fullWidth
                    type="password"
                    label="GigaChat Credentials (Base64)"
                    value={llmConfig.gigachat_credentials || ''}
                    onChange={(e) => setLlmConfig({ ...llmConfig, gigachat_credentials: e.target.value })}
                    placeholder="ClientID:ClientSecret in Base64"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    select
                    fullWidth
                    label="Scope"
                    value={llmConfig.gigachat_scope || 'GIGACHAT_API_PERS'}
                    onChange={(e) => setLlmConfig({ ...llmConfig, gigachat_scope: e.target.value })}
                  >
                    <MenuItem value="GIGACHAT_API_PERS">Личный (Personal)</MenuItem>
                    <MenuItem value="GIGACHAT_API_CORP">Корпоративный (Corp)</MenuItem>
                  </TextField>
                </Grid>
              </Grid>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* DeepSeek Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom color="primary">DeepSeek</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    type="password"
                    label="DeepSeek API Key"
                    value={llmConfig.deepseek_api_key || ''}
                    onChange={(e) => setLlmConfig({ ...llmConfig, deepseek_api_key: e.target.value })}
                    placeholder="sk-..."
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Qwen Section */}
            <Box sx={{ mb: 4 }}>
              <Typography variant="h6" gutterBottom color="primary">Qwen (Alibaba DashScope)</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    type="password"
                    label="Qwen API Key"
                    value={llmConfig.qwen_api_key || ''}
                    onChange={(e) => setLlmConfig({ ...llmConfig, qwen_api_key: e.target.value })}
                    placeholder="your-api-key"
                  />
                </Grid>
              </Grid>
            </Box>

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

            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, mt: 4, gap: 1 }}>
              <Typography variant="h6">Промпты на академическую честность</Typography>
              <Tooltip title="Настройте инструкции для ИИ по поиску плагиата и анализу поведения">
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={10}
                  label="Промпт детекции ИИ"
                  value={llmConfig.ai_check_prompt || ''}
                  onChange={(e) => setLlmConfig({ ...llmConfig, ai_check_prompt: e.target.value })}
                  placeholder="Инструкции для поиска признаков генерации текста..."
                  sx={{ fontFamily: 'monospace', mb: 2 }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={10}
                  label="Промпт анализа поведения"
                  value={llmConfig.integrity_check_prompt || ''}
                  onChange={(e) => setLlmConfig({ ...llmConfig, integrity_check_prompt: e.target.value })}
                  helperText="Используйте переменную {event_log} для вставки списка событий в формате JSON"
                  placeholder="Инструкции по оценке логов переключения вкладок..."
                  sx={{ fontFamily: 'monospace' }}
                />
              </Grid>
            </Grid>

            <Box sx={{ mt: 4 }}>
              <Typography variant="h6" gutterBottom>Пороги срабатывания (Академическая честность)</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Порог (Плагиат)"
                    value={llmConfig.plagiarism_threshold}
                    onChange={(e) => setLlmConfig({ ...llmConfig, plagiarism_threshold: Number(e.target.value) })}
                    helperText="Вероятность выше которой считается плагиатом. При превышении порога балл=0"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Порог предупреждения (ИИ)"
                    value={llmConfig.ai_threshold_warning}
                    onChange={(e) => setLlmConfig({ ...llmConfig, ai_threshold_warning: Number(e.target.value) })}
                    helperText="Желтая зона вероятности ИИ"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Порог критический (ИИ)"
                    value={llmConfig.ai_threshold_error}
                    onChange={(e) => setLlmConfig({ ...llmConfig, ai_threshold_error: Number(e.target.value) })}
                    helperText="Красная зона вероятности ИИ. При превышении порога балл=0"
                  />
                </Grid>
              </Grid>
            </Box>

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
              <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {/* Блок LLM */}
                <Alert severity={testResult.status === 'success' ? 'success' : 'error'}>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Проверка ИИ-сервиса ({testResult.provider}):
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

                {/* Блок Search API */}
                {testResult.search_result && testResult.search_result.status !== 'skipped' && (
                  <Alert 
                    severity={
                      testResult.search_result.status === 'success' || testResult.search_result.status === 'no_results' 
                        ? 'success' 
                        : 'error'
                    }
                  >
                    <Typography variant="subtitle2" fontWeight="bold">
                      Проверка Yandex Search API (Антиплагиат):
                    </Typography>
                    <Typography variant="body2">
                      {testResult.search_result.message}
                    </Typography>
                    {testResult.search_result.score !== undefined && (
                      <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                        Найдено совпадений: {testResult.search_result.score > 0 ? 'Да' : 'Нет'}
                      </Typography>
                    )}
                  </Alert>
                )}
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, bgcolor: '#f8fafc', mb: 3 }}>
            <Typography variant="h6" gutterBottom>Справка</Typography>
            
            <Typography variant="subtitle2" color="primary" gutterBottom sx={{ mt: 2 }}>
              1. Стратегии работы
            </Typography>
            <Typography variant="body2" paragraph>
              • <strong>Облако:</strong> Прямое использование выбранного провайдера (Yandex, GigaChat и др.).
              <br/>• <strong>Локально:</strong> Оценка только через ваш сервер (Ollama/vLLM).
              <br/>• <strong>Гибридная:</strong> Основной запрос идет в облако, но при любой ошибке система мгновенно переключается на локальную модель.
            </Typography>

            <Typography variant="subtitle2" color="primary" gutterBottom>
              2. Настройка провайдеров
            </Typography>
            <Typography variant="body2" paragraph>
              • <strong>YandexGPT:</strong> Нужен <em>API Key</em> и <em>Folder ID</em>. Модель Pro точнее, Lite — быстрее и дешевле.
              <br/>• <strong>GigaChat:</strong> Требует <em>Credentials</em> (Base64). Получите их в личном кабинете GigaChat API.
              <br/>• <strong>DeepSeek / Qwen:</strong> Вставьте только <em>API Key</em> соответствующего сервиса.
            </Typography>

            <Typography variant="subtitle2" color="primary" gutterBottom>
              3. Академическая честность
            </Typography>
            <Typography variant="body2" paragraph>
              • <strong>Yandex Search API:</strong> Используется для поиска совпадений в интернете. Ключ должен иметь права <code>search-api.executor</code>.
              <br/>• <strong>Детекция ИИ:</strong> Настраивается через промпт. Ищет признаки "машинного" текста.
              <br/>• <strong>Анализ поведения:</strong> Обязательно используйте переменную <code>{'{event_log}'}</code> в промпте. Система заменит её на JSON со списком действий (paste, tab switch).
            </Typography>

            <Typography variant="subtitle2" color="primary" gutterBottom>
              4. Промпты
            </Typography>
            <Typography variant="body2" paragraph>
              • <strong>Системный промпт:</strong> Определяет "личность" и критерии оценки для ИИ-преподавателя.
              <br/>• <strong>Промпты честности:</strong> Отдельные инструкции для анализа плагиата и поведения.
            </Typography>

            <Typography variant="subtitle2" color="primary" gutterBottom>
              5. Тестирование
            </Typography>
            <Typography variant="body2">
              Нажмите <strong>«Проверить соединение»</strong>, чтобы убедиться, что:
              <br/>1. LLM доступна и понимает ваш промпт.
              <br/>2. Search API принимает ключ и находит данные.
            </Typography>
          </Paper>

          <Alert severity="info" sx={{ '& .MuiAlert-message': { width: '100%' } }}>
            <Typography variant="subtitle2">Важно:</Typography>
            <Typography variant="body2">
              Изменения применяются мгновенно ко всем новым проверкам ответов.
            </Typography>
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
