#!/usr/bin/env python3
"""
Test YOLOv8 setup for Balatro card detection.

This script verifies that YOLOv8 is properly installed and can detect objects
in a sample image. Run this before starting Phase 3.1 implementation.
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from vision.card_detector import BalatroCardDetector
    print("✅ Successfully imported BalatroCardDetector")
except ImportError as e:
    print(f"❌ Failed to import BalatroCardDetector: {e}")
    print("Install dependencies with: pip install ultralytics")
    sys.exit(1)

def test_yolo_basic():
    """Test basic YOLOv8 functionality."""
    print("\n🧪 Testing YOLOv8 basic functionality...")
    
    try:
        # Initialize detector
        detector = BalatroCardDetector(confidence_threshold=0.5)
        print("✅ YOLOv8 model loaded successfully")
        
        # Create a test image (random noise)
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Run detection (should return empty list for random noise)
        detections = detector.detect_cards(test_image)
        print(f"✅ Detection ran successfully, found {len(detections)} objects")
        
        # Test performance
        import time
        start_time = time.time()
        for _ in range(5):
            detector.detect_cards(test_image)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 5 * 1000  # Convert to ms
        print(f"✅ Average detection time: {avg_time:.1f}ms")
        
        if avg_time < 100:
            print("🚀 Performance is excellent (<100ms)")
        elif avg_time < 500:
            print("⚡ Performance is good (<500ms)")
        else:
            print("⚠️  Performance is slow (>500ms) - consider GPU acceleration")
        
        return True
        
    except Exception as e:
        print(f"❌ YOLOv8 test failed: {e}")
        return False

def test_with_sample_screenshot():
    """Test with an actual Balatro screenshot if available."""
    print("\n📸 Testing with sample screenshot...")
    
    # Look for sample screenshots
    dataset_dir = Path(__file__).parent.parent / "dataset" / "raw"
    if not dataset_dir.exists():
        print("ℹ️  No dataset/raw directory found, skipping screenshot test")
        return True
    
    screenshot_files = list(dataset_dir.glob("*.png"))
    if not screenshot_files:
        print("ℹ️  No PNG files found in dataset/raw, skipping screenshot test")
        return True
    
    # Use first screenshot
    screenshot_path = screenshot_files[0]
    print(f"📁 Using screenshot: {screenshot_path}")
    
    try:
        # Load image
        image = cv2.imread(str(screenshot_path))
        if image is None:
            print(f"❌ Failed to load image: {screenshot_path}")
            return False
        
        print(f"✅ Loaded image: {image.shape[1]}x{image.shape[0]}")
        
        # Initialize detector
        detector = BalatroCardDetector(confidence_threshold=0.3)  # Lower threshold for testing
        
        # Extract cards region (bottom right 70% as per our architecture)
        height, width = image.shape[:2]
        cards_region = image[int(height * 0.3):, int(width * 0.25):]
        
        print(f"📏 Cards region: {cards_region.shape[1]}x{cards_region.shape[0]}")
        
        # Run detection
        detections = detector.detect_cards(cards_region, region_type='cards')
        
        print(f"🎯 Found {len(detections)} potential cards")
        
        for i, detection in enumerate(detections):
            print(f"  Card {i+1}: {detection.card_type} (confidence: {detection.confidence:.3f})")
        
        # Note: With pre-trained model, we expect mostly false positives
        # This will improve dramatically once we train on Balatro data
        if len(detections) > 0:
            print("✅ Detection pipeline working (results will improve with training)")
        else:
            print("ℹ️  No detections (expected with pre-trained model)")
        
        return True
        
    except Exception as e:
        print(f"❌ Screenshot test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🎮 Balatro YOLOv8 Setup Test")
    print("=" * 40)
    
    # Test basic functionality
    basic_test_passed = test_yolo_basic()
    
    # Test with screenshot if available
    screenshot_test_passed = test_with_sample_screenshot()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"  Basic YOLOv8: {'✅ PASS' if basic_test_passed else '❌ FAIL'}")
    print(f"  Screenshot Test: {'✅ PASS' if screenshot_test_passed else '❌ FAIL'}")
    
    if basic_test_passed and screenshot_test_passed:
        print("\n🎉 All tests passed! Ready to start Phase 3.1")
        print("\nNext steps:")
        print("1. Collect Balatro screenshots for training data")
        print("2. Use Nova to generate bounding box annotations")
        print("3. Train YOLOv8 model on Balatro-specific data")
    else:
        print("\n⚠️  Some tests failed. Check dependencies and setup.")
        print("Install missing packages with: pip install -r requirements.txt")

if __name__ == "__main__":
    main()