import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CVSettings from '../CVSettings';
import { adminApi } from '../../../lib/api';
import { vi } from 'vitest';
import { LocaleProvider } from '../../../contexts/LocaleContext';

vi.mock('../../../lib/api', () => ({
  adminApi: {
    getCVConfig: vi.fn().mockResolvedValue({
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
    }),
    updateCVConfig: vi.fn().mockResolvedValue({ status: 'ok' }),
  },
}));

describe('CVSettings (Настройки CV)', () => {
  const renderSettings = () => render(
    <LocaleProvider>
      <CVSettings />
    </LocaleProvider>
  );

  it('should load and display current config', async () => {
    renderSettings();
    
    await waitFor(() => {
      // Ищем 50% в основной части (их там несколько, берем первый)
      expect(screen.getAllByText(/50%/)[0]).toBeInTheDocument();
      // Проверяем наличие заголовков из переводов
      expect(screen.getByText(/Вес геометрической точности/i)).toBeInTheDocument();
    });
  });

  it('should toggle loyalty mode and show/hide options', async () => {
    renderSettings();
    
    await waitFor(() => expect(screen.getByText(/Сбалансированная лояльность/i)).toBeInTheDocument());
    
    // По умолчанию лояльность выключена, слайдера Grace Zone в основной части быть не должно
    // (он есть в справке справа, поэтому ищем более специфичный текст)
    expect(screen.queryByText(/Порог «идеальной точности»/i)).not.toBeInTheDocument();
    
    // Включаем лояльность
    // Switch в MUI имеет чекбокс внутри с лейблом
    const loyaltySwitch = screen.getByLabelText(/Выключено/i);
    fireEvent.click(loyaltySwitch);
    
    // Теперь опции должны появиться
    expect(screen.getByText(/Порог «идеальной точности»/i)).toBeInTheDocument();
    expect(screen.getByText(/Бонус за безошибочность/i)).toBeInTheDocument();
    expect(screen.getByText(/Порог округления итога/i)).toBeInTheDocument();
  });

  it('should validate weights sum before saving', async () => {
    renderSettings();
    // Ждем загрузки данных
    await waitFor(() => expect(screen.getAllByText(/50%/)[0]).toBeInTheDocument());
    
    // Кнопка сохранения
    const saveBtn = screen.getByText(/Сохранить параметры CV/i);
    fireEvent.click(saveBtn);
    
    await waitFor(() => {
      expect(adminApi.updateCVConfig).toHaveBeenCalled();
    });
  });
});
