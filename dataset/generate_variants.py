#!/usr/bin/env python3
"""
Generate synthetic Balatro-like card variants from spritesheets.
Config: `    render_scale: int = 6,        # 6-8 is a good range for 69x93`

Inputs:
  - ./resources/textures/1x/{spritesheet}.png
  - ./resources/shaders/{shaderfile}.fs   (used as "feature toggles" + reference)

Outputs:
  - ./dataset/raw_generated/{input_filename}/{tile_index}.png
    Each output is a 4x4 spritesheet of 16 slightly-random variations of that tile.

Notes:
  - This does NOT compile Love2D shaders. It approximates the *visual effects*
    implied by skew.fs, played.fs, CRT.fs (and lightly others) in Pillow/Numpy.
  - You should tune TILE_W/H and GRID (rows/cols) per spritesheet for best slicing.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import json
from tqdm import tqdm
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


# -----------------------------
# Config loading from resource_mapping.json
# -----------------------------
def load_resource_config(config_path: str = "./config/resource_mapping.json") -> Dict[str, Dict[str, int]]:
    """Load sprite sheet configurations from resource_mapping.json"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"[warn] Config file not found: {config_path}. Using fallback config.")
        return get_fallback_config()
    
    sheet_config = {}
    
    # Standard tile dimensions and margins for Balatro cards
    default_tile_config = {
        "tile_w": 69, "tile_h": 93, 
        "margin_x": 1, "margin_y": 1, 
        "pad_x": 2, "pad_y": 2
    }
    
    sprite_sheets = config.get("sprite_sheets", {})
    
    # Process main sprite sheets
    for sheet_key, sheet_data in sprite_sheets.items():
        resource_file = sheet_data.get("resource_file")
        if resource_file:
            grid = sheet_data.get("grid", {})
            sheet_config[resource_file] = {
                **default_tile_config,
                "cols": grid.get("cols", 1),
                "rows": grid.get("rows", 1)
            }
    
    # Process collab face cards
    collab_data = sprite_sheets.get("collab_face_cards", {})
    if collab_data:
        default_grid = collab_data.get("default_grid", {"cols": 3, "rows": 1})
        variants = collab_data.get("variants", {})
        
        for suit_variants in variants.values():
            for variant in suit_variants:
                # Add both standard and high_contrast versions
                for version_key in ["standard", "high_contrast"]:
                    filename = variant.get(version_key)
                    if filename:
                        sheet_config[filename] = {
                            **default_tile_config,
                            "cols": default_grid["cols"],
                            "rows": default_grid["rows"]
                        }
    
    return sheet_config

def get_fallback_config() -> Dict[str, Dict[str, int]]:
    """Fallback configuration if resource_mapping.json is not available"""
    default_config = {"tile_w": 69, "tile_h": 93, "margin_x": 1, "margin_y": 1, "pad_x": 2, "pad_y": 2}
    return {
        "Jokers.png": {**default_config, "cols": 10, "rows": 16},
        "Tarots.png": {**default_config, "cols": 10, "rows": 6},
        "8BitDeck.png": {**default_config, "cols": 13, "rows": 4},
        "8BitDeck_opt2.png": {**default_config, "cols": 13, "rows": 4},
        "Enhancers.png": {**default_config, "cols": 7, "rows": 5},
    }

# Load configuration at module level
SHEET_CONFIG = load_resource_config()
SPRITESHEET_BACKS = {
    # Based on 7x5 Enhancers.png grid (col, row)
    "base":   (1, 0),   # index 1: card_back_default
    # "stone":  (5, 0),   # index 5: stone_enhancement
    "gold":   (6, 0),   # index 6: gold_enhancement
    "bonus":  (1, 1),   # index 8: bonus_enhancement
    "mult":   (2, 1),   # index 9: mult_enhancement
    "wild":   (3, 1),   # index 10: wild_enhancement
    "lucky":  (4, 1),   # index 11: lucky_enhancement
    "glass":  (5, 1),   # index 12: glass_enhancement
    "steel":  (6, 1),   # index 13: steel_enhancement
}
BACK_COL, BACK_ROW = SPRITESHEET_BACKS["base"]

def get_base_composite_config(config_path: str = "./config/resource_mapping.json") -> Dict[str, Tuple[str, int, int]]:
    """Generate base composite config from resource mapping"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        return get_fallback_composite_config()
    
    composite_config = {}
    sprite_sheets = config.get("sprite_sheets", {})
    
    # Sheets that should NOT get composite backgrounds
    excluded_sheets = {"vouchers", "enhancers", "editions"}
    
    # Add composite backgrounds to all sheets except excluded ones
    for sheet_key, sheet_data in sprite_sheets.items():
        if sheet_key.lower() in excluded_sheets:
            continue
            
        resource_file = sheet_data.get("resource_file")
        if resource_file:
            composite_config[resource_file] = ("Enhancers.png", BACK_COL, BACK_ROW)
    
    # Handle collab face cards (they're nested in variants)
    collab_data = sprite_sheets.get("collab_face_cards", {})
    if collab_data:
        variants = collab_data.get("variants", {})
        for suit_variants in variants.values():
            for variant in suit_variants:
                for version_key in ["standard", "high_contrast"]:
                    filename = variant.get(version_key)
                    if filename:
                        composite_config[filename] = ("Enhancers.png", BACK_COL, BACK_ROW)
    
    return composite_config

def get_fallback_composite_config() -> Dict[str, Tuple[str, int, int]]:
    """Fallback composite config"""
    return {
        "8BitDeck.png": ("Enhancers.png", BACK_COL, BACK_ROW),
        "8BitDeck_opt2.png": ("Enhancers.png", BACK_COL, BACK_ROW),
    }

BASE_COMPOSITE_CONFIG = get_base_composite_config()

def crop_tile_from_sheet(img: Image.Image, grid: Grid, col: int, row: int) -> Image.Image:
    x0 = grid.margin_x + col * (grid.tile_w + grid.pad_x)
    y0 = grid.margin_y + row * (grid.tile_h + grid.pad_y)
    return img.crop((x0, y0, x0 + grid.tile_w, y0 + grid.tile_h)).convert("RGBA")



@dataclass
class Grid:
    tile_w: int
    tile_h: int
    cols: int
    rows: int
    margin_x: int = 0
    margin_y: int = 0
    pad_x: int = 0
    pad_y: int = 0


# -----------------------------
# Utilities
# -----------------------------
def load_image(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img


def shader_exists(shader_dir: Path, name: str) -> bool:
    return (shader_dir / name).exists()


def clamp01(x: np.ndarray) -> np.ndarray:
    return np.clip(x, 0.0, 1.0)


def pil_to_np(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img).astype(np.float32) / 255.0
    return arr


def np_to_pil(arr: np.ndarray) -> Image.Image:
    arr = clamp01(arr)
    out = (arr * 255.0).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def create_realistic_background(output_size: Tuple[int, int], rng: random.Random) -> Image.Image:
    """
    Create a realistic game background by combining two random background images.
    Top half from standard/, bottom half from misc/.
    """
    width, height = output_size
    
    # Paths to background directories
    standard_dir = Path("./assets/backgrounds/cropped/standard")
    misc_dir = Path("./assets/backgrounds/cropped/misc")
    
    # Check if directories exist
    if not standard_dir.exists() or not misc_dir.exists():
        # Fallback to solid black if background assets don't exist
        return Image.new("RGB", output_size, (0, 0, 0))
    
    # Get list of background files
    standard_files = list(standard_dir.glob("*.png")) + list(standard_dir.glob("*.jpg"))
    misc_files = list(misc_dir.glob("*.png")) + list(misc_dir.glob("*.jpg"))
    
    if not standard_files or not misc_files:
        # Fallback to solid black if no background files found
        return Image.new("RGB", output_size, (0, 0, 0))
    
    # Select random backgrounds
    standard_bg_path = rng.choice(standard_files)
    misc_bg_path = rng.choice(misc_files)
    
    try:
        # Load and resize backgrounds to fit half-height
        half_height = height // 2
        
        standard_bg = Image.open(standard_bg_path).convert("RGB")
        standard_bg = standard_bg.resize((width, half_height), Image.LANCZOS)
        
        misc_bg = Image.open(misc_bg_path).convert("RGB")
        misc_bg = misc_bg.resize((width, height - half_height), Image.LANCZOS)
        
        # Create composite background
        background = Image.new("RGB", output_size, (0, 0, 0))
        background.paste(standard_bg, (0, 0))
        background.paste(misc_bg, (0, half_height))
        
        return background
        
    except Exception as e:
        print(f"[warn] Failed to load background images: {e}. Using solid black.")
        return Image.new("RGB", output_size, (0, 0, 0))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_filename_mapping(config_path: str = "./config/resource_mapping.json") -> Dict[str, Dict[int, str]]:
    """Generate filename mappings from resource config for meaningful output names"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        return {}
    
    filename_mappings = {}
    sprite_sheets = config.get("sprite_sheets", {})
    
    # Handle playing cards
    playing_cards = sprite_sheets.get("playing_cards", {})
    if playing_cards.get("resource_file"):
        card_naming = playing_cards.get("card_naming", {})
        suits = card_naming.get("suits", ["H", "C", "D", "S"])
        ranks = card_naming.get("ranks", ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"])
        
        mapping = {}
        idx = 0
        for suit in suits:
            for rank in ranks:
                mapping[idx] = f"{rank}{suit}"
                idx += 1
        filename_mappings[playing_cards["resource_file"]] = mapping
    
    # Handle high contrast playing cards
    playing_cards_hc = sprite_sheets.get("playing_cards_high_contrast", {})
    if playing_cards_hc.get("resource_file"):
        # Same mapping as regular playing cards
        filename_mappings[playing_cards_hc["resource_file"]] = filename_mappings.get(playing_cards["resource_file"], {})
    
    # Handle collab face cards
    collab_data = sprite_sheets.get("collab_face_cards", {})
    if collab_data:
        default_cards = collab_data.get("default_cards", ["J", "Q", "K"])
        variants = collab_data.get("variants", {})
        
        for suit_name, suit_variants in variants.items():
            # Convert suit name to single letter (spades->S, hearts->H, etc.)
            suit_letter = suit_name[0].upper()
            
            for variant in suit_variants:
                variant_id = variant.get("id", "unknown")
                mapping = {}
                for i, card in enumerate(default_cards):
                    # Format: {rank}{suit}_{collab_id}
                    mapping[i] = f"{card}{suit_letter}_{variant_id}"
                
                # Apply to both standard and high contrast versions
                for version_key in ["standard", "high_contrast"]:
                    filename = variant.get(version_key)
                    if filename:
                        filename_mappings[filename] = mapping
    
    # Handle enhancers with explicit card mappings
    enhancers = sprite_sheets.get("enhancers", {})
    if enhancers.get("resource_file") and enhancers.get("cards"):
        cards = enhancers["cards"]
        mapping = {}
        for idx_str, card_name in cards.items():
            try:
                idx = int(idx_str)
                mapping[idx] = card_name
            except ValueError:
                continue
        filename_mappings[enhancers["resource_file"]] = mapping
    
    # Handle editions
    editions = sprite_sheets.get("editions", {})
    if editions.get("resource_file") and editions.get("cards"):
        cards = editions["cards"]
        mapping = {}
        for idx_str, card_name in cards.items():
            try:
                idx = int(idx_str)
                mapping[idx] = card_name
            except ValueError:
                continue
        filename_mappings[editions["resource_file"]] = mapping
    
    return filename_mappings

# Load filename mappings at module level
FILENAME_MAPPINGS = get_filename_mapping()

# -----------------------------
# Helpers
# -----------------------------
def _perspective_coeffs(pa, pb):
    """
    Solve coefficients for PIL.Image.transform(PERSPECTIVE) mapping.
    pa: list of 4 (x, y) in output image
    pb: list of 4 (x, y) in input image
    Returns 8 coefficients.
    """
    import numpy as _np
    A = []
    B = []
    for (x, y), (u, v) in zip(pa, pb):
        A.append([x, y, 1, 0, 0, 0, -u*x, -u*y])
        A.append([0, 0, 0, x, y, 1, -v*x, -v*y])
        B.append(u)
        B.append(v)
    A = _np.array(A, dtype=_np.float64)
    B = _np.array(B, dtype=_np.float64)
    coeffs = _np.linalg.lstsq(A, B, rcond=None)[0]
    return coeffs.tolist()

def upscale(img: Image.Image, s: int) -> Image.Image:
    if s == 1:
        return img
    return img.resize((img.size[0] * s, img.size[1] * s), resample=Image.NEAREST)

def downscale(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    # LANCZOS is best for downsampling
    return img.resize(size, resample=Image.LANCZOS)

from PIL import Image, ImageFilter  # ensure ImageFilter imported

def _upscale_nearest(img: Image.Image, s: int) -> Image.Image:
    if s <= 1:
        return img
    w, h = img.size
    return img.resize((w * s, h * s), resample=Image.NEAREST)

def _downscale_lanczos(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return img.resize(size, resample=Image.LANCZOS)

def render_card_to_cell(
    tile: Image.Image,
    rng: random.Random,
    use_skew: bool,
    use_played: bool,
    use_crt: bool,
    *,
    render_scale: int = 3,        # 3-6 is a good range for 69x93
    cell_extra_px: int = 32,      # extra space around card in "base pixels"
    out_cell_extra_px: int = 8,  # extra space in final output cell (also in base pixels)
) -> Image.Image:
    """
    Render one card into a larger cell to mimic "GPU moves the card on a big screen".

    Returns an RGBA image sized:
      ((tile_w + out_cell_extra_px) * render_scale, (tile_h + out_cell_extra_px) * render_scale)
    """

    base_w, base_h = tile.size

    # Work at high resolution (preserve pixel art)
    hi_tile = _upscale_nearest(tile, render_scale)
    hi_w, hi_h = hi_tile.size

    # High-res render cell (lots of room so transforms won't clip)
    hi_cell_w = hi_w + cell_extra_px * render_scale
    hi_cell_h = hi_h + cell_extra_px * render_scale
    img = Image.new("RGBA", (hi_cell_w, hi_cell_h), (0, 0, 0, 0))

    # Center the sprite in the high-res cell
    cx = (hi_cell_w - hi_w) // 2
    cy = (hi_cell_h - hi_h) // 2
    img.alpha_composite(hi_tile, (cx, cy))

    # Apply transforms on the big cell
    if use_skew:
        img = apply_skew_perspective(img, rng)  # keep resample=BICUBIC inside

    img = apply_rotation(img, rng)  # BICUBIC is fine

    # Post-geometry grading
    if use_played:
        img = apply_shadow(img, rng)
        img = apply_color_grade(img, rng)

    if use_crt:
        img = apply_crt_light(img, rng)

    # Final output size (keep it large)
    final_w = (base_w + out_cell_extra_px) * render_scale
    final_h = (base_h + out_cell_extra_px) * render_scale

    # Downsample only to the large target, not back to tiny
    out = _downscale_lanczos(img, (final_w, final_h))
    out = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=125, threshold=2))
    return out



# -----------------------------
# Slicing (grid-based)
# -----------------------------
def guess_grid(img: Image.Image) -> Grid:
    """
    Crude fallback: guess tile size by finding common repeating transparent gutters.
    This won't be perfect. Prefer setting SHEET_CONFIG.
    """
    w, h = img.size
    # Fallback guesses that often match Balatro card-ish assets
    # (These are NOT guaranteed correct for your files)
    candidates = [(71, 95), (69, 93), (72, 96), (70, 94)]
    # Try to pick one that divides reasonably
    best = None
    best_score = 1e9
    for tw, th in candidates:
        cols = max(1, w // tw)
        rows = max(1, h // th)
        score = abs(w - cols * tw) + abs(h - rows * th)
        if score < best_score:
            best_score = score
            best = (tw, th, cols, rows)
    tw, th, cols, rows = best
    return Grid(tile_w=tw, tile_h=th, cols=cols, rows=rows)


def slice_tiles(sheet: Image.Image, grid: Grid) -> Dict[int, Image.Image]:
    tiles: Dict[int, Image.Image] = {}
    idx = 0
    for r in range(grid.rows):
        for c in range(grid.cols):
            x0 = grid.margin_x + c * (grid.tile_w + grid.pad_x)
            y0 = grid.margin_y + r * (grid.tile_h + grid.pad_y)
            x1 = x0 + grid.tile_w
            y1 = y0 + grid.tile_h
            if x1 > sheet.size[0] or y1 > sheet.size[1]:
                continue
            tile = sheet.crop((x0, y0, x1, y1))
            tiles[idx] = tile
            idx += 1
    return tiles


# -----------------------------
# Effects approximating .fs logic
# -----------------------------
def apply_skew_perspective(img: Image.Image, rng: random.Random) -> Image.Image:
    """
    Subtle trapezoid + tiny shear, using a correct PERSPECTIVE transform.
    Output stays same size, no surprise 90deg rotation.
    """
    w, h = img.size

    top_shrink = rng.uniform(0.92, 0.98)
    dx = (1.0 - top_shrink) * w * 0.5
    shear = rng.uniform(-0.03, 0.03) * w

    # Output quad (where we want the input corners to land)
    ul = (dx + shear, rng.uniform(0.0, 0.01) * h)
    ur = (w - dx + shear, rng.uniform(0.0, 0.01) * h)
    lr = (w + rng.uniform(-0.01, 0.01) * w, h)
    ll = (rng.uniform(-0.01, 0.01) * w, h)

    out_quad = [ul, ur, lr, ll]
    in_quad = [(0, 0), (w, 0), (w, h), (0, h)]

    coeffs = _perspective_coeffs(out_quad, in_quad)
    return img.transform((w, h), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)


def apply_rotation(img: Image.Image, rng: random.Random) -> Image.Image:
    angle = rng.uniform(-3.0, 3.0)
    return img.rotate(angle, resample=Image.BICUBIC, expand=False)


def apply_shadow(img: Image.Image, rng: random.Random) -> Image.Image:
    """
    Approximation of played.fs shadow behavior:
    - soft drop shadow behind sprite
    """
    w, h = img.size
    offset_x = int(rng.uniform(2, 6))
    offset_y = int(rng.uniform(3, 7))
    blur = rng.uniform(2.0, 4.5)
    alpha_scale = rng.uniform(0.18, 0.32)

    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # shadow from alpha channel
    a = img.split()[-1]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow.putalpha(a)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur))

    # scale shadow alpha
    sh_np = pil_to_np(shadow)
    sh_np[..., 3] *= alpha_scale
    shadow = np_to_pil(sh_np)

    base.alpha_composite(shadow, (offset_x, offset_y))
    base.alpha_composite(img, (0, 0))
    return base


def apply_color_grade(img: Image.Image, rng: random.Random) -> Image.Image:
    """
    Approximation of the mild grade/curve seen in-game:
    - slight contrast bump
    - tiny saturation tweak
    - gentle shadow lift
    """
    # Contrast / saturation as Pillow enhancers
    contrast = ImageEnhance.Contrast(img).enhance(rng.uniform(1.03, 1.10))
    color = ImageEnhance.Color(contrast).enhance(rng.uniform(1.02, 1.10))

    arr = pil_to_np(color)

    # Shadow lift: push low values up a tiny bit (avoid crushing pixel art)
    lift = rng.uniform(0.015, 0.040)
    rgb = arr[..., :3]
    rgb = rgb + lift * (1.0 - rgb)
    arr[..., :3] = clamp01(rgb)

    return np_to_pil(arr)


def apply_crt_light(img: Image.Image, rng: random.Random) -> Image.Image:
    """
    Very light CRT.fs-inspired finish:
    - subtle scanlines
    - small chromatic offset
    - mild noise
    - optional tiny glitch stripe
    """
    arr = pil_to_np(img)
    h, w = arr.shape[0], arr.shape[1]

    # scanlines (very subtle)
    scan_amp = rng.uniform(0.005, 0.02)
    scan_freq = rng.uniform(0.8, 1.6)  # cycles over height
    y = np.linspace(0, 2 * math.pi * scan_freq, h, dtype=np.float32)
    scan = (1.0 - scan_amp * (0.5 * (1.0 + np.sin(y))))[:, None]
    arr[..., :3] *= scan[:, :, None]

    # chromatic aberration: shift R and B by +-1 px occasionally
    if rng.random() < 0.9:
        r_shift = rng.choice([-1, 0, 1])
        b_shift = rng.choice([-1, 0, 1])
        arr_r = np.roll(arr[..., 0], shift=r_shift, axis=1)
        arr_b = np.roll(arr[..., 2], shift=b_shift, axis=1)
        arr[..., 0] = arr_r
        arr[..., 2] = arr_b

    # noise (tiny)
    noise_amp = rng.uniform(0.002, 0.010)
    noise = (rng.random() * 0.0)  # keep RNG usage deterministic-ish
    n = (np.random.rand(h, w).astype(np.float32) - 0.5) * 2.0 * noise_amp
    arr[..., :3] = clamp01(arr[..., :3] + n[..., None])

    # small horizontal glitch band (rare)
    if rng.random() < 0.10:
        band_y = rng.randint(0, max(0, h - 3))
        band_h = rng.randint(1, 3)
        band_shift = rng.randint(-2, 2)
        arr[band_y:band_y + band_h, :, :3] = np.roll(arr[band_y:band_y + band_h, :, :3], shift=band_shift, axis=1)

    return np_to_pil(arr)


def apply_misc_augment(img: Image.Image, rng: random.Random) -> Image.Image:
    """
    Small extra jitter that often exists due to scaling/resampling:
    - tiny scale bounce and recenter (kept subtle)
    """
    w, h = img.size
    scale = rng.uniform(0.985, 1.020)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    tmp = img.resize((nw, nh), resample=Image.BICUBIC)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (w - nw) // 2 + int(rng.uniform(-1, 1))
    oy = (h - nh) // 2 + int(rng.uniform(-1, 1))
    out.alpha_composite(tmp, (ox, oy))
    return out


# -----------------------------
# Variant generation
# -----------------------------
def make_variation(
    tile: Image.Image,
    rng: random.Random,
    use_skew: bool,
    use_played: bool,
    use_crt: bool,
    render_scale: int = 3,   # try 3 or 4
) -> Image.Image:
    base_size = tile.size

    # Work at higher res to prevent mush
    img = upscale(tile, render_scale)

    if use_skew:
        img = apply_skew_perspective(img, rng)

    img = apply_rotation(img, rng)

    # Remove this if you want max crispness (it adds another resample)
    # img = apply_misc_augment(img, rng)

    if use_played:
        img = apply_shadow(img, rng)
        img = apply_color_grade(img, rng)

    if use_crt:
        img = apply_crt_light(img, rng)

    # Downsample back to original size
    img = downscale(img, base_size)

    # Tiny sharpening to restore edge snap after downsample
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=2))

    return img


def compose_4x4(variants: Tuple[Image.Image, ...], cell_pad: int = 4, bg=(0, 0, 0, 0), bg_img: Image.Image = None) -> Image.Image:
    assert len(variants) == 16
    cell_w, cell_h = variants[0].size

    out_w = 4 * cell_w + 3 * cell_pad
    out_h = 4 * cell_h + 3 * cell_pad
    
    if bg_img is not None:
        # Use provided background image, resize if necessary
        out = bg_img.resize((out_w, out_h), Image.LANCZOS).convert("RGBA")
    else:
        # Use solid color background
        out = Image.new("RGBA", (out_w, out_h), bg)

    i = 0
    for r in range(4):
        for c in range(4):
            x = c * (cell_w + cell_pad)
            y = r * (cell_h + cell_pad)
            out.alpha_composite(variants[i], (x, y))
            i += 1

    return out

def process_spritesheet(args, spritesheet_name: str) -> None:
    # Check if this is a collab file that needs special path handling
    if spritesheet_name.startswith("collab_"):
        tex_path = Path(args.texdir) / "collabs" / spritesheet_name
    else:
        tex_path = Path(args.texdir) / spritesheet_name
    
    shader_dir = Path(args.shaderdir)

    if not tex_path.exists():
        print(f"[skip] Missing spritesheet: {tex_path}")
        return

    sheet = load_image(tex_path)

    if spritesheet_name in SHEET_CONFIG:
        cfg = SHEET_CONFIG[spritesheet_name]
        
        # Validate configuration has valid dimensions
        if cfg.get("cols") is None or cfg.get("rows") is None:
            print(f"[skip] Invalid grid configuration for {spritesheet_name}: cols={cfg.get('cols')}, rows={cfg.get('rows')}")
            return
            
        grid = Grid(
            tile_w=cfg["tile_w"],
            tile_h=cfg["tile_h"],
            cols=cfg["cols"],
            rows=cfg["rows"],
            margin_x=cfg.get("margin_x", 0),
            margin_y=cfg.get("margin_y", 0),
            pad_x=cfg.get("pad_x", 0),
            pad_y=cfg.get("pad_y", 0),
        )
    else:
        grid = guess_grid(sheet)
        print(f"[warn] Using guessed grid for {spritesheet_name}: {grid}. Set SHEET_CONFIG for accurate slicing.")

    tiles = slice_tiles(sheet, grid)
    if not tiles:
        print(f"[skip] No tiles found for {spritesheet_name}")
        return

    # Output dir: ./dataset/raw_generated/{category}/
    # Group collab files under single "collabs" folder
    if spritesheet_name.startswith("collab_"):
        out_dir = Path(args.outdir) / "collabs"
    else:
        sheet_name = Path(spritesheet_name).stem
        out_dir = Path(args.outdir) / sheet_name
    ensure_dir(out_dir)

    # Shader presence toggles
    use_skew = shader_exists(shader_dir, "skew.fs")
    use_played = shader_exists(shader_dir, "played.fs")
    use_crt = shader_exists(shader_dir, "CRT.fs")

    # Reduce verbosity for collab files to avoid terminal clutter
    if not spritesheet_name.startswith("collab_"):
        print(f"\n== {spritesheet_name} ==")
        print(f"Using effects: skew={use_skew}, played={use_played}, crt={use_crt}")
        print(f"Tiles detected: {len(tiles)}")
        print(f"Output dir: {out_dir}")

    # Base compositing (8BitDeck -> base face)
    back_tiles: dict[str, Image.Image] | None = None
    if spritesheet_name in BASE_COMPOSITE_CONFIG:
        base_name = BASE_COMPOSITE_CONFIG[spritesheet_name][0]
        base_path = Path(args.texdir) / base_name
        if not base_path.exists():
            raise FileNotFoundError(f"Missing base sheet for compositing: {base_path}")

        base_sheet = load_image(base_path)

        # Use the correct grid configuration for the base sheet
        if base_name in SHEET_CONFIG:
            base_cfg = SHEET_CONFIG[base_name]
            base_grid = Grid(
                tile_w=base_cfg["tile_w"],
                tile_h=base_cfg["tile_h"],
                cols=base_cfg["cols"],
                rows=base_cfg["rows"],
                margin_x=base_cfg.get("margin_x", 0),
                margin_y=base_cfg.get("margin_y", 0),
                pad_x=base_cfg.get("pad_x", 0),
                pad_y=base_cfg.get("pad_y", 0),
            )
        else:
            # Fallback to old hardcoded values
            base_grid = Grid(
                tile_w=69, tile_h=93,
                cols=14, rows=10,
                margin_x=1, margin_y=1,
                pad_x=2, pad_y=2,
            )

        # Filter back tiles based on --modifiers flag
        if args.modifiers:
            # Generate all modifier variants
            back_tiles = {
                name: crop_tile_from_sheet(base_sheet, base_grid, col, row)
                for name, (col, row) in SPRITESHEET_BACKS.items()
            }
        else:
            # Only generate base cards
            back_tiles = {
                "base": crop_tile_from_sheet(base_sheet, base_grid, 
                                           SPRITESHEET_BACKS["base"][0], 
                                           SPRITESHEET_BACKS["base"][1])
            }

    rng_global = random.Random(args.seed)

    count = 0
    tile_items = list(tiles.items())
    # Create descriptive progress bar
    # For collab files: don't leave progress bar after completion to reduce clutter
    if spritesheet_name.startswith("collab_"):
        desc = f"{spritesheet_name} -> collabs/"
        leave = False
    else:
        desc = spritesheet_name
        leave = True
    pbar = tqdm(tile_items, desc=desc, unit="tile", leave=leave)
    for idx, tile in pbar:
        if args.limit > 0 and count >= args.limit:
            break

        # Skip fully transparent tiles
        a = np.asarray(tile.split()[-1])
        if int(a.max()) == 0:
            continue

        # Determine which backs to render
        if back_tiles is None:
            back_iter = [(None, tile)]
        else:
            back_iter = []
            for back_name, back_img in back_tiles.items():
                composed = back_img.copy()
                composed.alpha_composite(tile, (0, 0))
                back_iter.append((back_name, composed))

        # Render once per back
        for back_name, composed_tile in back_iter:
            tile_seed = rng_global.randint(0, 2**31 - 1)

            vars16 = tuple(
                render_card_to_cell(
                    composed_tile,
                    rng=random.Random(tile_seed + k * 9973),
                    use_skew=use_skew,
                    use_played=use_played,
                    use_crt=use_crt,
                    render_scale=args.render_scale,
                    cell_extra_px=args.cell_extra_px,
                    out_cell_extra_px=args.out_cell_extra_px,
                )
                for k in range(16)
            )

            # Choose background based on solid-background flag
            if args.solid_background:
                # Calculate expected output size for background generation
                cell_w = (69 + args.out_cell_extra_px) * args.render_scale
                cell_h = (93 + args.out_cell_extra_px) * args.render_scale
                output_w = 4 * cell_w + 3 * args.cell_pad
                output_h = 4 * cell_h + 3 * args.cell_pad
                
                # Create realistic game background instead of solid black
                bg_img = create_realistic_background((output_w, output_h), 
                                                   random.Random(tile_seed + 12345))
                bg_color = (0, 0, 0, 255)  # Will be replaced with background image
            else:
                bg_img = None
                bg_color = (0, 0, 0, 0)    # Transparent
                
            out_img = compose_4x4(
                vars16,
                cell_pad=args.cell_pad,
                bg=bg_color,
                bg_img=bg_img if args.solid_background else None,
            )
            
            # Convert to RGB if solid background requested (removes transparency)
            if args.solid_background:
                if out_img.mode == 'RGBA':
                    # Convert RGBA to RGB (background should already be applied)
                    rgb_img = Image.new("RGB", out_img.size, (0, 0, 0))
                    rgb_img.paste(out_img, mask=out_img.split()[-1])
                    out_img = rgb_img

            # Generate meaningful filename
            base_name = FILENAME_MAPPINGS.get(spritesheet_name, {}).get(idx, str(idx))
            
            # Add HC suffix for high contrast files
            is_high_contrast = (spritesheet_name == "8BitDeck_opt2.png" or 
                              spritesheet_name.endswith("_2.png"))
            
            if back_name is None:
                fname = f"{base_name}_HC.png" if is_high_contrast else f"{base_name}.png"
            else:
                fname = f"{base_name}_{back_name}_HC.png" if is_high_contrast else f"{base_name}_{back_name}.png"

            out_img.save(out_dir / fname)

        count += 1
        pbar.set_postfix(saved=count)

    # Reduce verbosity for collab files
    if not spritesheet_name.startswith("collab_"):
        print(f"Done {spritesheet_name}: wrote {count} tiles.")


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spritesheet", default=None,
                    help="Filename like Jokers.png (under ./resources/textures/1x/). If omitted, runs all sheets in SHEET_CONFIG.")
    ap.add_argument("--all", action="store_true", help="Run all sheets listed in SHEET_CONFIG.")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--limit", type=int, default=0, help="If >0, only process first N tiles")
    ap.add_argument("--outdir", default="./dataset/raw_generated")
    ap.add_argument("--texdir", default="./resources/textures/1x")
    ap.add_argument("--shaderdir", default="./resources/shaders")
    ap.add_argument("--modifiers", action="store_true", 
                    help="Generate cards with all modifier backgrounds (base, glass, gold, etc.). Without this flag, only generates base cards.")
    ap.add_argument("--solid-background", action="store_true",
                    help="Save images with solid black background instead of transparency (for labeling software compatibility).")

    # recommended knobs (so batch runs are consistent)
    ap.add_argument("--render-scale", type=int, default=3)
    ap.add_argument("--cell-extra-px", type=int, default=32)
    ap.add_argument("--out-cell-extra-px", type=int, default=8)
    ap.add_argument("--cell-pad", type=int, default=6)

    args = ap.parse_args()

    # Determine which spritesheets to run
    if args.all or args.spritesheet is None:
        sheets = list(SHEET_CONFIG.keys())
    else:
        sheets = [args.spritesheet]
    
    # Comment out filenames to exclude
    excluded_files = {
        # "8BitDeck.png",         # Skip standard playing cards (52)
        # "8BitDeck_opt2.png",    # Skip high contrast playing cards (52)
        "Jokers.png",           # Skip jokers (160 tiles)
        "Tarots.png",           # Skip tarots (60 tiles) 
        "Enhancers.png",           # Skip tarots (60 tiles) 
        "boosters.png",         # Skip boosters (36 tiles)
        "Vouchers.png",         # Skip vouchers (36 tiles)
    }
    # Add patterns to exclude (files starting with these strings)
    excluded_patterns = {
        # "collab_",              # Skip all collab files (48 files)
    }
    
    # Filter by exact names and patterns
    original_count = len(sheets)
    sheets = [s for s in sheets if s not in excluded_files and 
             not any(s.startswith(pattern) for pattern in excluded_patterns)]
    excluded_count = original_count - len(sheets)
    if excluded_count > 0:
        print(f"Excluding {excluded_count} sheets (exact + pattern matches)")
    
    print(f"Loaded configuration for {len(SHEET_CONFIG)} sprite sheets from resource mapping.")
    if FILENAME_MAPPINGS:
        print(f"Loaded filename mappings for {len(FILENAME_MAPPINGS)} sprite sheets.")

    for s in tqdm(sheets, desc="Spritesheets", unit="sheet"):
        process_spritesheet(args, s)


if __name__ == "__main__":
    main()
