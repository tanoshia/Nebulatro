#!/usr/bin/env python3
"""
Extract Cards from Screenshot - Extract individual cards from Balatro screenshots

DEPRECATED: This tool has been replaced by improved_screenshot_processor.py
This wrapper provides backward compatibility while redirecting to the new tool.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.improved_screenshot_processor import BalatroScreenProcessor


def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_cards_from_screenshot.py <screenshot.png>")
        print("Example: python extract_cards_from_screenshot.py dataset/raw/BalatroExample1.png")
        print()
        print("NOTE: This tool has been upgraded! For advanced features, use:")
        print("  python src/tools/improved_screenshot_processor.py <screenshot.png> --debug")
        print("  python src/tools/batch_screenshot_processor.py --tune --debug")
        return
    
    screenshot_path = Path(sys.argv[1])
    
    if not screenshot_path.exists():
        print(f"Error: Screenshot not found: {screenshot_path}")
        return
    
    print("=== Card Extractor (Legacy Compatibility) ===")
    print("This tool now uses the improved screenshot processor")
    print("For advanced features, use improved_screenshot_processor.py")
    print()
    
    # Use improved processor with optimized parameters
    processor = BalatroScreenProcessor(debug=True)
    
    # Apply tuned parameters for better detection
    processor.min_card_area = 2000
    processor.max_card_area = 40000
    processor.canny_low = 20
    processor.canny_high = 80
    
    # Process screenshot
    results = processor.process_screenshot(screenshot_path)
    
    # Print legacy-style output
    print(f"\nExtracted {results['cards']['count']} cards to dataset/debug_cards")
    print("Next steps:")
    print("1. Review the cards and regions in dataset/debug_cards")
    print("2. Use the GUI labeling mode to label the cards")
    print("3. For batch processing, use: python src/tools/batch_screenshot_processor.py")


if __name__ == "__main__":
    main()