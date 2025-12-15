"""state_builder.py

Builds canonical state JSON from current labeling information.

This module provides functionality to construct a canonical game state JSON
that conforms to the schema defined in schema/state_schema.json.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


def build_canonical_state_from_labeling(
    selected_card_class: Optional[int] = None,
    applied_modifiers: Optional[List[tuple]] = None,
    image_id: Optional[str] = None,
    resolution: Optional[tuple] = None
) -> Dict[str, Any]:
    """Build canonical state JSON from current labeling information.
    
    Args:
        selected_card_class: The selected card class (0-51 for playing cards)
        applied_modifiers: Dictionary of applied modifiers from modifier manager
        image_id: Source image identifier
        resolution: Image resolution as (width, height) tuple
        
    Returns:
        Dictionary representing canonical game state
    """
    
    # Build hand from selected card and modifiers
    hand = []
    if selected_card_class is not None and isinstance(selected_card_class, int) and 0 <= selected_card_class <= 51:
        card = _build_card_from_class_and_modifiers(selected_card_class, applied_modifiers)
        hand = [card]
    
    # Build minimal valid canonical state
    state = {
        "schema_version": "1.1",
        "screen": {
            "type": "play",  # Default to play screen for labeling
            "substate": "select_cards"
        },
        "hand": hand,
        "played_cards": [],
        "jokers": [],
        "economy": {
            "money": 0,
            "interest_cap": 0
        },
        "round": {
            "ante": 0,
            "blind": "unknown",
            "hands_left": 0,
            "discards_left": 0
        },
        "score": {
            "current": 0,
            "required": 0
        },
        "rng_visible": False
    }
    
    # Add optional meta information if available
    if image_id or resolution:
        state["meta"] = {}
        if image_id:
            state["meta"]["source_image_id"] = image_id
        if resolution:
            state["meta"]["resolution"] = list(resolution)
        state["meta"]["timestamp"] = int(time.time())
    
    return state


def _build_card_from_class_and_modifiers(card_class: int, applied_modifiers: Optional[List[tuple]] = None) -> Dict[str, Any]:
    """Build a card instance from class ID and applied modifiers.
    
    Args:
        card_class: Card class ID (0-51)
        applied_modifiers: Dictionary of applied modifiers
        
    Returns:
        Card instance dictionary
    """
    
    # Map card class to rank and suit
    # Card classes: 0-12 Hearts, 13-25 Clubs, 26-38 Diamonds, 39-51 Spades
    # Within each suit: 0=2, 1=3, ..., 12=A
    suit_idx = card_class // 13  # 0=H, 1=C, 2=D, 3=S
    rank_idx = card_class % 13   # 0=2, 1=3, ..., 12=A
    
    suits = ["hearts", "clubs", "diamonds", "spades"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    
    suit = suits[suit_idx]
    rank = ranks[rank_idx]
    
    # Build card instance
    card = {
        "id": f"{rank}_{suit}",
        "rank": rank,
        "suit": suit,
        "edition": None,
        "enhancements": [],
        "seal": None,
        "debuff": False
    }
    
    # Apply modifiers if provided
    if applied_modifiers:
        # Load modifier configuration to map indices to names
        modifier_names = _load_modifier_names()
        
        for modifier_category, modifier_idx in applied_modifiers:
            if modifier_category == "enhancement":
                enhancement_name = modifier_names["enhancements"].get(modifier_idx)
                if enhancement_name:
                    canonical_name = _map_enhancement_to_canonical(enhancement_name)
                    if canonical_name:
                        card["enhancements"].append(canonical_name)
            
            elif modifier_category == "edition":
                edition_name = modifier_names["editions"].get(modifier_idx)
                if edition_name:
                    if edition_name == "Disabled":
                        card["debuff"] = True
                    else:
                        canonical_name = _map_edition_to_canonical(edition_name)
                        if canonical_name:
                            card["edition"] = canonical_name
            
            elif modifier_category == "seal":
                seal_name = modifier_names["seals"].get(modifier_idx)
                if seal_name:
                    canonical_name = _map_seal_to_canonical(seal_name)
                    if canonical_name:
                        card["seal"] = canonical_name
            
            elif modifier_category == "debuff":
                card["debuff"] = True
    
    return card


def save_canonical_state(state: Dict[str, Any], image_id: str) -> Path:
    """Save canonical state JSON to dataset/states directory.
    
    Args:
        state: Canonical state dictionary
        image_id: Image identifier for filename
        
    Returns:
        Path to saved state file
    """
    from .dataset_writer import write_canonical_state
    return write_canonical_state(state, image_id)


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