"""template_matcher.py

Template matching system for Balatro card detection.

This module provides robust template matching using game sprites as templates,
with support for rotation, scale invariance, and multiple matching methods.
Serves as a fallback when YOLOv8 confidence is low.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import logging

# Import our sprite loader
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.sprite_loader import SpriteLoader

logger = logging.getLogger(__name__)


@dataclass
class TemplateMatch:
    """Represents a template matching result."""
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    template_name: str
    card_class: int  # 0-51 for playing cards
    method: str  # matching method used
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of the match."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)


class BalatroTemplateMatcher:
    """Template matching system for Balatro cards using game sprites."""
    
    def __init__(self, confidence_threshold: float = 0.7):
        """Initialize the template matcher.
        
        Args:
            confidence_threshold: Minimum confidence for matches
        """
        self.confidence_threshold = confidence_threshold
        self.sprite_loader = SpriteLoader()
        
        # Template cache
        self.templates = {}
        self.template_sizes = {}
        
        # Matching parameters
        self.scale_factors = [0.8, 0.9, 1.0, 1.1, 1.2]  # Multi-scale matching
        self.rotation_angles = [-5, 0, 5]  # Small rotation tolerance
        
        # Load templates
        self._load_card_templates()
        
        logger.info(f"Initialized BalatroTemplateMatcher with {len(self.templates)} templates")
    
    def _load_card_templates(self) -> None:
        """Load card templates from sprite sheets."""
        try:
            # Get playing cards sprites
            playing_cards_sheet = None
            
            # Try to find the best playing cards sheet
            for sheet_name in self.sprite_loader.sheets.keys():
                if 'playing' in sheet_name.lower() and 'high contrast' in sheet_name.lower():
                    playing_cards_sheet = sheet_name
                    break
            
            if not playing_cards_sheet:
                for sheet_name in self.sprite_loader.sheets.keys():
                    if 'playing' in sheet_name.lower():
                        playing_cards_sheet = sheet_name
                        break
            
            if not playing_cards_sheet:
                logger.warning("No playing cards sprite sheet found")
                return
            
            logger.info(f"Loading templates from: {playing_cards_sheet}")
            
            # Load all 52 playing card templates
            for card_class in range(52):
                try:
                    # Get sprite with backing (full card appearance)
                    sprite = self.sprite_loader.get_sprite(playing_cards_sheet, card_class, composite_back=True)
                    
                    if sprite is not None:
                        # Convert PIL to OpenCV format
                        template_array = np.array(sprite)
                        if len(template_array.shape) == 3:
                            template_cv = cv2.cvtColor(template_array, cv2.COLOR_RGB2BGR)
                        else:
                            template_cv = template_array
                        
                        # Store template
                        template_name = f"card_{card_class}"
                        self.templates[template_name] = template_cv
                        self.template_sizes[template_name] = template_cv.shape[:2]  # (height, width)
                        
                except Exception as e:
                    logger.warning(f"Failed to load template for card {card_class}: {e}")
            
            logger.info(f"Loaded {len(self.templates)} card templates")
            
        except Exception as e:
            logger.error(f"Failed to load card templates: {e}")
    
    def match_templates(self, image: np.ndarray, region_type: str = 'cards') -> List[TemplateMatch]:
        """Match templates against an image region.
        
        Args:
            image: Input image as numpy array (BGR format)
            region_type: Type of region ('cards', 'jokers', etc.)
            
        Returns:
            List of template matches
        """
        if image is None or image.size == 0:
            return []
        
        if not self.templates:
            logger.warning("No templates loaded")
            return []
        
        matches = []
        
        # Only match playing cards in cards region
        if region_type == 'cards':
            templates_to_match = {k: v for k, v in self.templates.items() if k.startswith('card_')}
        else:
            templates_to_match = self.templates
        
        # Convert image to grayscale for matching
        if len(image.shape) == 3:
            image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            image_gray = image
        
        # Match each template
        for template_name, template in templates_to_match.items():
            template_matches = self._match_single_template(
                image_gray, template, template_name
            )
            matches.extend(template_matches)
        
        # Remove overlapping matches (Non-Maximum Suppression)
        matches = self._apply_nms(matches)
        
        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        logger.debug(f"Found {len(matches)} template matches in {region_type} region")
        return matches
    
    def _match_single_template(self, image: np.ndarray, template: np.ndarray, template_name: str) -> List[TemplateMatch]:
        """Match a single template against the image with multi-scale and rotation.
        
        Args:
            image: Grayscale input image
            template: Template image (BGR)
            template_name: Name of the template
            
        Returns:
            List of matches for this template
        """
        matches = []
        
        # Convert template to grayscale
        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template
        
        template_h, template_w = template_gray.shape
        
        # Multi-scale matching
        for scale in self.scale_factors:
            # Resize template
            scaled_w = int(template_w * scale)
            scaled_h = int(template_h * scale)
            
            if scaled_w > image.shape[1] or scaled_h > image.shape[0]:
                continue  # Template too large
            
            scaled_template = cv2.resize(template_gray, (scaled_w, scaled_h))
            
            # Multi-rotation matching
            for angle in self.rotation_angles:
                rotated_template = self._rotate_template(scaled_template, angle)
                
                if rotated_template is None:
                    continue
                
                # Perform template matching
                result = cv2.matchTemplate(image, rotated_template, cv2.TM_CCOEFF_NORMED)
                
                # Find matches above threshold
                locations = np.where(result >= self.confidence_threshold)
                
                for pt in zip(*locations[::-1]):  # Switch x and y
                    x, y = pt
                    w, h = rotated_template.shape[1], rotated_template.shape[0]
                    confidence = result[y, x]
                    
                    # Extract card class from template name
                    card_class = int(template_name.split('_')[1]) if '_' in template_name else -1
                    
                    match = TemplateMatch(
                        bbox=(x, y, w, h),
                        confidence=float(confidence),
                        template_name=template_name,
                        card_class=card_class,
                        method=f"template_scale_{scale}_rot_{angle}"
                    )
                    matches.append(match)
        
        return matches
    
    def _rotate_template(self, template: np.ndarray, angle: float) -> Optional[np.ndarray]:
        """Rotate template by given angle.
        
        Args:
            template: Input template
            angle: Rotation angle in degrees
            
        Returns:
            Rotated template or None if rotation failed
        """
        if angle == 0:
            return template
        
        try:
            h, w = template.shape
            center = (w // 2, h // 2)
            
            # Get rotation matrix
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Calculate new dimensions
            cos_angle = abs(rotation_matrix[0, 0])
            sin_angle = abs(rotation_matrix[0, 1])
            new_w = int((h * sin_angle) + (w * cos_angle))
            new_h = int((h * cos_angle) + (w * sin_angle))
            
            # Adjust rotation matrix for new center
            rotation_matrix[0, 2] += (new_w / 2) - center[0]
            rotation_matrix[1, 2] += (new_h / 2) - center[1]
            
            # Perform rotation
            rotated = cv2.warpAffine(template, rotation_matrix, (new_w, new_h))
            
            return rotated
            
        except Exception as e:
            logger.warning(f"Failed to rotate template by {angle} degrees: {e}")
            return None
    
    def _apply_nms(self, matches: List[TemplateMatch], overlap_threshold: float = 0.3) -> List[TemplateMatch]:
        """Apply Non-Maximum Suppression to remove overlapping matches.
        
        Args:
            matches: List of template matches
            overlap_threshold: Maximum allowed overlap ratio
            
        Returns:
            Filtered list of matches
        """
        if not matches:
            return []
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        filtered_matches = []
        
        for match in matches:
            # Check if this match overlaps significantly with any accepted match
            overlap_found = False
            
            for accepted_match in filtered_matches:
                overlap_ratio = self._calculate_overlap_ratio(match.bbox, accepted_match.bbox)
                
                if overlap_ratio > overlap_threshold:
                    overlap_found = True
                    break
            
            if not overlap_found:
                filtered_matches.append(match)
        
        return filtered_matches
    
    def _calculate_overlap_ratio(self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate overlap ratio between two bounding boxes.
        
        Args:
            bbox1: First bounding box (x, y, w, h)
            bbox2: Second bounding box (x, y, w, h)
            
        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)
        
        if left >= right or top >= bottom:
            return 0.0  # No intersection
        
        intersection_area = (right - left) * (bottom - top)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union_area = area1 + area2 - intersection_area
        
        if union_area == 0:
            return 0.0
        
        return intersection_area / union_area
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about loaded templates.
        
        Returns:
            Dictionary with template information
        """
        return {
            'total_templates': len(self.templates),
            'template_names': list(self.templates.keys()),
            'template_sizes': self.template_sizes,
            'confidence_threshold': self.confidence_threshold
        }


# Global template matcher instance
_template_matcher = None


def get_template_matcher() -> BalatroTemplateMatcher:
    """Get the global template matcher instance.
    
    Returns:
        Global BalatroTemplateMatcher instance
    """
    global _template_matcher
    if _template_matcher is None:
        _template_matcher = BalatroTemplateMatcher()
    return _template_matcher


def match_cards_in_image(image: np.ndarray, region_type: str = 'cards') -> List[TemplateMatch]:
    """Convenience function to match cards using templates.
    
    Args:
        image: Input image as numpy array
        region_type: Type of region
        
    Returns:
        List of template matches
    """
    matcher = get_template_matcher()
    return matcher.match_templates(image, region_type)