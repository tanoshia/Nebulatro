#!/usr/bin/env python3
"""
Design Manager - Handles card design options (contrast, collaborations)
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image
import json
from pathlib import Path


class DesignManager:
    """Manages card design options and popup"""
    
    def __init__(self, root, sprite_loader, bg_color, card_contrast_var, face_card_collabs_vars):
        self.root = root
        self.sprite_loader = sprite_loader
        self.bg_color = bg_color
        self.card_contrast = card_contrast_var
        self.face_card_collabs = face_card_collabs_vars
        self.on_design_change = None
    
    def set_design_change_handler(self, handler):
        """Set callback for when design changes"""
        self.on_design_change = handler
    
    def open_design_popup(self):
        """Open card design options popup"""
        popup = tk.Toplevel(self.root)
        popup.title("Card Designs")
        popup.configure(bg=self.bg_color)
        popup.geometry("400x300")
        
        # Contrast selection
        contrast_frame = tk.LabelFrame(popup, text="Card Contrast", 
                                      bg=self.bg_color, fg='white', 
                                      font=('Arial', 11, 'bold'))
        contrast_frame.pack(padx=10, pady=10, fill=tk.X)
        
        tk.Radiobutton(contrast_frame, text="Standard", variable=self.card_contrast,
                      value="Standard", bg=self.bg_color, fg='white',
                      selectcolor=self.bg_color,
                      command=self._on_contrast_change).pack(anchor=tk.W, padx=10, pady=2)
        tk.Radiobutton(contrast_frame, text="High Contrast", variable=self.card_contrast,
                      value="High Contrast", bg=self.bg_color, fg='white',
                      selectcolor=self.bg_color,
                      command=self._on_contrast_change).pack(anchor=tk.W, padx=10, pady=2)
        
        # Face card collaborations
        collab_frame = tk.LabelFrame(popup, text="Face Card Collaborations", 
                                    bg=self.bg_color, fg='white',
                                    font=('Arial', 11, 'bold'))
        collab_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        collab_options_by_suit = self._load_collab_options()
        suits_display = {'spades': '♠ Spades', 'hearts': '♥ Hearts', 
                        'clubs': '♣ Clubs', 'diamonds': '♦ Diamonds'}
        
        for suit, display_name in suits_display.items():
            suit_frame = tk.Frame(collab_frame, bg=self.bg_color)
            suit_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(suit_frame, text=display_name, bg=self.bg_color, fg='white',
                    font=('Arial', 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            
            collab_options = collab_options_by_suit.get(suit, ["Default"])
            suit_menu = ttk.Combobox(suit_frame, textvariable=self.face_card_collabs[suit],
                                    values=collab_options, state='readonly', width=25)
            suit_menu.pack(side=tk.LEFT, padx=5)
            suit_menu.bind('<<ComboboxSelected>>', lambda e, s=suit: self._on_collab_change(s))
    
    def _load_collab_options(self):
        """Load collaboration options from config/resource_mapping.json"""
        collab_options = {}
        try:
            with open('config/resource_mapping.json', 'r') as f:
                resource_mapping = json.load(f)
            
            if 'sprite_sheets' in resource_mapping and 'collab_face_cards' in resource_mapping['sprite_sheets']:
                collab_data = resource_mapping['sprite_sheets']['collab_face_cards']
                variants = collab_data.get('variants', {})
                
                for suit in ['spades', 'hearts', 'clubs', 'diamonds']:
                    options = ["Default"]
                    if suit in variants:
                        for collab in variants[suit]:
                            options.append(collab['display_name'])
                    collab_options[suit] = options
        except Exception as e:
            print(f"Warning: Could not load collab options: {e}")
            for suit in ['spades', 'hearts', 'clubs', 'diamonds']:
                collab_options[suit] = ["Default"]
        
        return collab_options
    
    def _on_contrast_change(self):
        """Handle contrast change"""
        if self.on_design_change:
            self.on_design_change()
    
    def _on_collab_change(self, suit):
        """Handle collaboration change"""
        if self.on_design_change:
            self.on_design_change()
    
    def apply_collab_face_cards(self, ordered_sprites, order_indices):
        """Replace face cards with collab sprites if selected
        
        Returns:
            tuple: (ordered_sprites, set of replaced indices, dict of collab faces without backing)
        """
        replaced_indices = set()
        collab_faces = {}  # Store faces without backing for modifier application
        
        has_collabs = any(var.get() != "Default" for var in self.face_card_collabs.values())
        if not has_collabs:
            return ordered_sprites, replaced_indices, collab_faces
        
        try:
            with open('config/resource_mapping.json', 'r') as f:
                resource_mapping = json.load(f)
            
            collab_data = resource_mapping['sprite_sheets']['collab_face_cards']
            resource_path = Path(collab_data['resource_path'])
            variants = collab_data['variants']
            
            use_high_contrast = self.card_contrast.get() == "High Contrast"
            contrast_key = 'high_contrast' if use_high_contrast else 'standard'
            
            suit_rows = {'spades': 0, 'hearts': 1, 'clubs': 2, 'diamonds': 3}
            face_cols = {'K': 1, 'Q': 2, 'J': 3}
            
            for suit, row_idx in suit_rows.items():
                collab_name = self.face_card_collabs[suit].get()
                if collab_name == "Default":
                    continue
                
                collab_file = None
                for collab in variants.get(suit, []):
                    if collab['display_name'] == collab_name:
                        collab_file = collab[contrast_key]
                        break
                
                if not collab_file:
                    continue
                
                collab_path = resource_path / collab_file
                if not collab_path.exists():
                    print(f"Warning: Collab file not found: {collab_path}")
                    continue
                
                collab_img = Image.open(collab_path).convert('RGBA')
                card_width = collab_img.width // 3
                card_height = collab_img.height
                
                collab_to_display = {'J': 0, 'Q': 1, 'K': 2}
                
                for face_name, col_idx in face_cols.items():
                    collab_idx = collab_to_display[face_name]
                    left = collab_idx * card_width
                    face_only = collab_img.crop((left, 0, left + card_width, card_height))
                    
                    # Store the face without backing for modifier application
                    display_idx = row_idx * 13 + col_idx
                    collab_faces[display_idx] = face_only.copy()
                    
                    # Composite with backing for display
                    if self.sprite_loader and self.sprite_loader.card_back:
                        back = self.sprite_loader.card_back.copy()
                        if back.size != face_only.size:
                            back = back.resize(face_only.size, Image.Resampling.LANCZOS)
                        result = back.copy()
                        result.paste(face_only, (0, 0), face_only)
                        composited_sprite = result
                    else:
                        composited_sprite = face_only
                    
                    if display_idx < len(ordered_sprites):
                        ordered_sprites[display_idx] = composited_sprite
                        replaced_indices.add(display_idx)
        
        except Exception as e:
            print(f"Warning: Could not apply collab face cards: {e}")
        
        return ordered_sprites, replaced_indices, collab_faces
