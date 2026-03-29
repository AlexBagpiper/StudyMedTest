import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { AnnotationEditor } from '../AnnotationEditor';
import { useAnnotationStore } from '../hooks/useAnnotationStore';
import { LocaleProvider } from '../../../contexts/LocaleContext';
import { LoadingProvider } from '../../../contexts/LoadingContext';
import { vi } from 'vitest';

const renderEditor = (props = {}) => {
  return render(
    <LoadingProvider>
      <LocaleProvider>
        <AnnotationEditor 
          imageUrl="test.jpg" 
          {...props} 
        />
      </LocaleProvider>
    </LoadingProvider>
  );
};

describe('AnnotationEditor (Редактор аннотаций)', () => {
  beforeEach(() => {
    useAnnotationStore.getState().reset();
  });

  it('should initialize with provided data', () => {
    const initialData = {
      labels: [{ id: 'l1', name: 'Test Label', color: '#ff0000' }],
      annotations: [{ id: 'a1', label_id: 'l1', type: 'polygon', points: [0,0,10,0,10,10] }]
    };
    
    renderEditor({ initialData });
    
    expect(useAnnotationStore.getState().labels).toHaveLength(1);
    expect(useAnnotationStore.getState().annotations).toHaveLength(1);
    expect(screen.getByText(/Test Label/i)).toBeInTheDocument();
  });

  it('should change modes via toolbar', () => {
    renderEditor();
    
    // В Toolbar.tsx MUI Tooltip переносит title в aria-label для кнопок
    const polygonBtn = screen.getByLabelText(/Полигон/i);
    fireEvent.click(polygonBtn);
    
    expect(useAnnotationStore.getState().mode).toBe('polygon');
    
    const selectBtn = screen.getByLabelText(/Выделение/i);
    fireEvent.click(selectBtn);
    
    expect(useAnnotationStore.getState().mode).toBe('select');
  });

  it('should handle zoom buttons', () => {
    renderEditor();
    
    // Ищем кнопки именно в футере, так как AddIcon может быть и в панели меток
    const footer = screen.getByText(/100%/).closest('.MuiBox-root');
    const zoomInBtn = within(footer as HTMLElement).getByTestId('AddIcon').parentElement;
    const zoomOutBtn = within(footer as HTMLElement).getByTestId('RemoveIcon').parentElement;
    
    fireEvent.click(zoomInBtn!);
    expect(useAnnotationStore.getState().zoom).toBeGreaterThan(1);
    
    fireEvent.click(zoomOutBtn!);
    fireEvent.click(zoomOutBtn!);
    expect(useAnnotationStore.getState().zoom).toBeLessThan(1);
    
    const resetBtn = screen.getByText(/Reset/i);
    fireEvent.click(resetBtn);
    expect(useAnnotationStore.getState().zoom).toBe(1);
  });

  it('should call onFinish and onSave when clicking save', () => {
    const onFinish = vi.fn();
    const onSave = vi.fn();
    
    renderEditor({ onFinish, onSave });
    
    const saveBtn = screen.getByText(/Сохранить и вернуться/i);
    fireEvent.click(saveBtn);
    
    expect(onSave).toHaveBeenCalled();
    expect(onFinish).toHaveBeenCalled();
  });

  it('should respect readOnly mode', async () => {
    // Явно сбрасываем состояние перед тестом
    useAnnotationStore.setState({ mode: 'select' });
    
    renderEditor({ readOnly: true, onFinish: vi.fn() });
    
    // Тулбар не должен отображаться
    expect(screen.queryByTestId('Toolbar')).not.toBeInTheDocument();
    
    // Кнопка сохранения должна называться "Закрыть"
    const closeBtn = await screen.findByRole('button', { name: /Закрыть/i });
    expect(closeBtn).toBeInTheDocument();
    
    // В режиме readOnly должен автоматически установиться режим 'hand' (через useEffect)
    // Но мы в первую очередь проверяем, что режим НЕ меняется на инструменты рисования
    fireEvent.keyDown(window, { key: 'p' });
    expect(useAnnotationStore.getState().mode).not.toBe('polygon');
  });
});
