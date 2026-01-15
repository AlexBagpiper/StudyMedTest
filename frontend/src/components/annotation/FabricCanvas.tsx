import React, { useEffect, useRef, useState } from 'react'
import { fabric } from 'fabric'
import { Box } from '@mui/material'
import { useAnnotationStore } from './hooks/useAnnotationStore'

interface FabricCanvasProps {
  imageUrl: string
  readOnly?: boolean
}

// Расширяем типы fabric для кастомных свойств
interface ExtendedCanvas extends fabric.Canvas {
  isDragging?: boolean
  lastPosX?: number
  lastPosY?: number
}

export const FabricCanvas: React.FC<FabricCanvasProps> = ({ imageUrl, readOnly = false }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fabricCanvas = useRef<ExtendedCanvas | null>(null)
  const { 
    mode, 
    setZoom, 
    activeLabelId, 
    addAnnotation, 
    labels, 
    annotations,
    updateAnnotation,
    deleteAnnotation,
    setSelectedAnnotationId
  } = useAnnotationStore()

  const [polygonPoints, setPolygonPoints] = useState<fabric.Point[]>([])
  const [activeLine, setActiveLine] = useState<fabric.Line | null>(null)
  const [activeShape, setActiveShape] = useState<fabric.Object | null>(null)

  const finishPolygon = (canvas: ExtendedCanvas) => {
    if (polygonPoints.length < 3) return

    const color = labels.find(l => l.id === activeLabelId)?.color || '#ff0000'
    const id = addAnnotation({
      label_id: activeLabelId!,
      type: 'polygon',
      points: polygonPoints.flatMap(p => [p.x, p.y])
    })

    const polygon = new fabric.Polygon(polygonPoints, {
      fill: color + '44',
      stroke: color,
      strokeWidth: 2,
    })
    ;(polygon as any).id = id
    
    canvas.remove(...canvas.getObjects().filter(obj => (obj as any).id === 'temp-line'))
    canvas.add(polygon)
    
    setPolygonPoints([])
    setActiveLine(null)
    canvas.requestRenderAll()
  }

  useEffect(() => {
    if (!canvasRef.current) return

    const canvas = new fabric.Canvas(canvasRef.current, {
      width: 800,
      height: 600,
      selection: !readOnly,
      defaultCursor: 'default',
    }) as ExtendedCanvas

    fabricCanvas.current = canvas

    fabric.Image.fromURL(imageUrl, (img) => {
      if (!img) return
      
      const containerWidth = 800
      const containerHeight = 600
      const scale = Math.min(
        containerWidth / (img.width || 1),
        containerHeight / (img.height || 1)
      )
      
      canvas.setWidth(img.width! * scale)
      canvas.setHeight(img.height! * scale)
      
      canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
        scaleX: scale,
        scaleY: scale,
      })

      // Загрузка аннотаций после загрузки фона
      loadAnnotations(canvas)
    }, { crossOrigin: 'anonymous' })

    const loadAnnotations = (canvas: ExtendedCanvas) => {
      canvas.remove(...canvas.getObjects().filter(obj => (obj as any).id))
      annotations.forEach(ann => {
        const label = labels.find(l => l.id === ann.label_id)
        if (!label) return
        
        let obj: fabric.Object | null = null
        if (ann.type === 'rectangle' && ann.bbox) {
          obj = new fabric.Rect({
            left: ann.bbox[0],
            top: ann.bbox[1],
            width: ann.bbox[2],
            height: ann.bbox[3],
            fill: label.color + '44',
            stroke: label.color,
            strokeWidth: 2,
          })
        } else if (ann.type === 'ellipse' && ann.center && ann.radius) {
          obj = new fabric.Ellipse({
            left: ann.center[0] - ann.radius[0],
            top: ann.center[1] - ann.radius[1],
            rx: ann.radius[0],
            ry: ann.radius[1],
            fill: label.color + '44',
            stroke: label.color,
            strokeWidth: 2,
          })
        } else if (ann.type === 'point' && ann.center) {
          obj = new fabric.Circle({
            left: ann.center[0] - 4,
            top: ann.center[1] - 4,
            radius: 4,
            fill: label.color,
            stroke: '#fff',
            strokeWidth: 1,
          })
        } else if (ann.type === 'polygon' && ann.points) {
          const fPoints = []
          for (let i = 0; i < ann.points.length; i += 2) {
            fPoints.push({ x: ann.points[i], y: ann.points[i+1] })
          }
          obj = new fabric.Polygon(fPoints, {
            fill: label.color + '44',
            stroke: label.color,
            strokeWidth: 2,
          })
        }
        
        if (obj) {
          ;(obj as any).id = ann.id
          obj.selectable = !readOnly
          canvas.add(obj)
        }
      })
      canvas.requestRenderAll()
    }

    canvas.on('mouse:wheel', (opt) => {
      const delta = opt.e.deltaY
      let zoom = canvas.getZoom()
      zoom *= 0.999 ** delta
      if (zoom > 20) zoom = 20
      if (zoom < 0.01) zoom = 0.01
      canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom)
      setZoom(zoom)
      opt.e.preventDefault()
      opt.e.stopPropagation()
    })

    canvas.on('mouse:down', (opt) => {
      const evt = opt.e
      if (mode === 'hand' || (evt as any).altKey) {
        canvas.isDragging = true
        canvas.selection = false
        canvas.lastPosX = evt.clientX
        canvas.lastPosY = evt.clientY
        return
      }

      if (mode === 'eraser') {
        const target = canvas.findTarget(opt.e, false)
        if (target && (target as any).id) {
          deleteAnnotation((target as any).id)
          canvas.remove(target)
          canvas.requestRenderAll()
        }
        return
      }

      if (readOnly || !activeLabelId) return

      const pointer = canvas.getPointer(opt.e)
      const color = labels.find(l => l.id === activeLabelId)?.color || '#ff0000'

      if (mode === 'rectangle') {
        const rect = new fabric.Rect({
          left: pointer.x,
          top: pointer.y,
          width: 0,
          height: 0,
          fill: color + '44',
          stroke: color,
          strokeWidth: 2,
          id: 'temp'
        } as any)
        canvas.add(rect)
        canvas.setActiveObject(rect)
        setActiveShape(rect)
      } else if (mode === 'ellipse') {
        const ellipse = new fabric.Ellipse({
          left: pointer.x,
          top: pointer.y,
          rx: 0,
          ry: 0,
          fill: color + '44',
          stroke: color,
          strokeWidth: 2,
          id: 'temp'
        } as any)
        canvas.add(ellipse)
        canvas.setActiveObject(ellipse)
        setActiveShape(ellipse)
      } else if (mode === 'point') {
        const pObj = new fabric.Circle({
          left: pointer.x - 4,
          top: pointer.y - 4,
          radius: 4,
          fill: color,
          stroke: '#fff',
          strokeWidth: 1,
        })
        const id = addAnnotation({
          label_id: activeLabelId,
          type: 'point',
          center: [pointer.x, pointer.y]
        })
        ;(pObj as any).id = id
        canvas.add(pObj)
      } else if (mode === 'polygon') {
        if (polygonPoints.length > 2) {
          const first = polygonPoints[0]
          const d = Math.sqrt(Math.pow(pointer.x - first.x, 2) + Math.pow(pointer.y - first.y, 2))
          if (d < 10 / canvas.getZoom()) {
            finishPolygon(canvas)
            return
          }
        }
        setPolygonPoints(prev => {
          const nps = [...prev, new fabric.Point(pointer.x, pointer.y)]
          if (nps.length === 1) {
            const line = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], {
              stroke: color, strokeWidth: 2, selectable: false, evented: false, id: 'temp-line'
            } as any)
            canvas.add(line)
            setActiveLine(line)
          } else {
            const line = new fabric.Line([nps[nps.length-2].x, nps[nps.length-2].y, pointer.x, pointer.y], {
              stroke: color, strokeWidth: 2, selectable: false, evented: false, id: 'temp-line'
            } as any)
            canvas.add(line)
          }
          return nps
        })
      }
    })

    canvas.on('mouse:move', (opt) => {
      if (canvas.isDragging) {
        const e = opt.e
        const vpt = canvas.viewportTransform
        vpt![4] += e.clientX - canvas.lastPosX!
        vpt![5] += e.clientY - canvas.lastPosY!
        canvas.requestRenderAll()
        canvas.lastPosX = e.clientX
        canvas.lastPosY = e.clientY
        return
      }

      const pointer = canvas.getPointer(opt.e)
      if (mode === 'polygon' && activeLine) {
        activeLine.set({ x2: pointer.x, y2: pointer.y })
        canvas.requestRenderAll()
      }

      if (!activeShape) return
      if (mode === 'rectangle') {
        const rect = activeShape as fabric.Rect
        rect.set({ width: Math.abs(pointer.x - rect.left!), height: Math.abs(pointer.y - rect.top!) })
        rect.set({ originX: pointer.x < rect.left! ? 'right' : 'left', originY: pointer.y < rect.top! ? 'bottom' : 'top' })
      } else if (mode === 'ellipse') {
        const ell = activeShape as fabric.Ellipse
        ell.set({ rx: Math.abs(pointer.x - ell.left!) / 2, ry: Math.abs(pointer.y - ell.top!) / 2 })
      }
      canvas.requestRenderAll()
    })

    canvas.on('mouse:up', () => {
      if (canvas.isDragging) {
        canvas.setViewportTransform(canvas.viewportTransform!)
        canvas.isDragging = false
        canvas.selection = !readOnly && mode === 'select'
        return
      }
      if (activeShape) {
        const id = addAnnotation({
          label_id: activeLabelId!,
          type: mode as any,
          bbox: mode === 'rectangle' ? [activeShape.left!, activeShape.top!, activeShape.width!, activeShape.height!] : undefined,
          center: mode === 'ellipse' ? [activeShape.left! + activeShape.width!/2, activeShape.top! + activeShape.height!/2] : undefined,
          radius: mode === 'ellipse' ? [activeShape.width!/2, activeShape.height!/2] : undefined
        })
        ;(activeShape as any).id = id
        setActiveShape(null)
      }
    })

    canvas.on('object:modified', (opt) => {
      const obj = opt.target
      if (!obj || !(obj as any).id) return
      const id = (obj as any).id
      if (obj.type === 'rect') {
        updateAnnotation(id, { bbox: [obj.left!, obj.top!, obj.width! * obj.scaleX!, obj.height! * obj.scaleY!] })
      } else if (obj.type === 'ellipse') {
        const ell = obj as fabric.Ellipse
        updateAnnotation(id, {
          center: [ell.left! + (ell.width! * ell.scaleX!) / 2, ell.top! + (ell.height! * ell.scaleY!) / 2],
          radius: [(ell.width! * ell.scaleX!) / 2, (ell.height! * ell.scaleY!) / 2]
        })
      }
    })

    canvas.on('selection:created', (opt) => opt.selected?.[0] && setSelectedAnnotationId((opt.selected[0] as any).id))
    canvas.on('selection:cleared', () => setSelectedAnnotationId(null))

    return () => { canvas.dispose() }
  }, [imageUrl, readOnly])

  useEffect(() => {
    if (!fabricCanvas.current) return
    const canvas = fabricCanvas.current
    canvas.selection = !readOnly && mode === 'select'
    canvas.defaultCursor = mode === 'hand' ? 'grab' : 'default'
    if (mode !== 'select') {
      canvas.discardActiveObject()
      canvas.requestRenderAll()
    }
  }, [mode, readOnly])

  return (
    <Box sx={{ width: '100%', height: '600px', overflow: 'hidden', bgcolor: '#1a1a1a', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: 1, position: 'relative', border: '1px solid #333' }}>
      <canvas ref={canvasRef} />
    </Box>
  )
}
