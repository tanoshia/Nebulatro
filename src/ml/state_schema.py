"""state_schema.py

Canonical state JSON validation for Nebulatro.

Schema includes:
- Core play state (hand, jokers, counters)
- Owned vouchers (vouchers)
- Shop offers (shop.offers), including voucher offers

Place this file at: `src/ml/state_schema.py` (or `src/ml/state_schema.py`).
Place the schema JSON at: `schema/state_schema.json`.

Provides:
- load_schema(): loads JSON schema from disk
- validate_state(state): validates a state dict and raises a clear error

Keep this docstring up to date when the schema changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import jsonschema
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Missing dependency: jsonschema. Install with `pip install jsonschema`."
    ) from e


DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "state_schema.json"


@dataclass(frozen=True)
class StateValidationError(Exception):
    """Raised when a state dict does not match the canonical state schema."""
    message: str
    path: str = ""

    def __str__(self) -> str:
        return f"{self.message}{(' at ' + self.path) if self.path else ''}"


def load_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the canonical state JSON schema.

    Args:
        schema_path: Optional explicit schema path. If None, uses DEFAULT_SCHEMA_PATH.

    Returns:
        Parsed JSON schema as a dict.
    """
    path = schema_path or DEFAULT_SCHEMA_PATH
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_state(state: Dict[str, Any], schema_path: Optional[Path] = None) -> None:
    """Validate a state dict against the canonical schema.

    Args:
        state: The state dictionary to validate.
        schema_path: Optional explicit schema path.

    Raises:
        StateValidationError: If validation fails.
    """
    schema = load_schema(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(state), key=lambda e: e.path)

    if not errors:
        return

    err = errors[0]
    path = ".".join(str(p) for p in err.absolute_path)
    raise StateValidationError(err.message, path)
