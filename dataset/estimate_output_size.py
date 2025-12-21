#!/usr/bin/env python3
"""
Estimate the total output size for generate_variants.py before running it.
"""

import os
import json
from pathlib import Path
from generate_variants import SHEET_CONFIG, BASE_COMPOSITE_CONFIG, SPRITESHEET_BACKS

def estimate_file_size(render_scale=3, cell_extra_px=32, out_cell_extra_px=8):
    """
    Estimate file size based on render parameters.
    
    Each output is a 4x4 grid of card variants.
    Base card size: 69x93 pixels
    """
    base_w, base_h = 69, 93
    
    # Calculate final cell size
    final_cell_w = (base_w + out_cell_extra_px) * render_scale
    final_cell_h = (base_h + out_cell_extra_px) * render_scale
    
    # Calculate 4x4 grid size (with padding)
    cell_pad = 6  # default from script
    grid_w = 4 * final_cell_w + 3 * cell_pad
    grid_h = 4 * final_cell_h + 3 * cell_pad
    
    # Estimate PNG file size (rough approximation)
    # PNG compression varies, but for card images with transparency:
    # - Uncompressed: width * height * 4 bytes (RGBA)
    # - PNG compression typically 20-40% of uncompressed for card images
    uncompressed_bytes = grid_w * grid_h * 4
    estimated_png_bytes = int(uncompressed_bytes * 0.3)  # 30% compression ratio
    
    return estimated_png_bytes, grid_w, grid_h

def analyze_sheets(with_modifiers=True):
    """Analyze all configured sheets and estimate output."""
    
    total_files = 0
    total_tiles = 0
    sheet_details = []
    
    mode_str = "WITH modifiers" if with_modifiers else "WITHOUT modifiers (base only)"
    print(f"Sheet Analysis ({mode_str}):")
    print("=" * 80)
    
    for sheet_name, config in SHEET_CONFIG.items():
        cols = config.get('cols')
        rows = config.get('rows')
        
        # Skip sheets with invalid dimensions
        if cols is None or rows is None:
            print(f"  {sheet_name}: SKIPPED (invalid dimensions: {cols}x{rows})")
            continue
            
        tiles = cols * rows
        total_tiles += tiles
        
        # Check if this sheet uses composite (multiple backs)
        if sheet_name in BASE_COMPOSITE_CONFIG:
            if with_modifiers:
                backs_count = len(SPRITESHEET_BACKS)
                files = tiles * backs_count
                sheet_type = f"{tiles} tiles × {backs_count} backs"
            else:
                files = tiles  # Only base cards
                sheet_type = f"{tiles} tiles (base only)"
        else:
            files = tiles
            sheet_type = f"{tiles} tiles"
            
        total_files += files
        sheet_details.append({
            'name': sheet_name,
            'tiles': tiles,
            'files': files,
            'type': sheet_type
        })
        
        print(f"  {sheet_name:25} {sheet_type:20} = {files:4} files")
    
    return total_files, total_tiles, sheet_details

def main():
    print("Balatro Dataset Generation Size Estimator")
    print("=" * 50)
    
    # Analyze both scenarios
    print("\n" + "="*60)
    print("SCENARIO 1: WITHOUT --modifiers flag (base cards only)")
    print("="*60)
    total_files_base, total_tiles_base, sheet_details_base = analyze_sheets(with_modifiers=False)
    
    print("\n" + "="*60)
    print("SCENARIO 2: WITH --modifiers flag (all enhancement variants)")
    print("="*60)
    total_files_mod, total_tiles_mod, sheet_details_mod = analyze_sheets(with_modifiers=True)
    
    # Summary comparison
    print(f"\nSUMMARY COMPARISON:")
    print(f"  Total sheets configured: {len([s for s in SHEET_CONFIG.values() if s.get('cols') and s.get('rows')])}")
    print(f"  Total base tiles: {total_tiles_base}")
    print(f"  Files WITHOUT --modifiers: {total_files_base}")
    print(f"  Files WITH --modifiers: {total_files_mod}")
    print(f"  Modifier multiplier: {total_files_mod/total_files_base:.1f}x")
    
    # File size estimates for both scenarios
    print(f"\nFILE SIZE ESTIMATES:")
    print(f"{'Scenario':<20} {'Scale':<6} {'Grid Size':<12} {'Per File':<10} {'Total Size':<12}")
    print("-" * 70)
    
    for scenario_name, total_files in [("Base only", total_files_base), ("With modifiers", total_files_mod)]:
        for scale in [3, 4, 6]:
            file_size, grid_w, grid_h = estimate_file_size(render_scale=scale)
            total_size = file_size * total_files
            
            # Format sizes
            if file_size < 1024*1024:
                file_str = f"{file_size/1024:.0f}KB"
            else:
                file_str = f"{file_size/(1024*1024):.1f}MB"
                
            if total_size < 1024*1024*1024:
                total_str = f"{total_size/(1024*1024):.1f}MB"
            else:
                total_str = f"{total_size/(1024*1024*1024):.1f}GB"
                
            print(f"{scenario_name:<20} {scale:<6} {grid_w}x{grid_h:<7} {file_str:<10} {total_str:<12}")
        print()
    
    # Check available disk space
    try:
        output_dir = Path("./dataset/raw_generated")
        if output_dir.exists():
            stat = os.statvfs(output_dir)
        else:
            stat = os.statvfs(".")
        available_bytes = stat.f_bavail * stat.f_frsize
        available_gb = available_bytes / (1024*1024*1024)
        print(f"Available disk space: {available_gb:.1f}GB")
    except:
        print(f"Could not determine available disk space")
    
    print(f"\nUSAGE EXAMPLES:")
    print(f"  # Base cards only (smaller dataset)")
    print(f"  python dataset/generate_variants.py --all --render-scale 4")
    print(f"  ")
    print(f"  # All modifier variants (larger dataset)")
    print(f"  python dataset/generate_variants.py --all --modifiers --render-scale 3")

if __name__ == "__main__":
    main()