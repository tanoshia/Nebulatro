#!/usr/bin/env python3
"""
Improved Screenshot Processor - Enhanced Balatro screenshot analysis and card extraction

This tool properly divides full-screen Balatro screenshots into the correct regions:
- Data (left 25%): Game stats, score, hands remaining
- Jokers (top right 30%): Joker cards and consumables  
- Playing Cards (bottom right 70%): Current hand of playing cards

Features:
- Accurate region detection for any resolution
- Improved card detection algorithms
- Multiple detection methods with fallbacks
- Comprehensive debugging and visualization
- Integration with dataset management system
"""

import sys
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Dict, Any, Optional
import json


class BalatroScreenProcessor:
    """Enhanced Balatro screenshot processor with improved card detection."""
    
    def __init__(self, debug: bool = False):
        """Initialize the processor.
        
        Args:
            debug: Enable debug output and visualization
        """
        self.debug = debug
        
        # Card detection parameters
        self.min_card_area = 3000  # Minimum card area in pixels
        self.max_card_area = 50000  # Maximum card area in pixels
        self.min_aspect_ratio = 0.4  # Minimum width/height ratio
        self.max_aspect_ratio = 1.2  # Maximum width/height ratio
        
        # Edge detection parameters
        self.canny_low = 30
        self.canny_high = 100
        
    def extract_regions(self, screenshot_path: Path) -> Dict[str, Any]:
        """Extract all three regions from a Balatro screenshot.
        
        Args:
            screenshot_path: Path to the screenshot
            
        Returns:
            Dictionary with region information and images
        """
        # Load screenshot
        img = Image.open(screenshot_path)
        width, height = img.size
        
        if self.debug:
            print(f"Processing screenshot: {screenshot_path}")
            print(f"Resolution: {width}x{height}")
        
        # Calculate region boundaries
        data_left = 0
        data_right = int(width * 0.25)
        
        jokers_left = data_right
        jokers_right = width
        jokers_top = 0
        jokers_bottom = int(height * 0.30)
        
        cards_left = data_right
        cards_right = width
        cards_top = jokers_bottom
        cards_bottom = height
        
        # Extract regions
        regions = {
            "screenshot_info": {
                "path": str(screenshot_path),
                "resolution": [width, height],
                "aspect_ratio": width / height
            },
            "data_region": {
                "bounds": (data_left, 0, data_right, height),
                "size": (data_right - data_left, height),
                "image": img.crop((data_left, 0, data_right, height))
            },
            "jokers_region": {
                "bounds": (jokers_left, jokers_top, jokers_right, jokers_bottom),
                "size": (jokers_right - jokers_left, jokers_bottom - jokers_top),
                "image": img.crop((jokers_left, jokers_top, jokers_right, jokers_bottom))
            },
            "cards_region": {
                "bounds": (cards_left, cards_top, cards_right, cards_bottom),
                "size": (cards_right - cards_left, cards_bottom - cards_top),
                "image": img.crop((cards_left, cards_top, cards_right, cards_bottom))
            }
        }
        
        if self.debug:
            for region_name, region_data in regions.items():
                if region_name != "screenshot_info":
                    size = region_data["size"]
                    bounds = region_data["bounds"]
                    print(f"{region_name}: {size[0]}x{size[1]} at ({bounds[0]}, {bounds[1]})")
        
        return regions
    
    def detect_cards_advanced(self, cards_image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Advanced card detection using multiple methods.
        
        Args:
            cards_image: PIL Image of the cards region
            
        Returns:
            List of (x, y, width, height) tuples for detected cards
        """
        # Convert to OpenCV format
        img_array = np.array(cards_image)
        if len(img_array.shape) == 3:
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_cv = img_array
        
        # Method 1: Edge-based detection (primary)
        cards_edge = self._detect_cards_edges(img_cv)
        
        # Method 2: Color-based detection (fallback)
        cards_color = self._detect_cards_color(img_cv)
        
        # Method 3: Template-based detection (experimental)
        cards_template = self._detect_cards_template(img_cv)
        
        # Combine and filter results
        all_cards = cards_edge + cards_color + cards_template
        filtered_cards = self._filter_and_merge_detections(all_cards)
        
        if self.debug:
            print(f"Card detection results:")
            print(f"  Edge-based: {len(cards_edge)} cards")
            print(f"  Color-based: {len(cards_color)} cards")
            print(f"  Template-based: {len(cards_template)} cards")
            print(f"  Final filtered: {len(filtered_cards)} cards")
        
        return filtered_cards
    
    def _detect_cards_edges(self, img_cv: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect cards using edge detection."""
        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection with adaptive thresholds
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)
        
        # Morphological operations to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        cards = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if self._is_valid_card_region(x, y, w, h):
                cards.append((x, y, w, h))
        
        return cards
    
    def _detect_cards_color(self, img_cv: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect cards using color-based segmentation."""
        # Convert to HSV for better color segmentation
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for card backgrounds (adjust based on Balatro's color scheme)
        # Cards typically have light backgrounds
        lower_card = np.array([0, 0, 180])  # Light colors
        upper_card = np.array([180, 50, 255])
        
        # Create mask
        mask = cv2.inRange(hsv, lower_card, upper_card)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        cards = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if self._is_valid_card_region(x, y, w, h):
                cards.append((x, y, w, h))
        
        return cards
    
    def _detect_cards_template(self, img_cv: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect cards using template matching (experimental)."""
        # This is a placeholder for template-based detection
        # Could be implemented using card templates from the sprite system
        return []
    
    def _is_valid_card_region(self, x: int, y: int, w: int, h: int) -> bool:
        """Check if a region is a valid card based on size and aspect ratio."""
        area = w * h
        aspect_ratio = w / h if h > 0 else 0
        
        return (self.min_card_area <= area <= self.max_card_area and
                self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio)
    
    def _filter_and_merge_detections(self, detections: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Filter overlapping detections and merge similar ones."""
        if not detections:
            return []
        
        # Remove duplicates and overlapping regions
        filtered = []
        
        for x, y, w, h in detections:
            # Check if this detection overlaps significantly with existing ones
            overlap_found = False
            
            for fx, fy, fw, fh in filtered:
                # Calculate overlap
                overlap_x = max(0, min(x + w, fx + fw) - max(x, fx))
                overlap_y = max(0, min(y + h, fy + fh) - max(y, fy))
                overlap_area = overlap_x * overlap_y
                
                # If overlap is more than 50% of either region, consider it a duplicate
                area1 = w * h
                area2 = fw * fh
                
                if overlap_area > 0.5 * min(area1, area2):
                    overlap_found = True
                    break
            
            if not overlap_found:
                filtered.append((x, y, w, h))
        
        # Sort by x position (left to right)
        filtered.sort(key=lambda r: r[0])
        
        return filtered
    
    def save_regions_with_debug(self, regions: Dict[str, Any], output_dir: Path, 
                               screenshot_name: str) -> Dict[str, Path]:
        """Save all regions with debug visualization.
        
        Args:
            regions: Region data from extract_regions
            output_dir: Output directory
            screenshot_name: Base name for output files
            
        Returns:
            Dictionary mapping region names to saved file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = {}
        
        # Save individual regions
        for region_name, region_data in regions.items():
            if region_name == "screenshot_info":
                continue
                
            region_image = region_data["image"]
            region_path = output_dir / f"{screenshot_name}_{region_name}.png"
            region_image.save(region_path)
            saved_files[region_name] = region_path
            
            if self.debug:
                print(f"Saved {region_name}: {region_path}")
        
        # Create debug visualization
        if self.debug:
            debug_path = self._create_debug_visualization(regions, output_dir, screenshot_name)
            saved_files["debug_visualization"] = debug_path
        
        return saved_files
    
    def extract_and_save_cards(self, cards_region: Image.Image, output_dir: Path, 
                              screenshot_name: str) -> List[Path]:
        """Extract individual cards from the cards region.
        
        Args:
            cards_region: PIL Image of the cards region
            output_dir: Output directory
            screenshot_name: Base name for output files
            
        Returns:
            List of paths to saved card images
        """
        # Detect cards
        card_regions = self.detect_cards_advanced(cards_region)
        
        if not card_regions:
            if self.debug:
                print("No cards detected in the cards region")
            return []
        
        # Save individual cards
        saved_cards = []
        for i, (x, y, w, h) in enumerate(card_regions):
            # Extract card
            card_img = cards_region.crop((x, y, x + w, y + h))
            
            # Save card
            card_path = output_dir / f"{screenshot_name}_card{i+1}.png"
            card_img.save(card_path)
            saved_cards.append(card_path)
            
            if self.debug:
                print(f"  Card {i+1}: {w}x{h} at ({x}, {y}) -> {card_path}")
        
        # Create cards debug visualization
        if self.debug:
            debug_path = self._create_cards_debug_visualization(
                cards_region, card_regions, output_dir, screenshot_name
            )
            saved_cards.append(debug_path)
        
        return saved_cards
    
    def _create_debug_visualization(self, regions: Dict[str, Any], output_dir: Path, 
                                  screenshot_name: str) -> Path:
        """Create a debug visualization showing all regions."""
        # Load original screenshot
        original = Image.open(regions["screenshot_info"]["path"])
        
        # Create a copy for drawing
        debug_img = original.copy()
        draw = ImageDraw.Draw(debug_img)
        
        # Draw region boundaries
        colors = {
            "data_region": "red",
            "jokers_region": "blue", 
            "cards_region": "green"
        }
        
        for region_name, color in colors.items():
            if region_name in regions:
                bounds = regions[region_name]["bounds"]
                # Draw rectangle outline
                draw.rectangle(bounds, outline=color, width=5)
                
                # Add label
                label_x = bounds[0] + 10
                label_y = bounds[1] + 10
                draw.text((label_x, label_y), region_name.replace("_", " ").title(), 
                         fill=color)
        
        # Save debug image
        debug_path = output_dir / f"{screenshot_name}_debug_regions.png"
        debug_img.save(debug_path)
        
        print(f"Debug visualization saved: {debug_path}")
        return debug_path
    
    def _create_cards_debug_visualization(self, cards_image: Image.Image, 
                                        card_regions: List[Tuple[int, int, int, int]],
                                        output_dir: Path, screenshot_name: str) -> Path:
        """Create debug visualization for card detection."""
        debug_img = cards_image.copy()
        draw = ImageDraw.Draw(debug_img)
        
        # Draw detected card regions
        for i, (x, y, w, h) in enumerate(card_regions):
            # Draw rectangle
            draw.rectangle([x, y, x + w, y + h], outline="red", width=3)
            
            # Add card number
            draw.text((x + 5, y + 5), str(i + 1), fill="red")
        
        # Save debug image
        debug_path = output_dir / f"{screenshot_name}_debug_cards.png"
        debug_img.save(debug_path)
        
        print(f"Cards debug visualization saved: {debug_path}")
        return debug_path
    
    def process_screenshot(self, screenshot_path: Path, output_dir: Path = None) -> Dict[str, Any]:
        """Process a complete screenshot and extract all regions and cards.
        
        Args:
            screenshot_path: Path to the screenshot
            output_dir: Output directory (defaults to dataset/debug_cards)
            
        Returns:
            Dictionary with processing results
        """
        if output_dir is None:
            output_dir = Path("dataset/debug_cards")
        
        screenshot_name = screenshot_path.stem
        
        # Extract regions
        regions = self.extract_regions(screenshot_path)
        
        # Save regions
        saved_regions = self.save_regions_with_debug(regions, output_dir, screenshot_name)
        
        # Extract cards from the cards region
        cards_region = regions["cards_region"]["image"]
        saved_cards = self.extract_and_save_cards(cards_region, output_dir, screenshot_name)
        
        # Create summary
        results = {
            "screenshot_info": regions["screenshot_info"],
            "regions": {
                name: {
                    "bounds": data["bounds"],
                    "size": data["size"],
                    "saved_path": str(saved_regions.get(name, ""))
                }
                for name, data in regions.items()
                if name != "screenshot_info"
            },
            "cards": {
                "count": len(saved_cards) - (1 if self.debug else 0),  # Subtract debug file
                "saved_paths": [str(p) for p in saved_cards if not p.name.endswith("_debug_cards.png")]
            },
            "debug_files": [str(p) for p in saved_cards if p.name.endswith("_debug_cards.png")] + 
                          [str(saved_regions.get("debug_visualization", ""))]
        }
        
        return results


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python improved_screenshot_processor.py <screenshot.png> [--debug]")
        print("Example: python improved_screenshot_processor.py dataset/raw/BalatroExample1.png --debug")
        return
    
    screenshot_path = Path(sys.argv[1])
    debug = "--debug" in sys.argv
    
    if not screenshot_path.exists():
        print(f"Error: Screenshot not found: {screenshot_path}")
        return
    
    print("=== Improved Balatro Screenshot Processor ===")
    print(f"Processing: {screenshot_path}")
    print(f"Debug mode: {'ON' if debug else 'OFF'}")
    print()
    
    # Create processor
    processor = BalatroScreenProcessor(debug=debug)
    
    # Process screenshot
    results = processor.process_screenshot(screenshot_path)
    
    # Print results
    print("=== Processing Results ===")
    print(f"Screenshot: {results['screenshot_info']['resolution'][0]}x{results['screenshot_info']['resolution'][1]}")
    print(f"Cards detected: {results['cards']['count']}")
    print(f"Files saved: {len(results['cards']['saved_paths']) + len(results['regions'])}")
    
    if debug:
        print(f"Debug files: {len(results['debug_files'])}")
    
    print("\nNext steps:")
    print("1. Review the extracted cards and regions")
    print("2. Use the GUI labeling mode to label the cards")
    print("3. Run integrity checks on the dataset")


if __name__ == "__main__":
    main()