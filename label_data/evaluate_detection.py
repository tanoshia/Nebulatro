#!/usr/bin/env python3
"""
Detection Evaluation Tool

Compares detection results against ground truth annotations to measure accuracy.
Provides detailed metrics including precision, recall, F1-score, and IoU analysis.
"""

import sys
import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    mean_iou: float
    detection_count: int
    ground_truth_count: int

class DetectionEvaluator:
    """Evaluates detection performance against ground truth."""
    
    def __init__(self, iou_threshold: float = 0.5):
        """Initialize evaluator.
        
        Args:
            iou_threshold: Minimum IoU for a detection to be considered correct
        """
        self.iou_threshold = iou_threshold
    
    def calculate_iou(self, bbox1: Dict, bbox2: Dict) -> float:
        """Calculate Intersection over Union between two bounding boxes.
        
        Args:
            bbox1: First bounding box {x, y, width, height}
            bbox2: Second bounding box {x, y, width, height}
            
        Returns:
            IoU value between 0 and 1
        """
        x1, y1, w1, h1 = bbox1["x"], bbox1["y"], bbox1["width"], bbox1["height"]
        x2, y2, w2, h2 = bbox2["x"], bbox2["y"], bbox2["width"], bbox2["height"]
        
        # Calculate intersection
        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)
        
        if left >= right or top >= bottom:
            return 0.0
        
        intersection_area = (right - left) * (bottom - top)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union_area = area1 + area2 - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def match_detections_to_ground_truth(self, detections: List[Dict], 
                                       ground_truth: List[Dict]) -> Tuple[List[Tuple], List[int], List[int]]:
        """Match detections to ground truth using Hungarian algorithm (greedy approximation).
        
        Args:
            detections: List of detection dictionaries
            ground_truth: List of ground truth dictionaries
            
        Returns:
            Tuple of (matches, unmatched_detections, unmatched_ground_truth)
        """
        if not detections or not ground_truth:
            return [], list(range(len(detections))), list(range(len(ground_truth)))
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(detections), len(ground_truth)))
        
        for i, detection in enumerate(detections):
            for j, gt in enumerate(ground_truth):
                iou_matrix[i, j] = self.calculate_iou(detection["bbox"], gt["bbox"])
        
        # Greedy matching (simple approximation of Hungarian algorithm)
        matches = []
        used_detections = set()
        used_ground_truth = set()
        
        # Sort by IoU value (highest first)
        candidates = []
        for i in range(len(detections)):
            for j in range(len(ground_truth)):
                if iou_matrix[i, j] >= self.iou_threshold:
                    candidates.append((i, j, iou_matrix[i, j]))
        
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        for det_idx, gt_idx, iou_val in candidates:
            if det_idx not in used_detections and gt_idx not in used_ground_truth:
                matches.append((det_idx, gt_idx, iou_val))
                used_detections.add(det_idx)
                used_ground_truth.add(gt_idx)
        
        # Find unmatched
        unmatched_detections = [i for i in range(len(detections)) if i not in used_detections]
        unmatched_ground_truth = [i for i in range(len(ground_truth)) if i not in used_ground_truth]
        
        return matches, unmatched_detections, unmatched_ground_truth
    
    def evaluate_detections(self, detections: List[Dict], ground_truth: List[Dict]) -> EvaluationMetrics:
        """Evaluate detections against ground truth.
        
        Args:
            detections: List of detection results
            ground_truth: List of ground truth annotations
            
        Returns:
            Evaluation metrics
        """
        matches, unmatched_detections, unmatched_ground_truth = self.match_detections_to_ground_truth(
            detections, ground_truth
        )
        
        true_positives = len(matches)
        false_positives = len(unmatched_detections)
        false_negatives = len(unmatched_ground_truth)
        
        # Calculate metrics
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate mean IoU for matches
        mean_iou = np.mean([iou for _, _, iou in matches]) if matches else 0.0
        
        return EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            mean_iou=mean_iou,
            detection_count=len(detections),
            ground_truth_count=len(ground_truth)
        )
    
    def evaluate_image(self, image_path: Path, detection_method: str = "ensemble") -> Optional[Dict]:
        """Evaluate detection performance on a single image.
        
        Args:
            image_path: Path to the image file
            detection_method: Method to use for detection
            
        Returns:
            Evaluation results dictionary or None if evaluation failed
        """
        # Load ground truth
        gt_path = Path("dataset/ground_truth") / f"{image_path.stem}.json"
        if not gt_path.exists():
            print(f"⚠️  No ground truth found for {image_path.name}")
            return None
        
        try:
            with gt_path.open() as f:
                ground_truth = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load ground truth for {image_path.name}: {e}")
            return None
        
        # Load and process image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"❌ Failed to load image: {image_path}")
            return None
        
        # Extract regions
        height, width = image.shape[:2]
        cards_region = image[int(height * 0.3):, int(width * 0.25):]
        jokers_region = image[:int(height * 0.3), int(width * 0.25):]
        
        # Run detection
        try:
            from vision.hybrid_detector import BalatroHybridDetector, DetectionMethod
            
            detector = BalatroHybridDetector(
                yolo_confidence=0.3,
                template_confidence=0.5,
                ensemble_threshold=0.4
            )
            
            # Detect cards
            if detection_method == "yolo":
                method = DetectionMethod.YOLO
            elif detection_method == "template":
                method = DetectionMethod.TEMPLATE
            elif detection_method == "traditional_cv":
                method = DetectionMethod.TRADITIONAL_CV
            else:
                method = DetectionMethod.ENSEMBLE
            
            card_detections = detector.detect_cards(cards_region, region_type='cards', method=method)
            joker_detections = detector.detect_cards(jokers_region, region_type='jokers', method=method)
            
        except Exception as e:
            print(f"❌ Detection failed for {image_path.name}: {e}")
            return None
        
        # Convert detections to evaluation format
        card_detection_list = []
        for detection in card_detections:
            x, y, w, h = detection.bbox
            # Adjust coordinates back to full image space
            adjusted_y = y + int(height * 0.3)  # Cards region offset
            adjusted_x = x + int(width * 0.25)   # Region offset
            
            card_detection_list.append({
                "bbox": {"x": adjusted_x, "y": adjusted_y, "width": w, "height": h},
                "confidence": detection.confidence,
                "card_class": detection.card_class,
                "card_type": detection.card_type
            })
        
        joker_detection_list = []
        for detection in joker_detections:
            x, y, w, h = detection.bbox
            # Adjust coordinates back to full image space  
            adjusted_x = x + int(width * 0.25)   # Region offset
            
            joker_detection_list.append({
                "bbox": {"x": adjusted_x, "y": y, "width": w, "height": h},
                "confidence": detection.confidence,
                "card_type": detection.card_type
            })
        
        # Evaluate cards
        card_metrics = self.evaluate_detections(card_detection_list, ground_truth["cards"])
        
        # Evaluate jokers
        joker_metrics = self.evaluate_detections(joker_detection_list, ground_truth["jokers"])
        
        return {
            "image_id": image_path.stem,
            "detection_method": detection_method,
            "cards": {
                "metrics": card_metrics,
                "detections": card_detection_list,
                "ground_truth": ground_truth["cards"]
            },
            "jokers": {
                "metrics": joker_metrics,
                "detections": joker_detection_list,
                "ground_truth": ground_truth["jokers"]
            },
            "overall": {
                "total_detections": len(card_detection_list) + len(joker_detection_list),
                "total_ground_truth": len(ground_truth["cards"]) + len(ground_truth["jokers"])
            }
        }
    
    def print_metrics(self, metrics: EvaluationMetrics, category: str):
        """Print evaluation metrics in a formatted way."""
        print(f"\n📊 {category} Metrics:")
        print(f"  Precision: {metrics.precision:.3f}")
        print(f"  Recall: {metrics.recall:.3f}")
        print(f"  F1-Score: {metrics.f1_score:.3f}")
        print(f"  Mean IoU: {metrics.mean_iou:.3f}")
        print(f"  True Positives: {metrics.true_positives}")
        print(f"  False Positives: {metrics.false_positives}")
        print(f"  False Negatives: {metrics.false_negatives}")
        print(f"  Detections: {metrics.detection_count}")
        print(f"  Ground Truth: {metrics.ground_truth_count}")

def main():
    """Main evaluation workflow."""
    print("🎯 Detection Evaluation Tool")
    print("=" * 50)
    
    # Find images with ground truth
    gt_dir = Path("dataset/ground_truth")
    if not gt_dir.exists():
        print("❌ No ground truth directory found. Run label_data/annotate_ground_truth.py first.")
        return
    
    gt_files = list(gt_dir.glob("*.json"))
    if not gt_files:
        print("❌ No ground truth files found. Run label_data/annotate_ground_truth.py first.")
        return
    
    print(f"📁 Found {len(gt_files)} ground truth files")
    
    # Get detection method
    methods = ["ensemble", "yolo", "template", "traditional_cv"]
    print(f"\nAvailable detection methods: {methods}")
    method = input("Detection method (default: ensemble): ").strip().lower()
    if method not in methods:
        method = "ensemble"
    
    print(f"🔍 Using detection method: {method}")
    
    evaluator = DetectionEvaluator(iou_threshold=0.5)
    
    # Evaluate each image
    all_results = []
    
    for gt_file in gt_files:
        image_path = Path("dataset/raw") / f"{gt_file.stem}.png"
        
        if not image_path.exists():
            print(f"⚠️  Image not found: {image_path}")
            continue
        
        print(f"\n📸 Evaluating: {image_path.name}")
        
        result = evaluator.evaluate_image(image_path, method)
        if result:
            all_results.append(result)
            
            # Print individual results
            evaluator.print_metrics(result["cards"]["metrics"], "Cards")
            evaluator.print_metrics(result["jokers"]["metrics"], "Jokers")
        else:
            print(f"❌ Evaluation failed for {image_path.name}")
    
    # Calculate overall statistics
    if all_results:
        print("\n" + "=" * 50)
        print("📈 Overall Statistics")
        print("=" * 50)
        
        # Aggregate metrics
        total_card_tp = sum(r["cards"]["metrics"].true_positives for r in all_results)
        total_card_fp = sum(r["cards"]["metrics"].false_positives for r in all_results)
        total_card_fn = sum(r["cards"]["metrics"].false_negatives for r in all_results)
        
        total_joker_tp = sum(r["jokers"]["metrics"].true_positives for r in all_results)
        total_joker_fp = sum(r["jokers"]["metrics"].false_positives for r in all_results)
        total_joker_fn = sum(r["jokers"]["metrics"].false_negatives for r in all_results)
        
        # Calculate overall metrics
        card_precision = total_card_tp / (total_card_tp + total_card_fp) if (total_card_tp + total_card_fp) > 0 else 0
        card_recall = total_card_tp / (total_card_tp + total_card_fn) if (total_card_tp + total_card_fn) > 0 else 0
        card_f1 = 2 * (card_precision * card_recall) / (card_precision + card_recall) if (card_precision + card_recall) > 0 else 0
        
        joker_precision = total_joker_tp / (total_joker_tp + total_joker_fp) if (total_joker_tp + total_joker_fp) > 0 else 0
        joker_recall = total_joker_tp / (total_joker_tp + total_joker_fn) if (total_joker_tp + total_joker_fn) > 0 else 0
        joker_f1 = 2 * (joker_precision * joker_recall) / (joker_precision + joker_recall) if (joker_precision + joker_recall) > 0 else 0
        
        print(f"\n🎴 Cards Overall:")
        print(f"  Precision: {card_precision:.3f}")
        print(f"  Recall: {card_recall:.3f}")
        print(f"  F1-Score: {card_f1:.3f}")
        
        print(f"\n🃏 Jokers Overall:")
        print(f"  Precision: {joker_precision:.3f}")
        print(f"  Recall: {joker_recall:.3f}")
        print(f"  F1-Score: {joker_f1:.3f}")
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        if card_f1 >= 0.9:
            print("  Cards: ✅ Excellent (F1 ≥ 0.9)")
        elif card_f1 >= 0.7:
            print("  Cards: ⚡ Good (F1 ≥ 0.7)")
        elif card_f1 >= 0.5:
            print("  Cards: ⚠️  Fair (F1 ≥ 0.5)")
        else:
            print("  Cards: ❌ Poor (F1 < 0.5)")
        
        if joker_f1 >= 0.9:
            print("  Jokers: ✅ Excellent (F1 ≥ 0.9)")
        elif joker_f1 >= 0.7:
            print("  Jokers: ⚡ Good (F1 ≥ 0.7)")
        elif joker_f1 >= 0.5:
            print("  Jokers: ⚠️  Fair (F1 ≥ 0.5)")
        else:
            print("  Jokers: ❌ Poor (F1 < 0.5)")
        
        # Save results
        results_path = Path("dataset/evaluation_results") / f"{method}_evaluation.json"
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            "method": method,
            "iou_threshold": evaluator.iou_threshold,
            "images_evaluated": len(all_results),
            "overall_metrics": {
                "cards": {
                    "precision": card_precision,
                    "recall": card_recall,
                    "f1_score": card_f1,
                    "true_positives": total_card_tp,
                    "false_positives": total_card_fp,
                    "false_negatives": total_card_fn
                },
                "jokers": {
                    "precision": joker_precision,
                    "recall": joker_recall,
                    "f1_score": joker_f1,
                    "true_positives": total_joker_tp,
                    "false_positives": total_joker_fp,
                    "false_negatives": total_joker_fn
                }
            },
            "detailed_results": all_results
        }
        
        with results_path.open("w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_path}")
    
    else:
        print("❌ No successful evaluations")

if __name__ == "__main__":
    main()