"""annotation_builder.py

Builds annotation JSON from labeling workflow data.

This module creates rich annotation metadata that captures the complete
labeling context for training and debugging purposes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union


def build_annotation_from_labeling(
    image_path: Path,
    selected_card_class: Optional[Union[int, str]] = None,
    applied_modifiers: Optional[List[tuple]] = None,
    labeling_session_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build annotation JSON from current labeling information.
    
    Args:
        image_path: Path to the source image being labeled
        selected_card_class: The selected card class or special label
        applied_modifiers: List of applied modifiers from modifier manager
        labeling_session_info: Additional session metadata
        
    Returns:
        Dictionary representing annotation data
    """
    
    # Get image metadata
    image_id = image_path.stem
    
    # Get image resolution
    resolution = None
    try:
        import cv2
        image = cv2.imread(str(image_path))
        if image is not None:
            h, w = image.shape[:2]
            resolution = [w, h]
    except Exception:
        pass
    
    # Build base annotation
    annotation = {
        "image_id": image_id,
        "screen_type": "play",  # Default for labeling mode
        "resolution": resolution,
        "timestamp": int(time.time()),
        "source_image_path": str(image_path),
        
        # Labeling results
        "label_type": _determine_label_type(selected_card_class),
        "selected_class": selected_card_class,
        "applied_modifiers": _format_modifiers_for_annotation(applied_modifiers),
        
        # Card information (if applicable)
        "hand": _build_hand_annotation(selected_card_class, applied_modifiers),
        
        # Counters (unknown for single card labeling)
        "counters": {
            "money": None,
            "ante": None,
            "round": None,
            "hands_left": None,
            "discards_left": None
        },
        
        # Additional context
        "jokers": None,  # Not available in single card labeling
        "shop": None     # Not applicable for card labeling
    }
    
    # Add session info if provided
    if labeling_session_info:
        annotation["session"] = labeling_session_info
    
    return annotation


def _determine_label_type(selected_card_class: Optional[Union[int, str]]) -> str:
    """Determine the type of label applied."""
    if selected_card_class is None:
        return "unlabeled"
    elif isinstance(selected_card_class, int) and 0 <= selected_card_class <= 51:
        return "playing_card"
    elif selected_card_class == "not_card":
        return "not_card"
    elif str(selected_card_class).startswith("suit_only"):
        return "suit_only"
    else:
        return "category"


def _format_modifiers_for_annotation(applied_modifiers: Optional[List[tuple]]) -> List[Dict[str, Any]]:
    """Format modifiers for annotation JSON."""
    if not applied_modifiers:
        return []
    
    # Load modifier configuration to get names
    modifier_names = _load_modifier_names()
    
    formatted_modifiers = []
    for modifier_category, modifier_idx in applied_modifiers:
        # Map category names to config keys
        config_category = modifier_category
        if modifier_category == "enhancement":
            config_category = "enhancements"
        elif modifier_category == "edition" or modifier_category == "debuff":
            config_category = "editions"
        elif modifier_category == "seal":
            config_category = "seals"
        
        modifier_info = {
            "category": modifier_category,
            "index": modifier_idx,
            "name": modifier_names.get(config_category, {}).get(modifier_idx, f"Unknown_{modifier_idx}")
        }
        formatted_modifiers.append(modifier_info)
    
    return formatted_modifiers


def _build_hand_annotation(
    selected_card_class: Optional[Union[int, str]], 
    applied_modifiers: Optional[List[tuple]]
) -> Optional[List[Dict[str, Any]]]:
    """Build hand annotation for playing cards."""
    if not isinstance(selected_card_class, int) or not (0 <= selected_card_class <= 51):
        return None
    
    # Map card class to rank and suit
    suit_idx = selected_card_class // 13
    rank_idx = selected_card_class % 13
    
    suits = ["hearts", "clubs", "diamonds", "spades"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    
    suit = suits[suit_idx]
    rank = ranks[rank_idx]
    
    # Build card annotation
    card = {
        "slot": 0,  # Single card labeling
        "rank": rank,
        "suit": suit,
        "edition": None,
        "enhancements": [],
        "seal": None
    }
    
    # Apply modifiers if present
    if applied_modifiers:
        modifier_names = _load_modifier_names()
        
        for modifier_category, modifier_idx in applied_modifiers:
            # Map category names to config keys
            config_category = modifier_category
            if modifier_category == "enhancement":
                config_category = "enhancements"
            elif modifier_category == "edition" or modifier_category == "debuff":
                config_category = "editions"
            elif modifier_category == "seal":
                config_category = "seals"
            
            modifier_name = modifier_names.get(config_category, {}).get(modifier_idx)
            
            if modifier_category == "enhancement" and modifier_name:
                canonical_name = _map_enhancement_to_canonical(modifier_name)
                if canonical_name:
                    card["enhancements"].append(canonical_name)
            
            elif modifier_category == "edition" and modifier_name:
                if modifier_name != "Disabled":  # Disabled is handled as debuff
                    canonical_name = _map_edition_to_canonical(modifier_name)
                    if canonical_name:
                        card["edition"] = canonical_name
            
            elif modifier_category == "seal" and modifier_name:
                canonical_name = _map_seal_to_canonical(modifier_name)
                if canonical_name:
                    card["seal"] = canonical_name
    
    return [card]


def save_annotation(annotation: Dict[str, Any], image_id: str) -> Path:
    """Save annotation JSON to dataset/annotations directory.
    
    Args:
        annotation: Annotation dictionary
        image_id: Image identifier for filename
        
    Returns:
        Path to saved annotation file
    """
    from .dataset_writer import write_annotation
    return write_annotation(annotation, image_id)


def _load_modifier_names() -> Dict[str, Dict[int, str]]:
    """Load modifier names from configuration file."""
    import json
    
    config_path = Path("config/card_order_config.json")
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    
    modifiers_config = config["modifiers"]
    
    # Build index to name mappings
    modifier_names = {}
    
    for category in ["enhancements", "editions", "seals"]:
        if category in modifiers_config:
            indices = modifiers_config[category]["indices"]
            names = modifiers_config[category]["names"]
            modifier_names[category] = dict(zip(indices, names))
    
    return modifier_names


def _map_enhancement_to_canonical(enhancement_name: str) -> Optional[str]:
    """Map enhancement name to canonical format."""
    mapping = {
        "Stone": "stone",
        "Gold": "gold",
        "Bonus": "bonus",
        "Mult": "mult",
        "Wild": "wild",
        "Lucky": "lucky",
        "Glass": "glass",
        "Steel": "steel"
    }
    return mapping.get(enhancement_name)


def _map_edition_to_canonical(edition_name: str) -> Optional[str]:
    """Map edition name to canonical format."""
    mapping = {
        "Foil": "foil",
        "Holographic": "holographic",
        "Polychrome": "polychrome"
    }
    return mapping.get(edition_name)


def _map_seal_to_canonical(seal_name: str) -> Optional[str]:
    """Map seal name to canonical format."""
    mapping = {
        "Gold_Seal": "gold",
        "Purple_Seal": "purple", 
        "Red_Seal": "red",
        "Blue_Seal": "blue"
    }
    return mapping.get(seal_name)