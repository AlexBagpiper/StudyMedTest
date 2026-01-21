import { create } from 'zustand'
import { 
  Annotation, 
  AnnotationLabel, 
  AnnotationData, 
  EditorMode 
} from '../../../types/annotation'
import { v4 as uuidv4 } from 'uuid'

interface AnnotationState {
  // Данные
  labels: AnnotationLabel[]
  annotations: Annotation[]
  
  // Состояние редактора
  mode: EditorMode
  activeLabelId: string | null
  selectedAnnotationId: string | null
  zoom: number
  viewResetVersion: number
  
  // Действия с метками
  addLabel: (name: string, color: string) => void
  updateLabel: (id: string, name: string, color: string) => void
  deleteLabel: (id: string) => void
  setActiveLabelId: (id: string | null) => void
  
  // Действия с аннотациями
  addAnnotation: (annotation: Omit<Annotation, 'id'>) => string
  updateAnnotation: (id: string, updates: Partial<Annotation>) => void
  deleteAnnotation: (id: string) => void
  setSelectedAnnotationId: (id: string | null) => void
  
  // Общие действия
  setMode: (mode: EditorMode) => void
  setZoom: (zoom: number) => void
  zoomIn: () => void
  zoomOut: () => void
  resetZoom: () => void
  setData: (data: AnnotationData) => void
  reset: () => void
}

export const useAnnotationStore = create<AnnotationState>((set) => ({
  labels: [],
  annotations: [],
  mode: 'select',
  activeLabelId: null,
  selectedAnnotationId: null,
  zoom: 1,
  viewResetVersion: 0,

  addLabel: (name, color) => set((state) => {
    const newLabel = { id: uuidv4(), name, color }
    return { 
      labels: [...state.labels, newLabel],
      activeLabelId: state.activeLabelId || newLabel.id
    }
  }),

  updateLabel: (id, name, color) => set((state) => ({
    labels: state.labels.map(l => l.id === id ? { ...l, name, color } : l)
  })),

  deleteLabel: (id) => set((state) => ({
    labels: state.labels.filter(l => l.id !== id),
    annotations: state.annotations.filter(a => a.label_id !== id),
    activeLabelId: state.activeLabelId === id ? null : state.activeLabelId
  })),

  setActiveLabelId: (id) => set({ activeLabelId: id }),

  addAnnotation: (annotation) => {
    const id = uuidv4()
    set((state) => ({
      annotations: [...state.annotations, { ...annotation, id }]
    }))
    return id
  },

  updateAnnotation: (id, updates) => set((state) => ({
    annotations: state.annotations.map(a => a.id === id ? { ...a, ...updates } : a)
  })),

  deleteAnnotation: (id) => set((state) => ({
    annotations: state.annotations.filter(a => a.id !== id),
    selectedAnnotationId: state.selectedAnnotationId === id ? null : state.selectedAnnotationId
  })),

  setSelectedAnnotationId: (id) => set({ selectedAnnotationId: id }),

  setMode: (mode) => set({ mode }),
  setZoom: (zoom) => set({ zoom }),
  zoomIn: () => set((state) => ({ zoom: Math.min(state.zoom * 1.1, 20) })),
  zoomOut: () => set((state) => ({ zoom: Math.max(state.zoom / 1.1, 0.01) })),
  resetZoom: () => set((state) => ({ zoom: 1, viewResetVersion: state.viewResetVersion + 1 })),
  setData: (data) => set({ 
    labels: (data.labels || []).map((label, i) => {
      // Гарантируем уникальные и различимые цвета для каждой категории
      const hue = (i * 137.508) % 360
      return {
        ...label,
        color: `hsl(${hue}, 75%, 45%)` // Используем HSL для гарантии различимости
      }
    }), 
    annotations: data.annotations || [] 
  }),
  reset: () => set({
    labels: [],
    annotations: [],
    mode: 'select',
    activeLabelId: null,
    selectedAnnotationId: null,
    zoom: 1,
    viewResetVersion: 0
  })
}))
