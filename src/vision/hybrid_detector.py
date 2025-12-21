"""hybrid_detector.py

Hybrid detection pipeline combining YOLOv8, template matching, and traditional CV.

This module orchestrates multiple detection methods with voting systems,
confidence weighting, and intelligent fallback mechanisms for robust
Balatro card detection.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

from .card_detector import BalatroCardDetector, CardDetection
from .template_matcher import BalatroTemplateMatcher, TemplateMatch

logger = logging.getLogger(__name__)


class DetectionMethod(Enum):
    """Available detection methods."""
    YOLO = "yolo"
    TEMPLATE = "template"
    TRADITIONAL_CV = "traditional_cv"
    ENSEMBLE = "ensemble"


@dataclass
class HybridDetection:
    """Represents a detection from the hybrid system."""
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    card_type: str
    card_class: int
    method: DetectionMethod
    vote_count: int  # Number of methods that detected this card
    method_confidences: Dict[str, float]  # Confidence from each method
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of the detection."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)
    
    @property
    def area(self) -> int:
        """Get area of the detection."""
        return self.bbox[2] * self.bbox[3]


class BalatroHybridDetector:
    """Hybrid detection system combining multiple methods."""
    
    def __init__(self, 
                 yolo_confidence: float = 0.7,
                 template_confidence: float = 0.7,
                 ensemble_threshold: float = 0.6):
        """Initialize the hybrid detector.
        
        Args:
            yolo_confidence: Confidence threshold for YOLOv8
            template_confidence: Confidence threshold for template matching
            ensemble_threshold: Minimum confidence for ensemble results
        """
        self.yolo_confidence = yolo_confidence
        self.template_confidence = template_confidence
        self.ensemble_threshold = ensemble_threshold
        
        # Initialize detection methods
        self.yolo_detector = BalatroCardDetector(confidence_threshold=yolo_confidence)
        self.template_matcher = BalatroTemplateMatcher(confidence_threshold=template_confidence)
        
        # Method weights for ensemble voting
        self.method_weights = {
            DetectionMethod.YOLO: 1.0,
            DetectionMethod.TEMPLATE: 0.8,
            DetectionMethod.TRADITIONAL_CV: 0.6
        }
        
        # Performance tracking
        self.performance_stats = {
            'yolo_calls': 0,
            'template_calls': 0,
            'traditional_cv_calls': 0,
            'ensemble_calls': 0,
            'total_detections': 0
        }
        
        logger.info("Initialized BalatroHybridDetector")
    
    def detect_cards(self, image: np.ndarray, 
                    region_type: str = 'cards',
                    method: DetectionMethod = DetectionMethod.ENSEMBLE) -> List[HybridDetection]:
        """Detect cards using specified method(s).
        
        Args:
            image: Input image as numpy array (BGR format)
            region_type: Type of region ('cards', 'jokers', etc.)
            method: Detection method to use
            
        Returns:
            List of hybrid detections
        """
        if image is None or image.size == 0:
            return []
        
        if method == DetectionMethod.YOLO:
            return self._detect_yolo_only(image, region_type)
        elif method == DetectionMethod.TEMPLATE:
            return self._detect_template_only(image, region_type)
        elif method == DetectionMethod.TRADITIONAL_CV:
            return self._detect_traditional_cv_only(image, region_type)
        elif method == DetectionMethod.ENSEMBLE:
            return self._detect_ensemble(image, region_type)
        else:
            raise ValueError(f"Unknown detection method: {method}")
    
    def _detect_yolo_only(self, image: np.ndarray, region_type: str) -> List[HybridDetection]:
        """Detect using YOLOv8 only."""
        self.performance_stats['yolo_calls'] += 1
        
        yolo_detections = self.yolo_detector.detect_cards(image, region_type)
        
        hybrid_detections = []
        for detection in yolo_detections:
            hybrid_detection = HybridDetection(
                bbox=detection.bbox,
                confidence=detection.confidence,
                card_type=detection.card_type,
                card_class=detection.class_id,
                method=DetectionMethod.YOLO,
                vote_count=1,
                method_confidences={'yolo': detection.confidence}
            )
            hybrid_detections.append(hybrid_detection)
        
        return hybrid_detections
    
    def _detect_template_only(self, image: np.ndarray, region_type: str) -> List[HybridDetection]:
        """Detect using template matching only."""
        self.performance_stats['template_calls'] += 1
        
        template_matches = self.template_matcher.match_templates(image, region_type)
        
        hybrid_detections = []
        for match in template_matches:
            hybrid_detection = HybridDetection(
                bbox=match.bbox,
                confidence=match.confidence,
                card_type='playing_card',  # Template matcher focuses on playing cards
                card_class=match.card_class,
                method=DetectionMethod.TEMPLATE,
                vote_count=1,
                method_confidences={'template': match.confidence}
            )
            hybrid_detections.append(hybrid_detection)
        
        return hybrid_detections
    
    def _detect_traditional_cv_only(self, image: np.ndarray, region_type: str) -> List[HybridDetection]:
        """Detect using traditional computer vision methods."""
        self.performance_stats['traditional_cv_calls'] += 1
        
        # Implement basic edge detection + contour finding
        detections = self._traditional_cv_detection(image)
        
        hybrid_detections = []
        for detection in detections:
            hybrid_detection = HybridDetection(
                bbox=detection['bbox'],
                confidence=detection['confidence'],
                card_type='unknown',
                card_class=-1,
                method=DetectionMethod.TRADITIONAL_CV,
                vote_count=1,
                method_confidences={'traditional_cv': detection['confidence']}
            )
            hybrid_detections.append(hybrid_detection)
        
        return hybrid_detections
    
    def _detect_ensemble(self, image: np.ndarray, region_type: str) -> List[HybridDetection]:
        """Detect using ensemble of all methods."""
        self.performance_stats['ensemble_calls'] += 1
        
        # Run all detection methods
        yolo_detections = self.yolo_detector.detect_cards(image, region_type)
        template_matches = self.template_matcher.match_templates(image, region_type)
        traditional_detections = self._traditional_cv_detection(image)
        
        # Convert to common format
        all_detections = []
        
        # Add YOLOv8 detections
        for detection in yolo_detections:
            all_detections.append({
                'bbox': detection.bbox,
                'confidence': detection.confidence,
                'card_type': detection.card_type,
                'card_class': detection.class_id,
                'method': 'yolo',
                'source': detection
            })
        
        # Add template matches
        for match in template_matches:
            all_detections.append({
                'bbox': match.bbox,
                'confidence': match.confidence,
                'card_type': 'playing_card',
                'card_class': match.card_class,
                'method': 'template',
                'source': match
            })
        
        # Add traditional CV detections
        for detection in traditional_detections:
            all_detections.append({
                'bbox': detection['bbox'],
                'confidence': detection['confidence'],
                'card_type': 'unknown',
                'card_class': -1,
                'method': 'traditional_cv',
                'source': detection
            })
        
        # Perform ensemble voting
        ensemble_detections = self._ensemble_voting(all_detections)
        
        return ensemble_detections
    
    def _traditional_cv_detection(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Basic traditional computer vision detection."""
        detections = []
        
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 30, 100)
            
            # Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                aspect_ratio = w / h if h > 0 else 0
                
                # Filter by size and aspect ratio (typical card dimensions)
                if (3000 <= area <= 50000 and 
                    0.4 <= aspect_ratio <= 1.2):
                    
                    # Calculate confidence based on contour properties
                    contour_area = cv2.contourArea(contour)
                    bbox_area = w * h
                    fill_ratio = contour_area / bbox_area if bbox_area > 0 else 0
                    
                    confidence = min(0.8, fill_ratio)  # Max 0.8 for traditional CV
                    
                    detections.append({
                        'bbox': (x, y, w, h),
                        'confidence': confidence,
                        'area': area,
                        'aspect_ratio': aspect_ratio
                    })
            
        except Exception as e:
            logger.warning(f"Traditional CV detection failed: {e}")
        
        return detections
    
    def _ensemble_voting(self, all_detections: List[Dict[str, Any]]) -> List[HybridDetection]:
        """Perform ensemble voting to combine detections from multiple methods."""
        if not all_detections:
            return []
        
        # Group overlapping detections
        detection_groups = self._group_overlapping_detections(all_detections)
        
        ensemble_detections = []
        
        for group in detection_groups:
            if not group:
                continue
            
            # Calculate ensemble properties
            ensemble_detection = self._create_ensemble_detection(group)
            
            if ensemble_detection.confidence >= self.ensemble_threshold:
                ensemble_detections.append(ensemble_detection)
        
        # Sort by confidence
        ensemble_detections.sort(key=lambda d: d.confidence, reverse=True)
        
        self.performance_stats['total_detections'] += len(ensemble_detections)
        
        return ensemble_detections
    
    def _group_overlapping_detections(self, detections: List[Dict[str, Any]], 
                                    overlap_threshold: float = 0.3) -> List[List[Dict[str, Any]]]:
        """Group detections that overlap significantly."""
        if not detections:
            return []
        
        groups = []
        used = set()
        
        for i, detection in enumerate(detections):
            if i in used:
                continue
            
            group = [detection]
            used.add(i)
            
            # Find overlapping detections
            for j, other_detection in enumerate(detections):
                if j in used or i == j:
                    continue
                
                overlap_ratio = self._calculate_overlap_ratio(
                    detection['bbox'], other_detection['bbox']
                )
                
                if overlap_ratio > overlap_threshold:
                    group.append(other_detection)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def _create_ensemble_detection(self, group: List[Dict[str, Any]]) -> HybridDetection:
        """Create ensemble detection from a group of overlapping detections."""
        if not group:
            raise ValueError("Empty group")
        
        # Calculate weighted average bbox
        total_weight = 0
        weighted_x, weighted_y, weighted_w, weighted_h = 0, 0, 0, 0
        
        method_confidences = {}
        methods_used = set()
        
        for detection in group:
            method = detection['method']
            confidence = detection['confidence']
            weight = self.method_weights.get(DetectionMethod(method), 0.5)
            
            x, y, w, h = detection['bbox']
            weighted_x += x * weight
            weighted_y += y * weight
            weighted_w += w * weight
            weighted_h += h * weight
            total_weight += weight
            
            method_confidences[method] = confidence
            methods_used.add(method)
        
        if total_weight > 0:
            avg_x = int(weighted_x / total_weight)
            avg_y = int(weighted_y / total_weight)
            avg_w = int(weighted_w / total_weight)
            avg_h = int(weighted_h / total_weight)
        else:
            # Fallback to simple average
            avg_x = int(sum(d['bbox'][0] for d in group) / len(group))
            avg_y = int(sum(d['bbox'][1] for d in group) / len(group))
            avg_w = int(sum(d['bbox'][2] for d in group) / len(group))
            avg_h = int(sum(d['bbox'][3] for d in group) / len(group))
        
        # Calculate ensemble confidence
        ensemble_confidence = self._calculate_ensemble_confidence(group)
        
        # Determine card type and class (prefer YOLOv8 or template results)
        card_type = 'unknown'
        card_class = -1
        
        for detection in group:
            if detection['method'] == 'yolo' and detection.get('card_type') != 'unknown':
                card_type = detection['card_type']
                card_class = detection.get('card_class', -1)
                break
            elif detection['method'] == 'template':
                card_type = detection.get('card_type', 'playing_card')
                card_class = detection.get('card_class', -1)
        
        return HybridDetection(
            bbox=(avg_x, avg_y, avg_w, avg_h),
            confidence=ensemble_confidence,
            card_type=card_type,
            card_class=card_class,
            method=DetectionMethod.ENSEMBLE,
            vote_count=len(group),
            method_confidences=method_confidences
        )
    
    def _calculate_ensemble_confidence(self, group: List[Dict[str, Any]]) -> float:
        """Calculate ensemble confidence from a group of detections."""
        if not group:
            return 0.0
        
        # Weighted average of confidences
        total_weight = 0
        weighted_confidence = 0
        
        for detection in group:
            method = detection['method']
            confidence = detection['confidence']
            weight = self.method_weights.get(DetectionMethod(method), 0.5)
            
            weighted_confidence += confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            avg_confidence = weighted_confidence / total_weight
        else:
            avg_confidence = sum(d['confidence'] for d in group) / len(group)
        
        # Boost confidence based on number of agreeing methods
        vote_bonus = min(0.2, (len(group) - 1) * 0.1)  # Up to 0.2 bonus
        
        return min(1.0, avg_confidence + vote_bonus)
    
    def _calculate_overlap_ratio(self, bbox1: Tuple[int, int, int, int], 
                               bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate overlap ratio between two bounding boxes."""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)
        
        if left >= right or top >= bottom:
            return 0.0
        
        intersection_area = (right - left) * (bottom - top)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union_area = area1 + area2 - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def reset_performance_stats(self) -> None:
        """Reset performance statistics."""
        for key in self.performance_stats:
            self.performance_stats[key] = 0


# Global hybrid detector instance
_hybrid_detector = None


def get_hybrid_detector() -> BalatroHybridDetector:
    """Get the global hybrid detector instance.
    
    Returns:
        Global BalatroHybridDetector instance
    """
    global _hybrid_detector
    if _hybrid_detector is None:
        _hybrid_detector = BalatroHybridDetector()
    return _hybrid_detector


def detect_cards_hybrid(image: np.ndarray, 
                       region_type: str = 'cards',
                       method: DetectionMethod = DetectionMethod.ENSEMBLE) -> List[HybridDetection]:
    """Convenience function for hybrid card detection.
    
    Args:
        image: Input image as numpy array
        region_type: Type of region
        method: Detection method to use
        
    Returns:
        List of hybrid detections
    """
    detector = get_hybrid_detector()
    return detector.detect_cards(image, region_type, method)