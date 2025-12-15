"""dataset_reporter.py

Advanced reporting and analysis system for Nebulatro datasets.

Provides detailed dataset analysis, reporting dashboards, and insights
for training data quality and distribution analysis.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatasetReport:
    """Comprehensive dataset analysis report."""
    timestamp: int
    dataset_path: str
    summary: Dict[str, Any]
    card_distribution: Dict[str, Any]
    modifier_analysis: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    recommendations: List[str]
    detailed_stats: Dict[str, Any]


class DatasetReporter:
    """Advanced dataset reporting and analysis system."""
    
    def __init__(self, dataset_path: Optional[Path] = None):
        """Initialize dataset reporter.
        
        Args:
            dataset_path: Path to dataset directory (defaults to 'dataset/')
        """
        self.dataset_path = dataset_path or Path("dataset")
        
        # Load dataset index
        from .dataset_indexer import get_dataset_indexer
        self.indexer = get_dataset_indexer()
    
    def generate_comprehensive_report(self) -> DatasetReport:
        """Generate comprehensive dataset analysis report.
        
        Returns:
            Complete dataset report
        """
        logger.info("Generating comprehensive dataset report...")
        
        # Get current index
        index = self.indexer.get_index()
        
        # Generate report sections
        summary = self._generate_summary(index)
        card_distribution = self._analyze_card_distribution(index)
        modifier_analysis = self._analyze_modifiers(index)
        quality_metrics = self._calculate_quality_metrics(index)
        recommendations = self._generate_recommendations(index, quality_metrics)
        detailed_stats = self._generate_detailed_stats(index)
        
        report = DatasetReport(
            timestamp=int(time.time()),
            dataset_path=str(self.dataset_path),
            summary=summary,
            card_distribution=card_distribution,
            modifier_analysis=modifier_analysis,
            quality_metrics=quality_metrics,
            recommendations=recommendations,
            detailed_stats=detailed_stats
        )
        
        logger.info("Dataset report generation complete")
        return report
    
    def save_report(self, report: DatasetReport, output_path: Optional[Path] = None) -> Path:
        """Save dataset report to JSON file.
        
        Args:
            report: Dataset report to save
            output_path: Output file path (defaults to dataset/reports/)
            
        Returns:
            Path to saved report file
        """
        if output_path is None:
            reports_dir = self.dataset_path / "reports"
            reports_dir.mkdir(exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(report.timestamp))
            output_path = reports_dir / f"dataset_report_{timestamp_str}.json"
        
        # Convert report to dictionary
        report_dict = asdict(report)
        
        # Save to file
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Dataset report saved to {output_path}")
        return output_path
    
    def generate_html_dashboard(self, report: DatasetReport, output_path: Optional[Path] = None) -> Path:
        """Generate HTML dashboard from dataset report.
        
        Args:
            report: Dataset report to visualize
            output_path: Output HTML file path
            
        Returns:
            Path to generated HTML file
        """
        if output_path is None:
            reports_dir = self.dataset_path / "reports"
            reports_dir.mkdir(exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(report.timestamp))
            output_path = reports_dir / f"dashboard_{timestamp_str}.html"
        
        html_content = self._generate_html_content(report)
        
        with output_path.open("w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML dashboard saved to {output_path}")
        return output_path
    
    def get_training_readiness_score(self) -> Dict[str, Any]:
        """Calculate training readiness score for the dataset.
        
        Returns:
            Training readiness assessment
        """
        index = self.indexer.get_index()
        
        # Calculate various readiness metrics
        card_coverage = self._calculate_card_coverage(index)
        data_quality = self._calculate_data_quality(index)
        balance_score = self._calculate_balance_score(index)
        
        # Overall readiness score (0-100)
        overall_score = (card_coverage + data_quality + balance_score) / 3
        
        # Determine readiness level
        if overall_score >= 90:
            readiness_level = "excellent"
        elif overall_score >= 75:
            readiness_level = "good"
        elif overall_score >= 60:
            readiness_level = "fair"
        else:
            readiness_level = "poor"
        
        return {
            "overall_score": round(overall_score, 1),
            "readiness_level": readiness_level,
            "metrics": {
                "card_coverage": round(card_coverage, 1),
                "data_quality": round(data_quality, 1),
                "balance_score": round(balance_score, 1)
            },
            "recommendations": self._get_readiness_recommendations(overall_score, {
                "card_coverage": card_coverage,
                "data_quality": data_quality,
                "balance_score": balance_score
            })
        }
    
    def _generate_summary(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics."""
        summary = index.get("summary", {})
        
        return {
            "total_files": summary.get("total_files", 0),
            "total_size_mb": round(summary.get("total_size_bytes", 0) / (1024 * 1024), 2),
            "states_count": summary.get("states_count", 0),
            "annotations_count": summary.get("annotations_count", 0),
            "processed_images": summary.get("processed_images_count", 0),
            "raw_images": summary.get("raw_images_count", 0),
            "last_updated": summary.get("last_updated", 0)
        }
    
    def _analyze_card_distribution(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze card class distribution."""
        card_classes = Counter()
        suit_distribution = Counter()
        rank_distribution = Counter()
        
        # Analyze processed images for card classes
        for file_info in index.get("processed_images", {}).values():
            if "card_class" in file_info:
                card_class = file_info["card_class"]
                card_classes[card_class] += 1
                
                # Convert card class to suit and rank
                suit_idx = card_class // 13
                rank_idx = card_class % 13
                
                suits = ["hearts", "clubs", "diamonds", "spades"]
                ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
                
                if 0 <= suit_idx < len(suits):
                    suit_distribution[suits[suit_idx]] += 1
                if 0 <= rank_idx < len(ranks):
                    rank_distribution[ranks[rank_idx]] += 1
        
        # Calculate coverage statistics
        total_possible_classes = 52
        covered_classes = len(card_classes)
        coverage_percentage = (covered_classes / total_possible_classes) * 100
        
        # Find missing classes
        missing_classes = []
        for i in range(52):
            if i not in card_classes:
                missing_classes.append(i)
        
        return {
            "total_card_images": sum(card_classes.values()),
            "unique_classes_covered": covered_classes,
            "coverage_percentage": round(coverage_percentage, 1),
            "missing_classes": missing_classes,
            "class_distribution": dict(card_classes.most_common()),
            "suit_distribution": dict(suit_distribution),
            "rank_distribution": dict(rank_distribution),
            "min_samples_per_class": min(card_classes.values()) if card_classes else 0,
            "max_samples_per_class": max(card_classes.values()) if card_classes else 0,
            "avg_samples_per_class": round(sum(card_classes.values()) / len(card_classes), 1) if card_classes else 0
        }
    
    def _analyze_modifiers(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze modifier distribution and usage."""
        modifier_stats = defaultdict(lambda: defaultdict(int))
        
        # Analyze modifier images
        for file_info in index.get("processed_images", {}).values():
            if "modifier_category" in file_info and "modifier_name" in file_info:
                category = file_info["modifier_category"]
                name = file_info["modifier_name"]
                modifier_stats[category][name] += 1
        
        # Analyze state files for modifier usage
        state_modifiers = defaultdict(int)
        
        for file_path in index.get("states", {}):
            try:
                full_path = self.dataset_path / file_path
                if full_path.exists():
                    with full_path.open("r", encoding="utf-8") as f:
                        state = json.load(f)
                    
                    # Count modifiers in hand
                    for card in state.get("hand", []):
                        if card.get("edition"):
                            state_modifiers[f"edition_{card['edition']}"] += 1
                        if card.get("seal"):
                            state_modifiers[f"seal_{card['seal']}"] += 1
                        for enhancement in card.get("enhancements", []):
                            state_modifiers[f"enhancement_{enhancement}"] += 1
                        if card.get("debuff"):
                            state_modifiers["debuff"] += 1
                            
            except Exception as e:
                logger.warning(f"Failed to analyze state file {file_path}: {e}")
        
        return {
            "modifier_images": dict(modifier_stats),
            "state_modifiers": dict(state_modifiers),
            "total_modifier_images": sum(
                sum(category.values()) for category in modifier_stats.values()
            ),
            "categories_covered": list(modifier_stats.keys()),
            "most_common_modifiers": dict(Counter(state_modifiers).most_common(10))
        }
    
    def _calculate_quality_metrics(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate data quality metrics."""
        # Run integrity check
        integrity_results = self.indexer.check_integrity()
        
        # Calculate quality scores
        total_checks = integrity_results["summary"]["total_checks"]
        passed_checks = integrity_results["summary"]["passed_checks"]
        
        quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        # Analyze JSON validity
        valid_states = 0
        total_states = 0
        
        for file_info in index.get("states", {}).values():
            total_states += 1
            if file_info.get("valid_json", False):
                valid_states += 1
        
        json_validity = (valid_states / total_states * 100) if total_states > 0 else 0
        
        return {
            "overall_quality_score": round(quality_score, 1),
            "json_validity_percentage": round(json_validity, 1),
            "integrity_issues": len(integrity_results["issues_found"]),
            "orphaned_files": sum(1 for check in integrity_results["checks_performed"] 
                                if check["name"] == "orphaned_files" for _ in check.get("issues", [])),
            "missing_files": sum(1 for check in integrity_results["checks_performed"] 
                               if check["name"] == "missing_files" for _ in check.get("issues", [])),
            "schema_violations": sum(1 for check in integrity_results["checks_performed"] 
                                   if check["name"] == "schema_validation" for _ in check.get("issues", []))
        }
    
    def _generate_recommendations(self, index: Dict[str, Any], quality_metrics: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations for dataset improvement."""
        recommendations = []
        
        # Card coverage recommendations
        card_dist = self._analyze_card_distribution(index)
        if card_dist["coverage_percentage"] < 80:
            recommendations.append(
                f"Card coverage is {card_dist['coverage_percentage']:.1f}%. "
                f"Consider labeling more cards to reach at least 80% coverage."
            )
        
        if card_dist["min_samples_per_class"] < 5:
            recommendations.append(
                "Some card classes have fewer than 5 samples. "
                "Aim for at least 10 samples per class for reliable training."
            )
        
        # Quality recommendations
        if quality_metrics["overall_quality_score"] < 90:
            recommendations.append(
                f"Data quality score is {quality_metrics['overall_quality_score']:.1f}%. "
                "Review and fix integrity issues to improve quality."
            )
        
        if quality_metrics["orphaned_files"] > 0:
            recommendations.append(
                f"Found {quality_metrics['orphaned_files']} orphaned files. "
                "Consider cleaning up or properly labeling these files."
            )
        
        # Balance recommendations
        if card_dist["max_samples_per_class"] > card_dist["min_samples_per_class"] * 3:
            recommendations.append(
                "Dataset is imbalanced. Consider collecting more samples for underrepresented classes."
            )
        
        # Modifier recommendations
        modifier_analysis = self._analyze_modifiers(index)
        if modifier_analysis["total_modifier_images"] < 50:
            recommendations.append(
                "Limited modifier training data. Consider labeling more cards with modifiers."
            )
        
        return recommendations
    
    def _generate_detailed_stats(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed statistics for advanced analysis."""
        return {
            "file_size_distribution": self._calculate_file_size_stats(index),
            "temporal_distribution": self._calculate_temporal_stats(index),
            "directory_structure": self._analyze_directory_structure(index),
            "schema_versions": self._analyze_schema_versions(index)
        }
    
    def _calculate_file_size_stats(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate file size distribution statistics."""
        sizes = []
        
        for category in ["states", "annotations", "processed_images", "raw_images"]:
            for file_info in index.get(category, {}).values():
                sizes.append(file_info.get("size_bytes", 0))
        
        if not sizes:
            return {}
        
        sizes.sort()
        n = len(sizes)
        
        return {
            "total_files": n,
            "min_size_bytes": sizes[0],
            "max_size_bytes": sizes[-1],
            "median_size_bytes": sizes[n // 2],
            "avg_size_bytes": sum(sizes) // n,
            "total_size_mb": round(sum(sizes) / (1024 * 1024), 2)
        }
    
    def _calculate_temporal_stats(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate temporal distribution of files."""
        timestamps = []
        
        for category in ["states", "annotations", "processed_images", "raw_images"]:
            for file_info in index.get(category, {}).values():
                if "modified" in file_info:
                    timestamps.append(file_info["modified"])
        
        if not timestamps:
            return {}
        
        timestamps.sort()
        
        return {
            "earliest_file": timestamps[0],
            "latest_file": timestamps[-1],
            "time_span_days": (timestamps[-1] - timestamps[0]) / (24 * 3600),
            "files_last_24h": sum(1 for ts in timestamps if time.time() - ts < 24 * 3600),
            "files_last_week": sum(1 for ts in timestamps if time.time() - ts < 7 * 24 * 3600)
        }
    
    def _analyze_directory_structure(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze directory structure and organization."""
        directories = defaultdict(int)
        
        for category in ["states", "annotations", "processed_images", "raw_images"]:
            for file_path in index.get(category, {}):
                dir_path = str(Path(file_path).parent)
                directories[dir_path] += 1
        
        return {
            "total_directories": len(directories),
            "directory_distribution": dict(directories),
            "deepest_nesting": max(len(Path(path).parts) for path in directories.keys()) if directories else 0
        }
    
    def _analyze_schema_versions(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze schema version distribution."""
        versions = Counter()
        
        for file_info in index.get("states", {}).values():
            version = file_info.get("schema_version", "unknown")
            versions[version] += 1
        
        return {
            "version_distribution": dict(versions),
            "total_versions": len(versions),
            "most_common_version": versions.most_common(1)[0] if versions else None
        }
    
    def _calculate_card_coverage(self, index: Dict[str, Any]) -> float:
        """Calculate card coverage score (0-100)."""
        card_dist = self._analyze_card_distribution(index)
        return card_dist["coverage_percentage"]
    
    def _calculate_data_quality(self, index: Dict[str, Any]) -> float:
        """Calculate data quality score (0-100)."""
        quality_metrics = self._calculate_quality_metrics(index)
        return quality_metrics["overall_quality_score"]
    
    def _calculate_balance_score(self, index: Dict[str, Any]) -> float:
        """Calculate dataset balance score (0-100)."""
        card_dist = self._analyze_card_distribution(index)
        
        if card_dist["avg_samples_per_class"] == 0:
            return 0
        
        # Calculate coefficient of variation (lower is better)
        min_samples = card_dist["min_samples_per_class"]
        max_samples = card_dist["max_samples_per_class"]
        avg_samples = card_dist["avg_samples_per_class"]
        
        if avg_samples == 0:
            return 0
        
        # Balance score based on how close min/max are to average
        balance_ratio = min_samples / max_samples if max_samples > 0 else 0
        
        return balance_ratio * 100
    
    def _get_readiness_recommendations(self, overall_score: float, metrics: Dict[str, float]) -> List[str]:
        """Get training readiness recommendations."""
        recommendations = []
        
        if overall_score < 60:
            recommendations.append("Dataset not ready for training. Address major issues first.")
        elif overall_score < 75:
            recommendations.append("Dataset needs improvement before training. Focus on quality and coverage.")
        elif overall_score < 90:
            recommendations.append("Dataset is good for training but could be improved.")
        else:
            recommendations.append("Dataset is excellent and ready for high-quality training.")
        
        if metrics["card_coverage"] < 70:
            recommendations.append("Increase card coverage by labeling more diverse cards.")
        
        if metrics["data_quality"] < 80:
            recommendations.append("Fix data quality issues to improve training reliability.")
        
        if metrics["balance_score"] < 50:
            recommendations.append("Improve dataset balance by collecting more samples for underrepresented classes.")
        
        return recommendations
    
    def _generate_html_content(self, report: DatasetReport) -> str:
        """Generate HTML content for dashboard."""
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report.timestamp))
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nebulatro Dataset Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2b2b2b; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 4px; min-width: 150px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .recommendation {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        .quality-good {{ color: #28a745; }}
        .quality-warning {{ color: #ffc107; }}
        .quality-danger {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Nebulatro Dataset Report</h1>
            <p>Generated: {timestamp_str}</p>
            <p>Dataset: {report.dataset_path}</p>
        </div>
        
        <div class="section">
            <h2>Summary</h2>
            <div class="metric">
                <div class="metric-value">{report.summary['total_files']}</div>
                <div class="metric-label">Total Files</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.summary['total_size_mb']} MB</div>
                <div class="metric-label">Total Size</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.summary['states_count']}</div>
                <div class="metric-label">State Files</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.summary['processed_images']}</div>
                <div class="metric-label">Processed Images</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Card Distribution</h2>
            <div class="metric">
                <div class="metric-value">{report.card_distribution['coverage_percentage']}%</div>
                <div class="metric-label">Card Coverage</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.card_distribution['unique_classes_covered']}/52</div>
                <div class="metric-label">Classes Covered</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.card_distribution['avg_samples_per_class']}</div>
                <div class="metric-label">Avg Samples/Class</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Quality Metrics</h2>
            <div class="metric">
                <div class="metric-value {'quality-good' if report.quality_metrics['overall_quality_score'] >= 90 else 'quality-warning' if report.quality_metrics['overall_quality_score'] >= 70 else 'quality-danger'}">{report.quality_metrics['overall_quality_score']}%</div>
                <div class="metric-label">Quality Score</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report.quality_metrics['integrity_issues']}</div>
                <div class="metric-label">Integrity Issues</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Recommendations</h2>
            {''.join(f'<div class="recommendation">{rec}</div>' for rec in report.recommendations)}
        </div>
        
        <div class="section">
            <h2>Detailed Statistics</h2>
            <h3>File Size Distribution</h3>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Files</td><td>{report.detailed_stats['file_size_distribution'].get('total_files', 0)}</td></tr>
                <tr><td>Average Size</td><td>{report.detailed_stats['file_size_distribution'].get('avg_size_bytes', 0)} bytes</td></tr>
                <tr><td>Total Size</td><td>{report.detailed_stats['file_size_distribution'].get('total_size_mb', 0)} MB</td></tr>
            </table>
        </div>
    </div>
</body>
</html>
        """
        
        return html


# Global dataset reporter instance
_dataset_reporter = None


def get_dataset_reporter() -> DatasetReporter:
    """Get the global dataset reporter instance.
    
    Returns:
        Global DatasetReporter instance
    """
    global _dataset_reporter
    if _dataset_reporter is None:
        _dataset_reporter = DatasetReporter()
    return _dataset_reporter


def generate_dataset_report() -> DatasetReport:
    """Convenience function to generate comprehensive dataset report.
    
    Returns:
        Complete dataset report
    """
    return get_dataset_reporter().generate_comprehensive_report()


def get_training_readiness() -> Dict[str, Any]:
    """Convenience function to get training readiness assessment.
    
    Returns:
        Training readiness score and recommendations
    """
    return get_dataset_reporter().get_training_readiness_score()