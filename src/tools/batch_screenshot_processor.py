#!/usr/bin/env python3
"""
Batch Screenshot Processor - Process multiple Balatro screenshots

This tool processes all screenshots in the dataset/raw directory and provides
comprehensive analysis and card extraction with parameter tuning.
"""

import sys
from pathlib import Path
import json
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.improved_screenshot_processor import BalatroScreenProcessor
from ml.dataset_writer import get_dataset_writer
from ml.dataset_indexer import get_dataset_indexer


class BatchScreenshotProcessor:
    """Batch processor for multiple screenshots with analysis and tuning."""
    
    def __init__(self, debug: bool = False):
        """Initialize batch processor.
        
        Args:
            debug: Enable debug output
        """
        self.debug = debug
        self.processor = BalatroScreenProcessor(debug=debug)
        
    def process_all_screenshots(self, input_dir: Path = None, output_dir: Path = None) -> Dict[str, Any]:
        """Process all screenshots in the input directory.
        
        Args:
            input_dir: Directory containing screenshots (defaults to dataset/raw)
            output_dir: Output directory (defaults to dataset/debug_cards)
            
        Returns:
            Dictionary with batch processing results
        """
        if input_dir is None:
            input_dir = Path("dataset/raw")
        if output_dir is None:
            output_dir = Path("dataset/debug_cards")
        
        # Find all screenshot files
        screenshot_extensions = {".png", ".jpg", ".jpeg"}
        screenshots = [
            f for f in input_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in screenshot_extensions
        ]
        
        if not screenshots:
            print(f"No screenshots found in {input_dir}")
            return {"error": "No screenshots found"}
        
        print(f"Found {len(screenshots)} screenshots to process")
        
        # Process each screenshot
        results = {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "screenshots_processed": 0,
            "total_cards_detected": 0,
            "screenshots": {},
            "summary": {}
        }
        
        for screenshot_path in sorted(screenshots):
            print(f"\nProcessing: {screenshot_path.name}")
            
            try:
                # Process screenshot
                screenshot_results = self.processor.process_screenshot(screenshot_path, output_dir)
                
                # Store results
                results["screenshots"][screenshot_path.name] = screenshot_results
                results["screenshots_processed"] += 1
                results["total_cards_detected"] += screenshot_results["cards"]["count"]
                
                print(f"  Resolution: {screenshot_results['screenshot_info']['resolution'][0]}x{screenshot_results['screenshot_info']['resolution'][1]}")
                print(f"  Cards detected: {screenshot_results['cards']['count']}")
                
            except Exception as e:
                print(f"  Error processing {screenshot_path.name}: {e}")
                results["screenshots"][screenshot_path.name] = {"error": str(e)}
        
        # Generate summary
        self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> None:
        """Generate processing summary."""
        successful_screenshots = [
            name for name, data in results["screenshots"].items() 
            if "error" not in data
        ]
        
        failed_screenshots = [
            name for name, data in results["screenshots"].items() 
            if "error" in data
        ]
        
        # Calculate statistics
        resolutions = []
        cards_per_screenshot = []
        
        for name in successful_screenshots:
            screenshot_data = results["screenshots"][name]
            resolution = screenshot_data["screenshot_info"]["resolution"]
            resolutions.append(f"{resolution[0]}x{resolution[1]}")
            cards_per_screenshot.append(screenshot_data["cards"]["count"])
        
        # Create summary
        summary = {
            "total_screenshots": len(results["screenshots"]),
            "successful": len(successful_screenshots),
            "failed": len(failed_screenshots),
            "total_cards": results["total_cards_detected"],
            "average_cards_per_screenshot": (
                sum(cards_per_screenshot) / len(cards_per_screenshot) 
                if cards_per_screenshot else 0
            ),
            "resolutions_found": list(set(resolutions)),
            "failed_screenshots": failed_screenshots
        }
        
        results["summary"] = summary
        
        # Print summary
        print("\n" + "="*50)
        print("BATCH PROCESSING SUMMARY")
        print("="*50)
        print(f"Screenshots processed: {summary['successful']}/{summary['total_screenshots']}")
        print(f"Total cards detected: {summary['total_cards']}")
        print(f"Average cards per screenshot: {summary['average_cards_per_screenshot']:.1f}")
        print(f"Resolutions found: {', '.join(summary['resolutions_found'])}")
        
        if summary['failed']:
            print(f"Failed screenshots: {', '.join(summary['failed_screenshots'])}")
    
    def tune_detection_parameters(self, test_screenshot: Path = None) -> Dict[str, Any]:
        """Tune card detection parameters using a test screenshot.
        
        Args:
            test_screenshot: Path to test screenshot (uses first available if None)
            
        Returns:
            Dictionary with tuning results
        """
        if test_screenshot is None:
            # Find first available screenshot
            raw_dir = Path("dataset/raw")
            screenshots = list(raw_dir.glob("*.png"))
            if not screenshots:
                return {"error": "No test screenshots available"}
            test_screenshot = screenshots[0]
        
        print(f"Tuning detection parameters using: {test_screenshot.name}")
        
        # Test different parameter combinations
        parameter_sets = [
            {"min_area": 2000, "max_area": 40000, "canny_low": 20, "canny_high": 80},
            {"min_area": 3000, "max_area": 50000, "canny_low": 30, "canny_high": 100},
            {"min_area": 4000, "max_area": 60000, "canny_low": 40, "canny_high": 120},
            {"min_area": 1500, "max_area": 35000, "canny_low": 25, "canny_high": 90},
        ]
        
        results = {"test_screenshot": str(test_screenshot), "parameter_tests": []}
        
        for i, params in enumerate(parameter_sets):
            print(f"\nTesting parameter set {i+1}: {params}")
            
            # Create processor with test parameters
            test_processor = BalatroScreenProcessor(debug=False)
            test_processor.min_card_area = params["min_area"]
            test_processor.max_card_area = params["max_area"]
            test_processor.canny_low = params["canny_low"]
            test_processor.canny_high = params["canny_high"]
            
            # Extract regions and test card detection
            regions = test_processor.extract_regions(test_screenshot)
            cards_region = regions["cards_region"]["image"]
            detected_cards = test_processor.detect_cards_advanced(cards_region)
            
            test_result = {
                "parameters": params,
                "cards_detected": len(detected_cards),
                "card_regions": detected_cards
            }
            
            results["parameter_tests"].append(test_result)
            print(f"  Cards detected: {len(detected_cards)}")
        
        # Find best parameters (most cards detected)
        best_test = max(results["parameter_tests"], key=lambda x: x["cards_detected"])
        results["best_parameters"] = best_test["parameters"]
        results["best_card_count"] = best_test["cards_detected"]
        
        print(f"\nBest parameters: {results['best_parameters']}")
        print(f"Best card count: {results['best_card_count']}")
        
        return results
    
    def save_batch_results(self, results: Dict[str, Any], output_path: Path = None) -> Path:
        """Save batch processing results to JSON file.
        
        Args:
            results: Results from process_all_screenshots
            output_path: Output file path
            
        Returns:
            Path to saved results file
        """
        if output_path is None:
            output_path = Path("dataset/batch_processing_results.json")
        
        # Use dataset writer for atomic save
        dataset_writer = get_dataset_writer()
        
        # Convert Path objects to strings for JSON serialization
        json_results = self._prepare_for_json(results)
        
        # Save using dataset writer (as annotation-style JSON)
        results_path = dataset_writer.write_annotation(json_results, "batch_processing_results")
        
        print(f"Batch results saved to: {results_path}")
        return results_path
    
    def _prepare_for_json(self, obj: Any) -> Any:
        """Prepare object for JSON serialization by converting Path objects."""
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._prepare_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        else:
            return obj


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process Balatro screenshots")
    parser.add_argument("--input-dir", type=Path, default=Path("dataset/raw"),
                       help="Input directory containing screenshots")
    parser.add_argument("--output-dir", type=Path, default=Path("dataset/debug_cards"),
                       help="Output directory for extracted regions and cards")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output and visualizations")
    parser.add_argument("--tune", action="store_true",
                       help="Tune detection parameters before processing")
    parser.add_argument("--save-results", action="store_true",
                       help="Save batch results to JSON file")
    
    args = parser.parse_args()
    
    print("=== Batch Screenshot Processor ===")
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Debug mode: {'ON' if args.debug else 'OFF'}")
    print()
    
    # Create batch processor
    batch_processor = BatchScreenshotProcessor(debug=args.debug)
    
    # Tune parameters if requested
    if args.tune:
        print("Tuning detection parameters...")
        tuning_results = batch_processor.tune_detection_parameters()
        
        if "best_parameters" in tuning_results:
            # Apply best parameters
            best_params = tuning_results["best_parameters"]
            batch_processor.processor.min_card_area = best_params["min_area"]
            batch_processor.processor.max_card_area = best_params["max_area"]
            batch_processor.processor.canny_low = best_params["canny_low"]
            batch_processor.processor.canny_high = best_params["canny_high"]
            print("Applied best parameters to processor")
        print()
    
    # Process all screenshots
    results = batch_processor.process_all_screenshots(args.input_dir, args.output_dir)
    
    # Save results if requested
    if args.save_results:
        batch_processor.save_batch_results(results)
    
    # Update dataset index
    print("\nUpdating dataset index...")
    indexer = get_dataset_indexer()
    indexer.update_index(force_rebuild=True)
    print("Dataset index updated")
    
    print("\nBatch processing complete!")


if __name__ == "__main__":
    main()