#!/usr/bin/env python3
"""
Card Recognizer - Identifies cards and modifiers from game screenshots
"""

from PIL import Image
import numpy as np
from pathlib import Path
import cv2


class CardRecognizer:
    """Recognizes cards and modifiers from game screenshots"""
    
    def __init__(self, sprite_loader):
        """Initialize with sprite loader for template matching
        
        Args:
            sprite_loader: SpriteLoader instance with card sprites
        """
        self.sprite_loader = sprite_loader
        self.card_templates = {}
        self.modifier_templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load card and modifier sprites as templates for matching"""
        # Load playing cards as templates
        try:
            # Try to load 2x resolution textures first (better for matching high-res screenshots)
            from pathlib import Path
            
            texture_2x_path = Path("resources/textures/2x/8BitDeck.png")
            
            if texture_2x_path.exists():
                print("Loading 2x resolution card templates for better matching")
                # Load the 2x texture directly
                from PIL import Image
                deck_img = Image.open(texture_2x_path).convert('RGBA')
                
                # 8BitDeck is a 13x4 grid (13 ranks x 4 suits)
                card_width = deck_img.width // 13
                card_height = deck_img.height // 4
                
                # Extract each card
                for row in range(4):  # 4 suits
                    for col in range(13):  # 13 ranks
                        left = col * card_width
                        top = row * card_height
                        card_sprite = deck_img.crop((left, top, left + card_width, top + card_height))
                        
                        # DON'T composite with card back for templates
                        # The game cards already have their backing, so we want to match
                        # the face design directly (which has a white background in-game)
                        
                        # Convert RGBA to RGB with white background (like in-game cards)
                        if card_sprite.mode == 'RGBA':
                            # Create white background
                            white_bg = Image.new('RGB', card_sprite.size, (255, 255, 255))
                            white_bg.paste(card_sprite, mask=card_sprite.split()[3])  # Use alpha as mask
                            card_sprite = white_bg
                        
                        # Convert to numpy array
                        template = np.array(card_sprite.convert('RGB'))
                        idx = row * 13 + col
                        self.card_templates[idx] = template
                
                print(f"Loaded {len(self.card_templates)} card templates from 2x textures")
            else:
                # Fallback to sprite loader (1x resolution)
                print("2x textures not found, using 1x resolution templates")
                sheet_names = self.sprite_loader.get_sheet_names()
                if 'playing_cards' in sheet_names:
                    sprites = self.sprite_loader.get_all_sprites('playing_cards', composite_back=True)
                    
                    for idx, sprite in enumerate(sprites):
                        template = np.array(sprite.convert('RGB'))
                        self.card_templates[idx] = template
        
        except Exception as e:
            print(f"Warning: Could not load card templates: {e}")
            import traceback
            traceback.print_exc()
    
    def detect_cards(self, image):
        """Detect individual cards in an image
        
        Args:
            image: PIL Image of the game screen or card region
            
        Returns:
            List of detected card regions as (x, y, width, height) tuples
        """
        # Convert PIL to OpenCV format
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Try multiple detection methods
        card_regions = []
        
        # Method 1: Edge detection with multiple thresholds
        for low, high in [(30, 100), (50, 150), (70, 200)]:
            edges = cv2.Canny(gray, low, high)
            
            # Dilate edges to connect nearby edges
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                area = w * h
                
                # More lenient thresholds
                # Cards in Balatro can vary in size and aspect ratio
                if 0.4 < aspect_ratio < 1.2 and area > 500:
                    # Check if this region overlaps with existing regions
                    is_duplicate = False
                    for ex_x, ex_y, ex_w, ex_h in card_regions:
                        # Check for significant overlap
                        overlap_x = max(0, min(x + w, ex_x + ex_w) - max(x, ex_x))
                        overlap_y = max(0, min(y + h, ex_y + ex_h) - max(y, ex_y))
                        overlap_area = overlap_x * overlap_y
                        
                        if overlap_area > 0.5 * min(area, ex_w * ex_h):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        card_regions.append((x, y, w, h))
        
        # Method 2: Color-based detection (cards are usually lighter than background)
        # Apply threshold to find bright regions
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        # Find contours in thresholded image
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            area = w * h
            
            if 0.4 < aspect_ratio < 1.2 and area > 500:
                # Check for duplicates
                is_duplicate = False
                for ex_x, ex_y, ex_w, ex_h in card_regions:
                    overlap_x = max(0, min(x + w, ex_x + ex_w) - max(x, ex_x))
                    overlap_y = max(0, min(y + h, ex_y + ex_h) - max(y, ex_y))
                    overlap_area = overlap_x * overlap_y
                    
                    if overlap_area > 0.5 * min(area, ex_w * ex_h):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    card_regions.append((x, y, w, h))
        
        # Sort cards left to right
        card_regions.sort(key=lambda r: r[0])
        
        # Merge nearby regions that might be the same card
        merged_regions = []
        for x, y, w, h in card_regions:
            merged = False
            for i, (mx, my, mw, mh) in enumerate(merged_regions):
                # If regions are close horizontally, merge them
                if abs(x - mx) < 20 and abs(y - my) < 20:
                    # Take the larger bounding box
                    new_x = min(x, mx)
                    new_y = min(y, my)
                    new_w = max(x + w, mx + mw) - new_x
                    new_h = max(y + h, my + mh) - new_y
                    merged_regions[i] = (new_x, new_y, new_w, new_h)
                    merged = True
                    break
            
            if not merged:
                merged_regions.append((x, y, w, h))
        
        return merged_regions
    
    def recognize_card(self, card_image, use_features=True):
        """Recognize a specific card from an image region
        
        Uses feature-based matching (ORB) for robust recognition that works
        with jokers, consumables, and other visual elements.
        
        Args:
            card_image: PIL Image of a single card
            use_features: If True, use ORB feature matching; if False, use template matching
            
        Returns:
            tuple: (card_index, confidence) or (None, 0) if no match
        """
        if not self.card_templates:
            return None, 0
        
        # Convert to numpy array
        card_array = np.array(card_image.convert('RGB'))
        
        # Use full card image for recognition (matches training data)
        if use_features:
            return self._recognize_with_features(card_array)
        else:
            return self._recognize_with_template(card_array)
    
    def _recognize_with_features(self, card_image):
        """Use ORB feature matching for robust recognition"""
        # Convert to grayscale
        card_gray = cv2.cvtColor(card_image, cv2.COLOR_RGB2GRAY)
        
        # Initialize ORB detector
        orb = cv2.ORB_create(nfeatures=500)
        
        # Detect keypoints and compute descriptors for card
        kp1, des1 = orb.detectAndCompute(card_gray, None)
        
        if des1 is None or len(kp1) < 10:
            # Not enough features, fall back to template matching
            return self._recognize_with_template(card_image)
        
        # Create BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        best_match = None
        best_score = 0
        
        for card_idx, template in self.card_templates.items():
            # Use full template image
            template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
            
            # Detect keypoints and descriptors for template
            kp2, des2 = orb.detectAndCompute(template_gray, None)
            
            if des2 is None or len(kp2) < 10:
                continue
            
            try:
                # Match descriptors
                matches = bf.match(des1, des2)
                
                # Sort matches by distance (lower is better)
                matches = sorted(matches, key=lambda x: x.distance)
                
                # Calculate score based on good matches
                # Take top 30% of matches
                good_matches = matches[:max(1, len(matches) // 3)]
                
                if len(good_matches) > 0:
                    # Score based on number of good matches and their quality
                    avg_distance = sum(m.distance for m in good_matches) / len(good_matches)
                    # Normalize: more matches and lower distance = higher score
                    score = len(good_matches) / (1 + avg_distance / 100)
                    
                    if score > best_score:
                        best_score = score
                        best_match = card_idx
            
            except Exception as e:
                continue
        
        # Normalize score to 0-1 range (rough approximation)
        normalized_score = min(1.0, best_score / 20)
        
        if normalized_score > 0.3:
            return best_match, normalized_score
        
        return None, 0
    
    def _recognize_with_template(self, card_image):
        """Fallback template matching method"""
        best_match = None
        best_score = 0
        
        for card_idx, template in self.card_templates.items():
            # Use full template image
            # Calculate scale
            scale_h = card_image.shape[0] / template.shape[0]
            scale_w = card_image.shape[1] / template.shape[1]
            scale = (scale_h + scale_w) / 2
            
            # Resize template
            scaled_h = min(int(template.shape[0] * scale), card_image.shape[0])
            scaled_w = min(int(template.shape[1] * scale), card_image.shape[1])
            
            try:
                template_resized = cv2.resize(template, (scaled_w, scaled_h))
                result = cv2.matchTemplate(card_image, template_resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = card_idx
            except:
                continue
        
        if best_score > 0.5:
            return best_match, best_score
        
        return None, 0
    
    def detect_modifiers(self, card_image):
        """Detect modifiers on a card
        
        Args:
            card_image: PIL Image of a single card
            
        Returns:
            dict: {'enhancement': idx, 'edition': idx, 'seal': idx} or None for each
        """
        # TODO: Implement modifier detection
        # This will require analyzing specific regions of the card for modifier overlays
        return {
            'enhancement': None,
            'edition': None,
            'seal': None,
            'debuff': None
        }
    
    def recognize_hand(self, image):
        """Recognize all cards in a hand from an image
        
        Args:
            image: PIL Image of the card region
            
        Returns:
            List of dicts with card info: [{'index': int, 'modifiers': dict}, ...]
        """
        # Detect card regions
        card_regions = self.detect_cards(image)
        
        recognized_cards = []
        for x, y, w, h in card_regions:
            # Extract card region
            card_img = image.crop((x, y, x + w, y + h))
            
            # Recognize the card
            card_idx, confidence = self.recognize_card(card_img)
            
            if card_idx is not None:
                # Detect modifiers
                modifiers = self.detect_modifiers(card_img)
                
                recognized_cards.append({
                    'index': card_idx,
                    'confidence': confidence,
                    'modifiers': modifiers,
                    'region': (x, y, w, h)
                })
        
        return recognized_cards
