import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { LocaleProvider, useLocale } from '../LocaleContext';
import { vi } from 'vitest';

// Мокаем localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    clear: () => { store = {}; }
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('LocaleContext', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('should provide default locale (ru)', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <LocaleProvider>{children}</LocaleProvider>
    );
    const { result } = renderHook(() => useLocale(), { wrapper });

    expect(result.current.locale).toBe('ru');
  });

  it('should change locale and save to localStorage', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <LocaleProvider>{children}</LocaleProvider>
    );
    const { result } = renderHook(() => useLocale(), { wrapper });

    act(() => {
      result.current.setLocale('en');
    });

    expect(result.current.locale).toBe('en');
    expect(localStorageMock.getItem('app_locale')).toBe('en');
  });

  it('should translate keys correctly', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <LocaleProvider>{children}</LocaleProvider>
    );
    const { result } = renderHook(() => useLocale(), { wrapper });

    // Проверяем наличие базового перевода (предполагаем, что 'common.save' есть в словаре)
    const translation = result.current.t('common.save');
    expect(translation).toBeDefined();
    expect(typeof translation).toBe('string');
  });
});
