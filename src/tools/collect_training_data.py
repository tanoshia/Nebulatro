#!/usr/bin/env python3
"""
Training Data Collector - Extract and label cards from screenshots
"""

import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.vision import ScreenCapture, CardRecognizer
from src.utils import SpriteLoader


class DataCollector:
    """Collects and labels training data from screenshots"""
    
    def __init__(self, output_dir="dataset/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create card class directories (0-51 for playing cards)
        self.cards_dir = self.output_dir / "cards"
        for i in range(52):
            (self.cards_dir / str(i)).mkdir(parents=True, exist_ok=True)
        
        # Initialize vision components
        self.screen_capture = ScreenCapture()
        sprite_loader = SpriteLoader()
        self.card_recognizer = CardRecognizer(sprite_loader)
        
        # Card name mapping for labeling
        self.card_names = self._create_card_mapping()
        
        print(f"Data collector initialized. Output: {self.output_dir}")
    
    def _create_card_mapping(self):
        """Create mapping from card index to readable name"""
        suits = ['Hearts', 'Clubs', 'Diamonds', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        
        mapping = {}
        for suit_idx, suit in enumerate(suits):
            for rank_idx, rank in enumerate(ranks):
                card_idx = suit_idx * 13 + rank_idx
                mapping[card_idx] = f"{rank} of {suit}"
        
        return mapping
    
    def process_screenshot(self, image_path):
        """Process a screenshot and extract cards for labeling"""
        print(f"\nProcessing: {image_path}")
        
        # Load screenshot
        screenshot = self.screen_capture.capture_from_file(image_path)
        
        # Extract card region
        card_region = self.screen_capture.get_card_region(screenshot)
        if card_region is None:
            print("Could not extract card region")
            return
        
        # Detect cards
        card_regions = self.card_recognizer.detect_cards(card_region)
        print(f"Detected {len(card_regions)} card regions")
        
        if not card_regions:
            print("No cards detected")
            return
        
        # Extract each card and show for labeling
        for i, (x, y, w, h) in enumerate(card_regions):
            card_img = card_region.crop((x, y, x + w, y + h))
            
            # Extract corner region (what the model will see)
            corner_h = int(card_img.height * 0.35)
            corner_w = int(card_img.width * 0.35)
            corner_img = card_img.crop((0, 0, corner_w, corner_h))
            
            # Show card for labeling
            self._label_card(corner_img, f"{Path(image_path).stem}_card_{i+1}")
    
    def _label_card(self, card_image, card_id):
        """Show card and get user label"""
        # Convert PIL to OpenCV for display
        img_array = np.array(card_image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Resize for better visibility
        display_img = cv2.resize(img_bgr, (200, 200), interpolation=cv2.INTER_NEAREST)
        
        # Show image
        cv2.imshow(f'Label Card: {card_id}', display_img)
        
        print(f"\nLabeling card: {card_id}")
        print("Enter card class (0-51) or 's' to skip, 'q' to quit:")
        print("Examples: 0=2♥, 12=A♥, 13=2♣, 25=A♣, 26=2♦, 38=A♦, 39=2♠, 51=A♠")
        
        while True:
            key = cv2.waitKey(0) & 0xFF
            
            if key == ord('q'):
                cv2.destroyAllWindows()
                return False
            elif key == ord('s'):
                print("Skipped")
                cv2.destroyWindow(f'Label Card: {card_id}')
                return True
            elif key >= ord('0') and key <= ord('9'):
                # Start number input
                cv2.destroyWindow(f'Label Card: {card_id}')
                
                # Get full number from user
                try:
                    user_input = input("Enter card class (0-51): ")
                    if user_input.lower() == 's':
                        print("Skipped")
                        return True
                    elif user_input.lower() == 'q':
                        return False
                    
                    class_idx = int(user_input)
                    if 0 <= class_idx <= 51:
                        self._save_labeled_card(card_image, class_idx, card_id)
                        print(f"Saved as: {self.card_names[class_idx]}")
                        return True
                    else:
                        print("Invalid class. Must be 0-51")
                        return True
                except ValueError:
                    print("Invalid input")
                    return True
    
    def _save_labeled_card(self, card_image, class_idx, card_id):
        """Save labeled card to appropriate directory"""
        class_dir = self.cards_dir / str(class_idx)
        
        # Count existing files to avoid overwriting
        existing_files = list(class_dir.glob("*.png"))
        file_num = len(existing_files) + 1
        
        filename = f"{card_id}_{file_num:03d}.png"
        save_path = class_dir / filename
        
        card_image.save(save_path)
        print(f"Saved to: {save_path}")
    
    def batch_process(self, screenshots_dir):
        """Process multiple screenshots"""
        screenshots_dir = Path(screenshots_dir)
        
        if not screenshots_dir.exists():
            print(f"Directory not found: {screenshots_dir}")
            return
        
        # Find all image files
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(screenshots_dir.glob(ext))
        
        if not image_files:
            print(f"No image files found in {screenshots_dir}")
            return
        
        print(f"Found {len(image_files)} screenshots to process")
        
        for i, img_file in enumerate(image_files):
            print(f"\n--- Processing {i+1}/{len(image_files)} ---")
            
            if not self.process_screenshot(img_file):
                print("Quitting...")
                break
        
        cv2.destroyAllWindows()
        print("\nData collection complete!")
        self._print_summary()
    
    def _print_summary(self):
        """Print summary of collected data"""
        print("\nData Collection Summary:")
        
        total_samples = 0
        for class_idx in range(52):
            class_dir = self.cards_dir / str(class_idx)
            count = len(list(class_dir.glob("*.png")))
            if count > 0:
                print(f"  Class {class_idx:2d} ({self.card_names[class_idx]}): {count} samples")
                total_samples += count
        
        print(f"\nTotal samples collected: {total_samples}")
        
        if total_samples > 0:
            print(f"\nReady for training! Run:")
            print(f"  python train_card_classifier.py")


def main():
    """Main function"""
    print("=== Balatro Training Data Collector ===\n")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python collect_training_data.py <screenshot_file>")
        print("  python collect_training_data.py <screenshots_directory>")
        print("\nThis tool helps you label cards from screenshots for training.")
        print("Controls:")
        print("  - Enter number (0-51) to label card")
        print("  - 's' to skip card")
        print("  - 'q' to quit")
        return
    
    input_path = Path(sys.argv[1])
    collector = DataCollector()
    
    if input_path.is_file():
        # Process single screenshot
        collector.process_screenshot(input_path)
    elif input_path.is_dir():
        # Process directory of screenshots
        collector.batch_process(input_path)
    else:
        print(f"Path not found: {input_path}")


if __name__ == "__main__":
    main()