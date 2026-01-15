export type AnnotationType = 'polygon' | 'rectangle' | 'ellipse' | 'point'

export interface AnnotationLabel {
  id: string
  name: string
  color: string
}

export interface Annotation {
  id: string
  label_id: string
  type: AnnotationType
  points?: number[] // [x1, y1, x2, y2, ...]
  bbox?: [number, number, number, number] // [x, y, w, h]
  center?: [number, number] // [cx, cy]
  radius?: [number, number] // [rx, ry]
}

export interface AnnotationData {
  labels: AnnotationLabel[]
  annotations: Annotation[]
}

export type EditorMode = 'select' | 'hand' | 'polygon' | 'rectangle' | 'ellipse' | 'point' | 'eraser'
