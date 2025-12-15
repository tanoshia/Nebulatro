"""dataset_writer.py

Centralized dataset writing system for Nebulatro.

Provides robust, atomic data writing operations with comprehensive error handling,
logging, and data integrity guarantees. Replaces direct file writes throughout
the codebase with a unified, reliable system.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

# Set up logging
logger = logging.getLogger(__name__)


class DatasetWriteError(Exception):
    """Raised when dataset write operations fail."""
    pass


class DatasetWriter:
    """Centralized dataset writing system with atomic operations and error handling."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize dataset writer.
        
        Args:
            base_path: Base directory for dataset operations. Defaults to 'dataset/'
        """
        self.base_path = base_path or Path("dataset")
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Statistics tracking
        self.stats = {
            "files_written": 0,
            "bytes_written": 0,
            "errors": 0,
            "last_write": None
        }
    
    def write_canonical_state(
        self, 
        state: Dict[str, Any], 
        image_id: str,
        validate: bool = True
    ) -> Path:
        """Write canonical state JSON with validation.
        
        Args:
            state: Canonical state dictionary
            image_id: Image identifier for filename
            validate: Whether to validate against schema
            
        Returns:
            Path to written state file
            
        Raises:
            DatasetWriteError: If write operation fails
        """
        if validate:
            try:
                from .state_schema import validate_state
                validate_state(state)
            except Exception as e:
                raise DatasetWriteError(f"State validation failed: {e}") from e
        
        states_dir = self.base_path / "states"
        states_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = states_dir / f"{image_id}.state.json"
        
        return self._write_json_atomic(state, target_path, "canonical state")
    
    def write_annotation(
        self, 
        annotation: Dict[str, Any], 
        image_id: str
    ) -> Path:
        """Write annotation JSON.
        
        Args:
            annotation: Annotation dictionary
            image_id: Image identifier for filename
            
        Returns:
            Path to written annotation file
            
        Raises:
            DatasetWriteError: If write operation fails
        """
        annotations_dir = self.base_path / "annotations"
        annotations_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = annotations_dir / f"{image_id}.json"
        
        return self._write_json_atomic(annotation, target_path, "annotation")
    
    def write_labeled_image(
        self,
        source_path: Path,
        class_id: Union[int, str],
        image_id: Optional[str] = None
    ) -> Path:
        """Write labeled image to appropriate category directory.
        
        Args:
            source_path: Source image file path
            class_id: Class identifier (0-51 for cards, or special string)
            image_id: Optional custom image ID, defaults to source filename
            
        Returns:
            Path to written image file
            
        Raises:
            DatasetWriteError: If write operation fails
        """
        if image_id is None:
            image_id = source_path.stem
        
        # Determine target directory based on class_id
        if isinstance(class_id, int) and 0 <= class_id <= 51:
            target_dir = self.base_path / "processed" / "cards" / str(class_id)
        elif class_id == "not_card":
            target_dir = self.base_path / "processed" / "not_card"
        elif str(class_id).startswith("suit_only"):
            suit_part = str(class_id).replace("suit_only_", "")
            target_dir = self.base_path / "processed" / f"suit_only_{suit_part}"
        else:
            # Category labels (card_backs, booster_packs, etc.)
            target_dir = self.base_path / "processed" / str(class_id)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{image_id}.png"
        
        return self._copy_file_atomic(source_path, target_path, "labeled image")
    
    def write_modifier_image(
        self,
        source_path: Path,
        modifier_category: str,
        modifier_name: str,
        image_id: Optional[str] = None
    ) -> Path:
        """Write image to modifier-specific directory.
        
        Args:
            source_path: Source image file path
            modifier_category: Modifier category (enhancements, editions, seals)
            modifier_name: Specific modifier name
            image_id: Optional custom image ID, defaults to source filename
            
        Returns:
            Path to written image file
            
        Raises:
            DatasetWriteError: If write operation fails
        """
        if image_id is None:
            image_id = source_path.stem
        
        target_dir = self.base_path / "processed" / "modifiers" / modifier_category / modifier_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{image_id}.png"
        
        return self._copy_file_atomic(source_path, target_path, "modifier image")
    
    def write_batch_data(
        self,
        operations: List[Dict[str, Any]]
    ) -> List[Path]:
        """Write multiple data items in a batch operation.
        
        Args:
            operations: List of operation dictionaries with 'type' and parameters
            
        Returns:
            List of paths to written files
            
        Raises:
            DatasetWriteError: If any operation fails (all operations are rolled back)
        """
        written_files = []
        temp_files = []
        
        try:
            for op in operations:
                op_type = op.get("type")
                
                if op_type == "canonical_state":
                    path = self.write_canonical_state(
                        op["state"], op["image_id"], op.get("validate", True)
                    )
                elif op_type == "annotation":
                    path = self.write_annotation(op["annotation"], op["image_id"])
                elif op_type == "labeled_image":
                    path = self.write_labeled_image(
                        op["source_path"], op["class_id"], op.get("image_id")
                    )
                elif op_type == "modifier_image":
                    path = self.write_modifier_image(
                        op["source_path"], op["modifier_category"], 
                        op["modifier_name"], op.get("image_id")
                    )
                else:
                    raise DatasetWriteError(f"Unknown operation type: {op_type}")
                
                written_files.append(path)
            
            return written_files
            
        except Exception as e:
            # Rollback: remove any files that were written
            for path in written_files:
                try:
                    if path.exists():
                        path.unlink()
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup file {path}: {cleanup_error}")
            
            raise DatasetWriteError(f"Batch operation failed: {e}") from e
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dataset writer statistics.
        
        Returns:
            Dictionary with write statistics
        """
        return self.stats.copy()
    
    def _write_json_atomic(
        self, 
        data: Dict[str, Any], 
        target_path: Path, 
        data_type: str
    ) -> Path:
        """Write JSON data atomically using temporary file.
        
        Args:
            data: Data to write
            target_path: Final file path
            data_type: Description for logging
            
        Returns:
            Path to written file
            
        Raises:
            DatasetWriteError: If write operation fails
        """
        try:
            # Create temporary file in same directory as target
            temp_dir = target_path.parent
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=temp_dir, 
                suffix='.tmp', 
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                json.dump(data, temp_file, indent=2, ensure_ascii=False)
                temp_path = Path(temp_file.name)
            
            # Atomic move to final location
            shutil.move(str(temp_path), str(target_path))
            
            # Update statistics
            self._update_stats(target_path)
            
            logger.debug(f"Successfully wrote {data_type} to {target_path}")
            return target_path
            
        except Exception as e:
            # Cleanup temporary file if it exists
            try:
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            
            self.stats["errors"] += 1
            raise DatasetWriteError(f"Failed to write {data_type} to {target_path}: {e}") from e
    
    def _copy_file_atomic(
        self, 
        source_path: Path, 
        target_path: Path, 
        data_type: str
    ) -> Path:
        """Copy file atomically using temporary file.
        
        Args:
            source_path: Source file path
            target_path: Final file path
            data_type: Description for logging
            
        Returns:
            Path to written file
            
        Raises:
            DatasetWriteError: If copy operation fails
        """
        try:
            if not source_path.exists():
                raise DatasetWriteError(f"Source file does not exist: {source_path}")
            
            # Create temporary file in same directory as target
            temp_dir = target_path.parent
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            with tempfile.NamedTemporaryFile(
                dir=temp_dir, 
                suffix='.tmp', 
                delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)
            
            # Copy file to temporary location
            shutil.copy2(source_path, temp_path)
            
            # Atomic move to final location
            shutil.move(str(temp_path), str(target_path))
            
            # Update statistics
            self._update_stats(target_path)
            
            logger.debug(f"Successfully copied {data_type} to {target_path}")
            return target_path
            
        except Exception as e:
            # Cleanup temporary file if it exists
            try:
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            
            self.stats["errors"] += 1
            raise DatasetWriteError(f"Failed to copy {data_type} to {target_path}: {e}") from e
    
    def _update_stats(self, file_path: Path) -> None:
        """Update write statistics.
        
        Args:
            file_path: Path to file that was written
        """
        try:
            file_size = file_path.stat().st_size
            self.stats["files_written"] += 1
            self.stats["bytes_written"] += file_size
            self.stats["last_write"] = time.time()
            
            # Trigger dataset index update (async to avoid blocking writes)
            self._trigger_index_update()
            
        except Exception as e:
            logger.warning(f"Failed to update stats for {file_path}: {e}")
    
    def _trigger_index_update(self) -> None:
        """Trigger dataset index update (batched for efficiency)."""
        try:
            # Only update index every 10 writes to avoid performance impact
            if self.stats["files_written"] % 10 == 0:
                # Import here to avoid circular imports
                from .dataset_indexer import get_dataset_indexer
                
                indexer = get_dataset_indexer()
                indexer.update_index()
                logger.debug(f"Dataset index updated after {self.stats['files_written']} writes")
            
        except Exception as e:
            logger.warning(f"Failed to trigger index update: {e}")


# Global dataset writer instance
_dataset_writer = None


def get_dataset_writer() -> DatasetWriter:
    """Get the global dataset writer instance.
    
    Returns:
        Global DatasetWriter instance
    """
    global _dataset_writer
    if _dataset_writer is None:
        _dataset_writer = DatasetWriter()
    return _dataset_writer


def write_canonical_state(state: Dict[str, Any], image_id: str) -> Path:
    """Convenience function to write canonical state JSON.
    
    Args:
        state: Canonical state dictionary
        image_id: Image identifier
        
    Returns:
        Path to written file
    """
    return get_dataset_writer().write_canonical_state(state, image_id)


def write_annotation(annotation: Dict[str, Any], image_id: str) -> Path:
    """Convenience function to write annotation JSON.
    
    Args:
        annotation: Annotation dictionary
        image_id: Image identifier
        
    Returns:
        Path to written file
    """
    return get_dataset_writer().write_annotation(annotation, image_id)