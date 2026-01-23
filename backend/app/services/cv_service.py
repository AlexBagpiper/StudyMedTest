"""
Computer Vision Service - оценка аннотаций в формате COCO
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


class CVService:
    """
    Сервис для оценки графических аннотаций
    """
    
    def __init__(self):
        pass
    
    async def evaluate_annotation(
        self,
        student_data: Dict[str, Any],
        reference_data: Dict[str, Any],
        image_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Оценка аннотации студента
        
        Алгоритм IoU (Intersection over Union): Сравнение полигонов, нарисованных студентом, 
        с эталонными аннотациями в формате COCO.
        
        Метрики качества:
        - IoU (Accuracy): Точность попадания (50%)
        - Recall (Completeness): Полнота выделения всех объектов (30%)
        - Precision: Отсутствие лишних элементов (20%)
        """
        # Извлечение аннотаций студента
        student_annotations = student_data.get("annotations", [])
        
        # Извлечение аннотаций эталона (COCO формат)
        reference_annotations = reference_data.get("annotations", [])
        
        if not reference_annotations:
            return {
                "iou": 0,
                "recall": 0,
                "precision": 0,
                "total_score": 0,
                "iou_scores": []
            }
        
        # Конвертация эталона в полигоны
        ref_polys = []
        for ann in reference_annotations:
            poly = self._coco_to_polygon(ann)
            if poly and poly.is_valid:
                ref_polys.append(poly)
        
        # Конвертация ответов студента в полигоны
        stud_polys = []
        for ann in student_annotations:
            poly = self._custom_to_polygon(ann)
            if poly and poly.is_valid:
                stud_polys.append(poly)
        
        if not stud_polys:
            return {
                "iou": 0,
                "recall": 0,
                "precision": 0,
                "total_score": 0,
                "iou_scores": []
            }
            
        # Матчинг полигонов
        matches = self._match_polygons(stud_polys, ref_polys)
        
        all_iou_scores = []
        for s_poly, r_poly in matches:
            iou = self._calculate_iou(s_poly, r_poly)
            all_iou_scores.append(iou)
        
        # Расчет метрик
        # 1. Точность попадания (IoU) - средний IoU для найденных объектов
        avg_iou = np.mean(all_iou_scores) if all_iou_scores else 0
        
        # 2. Полнота (Recall) - доля найденных эталонных объектов (IoU > 0.5)
        true_positives = sum(1 for iou in all_iou_scores if iou >= 0.5)
        recall = true_positives / len(ref_polys) if ref_polys else 0
        
        # 3. Прецизионность (Precision) - отсутствие лишних элементов
        # Доля правильных объектов среди всех нарисованных студентом
        precision = true_positives / len(stud_polys) if stud_polys else 0
        
        # Итоговый взвешенный балл: 50% IoU + 30% Recall + 20% Precision
        total_score = (
            avg_iou * 0.5 + 
            recall * 0.3 + 
            precision * 0.2
        ) * 100
        
        return {
            "iou": round(avg_iou, 3),
            "recall": round(recall, 3),
            "precision": round(precision, 3),
            "total_score": round(total_score, 2),
            "iou_scores": [round(iou, 3) for iou in all_iou_scores]
        }
    
    def _coco_to_polygon(self, ann: Dict[str, Any]) -> Optional[Polygon]:
        """
        Конвертация COCO аннотации в Shapely Polygon
        """
        try:
            segmentation = ann.get("segmentation")
            if segmentation:
                if isinstance(segmentation, list) and len(segmentation) > 0:
                    pts = segmentation[0]
                    if len(pts) >= 6: # Минимум 3 точки
                        coords = [(pts[i], pts[i+1]) for i in range(0, len(pts), 2)]
                        return Polygon(coords)
            
            # Fallback to bbox
            bbox = ann.get("bbox")
            if bbox and len(bbox) == 4:
                x, y, w, h = bbox
                return Polygon([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])
                
            return None
        except Exception as e:
            print(f"Error converting COCO to polygon: {e}")
            return None

    def _custom_to_polygon(self, annotation: Dict[str, Any]) -> Optional[Polygon]:
        """
        Конвертация кастомной аннотации в Shapely Polygon
        """
        try:
            ann_type = annotation.get("type")
            
            if ann_type == 'polygon' and "points" in annotation:
                points = annotation["points"]
                if len(points) >= 6:
                    coords = [(points[i], points[i+1]) for i in range(0, len(points), 2)]
                    return Polygon(coords)
                
            elif ann_type == 'rectangle' and "bbox" in annotation:
                x, y, w, h = annotation["bbox"]
                return Polygon([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])
                
            elif ann_type == 'ellipse' and "center" in annotation and "radius" in annotation:
                cx, cy = annotation["center"]
                rx, ry = annotation["radius"]
                t = np.linspace(0, 2*np.pi, 32)
                coords = [(cx + rx*np.cos(ti), cy + ry*np.sin(ti)) for ti in t]
                return Polygon(coords)
                
            return None
        except Exception as e:
            print(f"Error converting custom annotation to polygon: {e}")
            return None
    
    def _calculate_iou(self, poly1: Polygon, poly2: Polygon) -> float:
        """
        Intersection over Union между двумя полигонами
        """
        try:
            if not poly1 or not poly2:
                return 0.0
            
            if not poly1.is_valid:
                poly1 = poly1.buffer(0)
            if not poly2.is_valid:
                poly2 = poly2.buffer(0)
            
            if not poly1.is_valid or not poly2.is_valid:
                return 0.0
            
            intersection = poly1.intersection(poly2).area
            union = poly1.union(poly2).area
            
            return intersection / union if union > 0 else 0.0
        
        except Exception as e:
            print(f"Error calculating IoU: {e}")
            return 0.0
    
    def _match_polygons(
        self,
        student_polygons: List[Polygon],
        reference_polygons: List[Polygon]
    ) -> List[tuple]:
        """
        Matching полигонов используя жадный алгоритм
        """
        matches = []
        used_reference = set()
        
        # Для каждого полигона студента находим лучший match
        for student_poly in student_polygons:
            if not student_poly:
                continue
            
            best_iou = 0
            best_ref_idx = None
            
            for ref_idx, ref_poly in enumerate(reference_polygons):
                if ref_idx in used_reference or not ref_poly:
                    continue
                
                iou = self._calculate_iou(student_poly, ref_poly)
                if iou > best_iou:
                    best_iou = iou
                    best_ref_idx = ref_idx
            
            # Добавляем match если IoU > 0
            if best_ref_idx is not None and best_iou > 0:
                matches.append((student_poly, reference_polygons[best_ref_idx]))
                used_reference.add(best_ref_idx)
        
        return matches


# Singleton
cv_service = CVService()
