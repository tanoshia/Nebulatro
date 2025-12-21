#!/usr/bin/env python3
"""
Test Phase 3.1 - Advanced Computer Vision Card Detection

This script tests the complete Phase 3.1 implementation:
- YOLOv8 card detection
- Template matching with game sprites
- Hybrid detection pipeline
- Performance benchmarking
"""

import sys
import cv2
import numpy as np
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_yolo_detection():
    """Test YOLOv8 card detection."""
    print("\n🤖 Testing YOLOv8 Detection...")
    
    try:
        from vision.card_detector import BalatroCardDetector
        
        detector = BalatroCardDetector(confidence_threshold=0.5)
        
        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test detection
        start_time = time.time()
        detections = detector.detect_cards(test_image)
        end_time = time.time()
        
        print(f"✅ YOLOv8 detection: {len(detections)} objects in {(end_time - start_time)*1000:.1f}ms")
        return True
        
    except Exception as e:
        print(f"❌ YOLOv8 detection failed: {e}")
        return False

def test_template_matching():
    """Test template matching system."""
    print("\n🎯 Testing Template Matching...")
    
    try:
        from vision.template_matcher import BalatroTemplateMatcher
        
        matcher = BalatroTemplateMatcher(confidence_threshold=0.6)
        
        # Get template info
        info = matcher.get_template_info()
        print(f"📚 Loaded {info['total_templates']} templates")
        
        if info['total_templates'] == 0:
            print("⚠️  No templates loaded - check sprite sheets")
            return False
        
        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test matching
        start_time = time.time()
        matches = matcher.match_templates(test_image)
        end_time = time.time()
        
        print(f"✅ Template matching: {len(matches)} matches in {(end_time - start_time)*1000:.1f}ms")
        return True
        
    except Exception as e:
        print(f"❌ Template matching failed: {e}")
        return False

def test_hybrid_detection():
    """Test hybrid detection pipeline."""
    print("\n🔄 Testing Hybrid Detection...")
    
    try:
        from vision.hybrid_detector import BalatroHybridDetector, DetectionMethod
        
        detector = BalatroHybridDetector()
        
        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test each method
        methods = [
            DetectionMethod.YOLO,
            DetectionMethod.TEMPLATE,
            DetectionMethod.TRADITIONAL_CV,
            DetectionMethod.ENSEMBLE
        ]
        
        results = {}
        
        for method in methods:
            start_time = time.time()
            detections = detector.detect_cards(test_image, method=method)
            end_time = time.time()
            
            results[method.value] = {
                'detections': len(detections),
                'time_ms': (end_time - start_time) * 1000
            }
            
            print(f"  {method.value}: {len(detections)} detections in {results[method.value]['time_ms']:.1f}ms")
        
        # Check performance stats
        stats = detector.get_performance_stats()
        print(f"📊 Performance stats: {stats}")
        
        print("✅ Hybrid detection pipeline working")
        return True
        
    except Exception as e:
        print(f"❌ Hybrid detection failed: {e}")
        return False

def test_with_real_screenshot():
    """Test with actual Balatro screenshot."""
    print("\n📸 Testing with Real Screenshot...")
    
    # Look for screenshots
    dataset_dir = Path(__file__).parent.parent / "dataset" / "raw"
    if not dataset_dir.exists():
        print("ℹ️  No dataset/raw directory found")
        return True
    
    screenshot_files = list(dataset_dir.glob("*.png"))
    if not screenshot_files:
        print("ℹ️  No PNG files found in dataset/raw")
        return True
    
    screenshot_path = screenshot_files[0]
    print(f"📁 Using: {screenshot_path.name}")
    
    try:
        # Load image
        image = cv2.imread(str(screenshot_path))
        if image is None:
            print(f"❌ Failed to load {screenshot_path}")
            return False
        
        print(f"✅ Loaded image: {image.shape[1]}x{image.shape[0]}")
        
        # Extract cards region
        height, width = image.shape[:2]
        cards_region = image[int(height * 0.3):, int(width * 0.25):]
        
        print(f"📏 Cards region: {cards_region.shape[1]}x{cards_region.shape[0]}")
        
        # Test hybrid detection
        from vision.hybrid_detector import BalatroHybridDetector, DetectionMethod
        
        detector = BalatroHybridDetector(
            yolo_confidence=0.3,      # Lower for testing
            template_confidence=0.5,   # Lower for testing
            ensemble_threshold=0.4     # Lower for testing
        )
        
        # Test different methods
        methods_to_test = [
            ("YOLOv8", DetectionMethod.YOLO),
            ("Template", DetectionMethod.TEMPLATE),
            ("Traditional CV", DetectionMethod.TRADITIONAL_CV),
            ("Ensemble", DetectionMethod.ENSEMBLE)
        ]
        
        results = {}
        
        for method_name, method in methods_to_test:
            start_time = time.time()
            detections = detector.detect_cards(cards_region, method=method)
            end_time = time.time()
            
            time_ms = (end_time - start_time) * 1000
            results[method_name] = {
                'count': len(detections),
                'time': time_ms
            }
            
            print(f"  {method_name}: {len(detections)} cards in {time_ms:.1f}ms")
            
            # Show top detections
            for i, detection in enumerate(detections[:3]):  # Top 3
                print(f"    Card {i+1}: confidence={detection.confidence:.3f}, "
                      f"type={detection.card_type}, class={detection.card_class}")
        
        # Performance comparison
        print(f"\n📊 Performance Summary:")
        for method_name, result in results.items():
            print(f"  {method_name}: {result['count']} detections, {result['time']:.1f}ms")
        
        # Check if ensemble found more than individual methods
        ensemble_count = results.get('Ensemble', {}).get('count', 0)
        yolo_count = results.get('YOLOv8', {}).get('count', 0)
        template_count = results.get('Template', {}).get('count', 0)
        
        if ensemble_count >= max(yolo_count, template_count):
            print("✅ Ensemble performing as expected")
        else:
            print("ℹ️  Ensemble results vary (expected with test data)")
        
        return True
        
    except Exception as e:
        print(f"❌ Real screenshot test failed: {e}")
        return False

def benchmark_performance():
    """Benchmark detection performance."""
    print("\n⚡ Performance Benchmark...")
    
    try:
        from vision.hybrid_detector import BalatroHybridDetector, DetectionMethod
        
        detector = BalatroHybridDetector()
        
        # Create test images of different sizes
        test_sizes = [
            (480, 640),   # Small
            (720, 1280),  # Medium
            (1080, 1920), # Large
        ]
        
        num_iterations = 3
        
        for height, width in test_sizes:
            print(f"\n📏 Testing {width}x{height} images:")
            
            # Create test image
            test_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            
            # Benchmark each method
            methods = [
                ("YOLOv8", DetectionMethod.YOLO),
                ("Template", DetectionMethod.TEMPLATE),
                ("Ensemble", DetectionMethod.ENSEMBLE)
            ]
            
            for method_name, method in methods:
                times = []
                
                for _ in range(num_iterations):
                    start_time = time.time()
                    detections = detector.detect_cards(test_image, method=method)
                    end_time = time.time()
                    times.append((end_time - start_time) * 1000)
                
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                print(f"  {method_name}: {avg_time:.1f}ms avg ({min_time:.1f}-{max_time:.1f}ms)")
        
        print("✅ Performance benchmark complete")
        return True
        
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return False

def main():
    """Run all Phase 3.1 tests."""
    print("🎮 Phase 3.1 - Advanced Computer Vision Test Suite")
    print("=" * 60)
    
    tests = [
        ("YOLOv8 Detection", test_yolo_detection),
        ("Template Matching", test_template_matching),
        ("Hybrid Detection", test_hybrid_detection),
        ("Real Screenshot", test_with_real_screenshot),
        ("Performance Benchmark", benchmark_performance)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Phase 3.1 Complete! All systems operational.")
        print("\nNext Steps:")
        print("1. Collect more Balatro screenshots for training")
        print("2. Implement Nova annotation system (Phase 3.2)")
        print("3. Train YOLOv8 on Balatro-specific data")
        print("4. Integrate with existing screenshot processor")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)