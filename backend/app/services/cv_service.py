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
        Оценка аннотации студента в кастомном формате
        """
        # Извлечение аннотаций
        student_annotations = student_data.get("annotations", [])
        reference_annotations = reference_data.get("annotations", [])
        
        if not reference_annotations:
            return {
                "iou_scores": [],
                "accuracy": 0,
                "completeness": 0,
                "precision": 0,
                "total_score": 0
            }
        
        # Группировка по label_id для корректного сравнения одинаковых структур
        ref_by_label = {}
        for ann in reference_annotations:
            lid = ann.get("label_id")
            if lid not in ref_by_label: ref_by_label[lid] = []
            ref_by_label[lid].append(self._custom_to_polygon(ann))
            
        stud_by_label = {}
        for ann in student_annotations:
            lid = ann.get("label_id")
            if lid not in stud_by_label: stud_by_label[lid] = []
            stud_by_label[lid].append(self._custom_to_polygon(ann))
            
        all_iou_scores = []
        total_ref_count = len(reference_annotations)
        total_matches = 0
        
        # Сравниваем аннотации для каждой метки отдельно
        for label_id, ref_polys in ref_by_label.items():
            stud_polys = stud_by_label.get(label_id, [])
            matches = self._match_polygons(stud_polys, ref_polys)
            total_matches += len(matches)
            
            for s_poly, r_poly in matches:
                all_iou_scores.append(self._calculate_iou(s_poly, r_poly))
        
        # Метрики
        accuracy = np.mean(all_iou_scores) if all_iou_scores else 0
        completeness = total_matches / total_ref_count if total_ref_count else 0
        
        # Precision
        true_positives = sum(1 for iou in all_iou_scores if iou > 0.5)
        precision = true_positives / len(student_annotations) if student_annotations else 0
        
        total_score = (
            accuracy * 0.5 + 
            completeness * 0.3 + 
            precision * 0.2
        ) * 100
        
        return {
            "iou_scores": [round(iou, 3) for iou in all_iou_scores],
            "accuracy": round(accuracy, 3),
            "completeness": round(completeness, 3),
            "precision": round(precision, 3),
            "total_score": round(total_score, 2)
        }
    
    def _custom_to_polygon(self, annotation: Dict[str, Any]) -> Optional[Polygon]:
        """
        Конвертация кастомной аннотации в Shapely Polygon
        """
        try:
            ann_type = annotation.get("type")
            
            if ann_type == 'polygon' and "points" in annotation:
                points = annotation["points"]
                coords = [(points[i], points[i+1]) for i in range(0, len(points), 2)]
                return Polygon(coords)
                
            elif ann_type == 'rectangle' and "bbox" in annotation:
                x, y, w, h = annotation["bbox"]
                return Polygon([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])
                
            elif ann_type == 'ellipse' and "center" in annotation and "radius" in annotation:
                cx, cy = annotation["center"]
                rx, ry = annotation["radius"]
                # Аппроксимация эллипса полигоном
                t = np.linspace(0, 2*np.pi, 32)
                coords = [(cx + rx*np.cos(ti), cy + ry*np.sin(ti)) for ti in t]
                return Polygon(coords)
                
            elif ann_type == 'point' and "center" in annotation:
                cx, cy = annotation["center"]
                # Точка как маленький круг для IoU
                return Polygon.from_bounds(cx-1, cy-1, cx+1, cy+1)
                
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

