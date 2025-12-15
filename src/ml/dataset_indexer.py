"""dataset_indexer.py

Dataset indexing and statistics system for Nebulatro.

Provides comprehensive dataset tracking, integrity checking, and metadata
management. Maintains dataset/index.json with statistics and enables
dataset analysis and reporting.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, Counter
import logging

# Set up logging
logger = logging.getLogger(__name__)


class DatasetIndexError(Exception):
    """Raised when dataset indexing operations fail."""
    pass


class DatasetIndexer:
    """Dataset indexing and statistics system."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize dataset indexer.
        
        Args:
            base_path: Base directory for dataset operations. Defaults to 'dataset/'
        """
        self.base_path = base_path or Path("dataset")
        self.index_path = self.base_path / "index.json"
        
        # Initialize index if it doesn't exist
        if not self.index_path.exists():
            self._create_initial_index()
    
    def update_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Update the dataset index with current statistics.
        
        Args:
            force_rebuild: If True, rebuild index from scratch
            
        Returns:
            Updated index dictionary
            
        Raises:
            DatasetIndexError: If indexing fails
        """
        try:
            if force_rebuild or not self.index_path.exists():
                index = self._build_index_from_scratch()
            else:
                index = self._load_index()
                index = self._update_existing_index(index)
            
            # Save updated index
            self._save_index(index)
            
            logger.info(f"Dataset index updated: {index['summary']['total_files']} files indexed")
            return index
            
        except Exception as e:
            raise DatasetIndexError(f"Failed to update dataset index: {e}") from e
    
    def get_index(self) -> Dict[str, Any]:
        """Get current dataset index.
        
        Returns:
            Current index dictionary
        """
        if not self.index_path.exists():
            return self._create_initial_index()
        
        return self._load_index()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics summary.
        
        Returns:
            Statistics dictionary
        """
        index = self.get_index()
        return index.get("summary", {})
    
    def check_integrity(self) -> Dict[str, Any]:
        """Check dataset integrity across all formats.
        
        Returns:
            Integrity check results
        """
        try:
            results = {
                "timestamp": int(time.time()),
                "checks_performed": [],
                "issues_found": [],
                "summary": {
                    "total_checks": 0,
                    "passed_checks": 0,
                    "failed_checks": 0,
                    "warnings": 0
                }
            }
            
            # Check 1: Orphaned files (images without corresponding JSON)
            orphaned_check = self._check_orphaned_files()
            results["checks_performed"].append(orphaned_check)
            
            # Check 2: Missing files (JSON without corresponding images)
            missing_check = self._check_missing_files()
            results["checks_performed"].append(missing_check)
            
            # Check 3: Schema validation for existing JSON files
            schema_check = self._check_schema_validation()
            results["checks_performed"].append(schema_check)
            
            # Check 4: Consistency between state and annotation JSON
            consistency_check = self._check_json_consistency()
            results["checks_performed"].append(consistency_check)
            
            # Aggregate results
            for check in results["checks_performed"]:
                results["summary"]["total_checks"] += 1
                if check["status"] == "passed":
                    results["summary"]["passed_checks"] += 1
                elif check["status"] == "failed":
                    results["summary"]["failed_checks"] += 1
                    results["issues_found"].extend(check.get("issues", []))
                elif check["status"] == "warning":
                    results["summary"]["warnings"] += 1
                    results["issues_found"].extend(check.get("issues", []))
            
            return results
            
        except Exception as e:
            raise DatasetIndexError(f"Integrity check failed: {e}") from e
    
    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific file.
        
        Args:
            file_path: Path to file (relative to dataset root)
            
        Returns:
            File information dictionary or None if not found
        """
        index = self.get_index()
        
        # Convert to relative path string
        rel_path = str(file_path.relative_to(self.base_path)) if file_path.is_absolute() else str(file_path)
        
        # Search in all file categories
        for category in ["states", "annotations", "processed_images", "raw_images"]:
            if category in index and rel_path in index[category]:
                return index[category][rel_path]
        
        return None
    
    def _create_initial_index(self) -> Dict[str, Any]:
        """Create initial empty index."""
        index = {
            "schema_version": "1.0",
            "created": int(time.time()),
            "last_updated": int(time.time()),
            "summary": {
                "total_files": 0,
                "total_size_bytes": 0,
                "states_count": 0,
                "annotations_count": 0,
                "processed_images_count": 0,
                "raw_images_count": 0,
                "card_classes": {},
                "modifier_categories": {},
                "label_types": {}
            },
            "states": {},
            "annotations": {},
            "processed_images": {},
            "raw_images": {}
        }
        
        self._save_index(index)
        return index
    
    def _build_index_from_scratch(self) -> Dict[str, Any]:
        """Build complete index from filesystem scan."""
        logger.info("Building dataset index from scratch...")
        
        index = self._create_initial_index()
        
        # Scan all dataset directories
        self._scan_states_directory(index, self.base_path / "states")
        self._scan_annotations_directory(index, self.base_path / "annotations")
        self._scan_directory(index, "processed_images", self.base_path / "processed", [".png", ".jpg", ".jpeg"])
        self._scan_directory(index, "raw_images", self.base_path / "raw", [".png", ".jpg", ".jpeg"])
        
        # Update summary statistics
        self._update_summary_statistics(index)
        
        return index
    
    def _update_existing_index(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing index with new/changed files (incremental)."""
        logger.debug("Performing incremental index update...")
        
        # Track changes
        changes = {
            "added": 0,
            "updated": 0,
            "removed": 0
        }
        
        # Check each category for changes
        for category, directory, extensions in [
            ("states", self.base_path / "states", [".json"]),
            ("annotations", self.base_path / "annotations", [".json"]),
            ("processed_images", self.base_path / "processed", [".png", ".jpg", ".jpeg"]),
            ("raw_images", self.base_path / "raw", [".png", ".jpg", ".jpeg"])
        ]:
            if category == "states":
                changes.update(self._update_states_incremental(index, directory))
            elif category == "annotations":
                changes.update(self._update_annotations_incremental(index, directory))
            else:
                changes.update(self._update_directory_incremental(index, category, directory, extensions))
        
        # Remove files that no longer exist
        changes["removed"] += self._remove_missing_files(index)
        
        # Update summary statistics
        self._update_summary_statistics(index)
        
        logger.info(f"Incremental update complete: {changes['added']} added, {changes['updated']} updated, {changes['removed']} removed")
        return index
    
    def _update_states_incremental(self, index: Dict[str, Any], directory: Path) -> Dict[str, int]:
        """Incrementally update states directory."""
        changes = {"added": 0, "updated": 0}
        
        if not directory.exists():
            return changes
        
        for file_path in directory.rglob("*.state.json"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.base_path))
                file_mtime = int(file_path.stat().st_mtime)
                
                # Check if file is new or updated
                existing_info = index.get("states", {}).get(rel_path)
                
                if existing_info is None:
                    # New file
                    file_info = {
                        "path": rel_path,
                        "size_bytes": file_path.stat().st_size,
                        "modified": file_mtime,
                        "category": "states"
                    }
                    file_info.update(self._analyze_state_file(file_path))
                    index["states"][rel_path] = file_info
                    changes["added"] += 1
                    
                elif existing_info.get("modified", 0) < file_mtime:
                    # Updated file
                    existing_info.update({
                        "size_bytes": file_path.stat().st_size,
                        "modified": file_mtime
                    })
                    existing_info.update(self._analyze_state_file(file_path))
                    changes["updated"] += 1
        
        return changes
    
    def _update_annotations_incremental(self, index: Dict[str, Any], directory: Path) -> Dict[str, int]:
        """Incrementally update annotations directory."""
        changes = {"added": 0, "updated": 0}
        
        if not directory.exists():
            return changes
        
        for file_path in directory.rglob("*.json"):
            if file_path.is_file() and not file_path.name.endswith(".state.json"):
                rel_path = str(file_path.relative_to(self.base_path))
                file_mtime = int(file_path.stat().st_mtime)
                
                # Check if file is new or updated
                existing_info = index.get("annotations", {}).get(rel_path)
                
                if existing_info is None:
                    # New file
                    file_info = {
                        "path": rel_path,
                        "size_bytes": file_path.stat().st_size,
                        "modified": file_mtime,
                        "category": "annotations"
                    }
                    file_info.update(self._analyze_annotation_file(file_path))
                    index["annotations"][rel_path] = file_info
                    changes["added"] += 1
                    
                elif existing_info.get("modified", 0) < file_mtime:
                    # Updated file
                    existing_info.update({
                        "size_bytes": file_path.stat().st_size,
                        "modified": file_mtime
                    })
                    existing_info.update(self._analyze_annotation_file(file_path))
                    changes["updated"] += 1
        
        return changes
    
    def _update_directory_incremental(self, index: Dict[str, Any], category: str, directory: Path, extensions: List[str]) -> Dict[str, int]:
        """Incrementally update a directory category."""
        changes = {"added": 0, "updated": 0}
        
        if not directory.exists():
            return changes
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                rel_path = str(file_path.relative_to(self.base_path))
                file_mtime = int(file_path.stat().st_mtime)
                
                # Check if file is new or updated
                existing_info = index.get(category, {}).get(rel_path)
                
                if existing_info is None:
                    # New file
                    file_info = {
                        "path": rel_path,
                        "size_bytes": file_path.stat().st_size,
                        "modified": file_mtime,
                        "category": category
                    }
                    file_info.update(self._analyze_image_file(file_path))
                    index[category][rel_path] = file_info
                    changes["added"] += 1
                    
                elif existing_info.get("modified", 0) < file_mtime:
                    # Updated file
                    existing_info.update({
                        "size_bytes": file_path.stat().st_size,
                        "modified": file_mtime
                    })
                    existing_info.update(self._analyze_image_file(file_path))
                    changes["updated"] += 1
        
        return changes
    
    def _remove_missing_files(self, index: Dict[str, Any]) -> int:
        """Remove files from index that no longer exist on disk."""
        removed_count = 0
        
        for category in ["states", "annotations", "processed_images", "raw_images"]:
            files_to_remove = []
            
            for rel_path in index.get(category, {}):
                full_path = self.base_path / rel_path
                if not full_path.exists():
                    files_to_remove.append(rel_path)
            
            for rel_path in files_to_remove:
                del index[category][rel_path]
                removed_count += 1
                logger.debug(f"Removed missing file from index: {rel_path}")
        
        return removed_count
    
    def _scan_directory(self, index: Dict[str, Any], category: str, directory: Path, extensions: List[str]) -> None:
        """Scan directory and add files to index.
        
        Args:
            index: Index dictionary to update
            category: Category name (states, annotations, etc.)
            directory: Directory to scan
            extensions: File extensions to include
        """
        if not directory.exists():
            return
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                rel_path = str(file_path.relative_to(self.base_path))
                
                file_info = {
                    "path": rel_path,
                    "size_bytes": file_path.stat().st_size,
                    "modified": int(file_path.stat().st_mtime),
                    "category": category
                }
                
                # Add category-specific metadata
                if category == "states":
                    file_info.update(self._analyze_state_file(file_path))
                elif category == "annotations":
                    file_info.update(self._analyze_annotation_file(file_path))
                elif category in ["processed_images", "raw_images"]:
                    file_info.update(self._analyze_image_file(file_path))
                
                index[category][rel_path] = file_info
    
    def _scan_states_directory(self, index: Dict[str, Any], directory: Path) -> None:
        """Scan states directory for .state.json files."""
        if not directory.exists():
            return
        
        for file_path in directory.rglob("*.state.json"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.base_path))
                
                file_info = {
                    "path": rel_path,
                    "size_bytes": file_path.stat().st_size,
                    "modified": int(file_path.stat().st_mtime),
                    "category": "states"
                }
                
                file_info.update(self._analyze_state_file(file_path))
                index["states"][rel_path] = file_info
    
    def _scan_annotations_directory(self, index: Dict[str, Any], directory: Path) -> None:
        """Scan annotations directory for .json files (excluding .state.json)."""
        if not directory.exists():
            return
        
        for file_path in directory.rglob("*.json"):
            if file_path.is_file() and not file_path.name.endswith(".state.json"):
                rel_path = str(file_path.relative_to(self.base_path))
                
                file_info = {
                    "path": rel_path,
                    "size_bytes": file_path.stat().st_size,
                    "modified": int(file_path.stat().st_mtime),
                    "category": "annotations"
                }
                
                file_info.update(self._analyze_annotation_file(file_path))
                index["annotations"][rel_path] = file_info
    
    def _analyze_state_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze canonical state JSON file."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                state = json.load(f)
            
            return {
                "schema_version": state.get("schema_version"),
                "screen_type": state.get("screen", {}).get("type"),
                "hand_size": len(state.get("hand", [])),
                "jokers_count": len(state.get("jokers", [])),
                "valid_json": True
            }
        except Exception as e:
            return {
                "valid_json": False,
                "error": str(e)
            }
    
    def _analyze_annotation_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze annotation JSON file."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                annotation = json.load(f)
            
            return {
                "label_type": annotation.get("label_type"),
                "selected_class": annotation.get("selected_class"),
                "modifiers_count": len(annotation.get("applied_modifiers", [])),
                "has_hand": annotation.get("hand") is not None,
                "valid_json": True
            }
        except Exception as e:
            return {
                "valid_json": False,
                "error": str(e)
            }
    
    def _analyze_image_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze image file."""
        try:
            # Extract metadata from path structure
            parts = file_path.parts
            
            info = {
                "file_type": "image"
            }
            
            # Determine image category from path
            if "processed" in parts:
                if "cards" in parts:
                    # Extract card class from path
                    try:
                        class_idx = next(i for i, part in enumerate(parts) if part == "cards")
                        if class_idx + 1 < len(parts):
                            info["card_class"] = int(parts[class_idx + 1])
                    except (ValueError, StopIteration):
                        pass
                elif "modifiers" in parts:
                    # Extract modifier info from path
                    try:
                        mod_idx = next(i for i, part in enumerate(parts) if part == "modifiers")
                        if mod_idx + 2 < len(parts):
                            info["modifier_category"] = parts[mod_idx + 1]
                            info["modifier_name"] = parts[mod_idx + 2]
                    except (ValueError, StopIteration):
                        pass
                else:
                    # Special categories (not_card, suit_only, etc.)
                    for part in parts:
                        if part.startswith(("not_card", "suit_only", "card_backs", "booster_packs", "consumables", "jokers")):
                            info["special_category"] = part
                            break
            
            return info
            
        except Exception as e:
            return {
                "file_type": "image",
                "error": str(e)
            }
    
    def _update_summary_statistics(self, index: Dict[str, Any]) -> None:
        """Update summary statistics in index."""
        summary = index["summary"]
        
        # Reset counters
        summary["total_files"] = 0
        summary["total_size_bytes"] = 0
        summary["states_count"] = len(index["states"])
        summary["annotations_count"] = len(index["annotations"])
        summary["processed_images_count"] = len(index["processed_images"])
        summary["raw_images_count"] = len(index["raw_images"])
        
        # Count by categories
        card_classes = Counter()
        modifier_categories = Counter()
        label_types = Counter()
        
        # Aggregate statistics from all files
        for category in ["states", "annotations", "processed_images", "raw_images"]:
            for file_info in index[category].values():
                summary["total_files"] += 1
                summary["total_size_bytes"] += file_info.get("size_bytes", 0)
                
                # Category-specific statistics
                if "card_class" in file_info:
                    card_classes[file_info["card_class"]] += 1
                if "modifier_category" in file_info:
                    modifier_categories[file_info["modifier_category"]] += 1
                if "label_type" in file_info:
                    label_types[file_info["label_type"]] += 1
        
        summary["card_classes"] = dict(card_classes)
        summary["modifier_categories"] = dict(modifier_categories)
        summary["label_types"] = dict(label_types)
        summary["last_updated"] = int(time.time())
    
    def _check_orphaned_files(self) -> Dict[str, Any]:
        """Check for orphaned files (images without corresponding JSON)."""
        issues = []
        
        # Get all processed images
        index = self.get_index()
        processed_images = set(index.get("processed_images", {}).keys())
        
        # Get corresponding JSON files
        states = set(f.replace(".state.json", "") for f in index.get("states", {}).keys())
        annotations = set(f.replace(".json", "") for f in index.get("annotations", {}).keys())
        
        # Find images without JSON
        for img_path in processed_images:
            img_stem = Path(img_path).stem
            if img_stem not in states and img_stem not in annotations:
                issues.append(f"Orphaned image: {img_path} (no corresponding JSON)")
        
        return {
            "name": "orphaned_files",
            "description": "Check for images without corresponding JSON files",
            "status": "passed" if not issues else "warning",
            "issues": issues,
            "count": len(issues)
        }
    
    def _check_missing_files(self) -> Dict[str, Any]:
        """Check for missing files (JSON without corresponding images)."""
        issues = []
        
        index = self.get_index()
        
        # Check states with missing images
        for state_file in index.get("states", {}).keys():
            img_stem = state_file.replace(".state.json", "")
            # Look for corresponding processed image
            found = False
            for img_path in index.get("processed_images", {}).keys():
                if Path(img_path).stem == img_stem:
                    found = True
                    break
            if not found:
                issues.append(f"Missing image for state: {state_file}")
        
        return {
            "name": "missing_files",
            "description": "Check for JSON files without corresponding images",
            "status": "passed" if not issues else "warning",
            "issues": issues,
            "count": len(issues)
        }
    
    def _check_schema_validation(self) -> Dict[str, Any]:
        """Check schema validation for JSON files."""
        issues = []
        
        index = self.get_index()
        
        # Check state files
        for file_path, file_info in index.get("states", {}).items():
            if not file_info.get("valid_json", True):
                issues.append(f"Invalid JSON in state file: {file_path} - {file_info.get('error', 'Unknown error')}")
        
        # Check annotation files
        for file_path, file_info in index.get("annotations", {}).items():
            if not file_info.get("valid_json", True):
                issues.append(f"Invalid JSON in annotation file: {file_path} - {file_info.get('error', 'Unknown error')}")
        
        return {
            "name": "schema_validation",
            "description": "Check JSON schema validation",
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "count": len(issues)
        }
    
    def _check_json_consistency(self) -> Dict[str, Any]:
        """Check consistency between state and annotation JSON files."""
        issues = []
        
        index = self.get_index()
        
        # Find matching state and annotation files
        state_stems = {Path(f).stem: f for f in index.get("states", {}).keys()}
        annotation_stems = {Path(f).stem: f for f in index.get("annotations", {}).keys()}
        
        common_stems = set(state_stems.keys()) & set(annotation_stems.keys())
        
        for stem in common_stems:
            state_file = state_stems[stem]
            annotation_file = annotation_stems[stem]
            
            state_info = index["states"][state_file]
            annotation_info = index["annotations"][annotation_file]
            
            # Check if both are valid JSON
            if not state_info.get("valid_json") or not annotation_info.get("valid_json"):
                continue
            
            # Check consistency (this could be expanded with more detailed checks)
            if state_info.get("hand_size", 0) > 0 and not annotation_info.get("has_hand", False):
                issues.append(f"Inconsistency: {stem} has hand in state but not in annotation")
        
        return {
            "name": "json_consistency",
            "description": "Check consistency between state and annotation JSON",
            "status": "passed" if not issues else "warning",
            "issues": issues,
            "count": len(issues)
        }
    
    def _load_index(self) -> Dict[str, Any]:
        """Load index from file."""
        try:
            with self.index_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load index, creating new one: {e}")
            return self._create_initial_index()
    
    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save index to file."""
        # Ensure directory exists
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use atomic write
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            dir=self.index_path.parent, 
            suffix='.tmp', 
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            json.dump(index, temp_file, indent=2, ensure_ascii=False)
            temp_path = Path(temp_file.name)
        
        # Atomic move
        shutil.move(str(temp_path), str(self.index_path))


# Global dataset indexer instance
_dataset_indexer = None


def get_dataset_indexer() -> DatasetIndexer:
    """Get the global dataset indexer instance.
    
    Returns:
        Global DatasetIndexer instance
    """
    global _dataset_indexer
    if _dataset_indexer is None:
        _dataset_indexer = DatasetIndexer()
    return _dataset_indexer


def update_dataset_index(force_rebuild: bool = False) -> Dict[str, Any]:
    """Convenience function to update dataset index.
    
    Args:
        force_rebuild: If True, rebuild index from scratch
        
    Returns:
        Updated index dictionary
    """
    return get_dataset_indexer().update_index(force_rebuild)


def get_dataset_statistics() -> Dict[str, Any]:
    """Convenience function to get dataset statistics.
    
    Returns:
        Statistics dictionary
    """
    return get_dataset_indexer().get_statistics()