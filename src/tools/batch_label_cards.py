#!/usr/bin/env python3
"""
Batch Label Cards - Process multiple cropped card images
"""

import sys
from pathlib import Path
from label_single_card import label_card, save_labeled_card


def batch_label_directory(cards_dir):
    """Label all cards in a directory"""
    cards_dir = Path(cards_dir)
    
    if not cards_dir.exists():
        print(f"Error: Directory {cards_dir} not found")
        return
    
    # Find all image files
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_files.extend(cards_dir.glob(ext))
    
    if not image_files:
        print(f"No image files found in {cards_dir}")
        return
    
    print(f"Found {len(image_files)} images to label")
    
    labeled_count = 0
    skipped_count = 0
    
    for i, image_path in enumerate(image_files):
        print(f"\n=== Card {i+1}/{len(image_files)} ===")
        
        class_id = label_card(image_path)
        
        if class_id is None:
            print("Quit - stopping batch processing")
            break
        elif class_id == 'skip':
            print("Skipped")
            skipped_count += 1
        else:
            save_labeled_card(image_path, class_id)
            print(f"✓ Labeled as class {class_id}")
            labeled_count += 1
    
    print(f"\n=== Batch Complete ===")
    print(f"Labeled: {labeled_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Total processed: {labeled_count + skipped_count}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python batch_label_cards.py <directory>")
        print("Example: python batch_label_cards.py dataset/debug_cards/")
        return
    
    cards_dir = sys.argv[1]
    
    print("=== Batch Card Labeler ===")
    print("This will process all images in the specified directory")
    print("For each card, you'll see the corner region and assign a class (0-51)")
    print()
    
    batch_label_directory(cards_dir)


if __name__ == "__main__":
    main()