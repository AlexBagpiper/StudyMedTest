import { describe, it, expect } from 'vitest'
import { fabric } from 'fabric'

describe('Polygon Nodes calculation', () => {
  it('should correctly calculate absolute positions of points and vice versa regardless of origin', () => {
    const points = [
      { x: 100, y: 100 },
      { x: 200, y: 100 },
      { x: 200, y: 200 },
      { x: 100, y: 200 }
    ]
    
    // Test with center origin
    const polyCenter = new fabric.Polygon(points, {
      originX: 'center',
      originY: 'center'
    })
    
    const mC = polyCenter.calcTransformMatrix()
    const invMC = fabric.util.invertTransform(mC)
    const offsetC = (polyCenter as any).pathOffset
    
    polyCenter.points?.forEach((p, index) => {
      const pAbs = fabric.util.transformPoint(new fabric.Point(p.x, p.y).subtract(offsetC), mC)
      expect(pAbs.x).toBeCloseTo(points[index].x)
      expect(pAbs.y).toBeCloseTo(points[index].y)

      const pLocal = fabric.util.transformPoint(pAbs, invMC).add(offsetC)
      expect(pLocal.x).toBeCloseTo(p.x)
      expect(pLocal.y).toBeCloseTo(p.y)
    })

    // Test with left/top origin
    const polyLeftTop = new fabric.Polygon(points, {
      originX: 'left',
      originY: 'top'
    })
    
    const mLT = polyLeftTop.calcTransformMatrix()
    const invMLT = fabric.util.invertTransform(mLT)
    const offsetLT = (polyLeftTop as any).pathOffset
    
    polyLeftTop.points?.forEach((p, index) => {
      const pAbs = fabric.util.transformPoint(new fabric.Point(p.x, p.y).subtract(offsetLT), mLT)
      expect(pAbs.x).toBeCloseTo(points[index].x)
      expect(pAbs.y).toBeCloseTo(points[index].y)

      const pLocal = fabric.util.transformPoint(pAbs, invMLT).add(offsetLT)
      expect(pLocal.x).toBeCloseTo(p.x)
      expect(pLocal.y).toBeCloseTo(p.y)
    })
  })
})
