"""
Computer Vision Service - оценка аннотаций в формате COCO
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


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
        image_id: Optional[UUID] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Оценка аннотации студента с поддержкой гибких настроек по меткам
        """
        # Настройки из БД или дефолтные
        config = config or {}
        
        # Хелпер для надежного получения числовых параметров
        def get_cfg_float(keys: List[str], default: float) -> float:
            for key in keys:
                if key in config and config[key] is not None:
                    try:
                        return float(config[key])
                    except (ValueError, TypeError):
                        continue
            return default

        iou_weight = get_cfg_float(["iou_weight"], 0.5)
        recall_weight = get_cfg_float(["recall_weight"], 0.3)
        precision_weight = get_cfg_float(["precision_weight"], 0.2)
        iou_threshold = get_cfg_float(["iou_threshold"], 0.5)

        # Параметры для частичного зачета
        allow_partial_global = config.get("allow_partial", False)
        inclusion_threshold = get_cfg_float(["inclusion_threshold", "inclusion"], 0.8)
        min_coverage_threshold = get_cfg_float(["min_coverage_threshold", "coverage"], 0.05)

        # Гибкая оценка по меткам
        label_configs = config.get("label_configs", {})

        # Режим лояльности
        loyalty_mode = config.get("loyalty_mode", False)
        accuracy_grace_threshold = get_cfg_float(["accuracy_grace_threshold"], 0.95)
        loyalty_boost_enabled = config.get("loyalty_boost_enabled", False)
        loyalty_boost_value = get_cfg_float(["loyalty_boost_value"], 0.05)
        top_off_threshold = get_cfg_float(["top_off_threshold"], 99.0)

        # Извлечение аннотаций
        student_annotations = student_data.get("annotations", [])
        reference_annotations = reference_data.get("annotations", [])
        
        logger.info(f"Evaluating annotation: stud_count={len(student_annotations)}, ref_count={len(reference_annotations)}")
        
        if not reference_annotations:
            return {
                "iou": 0, "recall": 0, "precision": 0, "total_score": 0,
                "iou_scores": [], "labels_breakdown": []
            }

        # 1. Группировка эталонных аннотаций по label_id
        ref_groups = {}
        for ann in reference_annotations:
            lid = str(ann.get("label_id", "default"))
            poly = self._any_to_polygon(ann)
            if poly and poly.is_valid and poly.area > 0.1:
                if lid not in ref_groups: ref_groups[lid] = []
                ref_groups[lid].append(poly)

        # 2. Группировка студенческих аннотаций по label_id с дедупликацией внутри групп
        stud_groups = {}
        total_valid_stud_count = 0
        for ann in student_annotations:
            lid = str(ann.get("label_id", "default"))
            poly = self._any_to_polygon(ann)
            if poly and poly.is_valid and poly.area > 0.1:
                if lid not in stud_groups: stud_groups[lid] = []
                
                # Дедупликация
                is_duplicate = False
                for existing_poly in stud_groups[lid]:
                    if self._calculate_iou(poly, existing_poly) > 0.99:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    stud_groups[lid].append(poly)
                    total_valid_stud_count += 1

        # 3. Основной цикл оценки по меткам
        labels_breakdown = []
        label_accuracy_scores = [] # Теперь храним взвешенные точности групп
        all_iou_vals = [] # Для детального списка IoU в ответе
        total_true_positives = 0
        label_recall_scores = []
        
        # Если label_configs пуст, создаем одну виртуальную группу из всех активных в эталоне меток
        active_labels = list(label_configs.keys()) if label_configs else list(ref_groups.keys())
        
        for lid in active_labels:
            if lid not in ref_groups:
                continue
                
            l_cfg = label_configs.get(lid, {}) if label_configs else {}
            mode = l_cfg.get("mode", "all")
            min_count = l_cfg.get("min_count", 1)
            l_weight = l_cfg.get("weight", 1.0)
            
            # Индивидуальный флаг частичного зачета для метки
            l_allow_partial = l_cfg.get("allow_partial", allow_partial_global)
            
            l_ref_polys = ref_groups[lid]
            l_stud_polys = stud_groups.get(lid, [])
            
            matches = self._match_polygons(l_stud_polys, l_ref_polys)
            
            l_found_count = 0
            l_accuracy_vals = []
            
            for s_poly, r_poly in matches:
                if not s_poly.is_valid: s_poly = s_poly.buffer(0)
                if not r_poly.is_valid: r_poly = r_poly.buffer(0)
                
                inter_area = s_poly.intersection(r_poly).area
                union_area = s_poly.union(r_poly).area
                iou = inter_area / union_area if union_area > 0 else 0
                
                inclusion = inter_area / s_poly.area if s_poly.area > 0 else 0
                coverage = inter_area / r_poly.area if r_poly.area > 0 else 0
                
                accuracy = inclusion if l_allow_partial else iou
                l_accuracy_vals.append(accuracy)
                all_iou_vals.append(accuracy)
                
                is_found = iou >= iou_threshold
                if l_allow_partial and not is_found:
                    if inclusion >= inclusion_threshold and coverage >= min_coverage_threshold:
                        is_found = True
                
                if is_found:
                    l_found_count += 1
                    total_true_positives += 1

            # Расчет Recall для данной метки
            if mode == "all":
                l_recall = l_found_count / len(l_ref_polys) if l_ref_polys else 0
            else: # any / at_least_n
                l_recall = 1.0 if l_found_count >= min_count else (l_found_count / min_count if min_count > 0 else 0)
            
            l_avg_accuracy = float(np.mean(l_accuracy_vals)) if l_accuracy_vals else 0.0
            
            label_recall_scores.append(l_recall * l_weight)
            label_accuracy_scores.append(l_avg_accuracy * l_weight) # Взвешенная точность
            
            labels_breakdown.append({
                "label_id": lid,
                "mode": mode,
                "min_count": min_count,
                "weight": l_weight,
                "allow_partial": l_allow_partial,
                "found_count": l_found_count,
                "total_count": len(l_ref_polys),
                "stud_count": len(l_stud_polys),
                "recall": round(float(l_recall), 3),
                "avg_accuracy": round(l_avg_accuracy, 3)
            })

        # 4. Итоговые агрегированные метрики
        # Средневзвешенные показатели
        total_label_weights = sum(label_configs.get(lid, {}).get("weight", 1.0) for lid in active_labels if lid in ref_groups) or len(active_labels)
        
        avg_accuracy = sum(label_accuracy_scores) / total_label_weights if total_label_weights > 0 else 0
        recall = sum(label_recall_scores) / total_label_weights if total_label_weights > 0 else 0
        
        precision = total_true_positives / total_valid_stud_count if total_valid_stud_count > 0 else 0
        
        if loyalty_mode:
            if avg_accuracy >= accuracy_grace_threshold:
                avg_accuracy = 1.0
            if loyalty_boost_enabled and recall >= 0.999 and precision >= 0.999:
                avg_accuracy = min(1.0, avg_accuracy + (loyalty_boost_value or 0.05))
        
        total_score = (
            avg_accuracy * iou_weight + 
            recall * recall_weight + 
            precision * precision_weight
        ) * 100
        
        if loyalty_mode and total_score >= (top_off_threshold or 99.0):
            total_score = 100.0
        
        logger.info(f"Evaluation results: accuracy={avg_accuracy:.3f}, recall={recall:.3f}, precision={precision:.3f}, score={total_score:.2f}")

        return {
            "iou": round(float(avg_accuracy), 3),
            "recall": round(float(recall), 3),
            "precision": round(float(precision), 3),
            "total_score": round(float(total_score), 2),
            "iou_scores": [round(float(s), 3) for s in all_iou_vals],
            "labels_breakdown": labels_breakdown,
            "total_true_positives": total_true_positives,
            "total_valid_stud_count": total_valid_stud_count
        }

    def _any_to_polygon(self, ann: Dict[str, Any]) -> Optional[Polygon]:
        """
        Универсальная конвертация любой аннотации (COCO или наш формат) в Shapely Polygon
        """
        try:
            poly = None
            # 1. Проверяем наш формат (points)
            points = ann.get("points")
            if points and isinstance(points, list):
                if len(points) >= 6:
                    if isinstance(points[0], (int, float)):
                        # Плоский список [x1, y1, x2, y2, ...]
                        coords = [(points[i], points[i+1]) for i in range(0, len(points), 2)]
                        poly = Polygon(coords)
                    elif isinstance(points[0], (list, tuple)) and len(points[0]) >= 2:
                        # Список пар [[x1, y1], [x2, y2], ...]
                        poly = Polygon(points)

            # 2. Проверяем COCO segmentation
            if not poly:
                segmentation = ann.get("segmentation")
                if segmentation and isinstance(segmentation, list) and len(segmentation) > 0:
                    pts = segmentation[0]
                    if len(pts) >= 6:
                        coords = [(pts[i], pts[i+1]) for i in range(0, len(pts), 2)]
                        poly = Polygon(coords)

            # 3. Проверяем bbox (COCO или наш)
            if not poly:
                bbox = ann.get("bbox")
                if bbox and len(bbox) == 4:
                    x, y, w, h = bbox
                    poly = Polygon([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])

            # 4. Ellipse
            if not poly and ann.get("type") == 'ellipse' and "center" in ann and "radius" in ann:
                cx, cy = ann["center"]
                rx, ry = ann["radius"]
                t = np.linspace(0, 2*np.pi, 32)
                coords = [(cx + rx*np.cos(ti), cy + ry*np.sin(ti)) for ti in t]
                poly = Polygon(coords)
            
            # Валидация и исправление
            if poly:
                if not poly.is_valid:
                    poly = poly.buffer(0) # Лечит самопересечения
                if poly.is_empty or poly.area <= 0.1:
                    return None
                return poly
                
            return None

            return None
        except Exception:
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
