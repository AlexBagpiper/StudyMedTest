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
        student_coco: Dict[str, Any],
        reference_coco: Dict[str, Any],
        image_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Оценка аннотации студента
        
        Args:
            student_coco: COCO JSON аннотации студента
            reference_coco: Эталонные COCO аннотации
            image_id: ID изображения (опционально)
        
        Returns:
            {
                "iou_scores": List[float],
                "accuracy": float,
                "completeness": float,
                "precision": float,
                "total_score": float
            }
        """
        # Извлечение аннотаций
        student_annotations = student_coco.get("annotations", [])
        reference_annotations = reference_coco.get("annotations", [])
        
        if not reference_annotations:
            return {
                "iou_scores": [],
                "accuracy": 0,
                "completeness": 0,
                "precision": 0,
                "total_score": 0
            }
        
        # Конвертация в полигоны Shapely
        student_polygons = [
            self._coco_to_polygon(ann) for ann in student_annotations
        ]
        reference_polygons = [
            self._coco_to_polygon(ann) for ann in reference_annotations
        ]
        
        # Hungarian algorithm для matching полигонов
        matches = self._match_polygons(student_polygons, reference_polygons)
        
        # Расчёт IoU для каждой пары
        iou_scores = []
        for student_poly, ref_poly in matches:
            iou = self._calculate_iou(student_poly, ref_poly)
            iou_scores.append(iou)
        
        # Метрики
        accuracy = np.mean(iou_scores) if iou_scores else 0
        completeness = len(matches) / len(reference_polygons) if reference_polygons else 0
        
        # Precision: сколько из предсказанных правильные
        true_positives = sum(1 for iou in iou_scores if iou > 0.5)
        precision = true_positives / len(student_polygons) if student_polygons else 0
        
        # Взвешенный итоговый балл
        total_score = (
            accuracy * 0.5 +          # 50% - точность аннотаций
            completeness * 0.3 +      # 30% - полнота (все объекты найдены)
            precision * 0.2           # 20% - precision (нет лишних)
        ) * 100
        
        return {
            "iou_scores": [round(iou, 3) for iou in iou_scores],
            "accuracy": round(accuracy, 3),
            "completeness": round(completeness, 3),
            "precision": round(precision, 3),
            "total_score": round(total_score, 2)
        }
    
    def _coco_to_polygon(self, annotation: Dict[str, Any]) -> Optional[Polygon]:
        """
        Конвертация COCO segmentation в Shapely Polygon
        """
        try:
            segmentation = annotation.get("segmentation", [])
            if not segmentation:
                return None
            
            # COCO формат: [[x1, y1, x2, y2, ...]]
            points = segmentation[0] if isinstance(segmentation[0], list) else segmentation
            
            # Преобразование в список (x, y) пар
            coords = [(points[i], points[i+1]) for i in range(0, len(points), 2)]
            
            if len(coords) < 3:
                return None
            
            return Polygon(coords)
        
        except Exception as e:
            print(f"Error converting COCO to polygon: {e}")
            return None
    
    def _calculate_iou(self, poly1: Polygon, poly2: Polygon) -> float:
        """
        Intersection over Union между двумя полигонами
        """
        try:
            if not poly1 or not poly2:
                return 0.0
            
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
        (упрощённая версия Hungarian algorithm)
        
        Returns:
            List[(student_poly, ref_poly), ...]
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
    
    def validate_coco_format(self, coco_data: Dict[str, Any]) -> bool:
        """
        Валидация COCO формата
        """
        required_keys = ["images", "annotations", "categories"]
        
        if not all(key in coco_data for key in required_keys):
            return False
        
        # Проверка структуры аннотаций
        for ann in coco_data.get("annotations", []):
            if not all(key in ann for key in ["id", "image_id", "category_id", "segmentation"]):
                return False
        
        return True


# Singleton
cv_service = CVService()

