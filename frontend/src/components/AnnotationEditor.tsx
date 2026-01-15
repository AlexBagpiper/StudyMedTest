import { useEffect, useRef, useState } from 'react'
import { Box, Button, ButtonGroup, Typography, Paper } from '@mui/material'
import { fabric } from 'fabric'

interface AnnotationEditorProps {
  imageUrl: string
  initialAnnotations?: any
  onSave?: (annotations: any) => void
  readOnly?: boolean
}

export default function AnnotationEditor({
  imageUrl,
  initialAnnotations,
  onSave,
  readOnly = false,
}: AnnotationEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [canvas, setCanvas] = useState<fabric.Canvas | null>(null)
  const [tool, setTool] = useState<'select' | 'polygon' | 'freehand'>('select')
  const [points, setPoints] = useState<{ x: number; y: number }[]>([])

  useEffect(() => {
    if (!canvasRef.current) return

    // Инициализация Fabric.js canvas
    const fabricCanvas = new fabric.Canvas(canvasRef.current, {
      width: 800,
      height: 600,
      selection: !readOnly,
    })

    setCanvas(fabricCanvas)

    // Загрузка изображения
    fabric.Image.fromURL(imageUrl, (img) => {
      // Масштабирование изображения под canvas
      const scale = Math.min(
        fabricCanvas.width! / img.width!,
        fabricCanvas.height! / img.height!
      )
      img.scale(scale)
      fabricCanvas.setBackgroundImage(img, fabricCanvas.renderAll.bind(fabricCanvas))
    }, { crossOrigin: 'anonymous' })

    // Загрузка существующих аннотаций
    if (initialAnnotations) {
      loadAnnotations(fabricCanvas, initialAnnotations)
    }

    return () => {
      fabricCanvas.dispose()
    }
  }, [imageUrl])

  const loadAnnotations = (canvas: fabric.Canvas, annotations: any) => {
    // TODO: Импорт COCO аннотаций в Fabric.js
    // Преобразование COCO segmentation в Fabric Polygon
    if (annotations.annotations) {
      annotations.annotations.forEach((ann: any) => {
        const segmentation = ann.segmentation[0]
        const points = []
        for (let i = 0; i < segmentation.length; i += 2) {
          points.push({ x: segmentation[i], y: segmentation[i + 1] })
        }
        
        const polygon = new fabric.Polygon(points, {
          fill: 'rgba(59, 130, 246, 0.3)',
          stroke: '#3B82F6',
          strokeWidth: 2,
          selectable: !readOnly,
        })
        canvas.add(polygon)
      })
    }
  }

  const handlePolygonTool = () => {
    if (!canvas || readOnly) return
    setTool('polygon')
    setPoints([])
    
    canvas.on('mouse:down', (e) => {
      if (tool !== 'polygon') return
      
      const pointer = canvas.getPointer(e.e)
      const newPoints = [...points, { x: pointer.x, y: pointer.y }]
      setPoints(newPoints)
      
      // Визуализация точек
      const circle = new fabric.Circle({
        left: pointer.x,
        top: pointer.y,
        radius: 3,
        fill: '#3B82F6',
        originX: 'center',
        originY: 'center',
        selectable: false,
      })
      canvas.add(circle)
    })
  }

  const finishPolygon = () => {
    if (!canvas || points.length < 3) return
    
    const polygon = new fabric.Polygon(points, {
      fill: 'rgba(59, 130, 246, 0.3)',
      stroke: '#3B82F6',
      strokeWidth: 2,
      selectable: true,
    })
    
    canvas.add(polygon)
    
    // Очистка временных точек
    canvas.getObjects('circle').forEach((obj) => {
      if (!obj.selectable) canvas.remove(obj)
    })
    
    setPoints([])
    setTool('select')
  }

  const handleClear = () => {
    if (!canvas || readOnly) return
    canvas.getObjects().forEach((obj) => {
      if (obj.type !== 'image') {
        canvas.remove(obj)
      }
    })
    canvas.renderAll()
  }

  const handleExportCOCO = () => {
    if (!canvas) return
    
    const annotations: any[] = []
    let annotationId = 1
    
    canvas.getObjects('polygon').forEach((obj: any) => {
      const points = obj.points
      const segmentation: number[] = []
      
      points.forEach((point: any) => {
        segmentation.push(point.x, point.y)
      })
      
      annotations.push({
        id: annotationId++,
        image_id: 1,
        category_id: 1,
        segmentation: [segmentation],
        area: calculatePolygonArea(points),
        bbox: calculateBoundingBox(points),
      })
    })
    
    const cocoData = {
      images: [{ id: 1, file_name: 'image.jpg', width: 800, height: 600 }],
      annotations,
      categories: [{ id: 1, name: 'annotation', supercategory: 'medical' }],
    }
    
    if (onSave) {
      onSave(cocoData)
    }
    
    return cocoData
  }

  const calculatePolygonArea = (points: any[]) => {
    let area = 0
    for (let i = 0; i < points.length; i++) {
      const j = (i + 1) % points.length
      area += points[i].x * points[j].y
      area -= points[j].x * points[i].y
    }
    return Math.abs(area / 2)
  }

  const calculateBoundingBox = (points: any[]) => {
    const xs = points.map((p) => p.x)
    const ys = points.map((p) => p.y)
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)
    return [minX, minY, maxX - minX, maxY - minY]
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">Редактор аннотаций</Typography>
        {!readOnly && (
          <ButtonGroup>
            <Button
              variant={tool === 'select' ? 'contained' : 'outlined'}
              onClick={() => setTool('select')}
            >
              Выбор
            </Button>
            <Button
              variant={tool === 'polygon' ? 'contained' : 'outlined'}
              onClick={handlePolygonTool}
            >
              Полигон
            </Button>
            {points.length > 2 && (
              <Button variant="contained" color="success" onClick={finishPolygon}>
                Завершить
              </Button>
            )}
            <Button variant="outlined" color="error" onClick={handleClear}>
              Очистить
            </Button>
            <Button variant="contained" onClick={handleExportCOCO}>
              Сохранить
            </Button>
          </ButtonGroup>
        )}
      </Box>
      
      <Box sx={{ border: '1px solid #ccc', borderRadius: 1 }}>
        <canvas ref={canvasRef} />
      </Box>
      
      {!readOnly && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Выберите инструмент "Полигон" и кликайте на изображении для создания контура.
          Нажмите "Завершить" когда закончите.
        </Typography>
      )}
    </Paper>
  )
}

