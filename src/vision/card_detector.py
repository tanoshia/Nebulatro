"""card_detector.py

YOLOv8-based card detection for Balatro screenshots.

This module implements robust card detection using YOLOv8 object detection,
specifically trained for Balatro cards with support for visual effects,
modifiers, and different card types.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import logging

try:
    from ultralytics import YOLO
except ImportError as e:
    raise ImportError(
        "Missing dependency: ultralytics. Install with `pip install ultralytics`."
    ) from e

logger = logging.getLogger(__name__)


@dataclass
class CardDetection:
    """Represents a detected card with metadata."""
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    card_type: str  # 'playing_card', 'joker', 'consumable', 'tarot'
    class_id: int
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of the card."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)
    
    @property
    def area(self) -> int:
        """Get area of the card."""
        return self.bbox[2] * self.bbox[3]


class BalatroCardDetector:
    """YOLOv8-based card detector for Balatro screenshots."""
    
    def __init__(self, model_path: Optional[Path] = None, confidence_threshold: float = 0.7):
        """Initialize the card detector.
        
        Args:
            model_path: Path to trained YOLOv8 model. If None, uses pre-trained model.
            confidence_threshold: Minimum confidence for detections
        """
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path
        
        # Card type mapping (will be updated based on training data)
        self.card_types = {
            0: 'playing_card',
            1: 'joker',
            2: 'consumable',
            3: 'tarot',
            4: 'planet',
            5: 'spectral'
        }
        
        # Initialize model
        self.model = self._load_model()
        
        logger.info(f"Initialized BalatroCardDetector with confidence threshold {confidence_threshold}")
    
    def _load_model(self) -> YOLO:
        """Load YOLOv8 model."""
        if self.model_path and self.model_path.exists():
            logger.info(f"Loading custom model from {self.model_path}")
            return YOLO(str(self.model_path))
        else:
            logger.info("Loading pre-trained YOLOv8 model (will need fine-tuning)")
            # Start with YOLOv8n (nano) for speed, can upgrade to YOLOv8s/m/l for accuracy
            return YOLO('yolov8n.pt')
    
    def detect_cards(self, image: np.ndarray, region_type: str = 'cards') -> List[CardDetection]:
        """Detect cards in an image region.
        
        Args:
            image: Input image as numpy array (BGR format)
            region_type: Type of region ('cards', 'jokers', 'shop', etc.)
            
        Returns:
            List of detected cards with metadata
        """
        if image is None or image.size == 0:
            return []
        
        # Run YOLOv8 inference
        results = self.model(image, conf=self.confidence_threshold, verbose=False)
        
        detections = []
        
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
                confidences = result.boxes.conf.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy().astype(int)
                
                for box, conf, class_id in zip(boxes, confidences, class_ids):
                    # Convert from x1,y1,x2,y2 to x,y,w,h
                    x1, y1, x2, y2 = box
                    x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)
                    
                    # Get card type
                    card_type = self.card_types.get(class_id, 'unknown')
                    
                    # Filter by region type if needed
                    if self._is_valid_for_region(card_type, region_type):
                        detection = CardDetection(
                            bbox=(x, y, w, h),
                            confidence=float(conf),
                            card_type=card_type,
                            class_id=class_id
                        )
                        detections.append(detection)
        
        # Sort by confidence (highest first)
        detections.sort(key=lambda d: d.confidence, reverse=True)
        
        logger.debug(f"Detected {len(detections)} cards in {region_type} region")
        return detections
    
    def _is_valid_for_region(self, card_type: str, region_type: str) -> bool:
        """Check if card type is valid for the given region."""
        region_filters = {
            'cards': ['playing_card'],  # Only playing cards in hand region
            'jokers': ['joker'],        # Only jokers in joker region
            'shop': ['playing_card', 'joker', 'consumable', 'tarot', 'planet', 'spectral'],
            'pack': ['consumable', 'tarot', 'planet', 'spectral']
        }
        
        allowed_types = region_filters.get(region_type, list(self.card_types.values()))
        return card_type in allowed_types
    
    def detect_cards_with_fallback(self, image: np.ndarray, region_type: str = 'cards') -> Tuple[List[CardDetection], str]:
        """Detect cards with fallback to template matching if confidence is low.
        
        Args:
            image: Input image as numpy array
            region_type: Type of region
            
        Returns:
            Tuple of (detections, method_used)
        """
        # Try YOLOv8 first
        detections = self.detect_cards(image, region_type)
        
        # Check if we have high-confidence detections
        high_conf_detections = [d for d in detections if d.confidence >= self.confidence_threshold]
        
        if high_conf_detections:
            return high_conf_detections, 'yolo'
        
        # Fallback to template matching (to be implemented)
        logger.debug("YOLOv8 confidence too low, falling back to template matching")
        template_detections = self._template_matching_fallback(image, region_type)
        
        return template_detections, 'template'
    
    def _template_matching_fallback(self, image: np.ndarray, region_type: str) -> List[CardDetection]:
        """Fallback template matching using sprite templates."""
        try:
            from .template_matcher import get_template_matcher
            
            matcher = get_template_matcher()
            template_matches = matcher.match_templates(image, region_type)
            
            # Convert template matches to card detections
            detections = []
            for match in template_matches:
                detection = CardDetection(
                    bbox=match.bbox,
                    confidence=match.confidence,
                    card_type='playing_card',  # Template matcher focuses on playing cards
                    class_id=match.card_class
                )
                detections.append(detection)
            
            logger.info(f"Template matching found {len(detections)} cards")
            return detections
            
        except Exception as e:
            logger.error(f"Template matching fallback failed: {e}")
            return []
    
    def train_on_dataset(self, dataset_path: Path, epochs: int = 100, batch_size: int = 16) -> Path:
        """Train YOLOv8 model on Balatro dataset.
        
        Args:
            dataset_path: Path to YOLO format dataset directory
            epochs: Number of training epochs
            batch_size: Training batch size
            
        Returns:
            Path to trained model
        """
        logger.info(f"Starting YOLOv8 training on {dataset_path}")
        
        # Ensure dataset structure exists
        if not (dataset_path / 'data.yaml').exists():
            raise FileNotFoundError(f"Dataset config not found: {dataset_path}/data.yaml")
        
        # Train the model
        results = self.model.train(
            data=str(dataset_path / 'data.yaml'),
            epochs=epochs,
            batch=batch_size,
            imgsz=640,  # Standard YOLO image size
            device='auto',  # Use GPU if available
            project=str(dataset_path.parent / 'runs'),
            name='balatro_cards',
            save=True,
            plots=True
        )
        
        # Get path to best model
        best_model_path = Path(results.save_dir) / 'weights' / 'best.pt'
        
        logger.info(f"Training complete. Best model saved to: {best_model_path}")
        return best_model_path
    
    def update_model(self, model_path: Path) -> None:
        """Update the detector with a new trained model.
        
        Args:
            model_path: Path to new model weights
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.model_path = model_path
        self.model = YOLO(str(model_path))
        
        logger.info(f"Updated model to {model_path}")
    
    def benchmark_performance(self, test_images: List[np.ndarray]) -> Dict[str, float]:
        """Benchmark detection performance on test images.
        
        Args:
            test_images: List of test images
            
        Returns:
            Performance metrics
        """
        import time
        
        total_time = 0
        total_detections = 0
        
        for image in test_images:
            start_time = time.time()
            detections = self.detect_cards(image)
            end_time = time.time()
            
            total_time += (end_time - start_time)
            total_detections += len(detections)
        
        avg_time_per_image = total_time / len(test_images) if test_images else 0
        avg_detections_per_image = total_detections / len(test_images) if test_images else 0
        
        return {
            'avg_time_per_image_ms': avg_time_per_image * 1000,
            'avg_detections_per_image': avg_detections_per_image,
            'total_images_processed': len(test_images),
            'fps': 1 / avg_time_per_image if avg_time_per_image > 0 else 0
        }


# Global detector instance
_card_detector = None


def get_card_detector() -> BalatroCardDetector:
    """Get the global card detector instance.
    
    Returns:
        Global BalatroCardDetector instance
    """
    global _card_detector
    if _card_detector is None:
        _card_detector = BalatroCardDetector()
    return _card_detector


def detect_cards_in_image(image: np.ndarray, region_type: str = 'cards') -> List[CardDetection]:
    """Convenience function to detect cards in an image.
    
    Args:
        image: Input image as numpy array
        region_type: Type of region
        
    Returns:
        List of detected cards
    """
    detector = get_card_detector()
    detections, _ = detector.detect_cards_with_fallback(image, region_type)
    return detections