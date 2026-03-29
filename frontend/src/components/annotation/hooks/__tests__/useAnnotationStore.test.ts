import { renderHook, act } from '@testing-library/react';
import { useAnnotationStore } from '../useAnnotationStore';
import { vi } from 'vitest';

describe('useAnnotationStore', () => {
  beforeEach(() => {
    act(() => {
      useAnnotationStore.getState().reset();
    });
  });

  it('should add a label correctly', () => {
    const { result } = renderHook(() => useAnnotationStore());

    let labelId: string = '';
    act(() => {
      labelId = result.current.addLabel('Tumor', '#FF0000');
    });

    expect(result.current.labels).toHaveLength(1);
    expect(result.current.labels[0]).toEqual({
      id: labelId,
      name: 'Tumor',
      color: '#FF0000',
    });
    expect(result.current.activeLabelId).toBe(labelId);
  });

  it('should add and delete annotations', () => {
    const { result } = renderHook(() => useAnnotationStore());

    let annId: string = '';
    act(() => {
      annId = result.current.addAnnotation({
        label_id: 'label1',
        type: 'polygon',
        points: [0, 0, 10, 0, 10, 10],
      });
    });

    expect(result.current.annotations).toHaveLength(1);
    expect(result.current.annotations[0].id).toBe(annId);

    act(() => {
      result.current.deleteAnnotation(annId);
    });

    expect(result.current.annotations).toHaveLength(0);
  });

  it('should update zoom correctly', () => {
    const { result } = renderHook(() => useAnnotationStore());

    act(() => {
      result.current.setZoom(2.0);
    });
    expect(result.current.zoom).toBe(2.0);

    act(() => {
      result.current.zoomIn();
    });
    expect(result.current.zoom).toBeCloseTo(2.2);

    act(() => {
      result.current.resetZoom();
    });
    expect(result.current.zoom).toBe(1.0);
  });

  it('should handle setData', () => {
    const { result } = renderHook(() => useAnnotationStore());

    const testData = {
      labels: [{ id: 'l1', name: 'L1', color: 'red' }],
      annotations: [{ id: 'a1', label_id: 'l1', type: 'rect' as any, points: [1, 2, 3, 4] }],
    };

    act(() => {
      result.current.setData(testData);
    });

    expect(result.current.labels).toEqual(testData.labels);
    expect(result.current.annotations).toEqual(testData.annotations);
  });
});
