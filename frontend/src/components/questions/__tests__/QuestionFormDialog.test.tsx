import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import QuestionFormDialog from '../QuestionFormDialog';
import { LocaleProvider } from '../../../contexts/LocaleContext';
import { LoadingProvider } from '../../../contexts/LoadingContext';
import { useAnnotationStore } from '../../annotation/hooks/useAnnotationStore';
import { vi } from 'vitest';

// Мокаем API и хуки
vi.mock('../../../lib/api/hooks/useTopics', () => ({
  useTopics: () => ({ data: [{ id: 'topic1', name: 'Topic 1' }] }),
}));

vi.mock('../../../lib/api', () => ({
  questionsApi: {
    uploadImage: vi.fn(),
    uploadAnnotations: vi.fn(),
  },
  adminApi: {
    getCVConfig: vi.fn().mockResolvedValue({
      iou_weight: 0.5,
      recall_weight: 0.3,
      precision_weight: 0.2,
      iou_threshold: 0.5,
    }),
  },
}));

const renderDialog = (props = {}) => {
  return render(
    <LoadingProvider>
      <LocaleProvider>
        <QuestionFormDialog 
          open={true} 
          onClose={vi.fn()} 
          onSubmit={vi.fn()} 
          {...props} 
        />
      </LocaleProvider>
    </LoadingProvider>
  );
};

describe('QuestionFormDialog (Конструктор вопросов)', () => {
  it('should switch between text and image_annotation types', async () => {
    renderDialog();
    
    // По умолчанию 'text'
    expect(screen.getByLabelText(/Эталонный ответ/i)).toBeInTheDocument();
    
    // Переключаем на 'image_annotation'
    const typeSelect = screen.getAllByRole('combobox')[0];
    fireEvent.mouseDown(typeSelect);
    const imageOption = await screen.findByRole('option', { name: /Графическая аннотация/i });
    fireEvent.click(imageOption);
    
    // Текстовое поле эталона должно исчезнуть, появиться загрузка изображения
    await waitFor(() => {
      expect(screen.queryByLabelText(/Эталонный ответ/i)).not.toBeInTheDocument();
      expect(screen.getByText(/Загрузите изображение/i)).toBeInTheDocument();
    });
  });

  it('should validate required fields', async () => {
    const onSubmit = vi.fn();
    renderDialog({ onSubmit });
    
    // Используем findByRole для надежности, т.к. там есть текст "Создать вопрос" в заголовке
    const submitBtn = await screen.findByRole('button', { name: /^Создать$/i });
    fireEvent.click(submitBtn);
    
    await waitFor(() => {
      expect(screen.getByText(/Введите текст вопроса/i)).toBeInTheDocument();
      expect(screen.getByText(/Введите эталонный ответ/i)).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('should balance weights correctly in custom CV config', async () => {
    renderDialog();
    
    // Включаем графический тип
    const typeSelect = screen.getAllByRole('combobox')[0];
    fireEvent.mouseDown(typeSelect);
    const imageOption = await screen.findByRole('option', { name: /Графическая аннотация/i });
    fireEvent.click(imageOption);
    
    // Включаем кастомные настройки
    // Ищем чекбокс через текст лейбла
    const customConfigLabel = await screen.findByText(/Использовать индивидуальные параметры/i);
    fireEvent.click(customConfigLabel);
    
    // Находим слайдеры весов (через их названия)
    await waitFor(() => {
      expect(screen.getAllByText(/50%/)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/30%/)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/20%/)[0]).toBeInTheDocument();
    });
  });

  it('should handle label configurations', async () => {
    // Подготовим данные с предзаполненными аннотациями (как после редактирования)
    const questionWithAnnotations = {
      id: 'q1',
      type: 'image_annotation',
      content: 'Test',
      image_id: 'img1',
      reference_data: {
        labels: [{ id: 'l1', name: 'Tumor', color: 'red' }],
        annotations: [{ id: 'a1', label_id: 'l1', type: 'polygon', points: [0,0,10,0,10,10] }]
      }
    };
    
    renderDialog({ question: questionWithAnnotations });
    
    // Включаем кастомные настройки
    const customConfigLabel = await screen.findByText(/Использовать индивидуальные параметры/i);
    fireEvent.click(customConfigLabel);
    
    // Должна появиться секция "Настройка оценки по меткам"
    await waitFor(() => {
      expect(screen.getByText(/Настройка оценки по меткам/i)).toBeInTheDocument();
      expect(screen.getByText(/Tumor/i)).toBeInTheDocument();
    });
    
    // Активируем метку Tumor для оценки
    const tumorCheckbox = screen.getByLabelText(/Tumor/i);
    fireEvent.click(tumorCheckbox);
    
    // Должны появиться настройки режима (Все контуры / Не менее N)
    // Текст "Режим" может встречаться несколько раз (в подсказках и лейблах), берем первый
    expect(screen.getAllByText(/Режим/i)[0]).toBeInTheDocument();
  });
});
