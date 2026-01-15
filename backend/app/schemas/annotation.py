from typing import List, Optional, Tuple, Union
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum

class AnnotationType(str, Enum):
    POLYGON = "polygon"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    POINT = "point"

class AnnotationLabel(BaseModel):
    id: str
    name: str
    color: str

class Annotation(BaseModel):
    id: str
    label_id: str
    type: AnnotationType
    points: Optional[List[float]] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    center: Optional[Tuple[float, float]] = None
    radius: Optional[Tuple[float, float]] = None

class AnnotationData(BaseModel):
    labels: List[AnnotationLabel]
    annotations: List[Annotation]
