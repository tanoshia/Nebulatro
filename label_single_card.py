#!/usr/bin/env python3
"""
Label Single Card - Interactive labeling for individual cropped card images
"""

import sys
import cv2
import numpy as np
from pathlib import Path
from PIL import Image


def show_card_reference():
    """Show card class reference"""
    print("\n=== Card Class Reference ===")
    suits = ["Hearts ♥", "Clubs ♣", "Diamonds ♦", "Spades ♠"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    
    for suit_idx, suit in enumerate(suits):
        print(f"\n{suit}:")
        for rank_idx, rank in enumerate(ranks):
            class_id = suit_idx * 13 + rank_idx
            print(f"  {class_id:2d}: {rank}")


def process_image(image):
    """Process image for training (now uses full image)"""
    return image


def label_card(image_path):
    """Label a single card image"""
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"Error: {image_path} not found")
        return
    
    # Load image
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Error: Could not load {image_path}")
        return
    
    # Process image (now uses full image)
    processed_image = process_image(image)
    
    # Save preview in the same directory as the card
    preview_dir = image_path.parent / "previews"
    preview_dir.mkdir(exist_ok=True)
    preview_path = preview_dir / f"{image_path.stem}_preview.png"
    cv2.imwrite(str(preview_path), processed_image)
    
    # Also save a side-by-side comparison
    full_resized = cv2.resize(image, (200, 240))  # Resize full card for comparison
    corner_resized = cv2.resize(corner, (200, 240))  # Resize corner to same size
    
    # Create side-by-side image
    comparison = np.hstack([full_resized, corner_resized])
    comparison_path = preview_dir / f"{image_path.stem}_comparison.png"
    cv2.imwrite(str(comparison_path), comparison)
    
    print(f"\nLabeling: {image_path.name}")
    print(f"Card size: {image.shape[1]}x{image.shape[0]}")
    print(f"Corner size: {corner.shape[1]}x{corner.shape[0]}")
    print(f"Corner preview: {preview_path}")
    print(f"Comparison view: {comparison_path}")
    print("(Left=full card, Right=corner that model sees)")
    
    # Try to open the comparison image automatically
    try:
        import subprocess
        subprocess.run(["open", str(comparison_path)], check=False)
        print("✓ Opened comparison image")
    except:
        print("→ Please open the comparison image manually to see the card")
    
    show_card_reference()
    
    while True:
        print(f"\nEnter card class (0-51), 'r' for reference, 's' to skip, 'q' to quit:")
        response = input("> ").strip().lower()
        
        if response == 'q':
            return None
        elif response == 's':
            return 'skip'
        elif response == 'r':
            show_card_reference()
            continue
        
        try:
            class_id = int(response)
            if 0 <= class_id <= 51:
                return class_id
            else:
                print("Error: Class must be 0-51")
        except ValueError:
            print("Error: Enter a number, 'r', 's', or 'q'")


def save_labeled_card(image_path, class_id):
    """Save labeled card to training directory"""
    image_path = Path(image_path)
    
    # Create class directory
    class_dir = Path("training_data/processed/cards") / str(class_id)
    class_dir.mkdir(parents=True, exist_ok=True)
    
    # Load and process image
    image = cv2.imread(str(image_path))
    processed_image = process_image(image)
    
    # Save processed image (full image for training)
    output_path = class_dir / f"{image_path.stem}.png"
    cv2.imwrite(str(output_path), processed_image)
    
    print(f"✓ Saved to: {output_path}")
    
    return output_path


def main():
    if len(sys.argv) != 2:
        print("Usage: python label_single_card.py <card_image.png>")
        print("Example: python label_single_card.py training_data/debug_cards/card1.png")
        return
    
    image_path = sys.argv[1]
    
    print("=== Single Card Labeler ===")
    print("This tool shows you the corner region that the model will see")
    print("and lets you assign the correct class (0-51).")
    
    class_id = label_card(image_path)
    
    if class_id is None:
        print("Quit.")
    elif class_id == 'skip':
        print("Skipped.")
    else:
        save_labeled_card(image_path, class_id)
        print(f"Card labeled as class {class_id}")


if __name__ == "__main__":
    main()