"""schema_migrator.py

Schema migration system for Nebulatro canonical state JSON.

Handles version changes and backward compatibility for existing datasets.
Provides automatic migration of state JSON files when schema versions change.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MigrationRule:
    """Defines a migration rule from one schema version to another."""
    from_version: str
    to_version: str
    description: str
    migration_func: Callable[[Dict[str, Any]], Dict[str, Any]]


class SchemaMigrationError(Exception):
    """Raised when schema migration fails."""
    pass


class SchemaMigrator:
    """Handles schema migrations for canonical state JSON files."""
    
    def __init__(self):
        """Initialize schema migrator with built-in migration rules."""
        self.migration_rules: List[MigrationRule] = []
        self.current_version = "1.1"  # Current schema version
        
        # Register built-in migration rules
        self._register_builtin_migrations()
    
    def migrate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a state dictionary to the current schema version.
        
        Args:
            state: State dictionary to migrate
            
        Returns:
            Migrated state dictionary
            
        Raises:
            SchemaMigrationError: If migration fails
        """
        current_version = state.get("schema_version", "1.0")
        
        if current_version == self.current_version:
            return state  # Already current version
        
        logger.info(f"Migrating state from version {current_version} to {self.current_version}")
        
        # Find migration path
        migration_path = self._find_migration_path(current_version, self.current_version)
        
        if not migration_path:
            raise SchemaMigrationError(
                f"No migration path found from {current_version} to {self.current_version}"
            )
        
        # Apply migrations in sequence
        migrated_state = state.copy()
        
        for rule in migration_path:
            try:
                logger.debug(f"Applying migration: {rule.description}")
                migrated_state = rule.migration_func(migrated_state)
                migrated_state["schema_version"] = rule.to_version
                
            except Exception as e:
                raise SchemaMigrationError(
                    f"Migration failed at {rule.from_version} -> {rule.to_version}: {e}"
                ) from e
        
        return migrated_state
    
    def migrate_file(self, file_path: Path, backup: bool = True) -> bool:
        """Migrate a state JSON file to the current schema version.
        
        Args:
            file_path: Path to state JSON file
            backup: Whether to create a backup before migration
            
        Returns:
            True if migration was performed, False if already current version
            
        Raises:
            SchemaMigrationError: If migration fails
        """
        try:
            # Load current state
            with file_path.open("r", encoding="utf-8") as f:
                state = json.load(f)
            
            current_version = state.get("schema_version", "1.0")
            
            if current_version == self.current_version:
                return False  # Already current version
            
            # Create backup if requested
            if backup:
                backup_path = file_path.with_suffix(f".v{current_version}.backup.json")
                with backup_path.open("w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                logger.info(f"Created backup: {backup_path}")
            
            # Migrate state
            migrated_state = self.migrate_state(state)
            
            # Write migrated state
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(migrated_state, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Migrated {file_path} from {current_version} to {self.current_version}")
            return True
            
        except Exception as e:
            raise SchemaMigrationError(f"Failed to migrate file {file_path}: {e}") from e
    
    def migrate_dataset(self, dataset_path: Path, backup: bool = True) -> Dict[str, Any]:
        """Migrate all state files in a dataset to the current schema version.
        
        Args:
            dataset_path: Path to dataset directory
            backup: Whether to create backups before migration
            
        Returns:
            Migration results summary
            
        Raises:
            SchemaMigrationError: If migration fails
        """
        states_dir = dataset_path / "states"
        
        if not states_dir.exists():
            return {"migrated_files": 0, "skipped_files": 0, "errors": []}
        
        results = {
            "migrated_files": 0,
            "skipped_files": 0,
            "errors": []
        }
        
        # Find all state files
        state_files = list(states_dir.rglob("*.state.json"))
        
        for file_path in state_files:
            try:
                migrated = self.migrate_file(file_path, backup)
                
                if migrated:
                    results["migrated_files"] += 1
                else:
                    results["skipped_files"] += 1
                    
            except Exception as e:
                error_msg = f"Failed to migrate {file_path}: {e}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        logger.info(
            f"Dataset migration complete: {results['migrated_files']} migrated, "
            f"{results['skipped_files']} skipped, {len(results['errors'])} errors"
        )
        
        return results
    
    def get_supported_versions(self) -> List[str]:
        """Get list of supported schema versions.
        
        Returns:
            List of version strings
        """
        versions = {self.current_version}
        
        for rule in self.migration_rules:
            versions.add(rule.from_version)
            versions.add(rule.to_version)
        
        return sorted(versions, key=self._version_key)
    
    def register_migration(self, rule: MigrationRule) -> None:
        """Register a custom migration rule.
        
        Args:
            rule: Migration rule to register
        """
        self.migration_rules.append(rule)
        logger.debug(f"Registered migration rule: {rule.description}")
    
    def _register_builtin_migrations(self) -> None:
        """Register built-in migration rules."""
        
        # Migration from 1.0 to 1.1 (example)
        def migrate_1_0_to_1_1(state: Dict[str, Any]) -> Dict[str, Any]:
            """Migrate from schema version 1.0 to 1.1."""
            migrated = state.copy()
            
            # Add new fields that were introduced in 1.1
            if "vouchers" not in migrated:
                migrated["vouchers"] = []
            
            # Ensure all cards have debuff field (default False)
            for card in migrated.get("hand", []):
                if "debuff" not in card:
                    card["debuff"] = False
            
            for card in migrated.get("played_cards", []):
                if "debuff" not in card:
                    card["debuff"] = False
            
            # Ensure all jokers have debuff field (default False)
            for joker in migrated.get("jokers", []):
                if "debuff" not in joker:
                    joker["debuff"] = False
            
            return migrated
        
        self.register_migration(MigrationRule(
            from_version="1.0",
            to_version="1.1",
            description="Add vouchers array and debuff fields",
            migration_func=migrate_1_0_to_1_1
        ))
    
    def _find_migration_path(self, from_version: str, to_version: str) -> Optional[List[MigrationRule]]:
        """Find migration path between two versions.
        
        Args:
            from_version: Starting version
            to_version: Target version
            
        Returns:
            List of migration rules to apply, or None if no path exists
        """
        if from_version == to_version:
            return []
        
        # Simple linear search for now (could be optimized with graph algorithms)
        path = []
        current_version = from_version
        
        while current_version != to_version:
            # Find next migration rule
            next_rule = None
            
            for rule in self.migration_rules:
                if rule.from_version == current_version:
                    # Prefer direct path to target, otherwise take any valid step
                    if rule.to_version == to_version or next_rule is None:
                        next_rule = rule
                    
                    if rule.to_version == to_version:
                        break  # Direct path found
            
            if next_rule is None:
                return None  # No migration path found
            
            path.append(next_rule)
            current_version = next_rule.to_version
            
            # Prevent infinite loops
            if len(path) > 10:
                logger.warning("Migration path too long, possible circular dependency")
                return None
        
        return path
    
    def _version_key(self, version: str) -> tuple:
        """Convert version string to sortable tuple.
        
        Args:
            version: Version string (e.g., "1.2.3")
            
        Returns:
            Tuple of integers for sorting
        """
        try:
            return tuple(int(x) for x in version.split("."))
        except ValueError:
            return (0, 0, 0)  # Fallback for invalid versions


# Global schema migrator instance
_schema_migrator = None


def get_schema_migrator() -> SchemaMigrator:
    """Get the global schema migrator instance.
    
    Returns:
        Global SchemaMigrator instance
    """
    global _schema_migrator
    if _schema_migrator is None:
        _schema_migrator = SchemaMigrator()
    return _schema_migrator


def migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to migrate a state dictionary.
    
    Args:
        state: State dictionary to migrate
        
    Returns:
        Migrated state dictionary
    """
    return get_schema_migrator().migrate_state(state)


def migrate_dataset(dataset_path: Optional[Path] = None) -> Dict[str, Any]:
    """Convenience function to migrate all state files in a dataset.
    
    Args:
        dataset_path: Path to dataset directory (defaults to 'dataset/')
        
    Returns:
        Migration results summary
    """
    path = dataset_path or Path("dataset")
    return get_schema_migrator().migrate_dataset(path)