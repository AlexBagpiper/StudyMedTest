import React, { useEffect, useRef, useState } from 'react'
import { fabric } from 'fabric'
import { 
  Box, Menu, MenuItem, ListItemText,
  Dialog, DialogTitle, List, ListItemButton, TextField, InputAdornment,
  ListItemIcon, Typography
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import UndoIcon from '@mui/icons-material/Undo'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import { useAnnotationStore } from './hooks/useAnnotationStore'
import { EditorMode } from '../../types/annotation'

import { MessageDialog } from '../common/MessageDialog'

/**
 * Factory function to create containsPoint for rectangles (stroke-only selection).
 * Extracted to avoid duplication across multiple places.
 */
const createRectContainsPoint = (fallbackZoom: number) => {
  return function(this: fabric.Rect, point: fabric.Point): boolean {
    const zoom = this.canvas?.getZoom() || fallbackZoom
    const vpt = this.canvas?.viewportTransform || [1, 0, 0, 1, 0, 0]
    const tolerance = Math.max(10 / zoom, 0.5)
    const rawCorners = [
      this.getPointByOrigin('left', 'top'),
      this.getPointByOrigin('right', 'top'),
      this.getPointByOrigin('right', 'bottom'),
      this.getPointByOrigin('left', 'bottom')
    ]
    const corners = rawCorners.map(c => fabric.util.transformPoint(c, vpt))
    for (let i = 0; i < 4; i++) {
      const p1 = corners[i], p2 = corners[(i + 1) % 4]
      const lenSq = Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2)
      if (lenSq === 0) continue
      const t = Math.max(0, Math.min(1, ((point.x - p1.x) * (p2.x - p1.x) + (point.y - p1.y) * (p2.y - p1.y)) / lenSq))
      const dist = Math.sqrt(Math.pow(point.x - (p1.x + t * (p2.x - p1.x)), 2) + Math.pow(point.y - (p1.y + t * (p2.y - p1.y)), 2))
      if (dist < tolerance) return true
    }
    return false
  }
}

interface FabricCanvasProps {
  imageUrl: string
  readOnly?: boolean
}

interface ExtendedCanvas extends fabric.Canvas {
  isDragging?: boolean
  lastPosX?: number
  lastPosY?: number
  upperCanvasEl: HTMLCanvasElement
  lowerCanvasEl: HTMLCanvasElement
}

export const FabricCanvas: React.FC<FabricCanvasProps> = ({ imageUrl, readOnly = false }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fabricCanvas = useRef<ExtendedCanvas | null>(null)
  const transformRef = useRef({ scale: 1, left: 0, top: 0 })
  const fabricImageRef = useRef<fabric.Image | null>(null)
  const lastSizeRef = useRef({ width: 0, height: 0 })
  const isUpdatingRef = useRef(false)
  const resetViewRef = useRef<() => void>()
  const loadAnnotationsRef = useRef<(canvas: ExtendedCanvas) => void>()
  const { 
    mode, setZoom, zoom, viewResetVersion, 
    addAnnotation, labels, annotations, updateAnnotation, deleteAnnotation, setSelectedAnnotationId,
    setMode
  } = useAnnotationStore()

  const annotationsRef = useRef(annotations); const labelsRef = useRef(labels);
  const modeRef = useRef<EditorMode>(mode); const zoomRef = useRef(zoom)

  useEffect(() => {
    annotationsRef.current = annotations; labelsRef.current = labels;
    modeRef.current = mode; zoomRef.current = zoom;
  }, [annotations, labels, mode, zoom])

  const polygonPointsRef = useRef<fabric.Point[]>([])
  const activeLineRef = useRef<fabric.Line | null>(null)
  const activeShapeRef = useRef<fabric.Object | null>(null)
  const editNodesRef = useRef<fabric.Object[]>([])
  const editNodesTargetIdRef = useRef<string | null>(null)
  const isDraggingNodeRef = useRef(false)
  const justSelectedIdRef = useRef<string | null>(null)
  const clearTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const [contextMenu, setContextMenu] = useState<{ mouseX: number; mouseY: number; type: 'drawing' | 'object'; targetId?: string; } | null>(null);
  const [hoveredInfo, setHoveredInfo] = useState<{ x: number; y: number; label: string; visible: boolean; id: string | null } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [labelPicker, setLabelPicker] = useState<{ open: boolean; type: 'polygon' | 'rectangle' | 'edit'; data?: any; annotationId?: string; } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Helper: convert HSL to RGBA for stable color interpolation
  const hslToRgba = (hslStr: string, alpha: number): string => {
    const match = hslStr.match(/hsl\(([^,]+),\s*([^%]+)%,\s*([^%]+)%\)/);
    if (!match) return `rgba(128,128,128,${alpha})`;
    const h = parseFloat(match[1]) / 360;
    const s = parseFloat(match[2]) / 100;
    const l = parseFloat(match[3]) / 100;
    
    let r, g, b;
    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p: number, q: number, t: number) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }
    return `rgba(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)},${alpha})`;
  };

  const getFillColor = (color: string) => {
    if (color.startsWith('hsl')) {
      return color.replace('hsl', 'hsla').replace(')', ', 0.27)')
    }
    return color + '44'
  }

  const handleLabelSelect = (labelId: string) => {
    if (!labelPicker || !fabricCanvas.current) return

    const { type, data, annotationId } = labelPicker
    const label = labels.find(l => l.id === labelId)
    
    if (label) {
      if (type === 'edit' && annotationId) {
        updateAnnotation(annotationId, { label_id: label.id })
        
        const canvas = fabricCanvas.current
        const obj = canvas.getObjects().find(o => (o as any).id === annotationId)
        if (obj) {
          obj.set({ fill: getFillColor(label.color), stroke: label.color })
          
          // Update edit nodes if they belong to this annotation
          if (editNodesTargetIdRef.current === annotationId) {
            editNodesRef.current.forEach(node => {
              node.set({ stroke: label.color })
            })
          }
          
          canvas.requestRenderAll()
        }
      } else if (data) {
        const id = addAnnotation({ ...data, label_id: label.id })
        
        const canvas = fabricCanvas.current
        if (type === 'polygon') {
          const polygon = new fabric.Polygon(polygonPointsRef.current, { 
            fill: getFillColor(label.color), stroke: label.color, strokeWidth: 1.75 / canvas.getZoom(), 
            selectable: !readOnly && modeRef.current === 'select', 
            hasControls: false, hasBorders: !readOnly, 
            lockMovementX: true, lockMovementY: true,
            lockRotation: true, lockScalingX: true, lockScalingY: true, 
            hoverCursor: 'default', originX: 'left', originY: 'top', 
            objectCaching: false, evented: !readOnly 
          })
          ;(polygon as any).id = id
          polygon.containsPoint = function(point: fabric.Point) {
            return findClosestSegment(this as fabric.Polygon, point) !== -1
          }
          canvas.add(polygon)
        } else if (type === 'rectangle') {
          const rect = activeShapeRef.current as fabric.Rect
          if (rect) {
            rect.set({ fill: getFillColor(label.color), stroke: label.color, strokeWidth: 1.75 / canvas.getZoom() })
            ;(rect as any).id = id
            rect.containsPoint = createRectContainsPoint(canvas.getZoom())
            if (modeRef.current === 'select') createEditNodes(canvas, rect)
          }
        }
        canvas.requestRenderAll()
      }
    }

    setLabelPicker(null)
    setSearchQuery('')
    if (type === 'polygon') {
      const canvas = fabricCanvas.current
      canvas.remove(...canvas.getObjects().filter(obj => (obj as any).id === 'temp-line' || (obj as any).id === 'temp-node'))
      polygonPointsRef.current = []; activeLineRef.current = null;
    } else if (type === 'rectangle') {
      activeShapeRef.current = null
    }
  }

  const clearEditNodes = (canvas: fabric.Canvas) => {
    if (editNodesRef.current.length > 0) {
      canvas.remove(...editNodesRef.current)
      editNodesRef.current = []
      editNodesTargetIdRef.current = null
      canvas.requestRenderAll()
    }
  }

  const createPolygonEditNodes = (canvas: fabric.Canvas, polygon: fabric.Polygon) => {
    if (!polygon.points) return
    const matrix = polygon.calcTransformMatrix()
    const color = (polygon.stroke as string) || '#ff0000'
    const currentZoom = canvas.getZoom()
    
    clearEditNodes(canvas)
    editNodesTargetIdRef.current = (polygon as any).id
    const nodes: fabric.Object[] = []
    
    polygon.points.forEach((p, index) => {
      const pAbs = fabric.util.transformPoint(
        new fabric.Point(p.x, p.y).subtract((polygon as any).pathOffset || { x: 0, y: 0 }),
        matrix
      )
      
      const circle = new fabric.Circle({
        left: pAbs.x, top: pAbs.y, radius: 3.5 / currentZoom, fill: 'white', stroke: color, strokeWidth: 1 / currentZoom,
        originX: 'center', originY: 'center', selectable: true, evented: true, hasControls: false, hasBorders: false,
        objectCaching: false
      })

      ;(circle as any).isNode = true; (circle as any).nodeIndex = index;

      circle.on('moving', () => {
        isDraggingNodeRef.current = true
        const invM = fabric.util.invertTransform(polygon.calcTransformMatrix())
        const pLocal = fabric.util.transformPoint(new fabric.Point(circle.left!, circle.top!), invM)
        polygon.points![index] = new fabric.Point(pLocal.x, pLocal.y).add((polygon as any).pathOffset || { x: 0, y: 0 })
        
        if ((polygon as any)._setPositionDimensions) {
          ;(polygon as any)._setPositionDimensions({})
        }
        
        polygon.setCoords()
        polygon.dirty = true
        canvas.requestRenderAll()
      })

      circle.on('mousedown', () => {
        isDraggingNodeRef.current = false
      })

      circle.on('mouseup', () => {
        if (isDraggingNodeRef.current) {
          const { scale, left, top } = transformRef.current
          const m = polygon.calcTransformMatrix()
          const pts = polygon.points!.flatMap(pt => {
            const abs = fabric.util.transformPoint(
              new fabric.Point(pt.x, pt.y).subtract((polygon as any).pathOffset || { x: 0, y: 0 }),
              m
            )
            return [(abs.x - left) / scale, (abs.y - top) / scale]
          })
          updateAnnotation((polygon as any).id, { points: pts })
        } else {
          if (polygon.points && polygon.points.length > 3) {
            polygon.points.splice(index, 1)
            if ((polygon as any)._setPositionDimensions) {
              ;(polygon as any)._setPositionDimensions({})
            }
            polygon.setCoords()
            polygon.dirty = true
            createPolygonEditNodes(canvas, polygon)
            
            const { scale, left, top } = transformRef.current
            const m = polygon.calcTransformMatrix()
            const pts = polygon.points.flatMap(pt => {
              const abs = fabric.util.transformPoint(
                new fabric.Point(pt.x, pt.y).subtract((polygon as any).pathOffset || { x: 0, y: 0 }),
                m
              )
              return [(abs.x - left) / scale, (abs.y - top) / scale]
            })
            updateAnnotation((polygon as any).id, { points: pts })
          }
        }
        isDraggingNodeRef.current = false
      })
      nodes.push(circle)
    })

    canvas.add(...nodes); nodes.forEach(n => n.bringToFront());
    editNodesRef.current = nodes; canvas.renderAll()
  }

  const createRectEditNodes = (canvas: fabric.Canvas, rect: fabric.Rect) => {
    const color = (rect.stroke as string) || '#ff0000'
    const currentZoom = canvas.getZoom()
    clearEditNodes(canvas)
    editNodesTargetIdRef.current = (rect as any).id
    const nodes: fabric.Object[] = []

    const getCorners = () => [
      rect.getPointByOrigin('left', 'top'),
      rect.getPointByOrigin('right', 'top'),
      rect.getPointByOrigin('right', 'bottom'),
      rect.getPointByOrigin('left', 'bottom')
    ]

    let fixedPoint: fabric.Point | null = null

    getCorners().forEach((pAbs, index) => {
      const circle = new fabric.Circle({
        left: pAbs.x, top: pAbs.y, radius: 3.5 / currentZoom, fill: 'white', stroke: color, strokeWidth: 1 / currentZoom,
        originX: 'center', originY: 'center', selectable: true, evented: true, hasControls: false, hasBorders: false,
        objectCaching: false
      })
      ;(circle as any).isNode = true; (circle as any).nodeIndex = index;

      circle.on('mousedown', () => { 
        isDraggingNodeRef.current = false
        const corners = getCorners()
        fixedPoint = corners[(index + 2) % 4]
      })

      circle.on('moving', () => {
        if (!fixedPoint) return
        isDraggingNodeRef.current = true
        let px = circle.left!, py = circle.top!
        
        // Clamping to prevent passing the fixed point
        if (index === 0) { // TL
          px = Math.min(px, fixedPoint.x - 1); py = Math.min(py, fixedPoint.y - 1)
        } else if (index === 1) { // TR
          px = Math.max(px, fixedPoint.x + 1); py = Math.min(py, fixedPoint.y - 1)
        } else if (index === 2) { // BR
          px = Math.max(px, fixedPoint.x + 1); py = Math.max(py, fixedPoint.y + 1)
        } else if (index === 3) { // BL
          px = Math.min(px, fixedPoint.x - 1); py = Math.max(py, fixedPoint.y + 1)
        }

        const newLeft = Math.min(px, fixedPoint.x)
        const newTop = Math.min(py, fixedPoint.y)
        const newWidth = Math.abs(px - fixedPoint.x)
        const newHeight = Math.abs(py - fixedPoint.y)

        rect.set({ 
          left: newLeft, 
          top: newTop, 
          width: newWidth, 
          height: newHeight,
          originX: 'left',
          originY: 'top',
          scaleX: 1,
          scaleY: 1
        })
        rect.setCoords()
        rect.dirty = true
        
        const newCorners = getCorners()
        nodes.forEach((node, i) => {
          if (i !== index) node.set({ left: newCorners[i].x, top: newCorners[i].y }).setCoords()
        })
        canvas.requestRenderAll()
      })

      circle.on('mouseup', () => {
        if (isDraggingNodeRef.current) {
          const { scale, left, top } = transformRef.current
          updateAnnotation((rect as any).id, { bbox: [(rect.left! - left) / scale, (rect.top! - top) / scale, rect.width! / scale, rect.height! / scale] })
        }
        isDraggingNodeRef.current = false
        fixedPoint = null
      })
      nodes.push(circle)
    })

    canvas.add(...nodes); nodes.forEach(n => n.bringToFront());
    editNodesRef.current = nodes; canvas.renderAll()
  }

  const createEditNodes = (canvas: fabric.Canvas, obj: fabric.Object) => {
    if (obj instanceof fabric.Polygon || (obj as any).type === 'polygon') createPolygonEditNodes(canvas, obj as fabric.Polygon)
    else if (obj instanceof fabric.Rect || (obj as any).type === 'rectangle') createRectEditNodes(canvas, obj as fabric.Rect)
  }

  const findClosestSegment = (polygon: fabric.Polygon, pointer: fabric.Point) => {
    if (!polygon.points) return -1
    const m = polygon.calcTransformMatrix()
    const vpt = polygon.canvas?.viewportTransform || [1, 0, 0, 1, 0, 0]
    // Combine object transform with viewport transform to get screen coordinates
    const fullMatrix = fabric.util.multiplyTransformMatrices(vpt, m)
    const zoom = polygon.canvas?.getZoom() || zoomRef.current || 1
    const tolerance = Math.max(10 / zoom, 0.5)
    
    const offset = (polygon as any).pathOffset || { x: 0, y: 0 }
    const points = polygon.points.map(p => fabric.util.transformPoint(
      new fabric.Point(p.x, p.y).subtract(offset), 
      fullMatrix
    ))
    let minDist = Infinity, segIdx = -1
    for (let i = 0; i < points.length; i++) {
      const p1 = points[i], p2 = points[(i + 1) % points.length]
      const lenSq = Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2)
      if (lenSq === 0) continue
      let t = Math.max(0, Math.min(1, ((pointer.x - p1.x) * (p2.x - p1.x) + (pointer.y - p1.y) * (p2.y - p1.y)) / lenSq))
      const dist = Math.sqrt(Math.pow(pointer.x - (p1.x + t * (p2.x - p1.x)), 2) + Math.pow(pointer.y - (p1.y + t * (p2.y - p1.y)), 2))
      if (dist < minDist && dist < tolerance) { minDist = dist; segIdx = i; }
    }
    return segIdx
  }

  const finishPolygon = (canvas: ExtendedCanvas) => {
    const points = polygonPointsRef.current
    if (points.length < 3) {
      canvas.remove(...canvas.getObjects().filter(obj => (obj as any).id === 'temp-line' || (obj as any).id === 'temp-node'))
      polygonPointsRef.current = []; activeLineRef.current = null; canvas.requestRenderAll(); return
    }
    const { scale, left, top } = transformRef.current
    
    // Show label picker instead of adding immediately
    setLabelPicker({
      open: true,
      type: 'polygon',
      data: {
        type: 'polygon',
        points: points.flatMap(p => [(p.x - left) / scale, (p.y - top) / scale])
      }
    })
  }

  const undoLastPolygonPoint = (canvas: fabric.Canvas) => {
    if (polygonPointsRef.current.length === 0) return

    // 1. Remove the active line (the one following the mouse)
    if (activeLineRef.current) {
      canvas.remove(activeLineRef.current)
      activeLineRef.current = null
    }

    // 2. Remove the last node
    const objects = canvas.getObjects()
    const tempNodes = objects.filter(obj => (obj as any).id === 'temp-node')
    const lastNode = tempNodes[tempNodes.length - 1]
    if (lastNode) canvas.remove(lastNode)

    // 3. Remove the last segment (the line between the last two points)
    const tempLines = objects.filter(obj => (obj as any).id === 'temp-line')
    const lastLine = tempLines[tempLines.length - 1]
    if (lastLine) canvas.remove(lastLine)

    // 4. Pop the point
    polygonPointsRef.current.pop()

    // 5. If there are still points, create a new active line starting from the NEW last point
    if (polygonPointsRef.current.length > 0) {
      const lastP = polygonPointsRef.current[polygonPointsRef.current.length - 1]
      const drawingColor = '#00ff00'
      const activeLine = new fabric.Line([lastP.x, lastP.y, lastP.x, lastP.y], { 
        stroke: drawingColor, strokeWidth: 1.75 / canvas.getZoom(), selectable: false, evented: false, id: 'temp-line' 
      } as any)
      canvas.add(activeLine)
      activeLineRef.current = activeLine

      // If we are back to the first point, ensure it's evented
      if (polygonPointsRef.current.length === 1) {
        const firstNode = canvas.getObjects().find(obj => (obj as any).isFirstNode)
        if (firstNode) firstNode.set({ evented: true })
      }
    }
    
    canvas.requestRenderAll()
  }

  useEffect(() => {
    if (!canvasRef.current) return
    let isMounted = true
    const canvas = new fabric.Canvas(canvasRef.current, { 
      selection: false, 
      defaultCursor: 'default', 
      fireRightClick: true, 
      stopContextMenu: true, 
      targetFindTolerance: 10, 
      preserveObjectStacking: true 
    }) as ExtendedCanvas
    fabricCanvas.current = canvas
    canvas.upperCanvasEl.oncontextmenu = (e: MouseEvent) => e.preventDefault();
    canvas.lowerCanvasEl.oncontextmenu = (e: MouseEvent) => e.preventDefault();

    const loadAnnotations = (c: ExtendedCanvas) => {
      if (!isMounted || !fabricCanvas.current || !(c as any).lowerCanvasEl) return
      c.remove(...c.getObjects().filter(obj => (obj as any).id))
      const { scale, left, top } = transformRef.current
      const currentZoom = c.getZoom()

      annotationsRef.current.forEach(ann => {
        const label = labelsRef.current.find(l => l.id === ann.label_id)
        if (!label) return
        let obj: fabric.Object | null = null

        if (ann.type === 'rectangle' && ann.bbox) {
          obj = new fabric.Rect({ 
            left: ann.bbox[0] * scale + left, top: ann.bbox[1] * scale + top, 
            width: ann.bbox[2] * scale, height: ann.bbox[3] * scale, 
            fill: getFillColor(label.color), stroke: label.color, 
            strokeWidth: 1.75 / currentZoom, objectCaching: false,
            lockMovementX: true, lockMovementY: true,
            lockRotation: true, lockScalingX: true, lockScalingY: true,
            originX: 'left', originY: 'top'
          })
          
          // Make rectangle selectable only by stroke
          obj.containsPoint = createRectContainsPoint(currentZoom)
        } else if (ann.type === 'polygon' && ann.points) {
          const fPoints = []
          for (let i = 0; i < ann.points.length; i += 2) fPoints.push({ x: ann.points[i] * scale + left, y: ann.points[i+1] * scale + top })
          obj = new fabric.Polygon(fPoints, { 
            fill: getFillColor(label.color), stroke: label.color, 
            strokeWidth: 1.75 / currentZoom, originX: 'left', originY: 'top', 
            objectCaching: false, lockMovementX: true, lockMovementY: true, 
            lockRotation: true, lockScalingX: true, lockScalingY: true
          })
          
          // Make selectable only by stroke
          obj.containsPoint = function(point: fabric.Point) {
            return findClosestSegment(this as fabric.Polygon, point) !== -1
          }
        }
        if (obj) {
          ;(obj as any).id = ann.id; 
          obj.selectable = !readOnly && modeRef.current === 'select'; 
          obj.hasControls = false; 
          obj.hasBorders = !readOnly; 
          obj.hoverCursor = 'default'; 
          obj.evented = true; 
          c.add(obj)
          obj.setCoords();
        }
      })
      c.requestRenderAll()
    }
    loadAnnotationsRef.current = loadAnnotations

    const resetView = () => {
      if (!containerRef.current || !fabricCanvas.current || !fabricImageRef.current) return
      const c = fabricCanvas.current, img = fabricImageRef.current, container = containerRef.current
      const cw = container.offsetWidth, ch = container.offsetHeight
      if (cw === 0 || ch === 0) return
      const s = Math.min(cw / (img.width || 1), ch / (img.height || 1))
      const l = (cw - (img.width || 0) * s) / 2, t = (ch - (img.height || 0) * s) / 2
      transformRef.current = { scale: s, left: l, top: t }; lastSizeRef.current = { width: cw, height: ch }
      c.setDimensions({ width: cw, height: ch }); c.setViewportTransform([1, 0, 0, 1, 0, 0])
      c.setBackgroundImage(img, c.renderAll.bind(c), { scaleX: s, scaleY: s, left: l, top: t })
      loadAnnotations(c); setZoom(1)
    }
    resetViewRef.current = resetView

    fabric.Image.fromURL(imageUrl, (img) => { if (!img || !isMounted || !fabricCanvas.current || !containerRef.current) return; fabricImageRef.current = img; resetView() }, { crossOrigin: 'anonymous' })
    const resizeObserver = new ResizeObserver(() => {
      if (!containerRef.current || !isMounted || !fabricCanvas.current || isUpdatingRef.current) return
      const cw = containerRef.current.offsetWidth, ch = containerRef.current.offsetHeight
      if (cw === 0 || ch === 0 || (Math.abs(lastSizeRef.current.width - cw) < 2 && Math.abs(lastSizeRef.current.height - ch) < 2)) return
      isUpdatingRef.current = true; resetView(); setTimeout(() => { isUpdatingRef.current = false }, 100)
    })
    if (containerRef.current) resizeObserver.observe(containerRef.current)

    canvas.on('mouse:wheel', (opt) => {
      const delta = opt.e.deltaY; let z = canvas.getZoom() * (0.999 ** delta)
      z = Math.max(0.01, Math.min(20, z))
      canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, z); setZoom(z); opt.e.preventDefault(); opt.e.stopPropagation()
    })

    canvas.on('mouse:over', (opt) => {
      const target = opt.target;
      if (target && (target as any).id && (target as any).id !== 'temp' && !(target as any).isNode) {
        const id = (target as any).id;
        const annotation = annotationsRef.current.find(a => a.id === id);
        const label = labelsRef.current.find(l => l.id === annotation?.label_id);
        
        if (label) {
          // Cancel any running animation for this target
          if ((target as any)._hoverAnimationId) {
            cancelAnimationFrame((target as any)._hoverAnimationId);
          }

          // Manual animation using requestAnimationFrame
          const startTime = performance.now();
          const duration = 250;
          
          const animateIn = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            const alpha = 0.27 + (0.5 - 0.27) * eased;
            target.set('fill', hslToRgba(label.color, alpha));
            canvas.renderAll();
            if (progress < 1) {
              (target as any)._hoverAnimationId = requestAnimationFrame(animateIn);
            }
          };
          
          target.set('fill', hslToRgba(label.color, 0.27));
          (target as any)._hoverAnimationId = requestAnimationFrame(animateIn);

          const e = opt.e as MouseEvent;
          setHoveredInfo({
            x: e.clientX,
            y: e.clientY,
            label: label.name,
            visible: true,
            id: id
          });
        }
      }
    });

    canvas.on('mouse:out', (opt) => {
      const target = opt.target;
      if (target && (target as any).id && (target as any).id !== 'temp' && !(target as any).isNode) {
        const id = (target as any).id;
        const annotation = annotationsRef.current.find(a => a.id === id);
        const label = labelsRef.current.find(l => l.id === annotation?.label_id);
        
        if (label) {
          // Cancel any running animation
          if ((target as any)._hoverAnimationId) {
            cancelAnimationFrame((target as any)._hoverAnimationId);
          }
          
          // Get current alpha from fill
          const currentFill = target.fill as string;
          const alphaMatch = currentFill?.match(/rgba?\([^)]+,\s*([0-9.]+)\)/);
          const currentAlpha = alphaMatch ? parseFloat(alphaMatch[1]) : 0.5;
          
          const startTime = performance.now();
          const duration = 200;
          
          const animateOut = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = progress * progress * progress; // easeInCubic
            const alpha = currentAlpha - (currentAlpha - 0.27) * eased;
            target.set('fill', hslToRgba(label.color, alpha));
            canvas.renderAll();
            if (progress < 1) {
              (target as any)._hoverAnimationId = requestAnimationFrame(animateOut);
            }
          };
          
          (target as any)._hoverAnimationId = requestAnimationFrame(animateOut);
        }
        setHoveredInfo(null);
      }
    });

    canvas.on('mouse:down', (opt) => {
      const evt = opt.e as MouseEvent, currentMode = modeRef.current
      if (opt.target && (opt.target as any).isNode) { canvas.setActiveObject(opt.target); return }

      if (currentMode === 'polygon' && polygonPointsRef.current.length === 0) {
        const target = opt.target || canvas.findTarget(evt, false);
        if (target && (target as any).id) {
          setMode('select');
          canvas.setActiveObject(target);
          return;
        }
      }
      if (currentMode === 'rectangle' && activeShapeRef.current === null) {
        const target = opt.target || canvas.findTarget(evt, false);
        if (target && (target as any).id) {
          setMode('select');
          canvas.setActiveObject(target);
          return;
        }
      }

      if (evt.button === 2 || (opt as any).button === 3 || (evt as any).which === 3) {
        evt.preventDefault(); evt.stopPropagation()
        if (!readOnly && currentMode === 'polygon' && polygonPointsRef.current.length > 0) setContextMenu({ mouseX: evt.clientX, mouseY: evt.clientY, type: 'drawing' })
        else if (!readOnly) { const target = opt.target || canvas.findTarget(evt, false); if (target && (target as any).id) setContextMenu({ mouseX: evt.clientX, mouseY: evt.clientY, type: 'object', targetId: (target as any).id }) }
        return
      }
      if (currentMode === 'hand' || (evt as any).altKey) { canvas.isDragging = true; canvas.selection = false; canvas.lastPosX = evt.clientX; canvas.lastPosY = evt.clientY; canvas.defaultCursor = 'grabbing'; canvas.requestRenderAll(); return }
      if (readOnly) return
      const pointer = canvas.getPointer(opt.e)
      if (currentMode === 'select') {
        const target = opt.target || canvas.findTarget(opt.e, false)
        if (target && (target instanceof fabric.Polygon || (target as any).type === 'polygon') && (target as any).id) {
          // If this object was JUST selected in this same mouse:down event, skip adding a point
          if (justSelectedIdRef.current === (target as any).id) {
            justSelectedIdRef.current = null;
            return;
          }
          
          // Transform pointer to screen coords for findClosestSegment (which now works in screen space)
          const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0]
          const screenPointer = fabric.util.transformPoint(new fabric.Point(pointer.x, pointer.y), vpt)
          const segIdx = findClosestSegment(target as fabric.Polygon, screenPointer as fabric.Point)
          // Only add point if the polygon is ALREADY selected and nodes for THIS polygon are already shown
          if (segIdx !== -1 && editNodesTargetIdRef.current === (target as any).id && canvas.getActiveObject() === target) {
            const invMatrix = fabric.util.invertTransform(target.calcTransformMatrix())
            const pLocal = fabric.util.transformPoint(new fabric.Point(pointer.x, pointer.y), invMatrix)
            ;(target as fabric.Polygon).points!.splice(segIdx + 1, 0, new fabric.Point(pLocal.x, pLocal.y).add((target as any).pathOffset || { x: 0, y: 0 }))
            if ((target as any)._setPositionDimensions) {
              ;(target as any)._setPositionDimensions({})
            }
            target.setCoords(); (target as any).dirty = true; createEditNodes(canvas, target)
            const { scale, left, top } = transformRef.current, matrix = target.calcTransformMatrix()
            const pts = (target as fabric.Polygon).points!.flatMap(p => {
              const abs = fabric.util.transformPoint(new fabric.Point(p.x, p.y).subtract((target as any).pathOffset || { x: 0, y: 0 }), matrix)
              return [(abs.x - left) / scale, (abs.y - top) / scale]
            })
            updateAnnotation((target as any).id, { points: pts }); return
          }
        }
      }
      const drawingColor = '#00ff00' // Green for drawing
      if (currentMode === 'rectangle') {
        const rect = new fabric.Rect({ left: pointer.x, top: pointer.y, width: 0, height: 0, fill: 'transparent', stroke: drawingColor, strokeWidth: 1.75 / canvas.getZoom(), id: 'temp', objectCaching: false } as any)
        canvas.add(rect); canvas.setActiveObject(rect); activeShapeRef.current = rect
      } else if (currentMode === 'polygon') {
        const isFirstPoint = polygonPointsRef.current.length === 0
        
        // If clicking on the first node and we have enough points, finish the polygon
        if (!isFirstPoint && opt.target && (opt.target as any).isFirstNode) {
          if (polygonPointsRef.current.length >= 3) {
            finishPolygon(canvas as ExtendedCanvas)
            return
          }
        }

        const circle = new fabric.Circle({ 
          radius: 4.2 / canvas.getZoom(), 
          fill: isFirstPoint ? '#ffffff' : drawingColor, 
          stroke: drawingColor,
          strokeWidth: 1.5 / canvas.getZoom(),
          left: pointer.x, 
          top: pointer.y, 
          originX: 'center', 
          originY: 'center', 
          selectable: false, 
          evented: isFirstPoint, // Only first point is evented to allow closure
          id: 'temp-node',
          isFirstNode: isFirstPoint
        } as any)

        if (isFirstPoint) {
          circle.on('mouseover', () => {
            if (polygonPointsRef.current.length >= 3) {
              circle.set({ radius: 5.6 / canvas.getZoom(), fill: '#00d2be' })
              canvas.requestRenderAll()
            }
          })
          circle.on('mouseout', () => {
            circle.set({ radius: 4.2 / canvas.getZoom(), fill: '#ffffff' })
            canvas.requestRenderAll()
          })
        }

        canvas.add(circle)
        polygonPointsRef.current = [...polygonPointsRef.current, new fabric.Point(pointer.x, pointer.y)]
        const line = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], { stroke: drawingColor, strokeWidth: 1.75 / canvas.getZoom(), selectable: false, evented: false, id: 'temp-line' } as any)
        canvas.add(line); activeLineRef.current = line
      }
    })

    canvas.on('mouse:move', (opt) => {
      if (canvas.isDragging) {
        const e = opt.e; const vpt = [...canvas.viewportTransform!]
        vpt[4] += e.clientX - canvas.lastPosX!; vpt[5] += e.clientY - canvas.lastPosY!
        canvas.setViewportTransform(vpt); canvas.lastPosX = e.clientX; canvas.lastPosY = e.clientY; return
      }
      const pointer = canvas.getPointer(opt.e), currentMode = modeRef.current
      
      // Handle tooltip position
      if (hoveredInfo?.visible) {
        setHoveredInfo(prev => prev ? { ...prev, x: (opt.e as MouseEvent).clientX, y: (opt.e as MouseEvent).clientY } : null);
      }

      if (currentMode === 'select' && !isDraggingNodeRef.current) {
        if (opt.target && (opt.target as any).isNode) { canvas.setCursor('pointer'); return }
        const target = canvas.findTarget(opt.e, false)
        if (target && (target instanceof fabric.Polygon || (target as any).type === 'polygon') && (target as any).id) {
          // Transform pointer to screen coords for findClosestSegment
          const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0]
          const screenPointer = fabric.util.transformPoint(new fabric.Point(pointer.x, pointer.y), vpt)
          if (findClosestSegment(target as fabric.Polygon, screenPointer as fabric.Point) !== -1 && editNodesRef.current.length > 0) { canvas.setCursor('copy'); return }
        }
        canvas.setCursor('default')
      }
      if (currentMode === 'polygon' && activeLineRef.current) { activeLineRef.current.set({ x2: pointer.x, y2: pointer.y }); canvas.requestRenderAll() }
      if (activeShapeRef.current && currentMode === 'rectangle') {
        const rect = activeShapeRef.current as fabric.Rect
        rect.set({ width: Math.abs(pointer.x - rect.left!), height: Math.abs(pointer.y - rect.top!), originX: pointer.x < rect.left! ? 'right' : 'left', originY: pointer.y < rect.top! ? 'bottom' : 'top' })
        canvas.requestRenderAll()
      }
    })

    canvas.on('mouse:up', () => {
      if (canvas.isDragging) { canvas.isDragging = false; canvas.selection = !readOnly && modeRef.current === 'select'; canvas.defaultCursor = modeRef.current === 'hand' ? 'grab' : 'default'; canvas.requestRenderAll(); return }
      if (activeShapeRef.current) {
        const { scale, left, top } = transformRef.current
        
        // Normalize rectangle coordinates if needed
        if (activeShapeRef.current instanceof fabric.Rect) {
          const rect = activeShapeRef.current;
          const topLeft = rect.getPointByOrigin('left', 'top');
          rect.set({
            left: topLeft.x,
            top: topLeft.y,
            originX: 'left',
            originY: 'top'
          });
          rect.setCoords();
        }

        activeShapeRef.current.set({ 
          selectable: !readOnly && modeRef.current === 'select', 
          hasControls: false, 
          hasBorders: !readOnly, 
          lockMovementX: true, 
          lockMovementY: true, 
          lockRotation: true, 
          lockScalingX: true, 
          lockScalingY: true, 
          hoverCursor: 'default',
          evented: !readOnly
        })

        // setLabelPicker instead of adding immediately for rectangle
        setLabelPicker({
          open: true,
          type: 'rectangle',
          data: {
            type: 'rectangle',
            bbox: [(activeShapeRef.current.left! - left) / scale, (activeShapeRef.current.top! - top) / scale, activeShapeRef.current.width! / scale, activeShapeRef.current.height! / scale]
          }
        })
        // Note: activeShapeRef.current is still set, handleLabelSelect will clear it
      }
    })

    canvas.on('selection:created', (e) => {
      if (e.target && e.target.type === 'activeSelection') {
        canvas.discardActiveObject();
        canvas.requestRenderAll();
        return;
      }
      const selected = canvas.getActiveObject()
      if (selected && (selected as any).isNode) return
      // Skip temp objects (being drawn) - they don't have proper dimensions yet
      const selectedId = (selected as any).id
      if (selected && selectedId && selectedId !== 'temp') {
        justSelectedIdRef.current = selectedId
        if (!readOnly) createEditNodes(canvas, selected)
        setSelectedAnnotationId(selectedId)
      }
    })

    canvas.on('selection:updated', (e) => {
      if (e.target && e.target.type === 'activeSelection') {
        canvas.discardActiveObject();
        canvas.requestRenderAll();
        return;
      }
      const selected = canvas.getActiveObject()
      if (selected && (selected as any).isNode) return
      // Skip temp objects (being drawn) - they don't have proper dimensions yet
      const selectedId = (selected as any).id
      if (selected && selectedId && selectedId !== 'temp') {
        justSelectedIdRef.current = selectedId
        if (!readOnly) createEditNodes(canvas, selected)
        setSelectedAnnotationId(selectedId)
      } else {
        clearEditNodes(canvas)
      }
    })

    canvas.on('selection:cleared', () => {
      // Clear any existing timeout to prevent race conditions
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current)
      }
      clearTimeoutRef.current = setTimeout(() => {
        if (canvas.getActiveObject() && (canvas.getActiveObject() as any).isNode) return
        clearEditNodes(canvas); setSelectedAnnotationId(null)
      }, 50)
    })

    return () => { 
      isMounted = false; 
      resizeObserver.disconnect(); 
      // Clear pending selection:cleared timeout to prevent memory leaks
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current)
        clearTimeoutRef.current = null
      }
      canvas.dispose(); 
      fabricCanvas.current = null; 
      fabricImageRef.current = null 
    }
  }, [imageUrl, readOnly])

  useEffect(() => { if (viewResetVersion > 0 && resetViewRef.current) resetViewRef.current() }, [viewResetVersion])
  useEffect(() => { 
    if (!fabricCanvas.current) return; 
    const c = fabricCanvas.current; 
    c.zoomToPoint(c.getVpCenter(), zoom); 
    
    // Update all objects strokeWidth AND their containsPoint logic
    c.getObjects().forEach(obj => { 
      const id = (obj as any).id || '';
      if ((obj as any).isNode || id === 'temp-node') {
        const drawingColor = '#00ff00'
        const baseRadius = (obj as any).isFirstNode ? 4.2 : 3.5
        ;(obj as any).set({ 
          radius: baseRadius / zoom, 
          strokeWidth: 1 / zoom,
          fill: (obj as any).isFirstNode ? '#ffffff' : (id === 'temp-node' ? drawingColor : (obj as any).fill)
        });
        obj.setCoords();
      } else if (id) {
        obj.set({ strokeWidth: 1.75 / zoom });
        
        // CRITICAL: Update containsPoint with new zoom for all annotation objects
        if (obj instanceof fabric.Rect || (obj as any).type === 'rectangle') {
          obj.containsPoint = createRectContainsPoint(zoom)
        } else if (obj instanceof fabric.Polygon || (obj as any).type === 'polygon') {
          obj.containsPoint = function(point: fabric.Point) {
            return findClosestSegment(this as fabric.Polygon, point) !== -1
          }
        }
        obj.setCoords();
      }
    });
    
    // Recreate edit nodes for active object to ensure correct positioning after zoom
    const activeObj = c.getActiveObject();
    if (activeObj && (activeObj as any).id && editNodesTargetIdRef.current === (activeObj as any).id) {
      createEditNodes(c, activeObj);
    }
    
    c.requestRenderAll() 
  }, [zoom])

  // Синхронизация аннотаций из хранилища для режима просмотра (review)
  useEffect(() => {
    if (readOnly && fabricCanvas.current && fabricImageRef.current) {
      loadAnnotationsRef.current?.(fabricCanvas.current)
    }
  }, [annotations, labels, readOnly])

  useEffect(() => { 
    if (!fabricCanvas.current) return; 
    const c = fabricCanvas.current; 
    c.selection = false; 
    c.defaultCursor = mode === 'hand' ? 'grab' : (mode === 'select' ? 'default' : 'crosshair'); 
    
    // Disable selection for all objects when not in select mode
    c.getObjects().forEach(obj => {
      if ((obj as any).id || (obj as any).isNode) {
        obj.selectable = !readOnly && (mode === 'select' || (obj as any).isNode);
        obj.evented = (obj as any).id ? true : !readOnly;
      }
    });

    if (mode !== 'select') { 
      c.discardActiveObject(); 
    } 

    // Cleanup temporary drawing objects when switching modes
    if (mode !== 'polygon') {
      const tempObjects = c.getObjects().filter(obj => 
        (obj as any).id === 'temp-line' || (obj as any).id === 'temp-node'
      );
      if (tempObjects.length > 0) {
        c.remove(...tempObjects);
        polygonPointsRef.current = [];
        activeLineRef.current = null;
      }
    }

    c.requestRenderAll();
  }, [mode, readOnly])

  return (
    <Box ref={containerRef} onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); }} sx={{ width: '100%', height: '100%', overflow: 'hidden', bgcolor: '#ffffff', position: 'relative', borderRadius: 1, border: '1px solid #e0e0e0' }}>
      <canvas ref={canvasRef} />
      <Menu 
        open={contextMenu !== null} 
        onClose={() => setContextMenu(null)} 
        anchorReference="anchorPosition" 
        anchorPosition={contextMenu !== null ? { top: contextMenu.mouseY, left: contextMenu.mouseX } : undefined} 
        sx={{ 
          zIndex: 5000,
          '& .MuiPaper-root': {
            borderRadius: '8px',
            minWidth: 180,
            boxShadow: '0px 4px 12px rgba(0,0,0,0.08)',
            border: '1px solid rgba(0,0,0,0.06)',
            mt: 0.5,
            py: 0.25
          }
        }}
      >
        {contextMenu?.type === 'drawing' ? [
          <MenuItem 
            key="finish" 
            onClick={() => { if (fabricCanvas.current) finishPolygon(fabricCanvas.current); setContextMenu(null); }}
            sx={{ py: 0.6, px: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: '32px !important' }}>
              <CheckCircleOutlineIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Замкнуть контур" primaryTypographyProps={{ variant: 'body2', fontSize: '0.8125rem', fontWeight: 500 }} />
          </MenuItem>,
          <MenuItem 
            key="undo" 
            onClick={() => { if (fabricCanvas.current) undoLastPolygonPoint(fabricCanvas.current); setContextMenu(null); }}
            sx={{ py: 0.6, px: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: '32px !important' }}>
              <UndoIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Отменить точку" primaryTypographyProps={{ variant: 'body2', fontSize: '0.8125rem', fontWeight: 500 }} />
          </MenuItem>,
          <MenuItem 
            key="delete" 
            onClick={() => { if (fabricCanvas.current) { const c = fabricCanvas.current; c.remove(...c.getObjects().filter(o => (o as any).id === 'temp-line' || (o as any).id === 'temp-node')); polygonPointsRef.current = []; activeLineRef.current = null; c.requestRenderAll(); } setContextMenu(null); }}
            sx={{ py: 0.6, px: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: '32px !important' }}>
              <DeleteOutlineIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Удалить контур" primaryTypographyProps={{ variant: 'body2', fontSize: '0.8125rem', fontWeight: 500 }} />
          </MenuItem>
        ] : [
          <MenuItem 
            key="edit-label" 
            onClick={() => {
              if (contextMenu?.targetId) {
                setLabelPicker({
                  open: true,
                  type: 'edit',
                  annotationId: contextMenu.targetId
                });
              }
              setContextMenu(null);
            }}
            sx={{ py: 0.6, px: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: '32px !important' }}>
              <EditOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Редактировать метку" primaryTypographyProps={{ variant: 'body2', fontSize: '0.8125rem', fontWeight: 500 }} />
          </MenuItem>,
          <MenuItem 
            key="delete-obj" 
            onClick={() => {
              if (contextMenu?.targetId && fabricCanvas.current) {
                const id = contextMenu.targetId;
                deleteAnnotation(id);
                setHoveredInfo(null);
                const obj = fabricCanvas.current.getObjects().find(o => (o as any).id === id);
                if (obj) {
                  fabricCanvas.current.remove(obj);
                  clearEditNodes(fabricCanvas.current);
                  fabricCanvas.current.requestRenderAll();
                }
              }
              setContextMenu(null);
            }}
            sx={{ py: 0.6, px: 1.5 }}
          >
            <ListItemIcon sx={{ minWidth: '32px !important' }}>
              <DeleteOutlineIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Удалить контур" primaryTypographyProps={{ variant: 'body2', fontSize: '0.8125rem', fontWeight: 500 }} />
          </MenuItem>
        ]}
      </Menu>

      <MessageDialog
        open={errorMessage !== null}
        title="Внимание"
        content={errorMessage || ''}
        severity="warning"
        onClose={() => setErrorMessage(null)}
      />

      <Dialog 
        open={labelPicker?.open || false} 
        onClose={() => {
          if (labelPicker?.type === 'polygon' && fabricCanvas.current) {
            const canvas = fabricCanvas.current
            canvas.remove(...canvas.getObjects().filter(obj => (obj as any).id === 'temp-line' || (obj as any).id === 'temp-node'))
            polygonPointsRef.current = []; activeLineRef.current = null;
          } else if (labelPicker?.type === 'rectangle') {
            if (activeShapeRef.current && fabricCanvas.current) fabricCanvas.current.remove(activeShapeRef.current)
            activeShapeRef.current = null
          }
          setLabelPicker(null)
          setSearchQuery('')
        }}
        maxWidth="xs"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: '10px',
            boxShadow: '0px 8px 32px rgba(0,0,0,0.12)',
            border: '1px solid rgba(0,0,0,0.05)'
          }
        }}
      >
        <DialogTitle sx={{ 
          pb: 1.5, 
          pt: 2, 
          px: 2, 
          fontSize: '0.95rem', 
          fontWeight: 600,
          color: 'text.primary'
        }}>
          Выберите метку для контура
        </DialogTitle>
        <Box sx={{ px: 2, pb: 1.5 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Поиск..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && searchQuery) {
                const filtered = labels.filter(l => l.name.toLowerCase().includes(searchQuery.toLowerCase()));
                if (filtered.length > 0) handleLabelSelect(filtered[0].id);
              }
            }}
            sx={{
              '& .MuiInputBase-root': {
                fontSize: '0.8125rem',
                borderRadius: '6px'
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
        </Box>
        <List sx={{ pt: 0, pb: 1, maxHeight: 350, overflow: 'auto' }}>
          {(() => {
            const currentAnnotation = labelPicker?.annotationId 
              ? annotations.find(a => a.id === labelPicker.annotationId) 
              : null;
            const currentLabelId = currentAnnotation?.label_id;

            return labels.filter(label => label.name.toLowerCase().includes(searchQuery.toLowerCase())).map((label) => (
              <ListItemButton 
                key={label.id} 
                onClick={() => handleLabelSelect(label.id)}
                selected={label.id === currentLabelId}
                sx={{ 
                  py: 0.75, 
                  px: 2,
                  mx: 1,
                  borderRadius: '6px',
                  '&.Mui-selected': {
                    bgcolor: 'primary.light',
                    '&:hover': { bgcolor: 'primary.light' }
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <FiberManualRecordIcon sx={{ color: label.color, fontSize: '0.75rem' }} />
                </ListItemIcon>
                <ListItemText 
                  primary={label.name} 
                  primaryTypographyProps={{ 
                    variant: 'body2', 
                    fontSize: '0.8125rem',
                    fontWeight: label.id === currentLabelId ? 600 : 500 
                  }} 
                />
              </ListItemButton>
            ));
          })()}
          {labels.length === 0 && (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8125rem' }}>
                Нет доступных категорий
              </Typography>
            </Box>
          )}
        </List>
      </Dialog>

      {/* Hover Tooltip */}
      <Box
        sx={{
          position: 'fixed',
          left: hoveredInfo?.x ? hoveredInfo.x + 15 : 0,
          top: hoveredInfo?.y ? hoveredInfo.y + 15 : 0,
          pointerEvents: 'none',
          bgcolor: 'rgba(255, 255, 255, 0.95)',
          color: 'text.primary',
          px: 1.2,
          py: 0.6,
          borderRadius: '6px',
          boxShadow: '0px 4px 12px rgba(0,0,0,0.15)',
          border: '1px solid rgba(0,0,0,0.08)',
          zIndex: 10000,
          fontSize: '0.75rem',
          fontWeight: 600,
          opacity: hoveredInfo?.visible ? 1 : 0,
          transform: hoveredInfo?.visible ? 'translateY(0)' : 'translateY(8px)',
          transition: 'opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          display: hoveredInfo ? 'flex' : 'none',
          alignItems: 'center',
          gap: 1,
          backdropFilter: 'blur(4px)'
        }}
      >
        <FiberManualRecordIcon 
          sx={{ 
            fontSize: '0.6rem', 
            color: labels.find(l => l.id === annotations.find(a => a.id === hoveredInfo?.id)?.label_id)?.color || 'primary.main' 
          }} 
        />
        {hoveredInfo?.label}
      </Box>
    </Box>
  )
}
