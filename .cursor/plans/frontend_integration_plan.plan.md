# План: Frontend Integration & Features

## 1. Setup & Infrastructure (2-3 дня)

### 1.1 API Client Configuration

**Задачи:**

- Настройка Axios instance с базовыми URL и interceptors
- React Query setup (QueryClient, devtools)
- Error handling и toast notifications
- Request/response interceptors для JWT refresh

**Файлы:**

```typescript
frontend/src/lib/
├── api/
│   ├── client.ts          // Axios instance + interceptors
│   ├── hooks/             // React Query hooks
│   │   ├── useAuth.ts
│   │   ├── useQuestions.ts
│   │   ├── useTests.ts
│   │   ├── useSubmissions.ts
│   │   └── useAnalytics.ts
│   └── types.ts           // API типы
└── utils/
    └── errorHandler.ts
```

**Реализация:**

```typescript
// client.ts
import axios from 'axios';
import { toast } from 'react-toastify';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor для добавления токена
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor для обработки 401 и refresh токена
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const { data } = await axios.post('/auth/refresh', { refresh_token: refreshToken });
        
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    // Error toast
    const message = error.response?.data?.detail || 'Произошла ошибка';
    toast.error(message);
    
    return Promise.reject(error);
  }
);
```
```typescript
// hooks/useQuestions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';

export const useQuestions = () => {
  return useQuery({
    queryKey: ['questions'],
    queryFn: async () => {
      const { data } = await apiClient.get('/questions');
      return data;
    },
  });
};

export const useCreateQuestion = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (questionData) => {
      const { data } = await apiClient.post('/questions', questionData);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      toast.success('Вопрос создан успешно');
    },
  });
};
```

---

## 2. Questions CRUD (3-4 дня)

### 2.1 Форма создания/редактирования вопроса

**Компоненты:**

```typescript
frontend/src/components/questions/
├── QuestionForm.tsx       // Универсальная форма (create/edit)
├── QuestionList.tsx       // Список вопросов с фильтрами
├── QuestionCard.tsx       // Карточка вопроса
├── RichTextEditor.tsx     // TinyMCE/Quill редактор
└── QuestionTypeSelector.tsx
```

**Форма (react-hook-form + zod):**

```typescript
// QuestionForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const questionSchema = z.object({
  type: z.enum(['text', 'image_annotation']),
  title: z.string().min(1).max(500),
  content: z.string().min(1),
  reference_data: z.object({
    reference_answer: z.string().optional(),
    coco_annotations: z.any().optional(),
  }).optional(),
  scoring_criteria: z.object({
    factual_correctness: z.number().min(0).max(40),
    completeness: z.number().min(0).max(30),
    terminology: z.number().min(0).max(20),
    structure: z.number().min(0).max(10),
  }).optional(),
  image_id: z.string().uuid().optional(),
});

export function QuestionForm({ question, onSuccess }) {
  const { register, handleSubmit, watch, setValue } = useForm({
    resolver: zodResolver(questionSchema),
    defaultValues: question || {
      type: 'text',
      scoring_criteria: {
        factual_correctness: 40,
        completeness: 30,
        terminology: 20,
        structure: 10,
      },
    },
  });
  
  const createMutation = useCreateQuestion();
  const updateMutation = useUpdateQuestion();
  
  const onSubmit = (data) => {
    if (question) {
      updateMutation.mutate({ id: question.id, data });
    } else {
      createMutation.mutate(data);
    }
  };
  
  const questionType = watch('type');
  
  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <QuestionTypeSelector {...register('type')} />
      
      <TextField
        label="Название вопроса"
        fullWidth
        {...register('title')}
      />
      
      <RichTextEditor
        value={watch('content')}
        onChange={(value) => setValue('content', value)}
      />
      
      {questionType === 'text' && (
        <TextField
          label="Эталонный ответ"
          multiline
          rows={4}
          {...register('reference_data.reference_answer')}
        />
      )}
      
      {questionType === 'image_annotation' && (
        <ImageUploadField
          onUpload={(imageId) => setValue('image_id', imageId)}
        />
      )}
      
      <ScoringCriteriaFields register={register} />
      
      <Button type="submit" variant="contained">
        {question ? 'Обновить' : 'Создать'}
      </Button>
    </Box>
  );
}
```

### 2.2 Rich Text Editor

**Опции:**

- **TinyMCE** (рекомендуется) - полнофункциональный WYSIWYG
- **Quill** - легковесный
- **Draft.js** - более низкоуровневый
```typescript
// RichTextEditor.tsx
import { Editor } from '@tinymce/tinymce-react';

export function RichTextEditor({ value, onChange }) {
  return (
    <Editor
      apiKey="your-tinymce-key" // или self-hosted
      value={value}
      onEditorChange={onChange}
      init={{
        height: 400,
        menubar: false,
        plugins: [
          'advlist', 'autolink', 'lists', 'link', 'image',
          'charmap', 'preview', 'searchreplace', 'code',
          'fullscreen', 'insertdatetime', 'table', 'help'
        ],
        toolbar: 'undo redo | formatselect | bold italic | \
                  alignleft aligncenter alignright | \
                  bullist numlist | link image | code',
        content_style: 'body { font-family: Inter, sans-serif; }',
      }}
    />
  );
}
```


---

## 3. Image Upload & Annotation Editor (4-5 дней)

### 3.1 Загрузка изображений

```typescript
// ImageUploadField.tsx
import { useState } from 'react';
import { Box, Button, CircularProgress } from '@mui/material';
import { apiClient } from '@/lib/api/client';

export function ImageUploadField({ onUpload }) {
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState(null);
  
  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);
    
    // Upload
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const { data } = await apiClient.post('/questions/images', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      onUpload(data.id);
      toast.success('Изображение загружено');
    } catch (error) {
      toast.error('Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <Box>
      <input
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        id="image-upload"
      />
      <label htmlFor="image-upload">
        <Button variant="outlined" component="span" disabled={uploading}>
          {uploading ? <CircularProgress size={24} /> : 'Загрузить изображение'}
        </Button>
      </label>
      
      {preview && (
        <Box mt={2}>
          <img src={preview} alt="Preview" style={{ maxWidth: '100%', maxHeight: 400 }} />
        </Box>
      )}
    </Box>
  );
}
```

### 3.2 Улучшение AnnotationEditor

**Добавить:**

- Zoom in/out
- Pan (перемещение холста)
- Отмена/повтор (undo/redo stack)
- Сохранение прогресса
- Загрузка эталонных аннотаций (полупрозрачный слой)
```typescript
// AnnotationEditor.tsx (улучшенная версия)
export default function AnnotationEditor({
  imageUrl,
  initialAnnotations,
  referenceAnnotations, // NEW: эталонные аннотации
  onSave,
  readOnly = false,
}) {
  const [canvas, setCanvas] = useState(null);
  const [tool, setTool] = useState('select');
  const [zoom, setZoom] = useState(1);
  const [showReference, setShowReference] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyStep, setHistoryStep] = useState(0);
  
  // Zoom controls
  const handleZoom = (delta) => {
    const newZoom = Math.max(0.5, Math.min(3, zoom + delta));
    setZoom(newZoom);
    canvas?.setZoom(newZoom);
  };
  
  // Undo/Redo
  const undo = () => {
    if (historyStep > 0) {
      const prevState = history[historyStep - 1];
      canvas.loadFromJSON(prevState, () => {
        canvas.renderAll();
        setHistoryStep(historyStep - 1);
      });
    }
  };
  
  const redo = () => {
    if (historyStep < history.length - 1) {
      const nextState = history[historyStep + 1];
      canvas.loadFromJSON(nextState, () => {
        canvas.renderAll();
        setHistoryStep(historyStep + 1);
      });
    }
  };
  
  // Save to history после каждого изменения
  const saveState = () => {
    const json = canvas.toJSON();
    const newHistory = history.slice(0, historyStep + 1);
    newHistory.push(json);
    setHistory(newHistory);
    setHistoryStep(newHistory.length - 1);
  };
  
  // Toggle reference layer
  const toggleReference = () => {
    setShowReference(!showReference);
    // Show/hide reference annotations layer
    canvas.getObjects('polygon').forEach(obj => {
      if (obj.isReference) {
        obj.visible = !showReference;
      }
    });
    canvas.renderAll();
  };
  
  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
        <ButtonGroup>
          <Button onClick={() => setTool('select')}>Выбор</Button>
          <Button onClick={() => setTool('polygon')}>Полигон</Button>
          <Button onClick={() => setTool('freehand')}>Свободное рисование</Button>
        </ButtonGroup>
        
        <ButtonGroup>
          <Button onClick={() => handleZoom(-0.1)}>-</Button>
          <Button disabled>{Math.round(zoom * 100)}%</Button>
          <Button onClick={() => handleZoom(0.1)}>+</Button>
        </ButtonGroup>
        
        <ButtonGroup>
          <Button onClick={undo} disabled={historyStep === 0}>Отменить</Button>
          <Button onClick={redo} disabled={historyStep === history.length - 1}>Повторить</Button>
        </ButtonGroup>
        
        {referenceAnnotations && (
          <FormControlLabel
            control={<Switch checked={showReference} onChange={toggleReference} />}
            label="Показать эталон"
          />
        )}
      </Box>
      
      <Box sx={{ border: '1px solid #ccc', borderRadius: 1, overflow: 'auto' }}>
        <canvas ref={canvasRef} />
      </Box>
    </Paper>
  );
}
```


---

## 4. Tests Constructor (5-6 дней)

### 4.1 Drag & Drop конструктор

**Библиотека:** `@dnd-kit/core` или `react-beautiful-dnd`

```typescript
// TestConstructor.tsx
import { DndContext, DragOverlay } from '@dnd-kit/core';
import { SortableContext, useSortable } from '@dnd-kit/sortable';

export function TestConstructor() {
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const [availableQuestions, setAvailableQuestions] = useState([]);
  const { data: questions } = useQuestions();
  
  useEffect(() => {
    setAvailableQuestions(questions || []);
  }, [questions]);
  
  const handleDragEnd = (event) => {
    const { active, over } = event;
    
    if (over?.id === 'test-area') {
      // Добавление вопроса в тест
      const question = availableQuestions.find(q => q.id === active.id);
      setSelectedQuestions([...selectedQuestions, question]);
    }
  };
  
  return (
    <DndContext onDragEnd={handleDragEnd}>
      <Grid container spacing={3}>
        {/* Левая панель: Банк вопросов */}
        <Grid item xs={6}>
          <Paper sx={{ p: 2, minHeight: 600 }}>
            <Typography variant="h6">Банк вопросов</Typography>
            <TextField
              placeholder="Поиск..."
              fullWidth
              sx={{ my: 2 }}
            />
            
            <Box sx={{ maxHeight: 500, overflow: 'auto' }}>
              {availableQuestions.map(question => (
                <DraggableQuestionCard key={question.id} question={question} />
              ))}
            </Box>
          </Paper>
        </Grid>
        
        {/* Правая панель: Конструктор теста */}
        <Grid item xs={6}>
          <Paper sx={{ p: 2, minHeight: 600 }} id="test-area">
            <Typography variant="h6">Тест</Typography>
            
            <SortableContext items={selectedQuestions.map(q => q.id)}>
              {selectedQuestions.map((question, index) => (
                <SortableQuestionItem
                  key={question.id}
                  question={question}
                  order={index + 1}
                  onRemove={() => {
                    setSelectedQuestions(selectedQuestions.filter(q => q.id !== question.id));
                  }}
                  onWeightChange={(weight) => {
                    // Update weight
                  }}
                />
              ))}
            </SortableContext>
            
            {selectedQuestions.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
                Перетащите сюда вопросы из банка
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
      
      {/* Настройки теста */}
      <Paper sx={{ p: 2, mt: 3 }}>
        <Typography variant="h6">Настройки теста</Typography>
        <Grid container spacing={2} mt={1}>
          <Grid item xs={4}>
            <TextField
              label="Время на прохождение (минуты)"
              type="number"
              fullWidth
            />
          </Grid>
          <Grid item xs={4}>
            <TextField
              label="Максимум попыток"
              type="number"
              fullWidth
            />
          </Grid>
          <Grid item xs={4}>
            <FormControlLabel
              control={<Switch />}
              label="Перемешивать вопросы"
            />
          </Grid>
        </Grid>
      </Paper>
      
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button variant="outlined">Сохранить черновик</Button>
        <Button variant="contained">Опубликовать тест</Button>
      </Box>
    </DndContext>
  );
}
```

---

## 5. Test Taking Flow (4-5 дней)

### 5.1 Прохождение теста студентом

**Функционал:**

- Таймер с автоматической отправкой
- Автосохранение каждые 30 сек
- Навигация между вопросами
- Индикатор прогресса
- Текстовые ответы + аннотации
```typescript
// TestTakingPage.tsx
export function TestTakingPage() {
  const { testId } = useParams();
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(null);
  
  const { data: submission } = useSubmission();
  const { data: variant } = useTestVariant(testId);
  const saveAnswerMutation = useSaveAnswer();
  const submitTestMutation = useSubmitTest();
  
  // Таймер
  useEffect(() => {
    if (!timeLeft) return;
    
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(timer);
  }, [timeLeft]);
  
  // Автосохранение
  useEffect(() => {
    const autoSave = setInterval(() => {
      saveCurrentAnswer();
    }, 30000); // 30 сек
    
    return () => clearInterval(autoSave);
  }, [currentQuestionIndex, answers]);
  
  const saveCurrentAnswer = () => {
    const currentQuestion = questions[currentQuestionIndex];
    const answer = answers[currentQuestion.id];
    
    if (answer) {
      saveAnswerMutation.mutate({
        submission_id: submission.id,
        question_id: currentQuestion.id,
        ...answer,
      });
    }
  };
  
  const handleNext = () => {
    saveCurrentAnswer();
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };
  
  const handleSubmit = () => {
    saveCurrentAnswer();
    submitTestMutation.mutate(submission.id, {
      onSuccess: () => {
        navigate(`/submissions/${submission.id}`);
      },
    });
  };
  
  const currentQuestion = questions[currentQuestionIndex];
  
  return (
    <Box>
      {/* Хедер с таймером и прогрессом */}
      <Paper sx={{ p: 2, mb: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h6">{variant?.test?.title}</Typography>
          <Typography variant="caption" color="text.secondary">
            Вопрос {currentQuestionIndex + 1} из {questions.length}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <LinearProgress
            variant="determinate"
            value={(currentQuestionIndex + 1) / questions.length * 100}
            sx={{ width: 200 }}
          />
          
          {timeLeft && (
            <Chip
              icon={<TimerIcon />}
              label={formatTime(timeLeft)}
              color={timeLeft < 300 ? 'error' : 'default'}
            />
          )}
        </Box>
      </Paper>
      
      {/* Вопрос */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {currentQuestion.title}
        </Typography>
        
        <Box dangerouslySetInnerHTML={{ __html: currentQuestion.content }} />
        
        {/* Область ответа */}
        {currentQuestion.type === 'text' ? (
          <TextField
            multiline
            rows={8}
            fullWidth
            placeholder="Введите ваш ответ..."
            value={answers[currentQuestion.id]?.student_answer || ''}
            onChange={(e) => {
              setAnswers({
                ...answers,
                [currentQuestion.id]: {
                  student_answer: e.target.value,
                },
              });
            }}
            sx={{ mt: 3 }}
          />
        ) : (
          <AnnotationEditor
            imageUrl={currentQuestion.image?.presigned_url}
            initialAnnotations={answers[currentQuestion.id]?.annotation_data}
            onSave={(cocoData) => {
              setAnswers({
                ...answers,
                [currentQuestion.id]: {
                  annotation_data: cocoData,
                },
              });
            }}
          />
        )}
      </Paper>
      
      {/* Навигация */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
        <Button
          variant="outlined"
          disabled={currentQuestionIndex === 0}
          onClick={() => setCurrentQuestionIndex(currentQuestionIndex - 1)}
        >
          Назад
        </Button>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" onClick={saveCurrentAnswer}>
            Сохранить
          </Button>
          
          {currentQuestionIndex === questions.length - 1 ? (
            <Button variant="contained" color="success" onClick={handleSubmit}>
              Завершить тест
            </Button>
          ) : (
            <Button variant="contained" onClick={handleNext}>
              Далее
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
}
```


---

## 6. Results & Feedback (2-3 дня)

### 6.1 Просмотр результатов

```typescript
// SubmissionResultPage.tsx
export function SubmissionResultPage() {
  const { submissionId } = useParams();
  const { data: submission, isLoading } = useSubmission(submissionId);
  
  if (isLoading) return <CircularProgress />;
  
  const result = submission.result;
  const answers = submission.answers;
  
  const getGradeColor = (grade) => {
    switch (grade) {
      case '5': return 'success';
      case '4': return 'info';
      case '3': return 'warning';
      default: return 'error';
    }
  };
  
  return (
    <Box>
      {/* Результат */}
      <Paper sx={{ p: 3, mb: 3, textAlign: 'center' }}>
        <Typography variant="h3" gutterBottom>
          Оценка: <Chip label={result.grade} color={getGradeColor(result.grade)} size="large" />
        </Typography>
        
        <Typography variant="h5" color="text.secondary">
          {result.total_score} / {result.max_score} баллов ({result.percentage.toFixed(1)}%)
        </Typography>
        
        {result.feedback && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {result.feedback}
          </Alert>
        )}
      </Paper>
      
      {/* Детализация по вопросам */}
      <Typography variant="h5" gutterBottom>
        Детальные результаты
      </Typography>
      
      {answers.map((answer, index) => (
        <Accordion key={answer.id}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
              <Typography>Вопрос {index + 1}</Typography>
              <Box sx={{ flexGrow: 1 }} />
              <Chip
                label={`${answer.score} / 100`}
                color={answer.score >= 70 ? 'success' : 'warning'}
                size="small"
              />
            </Box>
          </AccordionSummary>
          
          <AccordionDetails>
            <Typography variant="subtitle2" gutterBottom>
              Вопрос:
            </Typography>
            <Box dangerouslySetInnerHTML={{ __html: answer.question.content }} />
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle2" gutterBottom>
              Ваш ответ:
            </Typography>
            {answer.student_answer ? (
              <Typography>{answer.student_answer}</Typography>
            ) : (
              <Box>
                {/* Показать аннотации студента */}
                <AnnotationEditor
                  imageUrl={answer.question.image?.presigned_url}
                  initialAnnotations={answer.annotation_data}
                  readOnly
                />
              </Box>
            )}
            
            <Divider sx={{ my: 2 }} />
            
            {/* Обратная связь от LLM/CV */}
            {answer.evaluation && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Оценка:
                </Typography>
                
                {answer.evaluation.criteria_scores && (
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    {Object.entries(answer.evaluation.criteria_scores).map(([key, value]) => (
                      <Grid item xs={6} key={key}>
                        <Box>
                          <Typography variant="caption">{key}</Typography>
                          <LinearProgress
                            variant="determinate"
                            value={(value / 40) * 100}
                            sx={{ height: 8, borderRadius: 1 }}
                          />
                          <Typography variant="caption">{value} баллов</Typography>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                )}
                
                {answer.evaluation.feedback && (
                  <Alert severity="info">
                    <Typography variant="body2">{answer.evaluation.feedback}</Typography>
                  </Alert>
                )}
                
                {/* Для графических вопросов - IoU метрики */}
                {answer.evaluation.iou_scores && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption">IoU Scores:</Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {answer.evaluation.iou_scores.map((iou, i) => (
                        <Chip
                          key={i}
                          label={`${(iou * 100).toFixed(1)}%`}
                          size="small"
                          color={iou > 0.5 ? 'success' : 'error'}
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
```

---

## 7. Analytics & Charts (3-4 дня)

### 7.1 Teacher Dashboard

```typescript
// TeacherAnalyticsPage.tsx
import { BarChart, Bar, LineChart, Line, PieChart, Pie } from 'recharts';

export function TeacherAnalyticsPage() {
  const { data: analytics } = useTeacherAnalytics();
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Аналитика
      </Typography>
      
      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Всего тестов
              </Typography>
              <Typography variant="h3">{analytics.tests.total}</Typography>
              <Chip
                label={`${analytics.tests.published} опубликовано`}
                size="small"
                color="success"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Вопросов
              </Typography>
              <Typography variant="h3">{analytics.questions.total}</Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Попыток
              </Typography>
              <Typography variant="h3">{analytics.submissions.total}</Typography>
              <Chip
                label={`${analytics.submissions.completed} завершено`}
                size="small"
                color="info"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Средний балл
              </Typography>
              <Typography variant="h3">
                {analytics.average_score?.toFixed(1) || 'N/A'}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      {/* Графики */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Активность студентов
            </Typography>
            <LineChart width={600} height={300} data={activityData}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="submissions" stroke="#3B82F6" />
            </LineChart>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Распределение оценок
            </Typography>
            <PieChart width={300} height={300}>
              <Pie
                data={gradesDistribution}
                dataKey="count"
                nameKey="grade"
                fill="#3B82F6"
                label
              />
              <Tooltip />
            </PieChart>
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Статистика по тестам
            </Typography>
            <BarChart width={800} height={300} data={testsStats}>
              <XAxis dataKey="test_name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="avg_score" fill="#3B82F6" />
              <Bar dataKey="attempts" fill="#10B981" />
            </BarChart>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
```

---

## 8. Admin Panel (4-5 дней)

### 8.1 Таблицы с поиском и фильтрами

```typescript
// AdminUsersTable.tsx
import { DataGrid } from '@mui/x-data-grid';

export function AdminUsersTable() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState(null);
  
  const { data, isLoading } = useAdminUsers({
    skip: page * pageSize,
    limit: pageSize,
    search,
    role: roleFilter,
  });
  
  const columns = [
    { field: 'email', headerName: 'Email', width: 250 },
    { field: 'last_name', headerName: 'Фамилия', width: 150 },
    { field: 'first_name', headerName: 'Имя', width: 150 },
    {
      field: 'role',
      headerName: 'Роль',
      width: 120,
      renderCell: (params) => (
        <Chip label={params.value} size="small" color="primary" />
      ),
    },
    {
      field: 'is_active',
      headerName: 'Активен',
      width: 100,
      renderCell: (params) => (
        params.value ? <CheckIcon color="success" /> : <CloseIcon color="error" />
      ),
    },
    {
      field: 'created_at',
      headerName: 'Создан',
      width: 180,
      valueFormatter: (params) => new Date(params.value).toLocaleString('ru'),
    },
    {
      field: 'actions',
      headerName: 'Действия',
      width: 150,
      renderCell: (params) => (
        <Box>
          <IconButton onClick={() => handleEdit(params.row)}>
            <EditIcon />
          </IconButton>
          <IconButton onClick={() => handleDelete(params.row.id)}>
            <DeleteIcon />
          </IconButton>
        </Box>
      ),
    },
  ];
  
  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          placeholder="Поиск..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ flexGrow: 1 }}
        />
        
        <Select
          value={roleFilter || ''}
          onChange={(e) => setRoleFilter(e.target.value || null)}
          displayEmpty
        >
          <MenuItem value="">Все роли</MenuItem>
          <MenuItem value="student">Студент</MenuItem>
          <MenuItem value="teacher">Преподаватель</MenuItem>
          <MenuItem value="admin">Администратор</MenuItem>
        </Select>
        
        <Button variant="contained" startIcon={<AddIcon />}>
          Создать
        </Button>
      </Box>
      
      <DataGrid
        rows={data?.items || []}
        columns={columns}
        pageSize={pageSize}
        onPageSizeChange={setPageSize}
        rowCount={data?.total || 0}
        page={page}
        onPageChange={setPage}
        loading={isLoading}
        paginationMode="server"
        disableSelectionOnClick
      />
    </Box>
  );
}
```

---

## 9. Тестирование & Оптимизация (3-4 дня)

### 9.1 Unit тесты (Vitest)

```typescript
// __tests__/QuestionForm.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestionForm } from '@/components/questions/QuestionForm';

describe('QuestionForm', () => {
  it('should render form fields', () => {
    render(<QuestionForm />);
    
    expect(screen.getByLabelText('Название вопроса')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Создать' })).toBeInTheDocument();
  });
  
  it('should validate required fields', async () => {
    render(<QuestionForm />);
    
    const submitButton = screen.getByRole('button', { name: 'Создать' });
    await userEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/required/i)).toBeInTheDocument();
    });
  });
  
  it('should submit form with valid data', async () => {
    const onSuccess = vi.fn();
    render(<QuestionForm onSuccess={onSuccess} />);
    
    await userEvent.type(screen.getByLabelText('Название вопроса'), 'Test question');
    await userEvent.click(screen.getByRole('button', { name: 'Создать' }));
    
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
```

### 9.2 E2E тесты (Playwright)

```typescript
// e2e/test-taking.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Test Taking Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="username"]', 'student@test.com');
    await page.fill('[name="password"]', 'password');
    await page.click('button[type="submit"]');
  });
  
  test('should complete a test', async ({ page }) => {
    // Navigate to tests
    await page.goto('/tests');
    await page.click('text=Доступные тесты');
    
    // Start test
    await page.click('button:has-text("Начать тест")');
    
    // Answer questions
    await page.fill('textarea', 'My answer');
    await page.click('button:has-text("Далее")');
    
    // Submit test
    await page.click('button:has-text("Завершить тест")');
    
    // Check result
    await expect(page.locator('text=Оценка:')).toBeVisible();
  });
});
```

### 9.3 Performance оптимизация

- React.lazy для code splitting
- useMemo/useCallback для тяжелых вычислений
- Virtualization для длинных списков (react-window)
- Debounce для поиска
- Image optimization (WebP, lazy loading)

---

## 10. Финальная интеграция (2-3 дня)

### 10.1 Чеклист перед релизом

- [ ] Все API endpoints подключены
- [ ] Error handling на всех формах
- [ ] Loading states везде
- [ ] Toast notifications
- [ ] Responsive design (mobile/tablet)
- [ ] Dark mode (опционально)
- [ ] Локализация (i18n)
- [ ] SEO meta tags
- [ ] Analytics integration (опционально)

### 10.2 Build & Deploy

```bash
# Frontend build
cd frontend
npm run build
# → dist/ folder

# Backend migrations
cd backend
alembic upgrade head

# Docker compose
docker-compose up -d --build
```

---

## Оценка времени

| Этап | Дни | Недели |

|------|-----|--------|

| 1. Setup & API Client | 2-3 | 0.5 |

| 2. Questions CRUD | 3-4 | 0.7 |

| 3. Image Upload & Editor | 4-5 | 1 |

| 4. Tests Constructor | 5-6 | 1.2 |

| 5. Test Taking Flow | 4-5 | 1 |

| 6. Results & Feedback | 2-3 | 0.5 |

| 7. Analytics & Charts | 3-4 | 0.7 |

| 8. Admin Panel | 4-5 | 1 |

| 9. Testing & Optimization | 3-4 | 0.7 |

| 10. Final Integration | 2-3 | 0.5 |

| **ИТОГО** | **32-42** | **7-9** |

**Рекомендуемый график:** 8 недель (2 месяца) с 1 разработчиком

---

## Приоритеты

### 🔥 Критичные (MVP):

1. API Client Setup
2. Questions CRUD
3. Tests Constructor
4. Test Taking Flow
5. Results View

### ⚡ Важные:

6. Image Upload & Annotation Editor
7. Analytics (базовые метрики)
8. Admin Panel (users management)

### 💡 Nice-to-have:

9. Advanced Analytics (charts)
10. E2E тесты
11. Performance optimization

---

## Риски

| Риск | Вероятность | Митигация |

|------|-------------|-----------|

| Сложность Fabric.js | Средняя | Использовать готовые примеры, консультации |

| Performance больших изображений | Средняя | Lazy loading, WebP, CDN |

| React Query cache invalidation | Низкая | Четкая стратегия invalidation |

| Drag & Drop UX | Средняя | User testing, итерации |

---

## Следующие шаги

1. ✅ Утвердить план
2. ⏩ Создать GitHub Issues/Tasks
3. ⏩ Setup development environment
4. ⏩ Start with API Client (Week 1)