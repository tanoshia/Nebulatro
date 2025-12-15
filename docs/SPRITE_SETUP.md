# Quick Sprite Sheet Setup Guide

## Super Simple Setup

Just name your sprite sheet files with the grid size at the start!

### Filename Format
```
COLSxROWS Description.png
```

### Examples
- `13x4 Playing Cards.png` - 13 columns × 4 rows (52 cards)
- `5x3 Jokers.png` - 5 columns × 3 rows (15 cards)
- `11x2 Tarot Cards.png` - 11 columns × 2 rows (22 cards)
- `13x4 Playing Cards (High Contrast).png` - Any description works!

### Setup Steps

1. **Name your sprite sheet** with the grid dimensions:
   ```
   13x4 Playing Cards.png
   ```

2. **Place it in the assets folder**:
   ```
   assets/13x4 Playing Cards.png
   ```

3. **Run the tracker**:
   ```bash
   source venv/bin/activate
   python3 nebulatro.py
   ```

That's it! No configuration files needed.

## Testing

To extract individual cards and verify:
```bash
python3 sprite_loader.py
```

This will save all cards to the `cards/` folder so you can check they're split correctly.

## Multiple Sprite Sheets

Just add more files to the assets folder:
```
assets/
  13x4 Playing Cards.png
  5x3 Jokers.png
  11x2 Tarot Cards.png
```

The tracker will automatically use the first sheet it finds.

## Using Game Resources (Recommended)

The tracker now uses Balatro's game resources directly via `resource_mapping.json`:

1. **Copy resources folder** from your Balatro installation:
   ```bash
   cp -r /path/to/Balatro/resources ./
   ```


The system will:
- Load sprite sheets from `resources/textures/1x/`
- Use grid dimensions from `resource_mapping.json`
- Fall back to `assets/` folder if resources unavailable

## Manual Sprite Sheet Setup (Fallback)

If you don't have access to game resources:

1. **Name your sprite sheet**:
   ```
   13x4 Playing Cards (High Contrast).png
   ```

2. **Move to assets**:
   ```bash
   mv "13x4 Playing Cards (High Contrast).png" assets/
   ```

3. **Run the tracker**:
   ```bash
   source venv/bin/activate
   python3 nebulatro.py
   ```

## Tips

- The system automatically calculates card dimensions by dividing the image size by the grid
- Cards are extracted left-to-right, top-to-bottom
- Works with any grid size - just update the filename
- No spacing between cards is assumed (edge-to-edge grid)
- If your sprite sheet has spacing/padding, you'll need to crop it first


## Resource Mapping

The `resource_mapping.json` file defines:
- Which game files to use
- Grid dimensions for each sprite sheet
- Card names and positions
- Fallback files in `assets/` folder

Edit this file to add new sprite sheets or update configurations.

## Transparency and Compositing

The system handles:
- **Card faces**: Loaded without backing, composited onto card back texture
- **Card back**: Loaded from Enhancers.png (index 1)
- **Modifiers**: Applied with various render modes:
  - `overlay`: Composited on top of card
  - `background`: Replaces card backing (Bonus, Mult, Wild)
- **Blend modes**: 
  - `normal`: Standard alpha compositing
  - `multiply`: RGB multiplication
  - `color`: Takes luminance from card, color from modifier (Polychrome)
- **Transparency**: All PNG transparency preserved, rounded corners maintained
