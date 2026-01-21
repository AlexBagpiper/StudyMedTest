import React, { useEffect, useRef, useState } from 'react'
import { fabric } from 'fabric'
import { Box, Menu, MenuItem, ListItemText } from '@mui/material'
import { useAnnotationStore } from './hooks/useAnnotationStore'
import { EditorMode } from '../../types/annotation'

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
    mode, setZoom, zoom, viewResetVersion, activeLabelId, 
    addAnnotation, labels, annotations, updateAnnotation, setSelectedAnnotationId,
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

  const [contextMenu, setContextMenu] = useState<{ mouseX: number; mouseY: number; type: 'drawing' | 'object'; targetId?: string; } | null>(null);

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
        left: pAbs.x, top: pAbs.y, radius: 5 / currentZoom, fill: 'white', stroke: color, strokeWidth: 1 / currentZoom,
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
        left: pAbs.x, top: pAbs.y, radius: 5 / currentZoom, fill: 'white', stroke: color, strokeWidth: 1 / currentZoom,
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
    const labelId = activeLabelId || labelsRef.current[0]?.id
    if (!labelId) return
    const color = labelsRef.current.find(l => l.id === labelId)?.color || '#ff0000'
    const currentZoom = canvas.getZoom()
    const id = addAnnotation({ label_id: labelId, type: 'polygon', points: points.flatMap(p => [(p.x - left) / scale, (p.y - top) / scale]) })
    const polygon = new fabric.Polygon(points, { 
      fill: color + '44', stroke: color, strokeWidth: 2.5 / currentZoom, 
      selectable: !readOnly && modeRef.current === 'select', 
      hasControls: false, hasBorders: !readOnly, 
      lockMovementX: true, lockMovementY: true,
      lockRotation: true, lockScalingX: true, lockScalingY: true, 
      hoverCursor: 'default', originX: 'left', originY: 'top', 
      objectCaching: false, evented: !readOnly 
    })
    ;(polygon as any).id = id
    
    // Make selectable only by stroke (keeping this to avoid accidental clicks inside)
    polygon.containsPoint = function(point: fabric.Point) {
      return findClosestSegment(this as fabric.Polygon, point) !== -1
    }
    
    canvas.remove(...canvas.getObjects().filter(obj => (obj as any).id === 'temp-line' || (obj as any).id === 'temp-node'))
    canvas.add(polygon); polygonPointsRef.current = []; activeLineRef.current = null; canvas.requestRenderAll()
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
            fill: label.color + '44', stroke: label.color, 
            strokeWidth: 2.5 / currentZoom, objectCaching: false,
            lockMovementX: true, lockMovementY: true,
            lockRotation: true, lockScalingX: true, lockScalingY: true,
            originX: 'left', originY: 'top'
          })
          
          // Make rectangle selectable only by stroke
          obj.containsPoint = function(point: fabric.Point) {
            const zoom = this.canvas?.getZoom() || currentZoom
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
              let t = Math.max(0, Math.min(1, ((point.x - p1.x) * (p2.x - p1.x) + (point.y - p1.y) * (p2.y - p1.y)) / lenSq))
              const dist = Math.sqrt(Math.pow(point.x - (p1.x + t * (p2.x - p1.x)), 2) + Math.pow(point.y - (p1.y + t * (p2.y - p1.y)), 2))
              if (dist < tolerance) return true
            }
            return false
          }
        } else if (ann.type === 'polygon' && ann.points) {
          const fPoints = []
          for (let i = 0; i < ann.points.length; i += 2) fPoints.push({ x: ann.points[i] * scale + left, y: ann.points[i+1] * scale + top })
          obj = new fabric.Polygon(fPoints, { 
            fill: label.color + '44', stroke: label.color, 
            strokeWidth: 2.5 / currentZoom, originX: 'left', originY: 'top', 
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
          obj.evented = !readOnly; 
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
        if (currentMode === 'polygon' && polygonPointsRef.current.length > 0) setContextMenu({ mouseX: evt.clientX, mouseY: evt.clientY, type: 'drawing' })
        else { const target = opt.target || canvas.findTarget(evt, false); if (target && (target as any).id) setContextMenu({ mouseX: evt.clientX, mouseY: evt.clientY, type: 'object', targetId: (target as any).id }) }
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
      const labelId = activeLabelId || labelsRef.current[0]?.id
      if ((currentMode as string) !== 'select' && (currentMode as string) !== 'hand' && !labelId) return
      const color = labelsRef.current.find(l => l.id === labelId)?.color || '#ff0000'
      if (currentMode === 'rectangle') {
        const rect = new fabric.Rect({ left: pointer.x, top: pointer.y, width: 0, height: 0, fill: color + '44', stroke: color, strokeWidth: 2.5 / canvas.getZoom(), id: 'temp', objectCaching: false } as any)
        canvas.add(rect); canvas.setActiveObject(rect); activeShapeRef.current = rect
      } else if (currentMode === 'polygon') {
        const circle = new fabric.Circle({ radius: 5 / canvas.getZoom(), fill: color, left: pointer.x, top: pointer.y, originX: 'center', originY: 'center', selectable: false, evented: false, id: 'temp-node' } as any)
        canvas.add(circle)
        polygonPointsRef.current = [...polygonPointsRef.current, new fabric.Point(pointer.x, pointer.y)]
        const line = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], { stroke: color, strokeWidth: 2.5 / canvas.getZoom(), selectable: false, evented: false, id: 'temp-line' } as any)
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

        const labelId = activeLabelId || labelsRef.current[0]?.id
        const id = addAnnotation({ label_id: labelId!, type: modeRef.current as any, bbox: modeRef.current === 'rectangle' ? [(activeShapeRef.current.left! - left) / scale, (activeShapeRef.current.top! - top) / scale, activeShapeRef.current.width! / scale, activeShapeRef.current.height! / scale] : undefined })
        ;(activeShapeRef.current as any).id = id

    // Make rectangle selectable only by stroke
    if (activeShapeRef.current instanceof fabric.Rect) {
      const currentZoom = canvas.getZoom()
      activeShapeRef.current.containsPoint = function(point: fabric.Point) {
        const zoom = this.canvas?.getZoom() || currentZoom
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
          let t = Math.max(0, Math.min(1, ((point.x - p1.x) * (p2.x - p1.x) + (point.y - p1.y) * (p2.y - p1.y)) / lenSq))
          const dist = Math.sqrt(Math.pow(point.x - (p1.x + t * (p2.x - p1.x)), 2) + Math.pow(point.y - (p1.y + t * (p2.y - p1.y)), 2))
          if (dist < tolerance) return true
        }
        return false
      }
      
      // If we are in select mode, show nodes immediately
      if (modeRef.current === 'select') {
        createEditNodes(canvas, activeShapeRef.current)
      }
    }
    
    activeShapeRef.current = null
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
      if (selected && (selected as any).id) {
        justSelectedIdRef.current = (selected as any).id
        createEditNodes(canvas, selected)
        setSelectedAnnotationId((selected as any).id)
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
      if (selected && (selected as any).id) {
        justSelectedIdRef.current = (selected as any).id
        createEditNodes(canvas, selected)
        setSelectedAnnotationId((selected as any).id)
      } else {
        clearEditNodes(canvas)
      }
    })

    canvas.on('selection:cleared', () => {
      setTimeout(() => {
        if (canvas.getActiveObject() && (canvas.getActiveObject() as any).isNode) return
        clearEditNodes(canvas); setSelectedAnnotationId(null)
      }, 50)
    })

    return () => { isMounted = false; resizeObserver.disconnect(); canvas.dispose(); fabricCanvas.current = null; fabricImageRef.current = null }
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
        ;(obj as any).set({ 
          radius: 5 / zoom, 
          strokeWidth: 1 / zoom 
        });
        obj.setCoords();
      } else if (id) {
        obj.set({ strokeWidth: 2.5 / zoom });
        
        // CRITICAL: Update containsPoint with new zoom for all annotation objects
        if (obj instanceof fabric.Rect || (obj as any).type === 'rectangle') {
          obj.containsPoint = function(point: fabric.Point) {
            const currentZoom = this.canvas?.getZoom() || zoom
            const vpt = this.canvas?.viewportTransform || [1, 0, 0, 1, 0, 0]
            const tolerance = Math.max(10 / currentZoom, 0.5)
            // Transform corners to screen coordinates (with viewportTransform)
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
              let t = Math.max(0, Math.min(1, ((point.x - p1.x) * (p2.x - p1.x) + (point.y - p1.y) * (p2.y - p1.y)) / lenSq))
              const dist = Math.sqrt(Math.pow(point.x - (p1.x + t * (p2.x - p1.x)), 2) + Math.pow(point.y - (p1.y + t * (p2.y - p1.y)), 2))
              if (dist < tolerance) return true
            }
            return false
          }
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
  useEffect(() => { 
    if (!fabricCanvas.current) return; 
    const c = fabricCanvas.current; 
    c.selection = false; 
    c.defaultCursor = mode === 'hand' ? 'grab' : (mode === 'select' ? 'default' : 'crosshair'); 
    
    // Disable selection for all objects when not in select mode
    c.getObjects().forEach(obj => {
      if ((obj as any).id || (obj as any).isNode) {
        obj.selectable = !readOnly && (mode === 'select' || (obj as any).isNode);
        obj.evented = !readOnly;
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
      <Menu open={contextMenu !== null} onClose={() => setContextMenu(null)} anchorReference="anchorPosition" anchorPosition={contextMenu !== null ? { top: contextMenu.mouseY, left: contextMenu.mouseX } : undefined} sx={{ zIndex: 5000 }}>
        {contextMenu?.type === 'drawing' ? [
          <MenuItem key="finish" onClick={() => { if (fabricCanvas.current) finishPolygon(fabricCanvas.current); setContextMenu(null); }}><ListItemText primary="Замкнуть контур" /></MenuItem>,
          <MenuItem key="delete" onClick={() => { if (fabricCanvas.current) { const c = fabricCanvas.current; c.remove(...c.getObjects().filter(o => (o as any).id === 'temp-line' || (o as any).id === 'temp-node')); polygonPointsRef.current = []; activeLineRef.current = null; c.requestRenderAll(); } setContextMenu(null); }}><ListItemText primary="Удалить контур" /></MenuItem>
        ] : <MenuItem onClick={() => setContextMenu(null)}><ListItemText primary={`Действия с объектом ${contextMenu?.targetId?.slice(0,8)}...`} /></MenuItem>}
      </Menu>
    </Box>
  )
}
