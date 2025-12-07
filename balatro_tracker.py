#!/usr/bin/env python3
"""
Balatro Card Order Tracker
A simple GUI app to track card order by clicking on card images.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
import json
from pathlib import Path
from datetime import datetime
from sprite_loader import SpriteLoader


class BalatroTracker:
    def __init__(self, root, use_sprite_loader=True):
        self.root = root
        self.root.title("Balatro Card Tracker")
        
        # UI Configuration
        self.card_spacing = 2  # Spacing between cards (pixels)
        self.card_display_width = 71  # Match actual card width
        self.card_display_height = 95  # Match actual card height
        
        # Set minimum window size
        # Minimum width: enough for cards with 70% overlap
        # 13 cards with 70% overlap = 13 * 71 - 12 * (71 * 0.7) = 923 - 596 = 327px
        min_width = int(13 * self.card_display_width - 12 * (self.card_display_width * 0.55)) + 15
        # Minimum height: all UI components
        min_height = 710
        self.root.minsize(min_width, min_height)
        
        # Dark theme colors
        self.bg_color = '#2b2b2b'
        self.canvas_bg = '#1e1e1e'
        
        # Configure root background
        self.root.configure(bg=self.bg_color)
        
        # Store card order
        self.card_order = []
        
        # Selected modifiers (one per category)
        self.selected_enhancement = None
        self.selected_edition = None
        self.selected_seal = None
        
        # Card images folder (fallback)
        self.cards_folder = Path("cards")
        
        # Image references (prevent garbage collection)
        self.card_images = {}
        self.small_card_images = {}
        
        # Sprite loader
        self.use_sprite_loader = use_sprite_loader
        self.sprite_loader = None
        
        # Load card order config
        self.card_order_config = self._load_card_order_config()
        
        self.setup_ui()
        self.load_modifiers()
        self.load_cards()
        
        # Bind window resize event
        self.root.bind('<Configure>', self._on_window_resize)
        
        # Force recalculation of modifier positions after window is shown
        self.root.after(100, self._recalculate_modifier_positions)
    
    def setup_ui(self):
        """Create the UI layout"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title and filter row
        title_frame = tk.Frame(main_frame, bg=self.bg_color)
        title_frame.grid(row=0, column=0, pady=10)
        
        title = tk.Label(title_frame, text="Click a card to add to sequence", 
                        font=('Arial', 14, 'bold'),
                        bg=self.bg_color, fg='white')
        title.pack(side=tk.LEFT, padx=(0, 20))
        
        # Filter dropdown
        filter_label = tk.Label(title_frame, text="Filters:", 
                               font=('Arial', 11),
                               bg=self.bg_color, fg='white')
        filter_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Initialize filter variables
        self.modifier_filter = tk.StringVar(value="All Modifiers")
        self.card_contrast = tk.StringVar(value="Standard")
        self.face_card_collabs = {
            'spades': tk.StringVar(value="Default"),
            'hearts': tk.StringVar(value="Default"),
            'clubs': tk.StringVar(value="Default"),
            'diamonds': tk.StringVar(value="Default")
        }
        
        # Modifier filter dropdown
        modifier_options = ["All Modifiers", "Scoring Only"]
        modifier_menu = ttk.Combobox(title_frame, textvariable=self.modifier_filter,
                                    values=modifier_options, state='readonly', width=15)
        modifier_menu.pack(side=tk.LEFT, padx=5)
        modifier_menu.bind('<<ComboboxSelected>>', self._on_modifier_filter_change)
        
        # Card designs button (opens popup menu)
        card_design_btn = ttk.Button(title_frame, text="Card Designs...", 
                                     command=self._open_card_design_menu)
        card_design_btn.pack(side=tk.LEFT, padx=5)
        
        # Modifiers canvas (Enhancements and Seals)
        self.modifiers_canvas = tk.Canvas(main_frame, bg=self.bg_color,
                                         highlightthickness=0)
        self.modifiers_canvas.grid(row=1, column=0, pady=(0, 5))
        
        # Card grid canvas for proper transparency
        self.card_grid_canvas = tk.Canvas(main_frame, bg=self.bg_color, 
                                         highlightthickness=0)
        self.card_grid_canvas.grid(row=2, column=0, pady=10)
        
        # Store card button references
        self.card_buttons = []
        self.modifier_images = {}
        
        # Separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Order list label
        order_label = tk.Label(main_frame, text="Card Order:", 
                              font=('Arial', 12, 'bold'),
                              bg=self.bg_color, fg='white')
        order_label.grid(row=4, column=0, sticky=tk.W)
        
        # Order list frame with scrollbar
        order_container = tk.Frame(main_frame, bg=self.bg_color)
        order_container.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.order_canvas = tk.Canvas(order_container, height=90, 
                                     bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(order_container, orient='horizontal', 
                                 command=self.order_canvas.xview)
        self.order_frame = tk.Frame(self.order_canvas, bg=self.bg_color)
        
        self.order_canvas.configure(xscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.order_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.order_canvas.create_window((0, 0), window=self.order_frame, 
                                       anchor='nw')
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, pady=10)
        
        clear_btn = ttk.Button(button_frame, text="Clear Order", 
                              command=self.clear_order)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        undo_btn = ttk.Button(button_frame, text="Undo Last", 
                             command=self.undo_last)
        undo_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(button_frame, text="Save", 
                             command=self.save_order)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
    
    def load_modifiers(self):
        """Load card modifiers (Enhancements and Seals) from sprite sheet"""
        if not self.use_sprite_loader:
            return
        
        try:
            if not self.sprite_loader:
                self.sprite_loader = SpriteLoader()
            
            # Find the Card Backs sheet (check resource mapping names first)
            backs_sheet_name = None
            for name in self.sprite_loader.get_sheet_names():
                # Check for resource mapping names or filename-based names
                if name == 'enhancers' or ('back' in name.lower() and ('enhancer' in name.lower() or 'seal' in name.lower())):
                    backs_sheet_name = name
                    break
            
            if not backs_sheet_name:
                print("Warning: Card Backs sheet not found for modifiers")
                return
            
            # Get current filter
            filter_mode = self.modifier_filter.get() if hasattr(self, 'modifier_filter') else "All Modifiers"
            
            # Define non-scoring seal indices (Gold, Purple, Blue)
            non_scoring_seals = [2, 32, 34]
            
            # Load modifier configuration
            modifiers = []
            if self.card_order_config and 'modifiers' in self.card_order_config:
                mod_config = self.card_order_config['modifiers']
                
                # Load enhancements
                if 'enhancements' in mod_config:
                    indices = mod_config['enhancements']['indices']
                    render_modes = mod_config['enhancements'].get('render_modes', ['overlay'] * len(indices))
                    for i, idx in enumerate(indices):
                        sprite = self.sprite_loader.get_sprite(backs_sheet_name, idx, composite_back=False)
                        render_mode = render_modes[i] if i < len(render_modes) else 'overlay'
                        modifiers.append((idx, sprite, 'enhancement', render_mode))
                
                # Load seals (with filtering)
                if 'seals' in mod_config:
                    indices = mod_config['seals']['indices']
                    render_modes = mod_config['seals'].get('render_modes', ['overlay'] * len(indices))
                    for i, idx in enumerate(indices):
                        # Skip non-scoring seals if "Scoring Only" filter is active
                        if filter_mode == "Scoring Only" and idx in non_scoring_seals:
                            continue
                        sprite = self.sprite_loader.get_sprite(backs_sheet_name, idx, composite_back=False)
                        render_mode = render_modes[i] if i < len(render_modes) else 'overlay'
                        modifiers.append((idx, sprite, 'seal', render_mode))
                
                # Find and load Editions sheet
                if 'editions' in mod_config:
                    editions_sheet_name = None
                    for name in self.sprite_loader.get_sheet_names():
                        if 'edition' in name.lower():
                            editions_sheet_name = name
                            break
                    
                    if editions_sheet_name:
                        indices = mod_config['editions']['indices']
                        render_modes = mod_config['editions'].get('render_modes', ['overlay'] * len(indices))
                        opacities = mod_config['editions'].get('opacity', [1.0] * len(indices))
                        blend_modes = mod_config['editions'].get('blend_modes', ['normal'] * len(indices))
                        for i, idx in enumerate(indices):
                            sprite = self.sprite_loader.get_sprite(editions_sheet_name, idx, composite_back=False)
                            render_mode = render_modes[i] if i < len(render_modes) else 'overlay'
                            opacity = opacities[i] if i < len(opacities) else 1.0
                            blend_mode = blend_modes[i] if i < len(blend_modes) else 'normal'
                            # Last edition (index 4) is debuff, separate category
                            mod_type = 'debuff' if idx == 4 else 'edition'
                            modifiers.append((idx, sprite, mod_type, render_mode, opacity, blend_mode))
                    else:
                        print("Warning: Editions sheet not found")
            else:
                print("Warning: No modifier configuration found")
            
            # Store modifiers for later positioning
            self.modifier_data = modifiers
            
            # Calculate canvas size to match playing cards width
            # Playing cards: 13 columns
            playing_cards_width = 13 * (self.card_display_width + self.card_spacing) - self.card_spacing
            canvas_height = self.card_display_height
            self.modifiers_canvas.config(width=playing_cards_width, height=canvas_height)
            
            # Display modifiers
            for display_idx, modifier_data in enumerate(modifiers):
                sprite_idx = modifier_data[0]
                sprite = modifier_data[1]
                mod_type = modifier_data[2]
                render_mode = modifier_data[3] if len(modifier_data) > 3 else 'overlay'
                opacity = modifier_data[4] if len(modifier_data) > 4 else 1.0
                blend_mode = modifier_data[5] if len(modifier_data) > 5 else 'normal'
                self._create_modifier_button(sprite_idx, sprite, display_idx, mod_type, render_mode, opacity, blend_mode)
            
            # Initial positioning
            self._recalculate_modifier_positions()
            
        except Exception as e:
            print(f"Warning: Could not load modifiers: {e}")
    
    def _create_modifier_button(self, sprite_idx, sprite, display_idx, mod_type, render_mode='overlay', opacity=1.0, blend_mode='normal', spacing_override=None):
        """Create a clickable modifier button"""
        try:
            # For seals, crop to just the circular seal part
            img = sprite.copy()
            if 'seal' in mod_type:
                # Seal dimensions: starts at x=13, width=27, ends at x=40 (out of 69 total width)
                # Calculate crop box maintaining aspect ratio
                original_width = img.width
                original_height = img.height
                
                # Calculate crop coordinates based on proportions
                left = int(original_width * (13 / 69))
                right = int(original_width * (40 / 69))
                top = 0
                bottom = original_height
                
                # Crop to just the seal circle
                img = img.crop((left, top, right, bottom))
            
            # Resize image
            img.thumbnail((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Store reference
            modifier_key = f"modifier_{mod_type}_{sprite_idx}"
            self.modifier_images[modifier_key] = photo
            
            # Store sprite and metadata for overlaying
            if not hasattr(self, 'modifier_sprites'):
                self.modifier_sprites = {}
            if not hasattr(self, 'modifier_metadata'):
                self.modifier_metadata = {}
            self.modifier_sprites[modifier_key] = sprite
            self.modifier_metadata[modifier_key] = {
                'render_mode': render_mode,
                'opacity': opacity,
                'blend_mode': blend_mode
            }
            
            # Calculate display width (seals are cropped to ~39% of card width: 27/69)
            display_width = img.width if 'seal' in mod_type else self.card_display_width
            
            # Calculate initial position
            x = display_idx * (self.card_display_width + self.card_spacing)
            y = 0
            
            # Create image on canvas
            img_id = self.modifiers_canvas.create_image(x, y, image=photo, anchor=tk.NW)
            
            # Store img_id, position info, mod_type, display width, and spacing override
            if not hasattr(self, 'modifier_img_ids'):
                self.modifier_img_ids = {}
            if not hasattr(self, 'modifier_positions'):
                self.modifier_positions = {}
            if not hasattr(self, 'modifier_spacing_overrides'):
                self.modifier_spacing_overrides = {}
            if not hasattr(self, 'modifier_types'):
                self.modifier_types = {}
            if not hasattr(self, 'modifier_display_widths'):
                self.modifier_display_widths = {}
            self.modifier_img_ids[modifier_key] = img_id
            self.modifier_positions[modifier_key] = display_idx
            self.modifier_spacing_overrides[modifier_key] = spacing_override
            self.modifier_types[modifier_key] = mod_type
            self.modifier_display_widths[modifier_key] = display_width
            
            # Bind click event to select modifier
            self.modifiers_canvas.tag_bind(img_id, '<Button-1>',
                                          lambda e, key=modifier_key, idx=sprite_idx, mtype=mod_type:
                                          self.select_modifier(key, idx, mtype))
            
            # Add hover effect
            self.modifiers_canvas.tag_bind(img_id, '<Enter>',
                                          lambda e: self.modifiers_canvas.config(cursor='hand2'))
            self.modifiers_canvas.tag_bind(img_id, '<Leave>',
                                          lambda e: self.modifiers_canvas.config(cursor=''))
            
        except Exception as e:
            print(f"Error creating modifier button: {e}")
    
    def select_modifier(self, modifier_key, sprite_idx, mod_type):
        """Select a modifier to apply to cards"""
        # Determine category
        category = None
        if 'enhancement' in mod_type:
            category = 'enhancement'
            old_selection = self.selected_enhancement
            self.selected_enhancement = (modifier_key, sprite_idx) if old_selection != (modifier_key, sprite_idx) else None
        elif 'debuff' in mod_type:
            category = 'debuff'
            old_selection = getattr(self, 'selected_debuff', None)
            self.selected_debuff = (modifier_key, sprite_idx) if old_selection != (modifier_key, sprite_idx) else None
        elif 'edition' in mod_type:
            category = 'edition'
            old_selection = self.selected_edition
            self.selected_edition = (modifier_key, sprite_idx) if old_selection != (modifier_key, sprite_idx) else None
        elif 'seal' in mod_type:
            category = 'seal'
            old_selection = self.selected_seal
            self.selected_seal = (modifier_key, sprite_idx) if old_selection != (modifier_key, sprite_idx) else None
        
        # Update visual selection (highlight selected modifier)
        self._update_modifier_highlights()
        
        # Refresh card display with new overlays
        self._refresh_card_overlays()
    
    def _update_modifier_highlights(self):
        """Update visual highlights on selected modifiers"""
        # No visual highlighting needed - selection is shown by the cards updating
        pass
    
    def _refresh_card_overlays(self):
        """Refresh all playing cards with current modifier overlays"""
        if not hasattr(self, 'base_card_sprites') or not hasattr(self, 'card_img_ids'):
            return
        
        # Update each card's display
        for card_name, base_sprite in self.base_card_sprites.items():
            if card_name in self.card_img_ids:
                # Apply modifiers
                display_sprite = self._apply_modifiers_to_card(base_sprite, card_name)
                
                # Resize and convert to photo
                img = display_sprite.copy()
                img.thumbnail((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # Update canvas image
                img_id = self.card_img_ids[card_name]
                self.card_grid_canvas.itemconfig(img_id, image=photo)
                
                # Store reference to prevent garbage collection
                self.card_images[card_name] = photo
    
    def load_cards(self):
        """Load card images from sprite sheets or cards folder"""
        # Try sprite loader first
        if self.use_sprite_loader:
            try:
                if not self.sprite_loader:
                    self.sprite_loader = SpriteLoader()
                self.load_cards_from_sprites()
                return
            except (FileNotFoundError, Exception) as e:
                print(f"Sprite loader failed: {e}")
                print("Falling back to cards folder...")
        
        # Fallback to cards folder
        if not self.cards_folder.exists():
            self.cards_folder.mkdir()
            msg = ttk.Label(self.card_grid_frame, 
                          text=f"Please add card images to the '{self.cards_folder}' folder\n"
                               f"or configure sprite_config.json for sprite sheets",
                          font=('Arial', 11))
            msg.grid(row=0, column=0, padx=20, pady=20)
            return
        
        # Get all image files
        image_extensions = {'.png', '.jpg', '.jpeg'}
        card_files = [f for f in self.cards_folder.iterdir() 
                     if f.suffix.lower() in image_extensions]
        
        if not card_files:
            msg = ttk.Label(self.card_grid_frame, 
                          text=f"No card images found in '{self.cards_folder}' folder",
                          font=('Arial', 11))
            msg.grid(row=0, column=0, padx=20, pady=20)
            return
        
        # Sort files for consistent ordering
        card_files.sort()
        
        # Display cards in a grid
        cols = 13  # 13 columns for playing cards
        for idx, card_file in enumerate(card_files):
            row = idx // cols
            col = idx % cols
            self.create_card_button_from_file(card_file, row, col)
    
    def load_cards_from_sprites(self):
        """Load cards from sprite sheets"""
        sheet_names = self.sprite_loader.get_sheet_names()
        if not sheet_names:
            raise ValueError("No sprite sheets found in assets/ directory")
        
        # Check contrast filter setting
        use_high_contrast = hasattr(self, 'card_contrast') and self.card_contrast.get() == "High Contrast"
        
        # Select appropriate sheet based on contrast setting
        sheet_name = None
        if use_high_contrast:
            # Look for playing_cards_high_contrast first (from resource mapping)
            if 'playing_cards_high_contrast' in sheet_names:
                sheet_name = 'playing_cards_high_contrast'
            else:
                # Fallback: look for any high contrast sheet
                for name in sheet_names:
                    if 'high' in name.lower() and 'contrast' in name.lower() and 'playing' in name.lower():
                        sheet_name = name
                        break
        else:
            # Look for playing_cards (standard) first (from resource mapping)
            if 'playing_cards' in sheet_names:
                sheet_name = 'playing_cards'
            else:
                # Fallback: look for standard sheet (not high contrast)
                for name in sheet_names:
                    name_lower = name.lower()
                    if ('playing' in name_lower or '8bitdeck' in name_lower) and \
                       'high' not in name_lower and \
                       'contrast' not in name_lower and \
                       'back' not in name_lower and \
                       'booster' not in name_lower and \
                       'joker' not in name_lower and \
                       'tarot' not in name_lower:
                        sheet_name = name
                        break
        
        # Fallback: find any playing cards sheet
        if not sheet_name:
            for name in sheet_names:
                name_lower = name.lower()
                if ('playing' in name_lower or 'card' in name_lower) and \
                   'back' not in name_lower and \
                   'booster' not in name_lower and \
                   'joker' not in name_lower and \
                   'tarot' not in name_lower and \
                   'spectral' not in name_lower and \
                   'planet' not in name_lower:
                    sheet_name = name
                    break
        
        # Last resort: use first sheet
        if not sheet_name:
            sheet_name = sheet_names[0]
        
        print(f"Loading cards from: {sheet_name} (High Contrast: {use_high_contrast})")
        print(f"Available sheets: {sheet_names}")
        
        sheet_info = self.sprite_loader.get_sheet_info(sheet_name)
        
        # Load sprites with card back composite for playing cards
        use_composite = 'playing' in sheet_name.lower()
        sprites = self.sprite_loader.get_all_sprites(sheet_name, composite_back=use_composite)
        
        # Check if we should use custom order for playing cards
        use_custom_order = ('playing' in sheet_name.lower() and 
                           self.card_order_config and 
                           'playing_cards_order' in self.card_order_config)
        
        if use_custom_order:
            # Use custom order from config
            order_indices = self.card_order_config['playing_cards_order']['sprite_sheet_mapping']['order']
            ordered_sprites = [sprites[i] for i in order_indices]
            cols = 13  # Display in 13 columns (one per rank)
            rows = 4   # 4 rows (one per suit)
        else:
            # Use original sprite sheet layout
            ordered_sprites = sprites
            cols = sheet_info['cols']
            rows = (len(sprites) + cols - 1) // cols
        
        # Replace face cards with collab sprites if selected
        if use_custom_order:
            ordered_sprites = self._apply_collab_face_cards(ordered_sprites, order_indices)
        
        # Set canvas size
        canvas_width = cols * (self.card_display_width + self.card_spacing) - self.card_spacing
        canvas_height = rows * (self.card_display_height + self.card_spacing) - self.card_spacing
        self.card_grid_canvas.config(width=canvas_width, height=canvas_height)
        
        for idx, sprite in enumerate(ordered_sprites):
            row = idx // cols
            col = idx % cols
            # Use original sprite index for card name to maintain reference
            if use_custom_order:
                original_idx = order_indices[idx]
                card_name = f"{sheet_name}_{original_idx}"
            else:
                card_name = f"{sheet_name}_{idx}"
            self.create_card_button_from_sprite(card_name, sprite, row, col)
        
        # Auto-size window to fit cards
        self._auto_size_window(canvas_width, canvas_height)
    
    def create_card_button_from_sprite(self, card_name, sprite, row, col):
        """Create a clickable card button from a sprite"""
        try:
            # Store base sprite (already has card back composited)
            if not hasattr(self, 'base_card_sprites'):
                self.base_card_sprites = {}
            self.base_card_sprites[card_name] = sprite
            
            # Also get the card face without backing for background modifiers
            # For collab face cards, extract from the base_sprite (which already has collab applied)
            # For regular cards, get from sprite loader
            if not hasattr(self, 'card_faces'):
                self.card_faces = {}
            
            # Check if this is a collab-replaced face card
            # The base_sprite already has the collab face composited with backing
            # We need to extract just the face part
            if hasattr(self, 'sprite_loader') and self.sprite_loader and self.sprite_loader.card_back:
                try:
                    # For collab cards, the sprite parameter is already the composited version
                    # We need to extract the face by removing the backing
                    # For now, just use the sprite without backing from the original sheet
                    if '_' in card_name and card_name.split('_')[-1].isdigit():
                        sprite_idx = int(card_name.split('_')[-1])
                        sheet_name = '_'.join(card_name.split('_')[:-1])
                        card_face = self.sprite_loader.get_sprite(sheet_name, sprite_idx, composite_back=False)
                        
                        # Check if this card should use a collab face
                        # This is a bit hacky but we need to re-apply collab logic here
                        card_face = self._get_collab_face_if_applicable(card_name, card_face, row, col)
                        
                        self.card_faces[card_name] = card_face
                except:
                    pass
            
            # Apply current modifiers and create display image
            display_sprite = self._apply_modifiers_to_card(sprite, card_name)
            
            # Resize image for grid
            img = display_sprite.copy()
            img.thumbnail((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Store references
            self.card_images[card_name] = photo
            self.small_card_images[card_name] = None  # Will be created on demand
            
            # Calculate initial position on canvas
            x = col * (self.card_display_width + self.card_spacing)
            y = row * (self.card_display_height + self.card_spacing)
            
            # Create image on canvas
            img_id = self.card_grid_canvas.create_image(x, y, image=photo, anchor=tk.NW)
            
            # Store img_id and position info for updating
            if not hasattr(self, 'card_img_ids'):
                self.card_img_ids = {}
            if not hasattr(self, 'card_positions'):
                self.card_positions = {}
            self.card_img_ids[card_name] = img_id
            self.card_positions[card_name] = {'row': row, 'col': col}
            
            # Bind click event
            self.card_grid_canvas.tag_bind(img_id, '<Button-1>', 
                                          lambda e, name=card_name: 
                                          self.add_card_with_modifiers(name))
            
            # Add hover effect
            self.card_grid_canvas.tag_bind(img_id, '<Enter>', 
                                          lambda e: self.card_grid_canvas.config(cursor='hand2'))
            self.card_grid_canvas.tag_bind(img_id, '<Leave>', 
                                          lambda e: self.card_grid_canvas.config(cursor=''))
            
        except Exception as e:
            print(f"Error creating button for {card_name}: {e}")
    
    def _apply_modifiers_to_card(self, base_sprite, card_name=None):
        """Apply selected modifiers to a card sprite"""
        # Check if we need to use card face for background modifiers
        use_card_face = False
        if self.selected_enhancement and hasattr(self, 'modifier_metadata'):
            modifier_key, _ = self.selected_enhancement
            metadata = self.modifier_metadata.get(modifier_key, {})
            if metadata.get('render_mode') == 'background':
                use_card_face = True
        
        # Start with card face if using background modifier, otherwise use full card
        if use_card_face and card_name and hasattr(self, 'card_faces') and card_name in self.card_faces:
            # Start with just the card face (no backing)
            result = self.card_faces[card_name].copy().convert('RGBA')
            
            # Apply background enhancement first
            if self.selected_enhancement and hasattr(self, 'modifier_sprites'):
                modifier_key, _ = self.selected_enhancement
                if modifier_key in self.modifier_sprites:
                    enhancement = self.modifier_sprites[modifier_key].copy().convert('RGBA')
                    if enhancement.size != result.size:
                        enhancement = enhancement.resize(result.size, Image.Resampling.LANCZOS)
                    # Composite card face on top of enhancement background
                    result = Image.alpha_composite(enhancement, result)
        else:
            # Use full card with backing
            result = base_sprite.copy().convert('RGBA')
            
            # Apply enhancement as overlay if not background mode
            if self.selected_enhancement and hasattr(self, 'modifier_sprites'):
                modifier_key, _ = self.selected_enhancement
                if modifier_key in self.modifier_sprites:
                    metadata = self.modifier_metadata.get(modifier_key, {})
                    if metadata.get('render_mode') != 'background':
                        enhancement = self.modifier_sprites[modifier_key].copy().convert('RGBA')
                        if enhancement.size != result.size:
                            enhancement = enhancement.resize(result.size, Image.Resampling.LANCZOS)
                        result = Image.alpha_composite(result, enhancement)
        
        # Apply edition (always overlay, may have opacity and blend mode)
        if self.selected_edition and hasattr(self, 'modifier_sprites'):
            modifier_key, _ = self.selected_edition
            if modifier_key in self.modifier_sprites:
                edition = self.modifier_sprites[modifier_key].copy().convert('RGBA')
                if edition.size != result.size:
                    edition = edition.resize(result.size, Image.Resampling.LANCZOS)
                
                metadata = self.modifier_metadata.get(modifier_key, {})
                opacity = metadata.get('opacity', 1.0)
                blend_mode = metadata.get('blend_mode', 'normal')
                
                # Apply blend mode
                if blend_mode == 'multiply':
                    # Multiply blend: multiply RGB values
                    result_rgb = result.convert('RGB')
                    edition_rgb = edition.convert('RGB')
                    
                    # Multiply each channel
                    from PIL import ImageChops
                    blended = ImageChops.multiply(result_rgb, edition_rgb)
                    
                    # Convert back to RGBA and preserve original alpha
                    blended = blended.convert('RGBA')
                    blended.putalpha(result.split()[3])
                    result = blended
                elif blend_mode == 'color':
                    # Color blend: take luminance from base, color from edition
                    base_rgb = result.convert('RGB')
                    edition_rgb = edition.convert('RGB')
                    
                    # Convert to YCbCr color space
                    base_ycbcr = base_rgb.convert('YCbCr')
                    edition_ycbcr = edition_rgb.convert('YCbCr')
                    
                    # Split channels
                    bY, bCb, bCr = base_ycbcr.split()
                    _, eCb, eCr = edition_ycbcr.split()
                    
                    # Compose: luminance from base, color from edition
                    colored_ycbcr = Image.merge('YCbCr', (bY, eCb, eCr))
                    colored_rgb = colored_ycbcr.convert('RGB')
                    
                    # Apply opacity
                    if opacity < 1.0:
                        colored_rgb = Image.blend(base_rgb, colored_rgb, opacity)
                    
                    # Restore alpha channel
                    result = Image.merge('RGBA', (*colored_rgb.split(), result.split()[3]))
                else:
                    # Normal blend with opacity
                    if opacity < 1.0:
                        # Adjust alpha channel
                        alpha = edition.split()[3]
                        alpha = alpha.point(lambda p: int(p * opacity))
                        edition.putalpha(alpha)
                    
                    result = Image.alpha_composite(result, edition)
        
        # Apply seal (always overlay)
        if self.selected_seal and hasattr(self, 'modifier_sprites'):
            modifier_key, _ = self.selected_seal
            if modifier_key in self.modifier_sprites:
                seal = self.modifier_sprites[modifier_key].copy().convert('RGBA')
                if seal.size != result.size:
                    seal = seal.resize(result.size, Image.Resampling.LANCZOS)
                result = Image.alpha_composite(result, seal)
        
        # Apply debuff (always overlay)
        if hasattr(self, 'selected_debuff') and self.selected_debuff and hasattr(self, 'modifier_sprites'):
            modifier_key, _ = self.selected_debuff
            if modifier_key in self.modifier_sprites:
                debuff = self.modifier_sprites[modifier_key].copy().convert('RGBA')
                if debuff.size != result.size:
                    debuff = debuff.resize(result.size, Image.Resampling.LANCZOS)
                result = Image.alpha_composite(result, debuff)
        
        return result
    
    def add_card_with_modifiers(self, card_name):
        """Add a card to order with current modifiers applied"""
        # Get base sprite
        if not hasattr(self, 'base_card_sprites') or card_name not in self.base_card_sprites:
            return
        
        base_sprite = self.base_card_sprites[card_name]
        
        # Apply modifiers
        final_sprite = self._apply_modifiers_to_card(base_sprite, card_name)
        
        # Build card name with modifiers
        modifiers_applied = []
        if self.selected_enhancement:
            _, idx = self.selected_enhancement
            modifiers_applied.append(('enhancement', idx))
        if self.selected_edition:
            _, idx = self.selected_edition
            modifiers_applied.append(('edition', idx))
        if self.selected_seal:
            _, idx = self.selected_seal
            modifiers_applied.append(('seal', idx))
        if hasattr(self, 'selected_debuff') and self.selected_debuff:
            _, idx = self.selected_debuff
            modifiers_applied.append(('debuff', idx))
        
        # Add to order
        self.card_order.append((card_name, final_sprite, modifiers_applied))
        self.update_order_display()
    
    def create_card_button_from_file(self, card_path, row, col):
        """Create a clickable card button from a file"""
        try:
            # Load and resize image for grid
            img = Image.open(card_path)
            img.thumbnail((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Store reference
            card_name = card_path.stem
            self.card_images[card_name] = photo
            
            # Calculate position on canvas
            x = col * (self.card_display_width + self.card_spacing)
            y = row * (self.card_display_height + self.card_spacing)
            
            # Create image on canvas
            img_id = self.card_grid_canvas.create_image(x, y, image=photo, anchor=tk.NW)
            
            # Bind click event
            self.card_grid_canvas.tag_bind(img_id, '<Button-1>', 
                                          lambda e, name=card_name, path=card_path: 
                                          self.add_card_to_order(name, path))
            
            # Add hover effect
            self.card_grid_canvas.tag_bind(img_id, '<Enter>', 
                                          lambda e: self.card_grid_canvas.config(cursor='hand2'))
            self.card_grid_canvas.tag_bind(img_id, '<Leave>', 
                                          lambda e: self.card_grid_canvas.config(cursor=''))
            
        except Exception as e:
            print(f"Error loading {card_path}: {e}")
    
    def add_card_to_order(self, card_name, card_source):
        """Add a card to the order list"""
        self.card_order.append((card_name, card_source))
        self.update_order_display()
    
    def update_order_display(self):
        """Update the order list display"""
        # Clear existing widgets
        for widget in self.order_frame.winfo_children():
            widget.destroy()
        
        # Display each card in order
        for idx, item in enumerate(self.card_order):
            # Handle both old format (card_name, card_source) and new format (card_name, card_source, modifiers)
            if len(item) == 2:
                card_name, card_source = item
                modifiers_applied = []
            else:
                card_name, card_source, modifiers_applied = item
            # Create unique cache key that includes modifiers
            modifier_key = '+'.join([f"{mt}_{mi}" for mt, mi in modifiers_applied])
            cache_key = f"{card_name}_{modifier_key}_{idx}"
            
            # Always create new image (don't cache since modifiers change)
            # Check if card_source is a Path or Image
            if isinstance(card_source, Path):
                img = Image.open(card_source)
            else:
                img = card_source.copy()
            
            img.thumbnail((50, 70), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Store with unique key
            self.small_card_images[cache_key] = photo
            
            # Create frame for card + number
            card_frame = tk.Frame(self.order_frame, bg=self.bg_color)
            card_frame.pack(side=tk.LEFT, padx=3)
            
            # Number label (smaller font, no hashtag)
            num_label = tk.Label(card_frame, text=f"{idx+1}", 
                                font=('Arial', 7, 'bold'),
                                bg=self.bg_color, fg='white')
            num_label.pack()
            
            # Card image
            card_label = tk.Label(card_frame, 
                                 image=photo,
                                 bg=self.bg_color, borderwidth=0,
                                 highlightthickness=0)
            card_label.pack()
        
        # Update scroll region
        self.order_frame.update_idletasks()
        self.order_canvas.configure(scrollregion=self.order_canvas.bbox('all'))
        
        # Scroll to the far right to show most recent additions
        self.order_canvas.xview_moveto(1.0)
    
    def clear_order(self):
        """Clear the entire order list"""
        self.card_order.clear()
        self.update_order_display()
    
    def undo_last(self):
        """Remove the last card from the order"""
        if self.card_order:
            self.card_order.pop()
            self.update_order_display()
    
    def save_order(self):
        """Save the card order to a CSV file"""
        if not self.card_order:
            self._show_message("No cards to save", "Please add some cards before saving.")
            return
        
        # Convert card order to readable card names
        card_names = []
        for item in self.card_order:
            # Handle both old and new format
            if len(item) == 2:
                card_name, card_source = item
                modifiers_applied = []
            else:
                card_name, card_source, modifiers_applied = item
            # Extract readable name from card_name
            readable_parts = []
            
            # Get base card name
            if '_' in card_name and card_name.split('_')[-1].isdigit():
                sprite_idx = int(card_name.split('_')[-1])
                base_name = self._get_card_name_from_index(sprite_idx)
                readable_parts.append(base_name)
            else:
                readable_parts.append(card_name)
            
            # Add modifiers
            for mod_type, mod_idx in modifiers_applied:
                mod_name = self._get_modifier_name_from_index(mod_type, mod_idx)
                readable_parts.append(mod_name)
            
            # Combine: "AS+Mult+Foil+Red_Seal"
            card_names.append('+'.join(readable_parts))
        
        # Create CSV string
        csv_content = ','.join(card_names)
        
        # Save to file with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"card_order_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(csv_content)
            self._show_message("Saved!", f"Card order saved to:\n{filename}")
        except Exception as e:
            self._show_message("Error", f"Failed to save: {e}")
    
    def _get_card_name_from_index(self, sprite_idx):
        """Convert sprite sheet index to readable card name"""
        # Sprite sheet order: 2-A Hearts (0-12), 2-A Clubs (13-25), 2-A Diamonds (26-38), 2-A Spades (39-51)
        suits = ['H', 'C', 'D', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        
        suit_idx = sprite_idx // 13
        rank_idx = sprite_idx % 13
        
        if suit_idx < len(suits) and rank_idx < len(ranks):
            return f"{ranks[rank_idx]}{suits[suit_idx]}"
        return f"Card_{sprite_idx}"
    
    def _get_modifier_name_from_index(self, mod_type, sprite_idx):
        """Convert modifier sprite index to readable name using config"""
        if not self.card_order_config or 'modifiers' not in self.card_order_config:
            return f"Modifier_{sprite_idx}"
        
        mod_config = self.card_order_config['modifiers']
        
        # Check each modifier type
        for category in ['enhancements', 'seals', 'editions']:
            if category in mod_config and mod_type in category:
                indices = mod_config[category]['indices']
                names = mod_config[category]['names']
                if sprite_idx in indices:
                    idx_pos = indices.index(sprite_idx)
                    if idx_pos < len(names):
                        return names[idx_pos]
        
        return f"Modifier_{sprite_idx}"
    
    def _on_modifier_filter_change(self, event=None):
        """Handle modifier filter change"""
        filter_value = self.modifier_filter.get()
        print(f"Modifier filter changed to: {filter_value}")
        
        # Clear existing modifiers
        if hasattr(self, 'modifiers_canvas'):
            self.modifiers_canvas.delete('all')
        
        # Clear modifier data structures
        if hasattr(self, 'modifier_images'):
            self.modifier_images.clear()
        if hasattr(self, 'modifier_img_ids'):
            self.modifier_img_ids.clear()
        if hasattr(self, 'modifier_positions'):
            self.modifier_positions.clear()
        if hasattr(self, 'modifier_types'):
            self.modifier_types.clear()
        if hasattr(self, 'modifier_display_widths'):
            self.modifier_display_widths.clear()
        
        # Reload modifiers with new filter
        self.load_modifiers()
    
    def _open_card_design_menu(self):
        """Open a popup window for card design options"""
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
        
        # Load collab options from resource_mapping.json
        collab_options_by_suit = self._load_collab_options()
        
        suits_display = {'spades': '♠ Spades', 'hearts': '♥ Hearts', 
                        'clubs': '♣ Clubs', 'diamonds': '♦ Diamonds'}
        
        for suit, display_name in suits_display.items():
            suit_frame = tk.Frame(collab_frame, bg=self.bg_color)
            suit_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(suit_frame, text=display_name, bg=self.bg_color, fg='white',
                    font=('Arial', 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            
            # Get collab options for this suit
            collab_options = collab_options_by_suit.get(suit, ["Default"])
            
            suit_menu = ttk.Combobox(suit_frame, textvariable=self.face_card_collabs[suit],
                                    values=collab_options, state='readonly', width=25)
            suit_menu.pack(side=tk.LEFT, padx=5)
            suit_menu.bind('<<ComboboxSelected>>', lambda e, s=suit: self._on_collab_change(s))
    
    def _load_collab_options(self):
        """Load collaboration options from resource_mapping.json"""
        collab_options = {}
        
        try:
            with open('resource_mapping.json', 'r') as f:
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
            # Fallback to default
            for suit in ['spades', 'hearts', 'clubs', 'diamonds']:
                collab_options[suit] = ["Default"]
        
        return collab_options
    
    def _get_collab_face_if_applicable(self, card_name, default_face, row, col):
        """Get collab face sprite if this card should use one"""
        # Check if this is a face card position (K=col 1, Q=col 2, J=col 3)
        if col not in [1, 2, 3]:
            return default_face
        
        # Map column to face name
        col_to_face = {1: 'K', 2: 'Q', 3: 'J'}
        face_name = col_to_face[col]
        
        # Map row to suit
        row_to_suit = {0: 'spades', 1: 'hearts', 2: 'clubs', 3: 'diamonds'}
        if row not in row_to_suit:
            return default_face
        
        suit = row_to_suit[row]
        
        # Check if a collab is selected for this suit
        if not hasattr(self, 'face_card_collabs'):
            return default_face
        
        collab_name = self.face_card_collabs[suit].get()
        if collab_name == "Default":
            return default_face
        
        # Load the collab face
        try:
            with open('resource_mapping.json', 'r') as f:
                resource_mapping = json.load(f)
            
            collab_data = resource_mapping['sprite_sheets']['collab_face_cards']
            resource_path = Path(collab_data['resource_path'])
            variants = collab_data['variants']
            
            # Determine contrast mode
            use_high_contrast = hasattr(self, 'card_contrast') and self.card_contrast.get() == "High Contrast"
            contrast_key = 'high_contrast' if use_high_contrast else 'standard'
            
            # Find the collab data
            collab_file = None
            for collab in variants.get(suit, []):
                if collab['display_name'] == collab_name:
                    collab_file = collab[contrast_key]
                    break
            
            if not collab_file:
                return default_face
            
            # Load collab sprite sheet
            collab_path = resource_path / collab_file
            if not collab_path.exists():
                return default_face
            
            # Load and extract the specific face card
            collab_img = Image.open(collab_path).convert('RGBA')
            card_width = collab_img.width // 3
            
            # Collab sprite sheet order: J, Q, K (indices 0, 1, 2)
            face_to_collab_idx = {'J': 0, 'Q': 1, 'K': 2}
            collab_idx = face_to_collab_idx[face_name]
            
            left = collab_idx * card_width
            face_sprite = collab_img.crop((left, 0, left + card_width, collab_img.height))
            
            return face_sprite
        
        except Exception as e:
            print(f"Warning: Could not load collab face for {suit} {face_name}: {e}")
            return default_face
    
    def _apply_collab_face_cards(self, ordered_sprites, order_indices):
        """Replace face cards (J, Q, K) with collab sprites if selected"""
        # Check if any collabs are selected
        has_collabs = False
        for suit, var in self.face_card_collabs.items():
            if var.get() != "Default":
                has_collabs = True
                break
        
        if not has_collabs:
            return ordered_sprites
        
        # Load resource mapping to get collab file paths
        try:
            with open('resource_mapping.json', 'r') as f:
                resource_mapping = json.load(f)
            
            collab_data = resource_mapping['sprite_sheets']['collab_face_cards']
            resource_path = Path(collab_data['resource_path'])
            variants = collab_data['variants']
            
            # Determine contrast mode
            use_high_contrast = hasattr(self, 'card_contrast') and self.card_contrast.get() == "High Contrast"
            contrast_key = 'high_contrast' if use_high_contrast else 'standard'
            
            # Map suits to their row indices (based on custom order: S, H, C, D)
            suit_rows = {'spades': 0, 'hearts': 1, 'clubs': 2, 'diamonds': 3}
            
            # Face card columns in display order (A, K, Q, J, 10, 9, 8, 7, 6, 5, 4, 3, 2)
            # K=1, Q=2, J=3 in 0-indexed 13-column layout
            face_cols = {'K': 1, 'Q': 2, 'J': 3}
            
            # Process each suit
            for suit, row_idx in suit_rows.items():
                collab_name = self.face_card_collabs[suit].get()
                if collab_name == "Default":
                    continue
                
                # Find the collab data
                collab_file = None
                for collab in variants.get(suit, []):
                    if collab['display_name'] == collab_name:
                        collab_file = collab[contrast_key]
                        break
                
                if not collab_file:
                    continue
                
                # Load collab sprite sheet
                collab_path = resource_path / collab_file
                if not collab_path.exists():
                    print(f"Warning: Collab file not found: {collab_path}")
                    continue
                
                # Load and split the 3x1 collab sprite sheet
                collab_img = Image.open(collab_path).convert('RGBA')
                card_width = collab_img.width // 3
                card_height = collab_img.height
                
                # Collab sprite sheet order: J, Q, K (indices 0, 1, 2)
                # Display order: K, Q, J (columns 1, 2, 3)
                collab_to_display = {'J': 0, 'Q': 1, 'K': 2}
                
                # Extract J, Q, K sprites and composite with card back
                for face_name, col_idx in face_cols.items():
                    # Get the correct index from collab sheet
                    collab_idx = collab_to_display[face_name]
                    left = collab_idx * card_width
                    face_sprite = collab_img.crop((left, 0, left + card_width, card_height))
                    
                    # Composite with card back
                    if self.sprite_loader and self.sprite_loader.card_back:
                        back = self.sprite_loader.card_back.copy()
                        if back.size != face_sprite.size:
                            back = back.resize(face_sprite.size, Image.Resampling.LANCZOS)
                        result = back.copy()
                        result.paste(face_sprite, (0, 0), face_sprite)
                        face_sprite = result
                    
                    # Replace in ordered_sprites
                    display_idx = row_idx * 13 + col_idx
                    if display_idx < len(ordered_sprites):
                        ordered_sprites[display_idx] = face_sprite
                        print(f"Replaced {suit} {face_name} with {collab_name}")
        
        except Exception as e:
            print(f"Warning: Could not apply collab face cards: {e}")
            import traceback
            traceback.print_exc()
        
        return ordered_sprites
    
    def _on_contrast_change(self):
        """Handle contrast change - reload cards immediately"""
        print(f"Contrast changed to: {self.card_contrast.get()}")
        self._reload_cards()
    
    def _on_collab_change(self, suit):
        """Handle collaboration change for a suit - reload cards immediately"""
        print(f"Collab changed for {suit}: {self.face_card_collabs[suit].get()}")
        self._reload_cards()
    
    def _reload_cards(self):
        """Reload all playing cards with current design settings"""
        # Clear existing cards
        if hasattr(self, 'card_grid_canvas'):
            self.card_grid_canvas.delete('all')
        
        # Clear card data structures
        if hasattr(self, 'card_images'):
            self.card_images.clear()
        if hasattr(self, 'card_img_ids'):
            self.card_img_ids.clear()
        if hasattr(self, 'card_positions'):
            self.card_positions.clear()
        if hasattr(self, 'base_card_sprites'):
            self.base_card_sprites.clear()
        if hasattr(self, 'card_faces'):
            self.card_faces.clear()
        
        # Reload cards with new settings
        self.load_cards()
    
    def _show_message(self, title, message):
        """Show a message dialog"""
        from tkinter import messagebox
        messagebox.showinfo(title, message)
    
    def _on_window_resize(self, event):
        """Handle window resize to adjust card spacing"""
        # Respond to root window resize events
        if event.widget != self.root:
            return
        
        # Update immediately without debounce for live feedback
        self._recalculate_card_positions()
    
    def _recalculate_card_positions(self):
        """Recalculate card positions based on available width"""
        if not hasattr(self, 'card_positions') or not hasattr(self, 'card_img_ids'):
            return
        
        # Get available width
        canvas_width = self.card_grid_canvas.winfo_width()
        if canvas_width <= 1:  # Canvas not yet rendered
            return
        
        # Calculate how many columns we have
        cols = 13  # Playing cards are 13 columns
        rows = 4   # 4 rows
        
        # Calculate spacing needed
        # Total width needed = cols * card_width + (cols - 1) * spacing
        # Available width = canvas_width
        # Solve for spacing: spacing = (canvas_width - cols * card_width) / (cols - 1)
        
        available_width = canvas_width - 20  # Account for padding
        calculated_spacing = (available_width - (cols * self.card_display_width)) / (cols - 1)
        
        # Clamp spacing: minimum can be negative (overlap), maximum is self.card_spacing
        max_spacing = self.card_spacing
        min_spacing = -self.card_display_width * 0.7  # Allow up to 70% overlap
        
        actual_spacing = max(min_spacing, min(max_spacing, calculated_spacing))
        
        # Update card positions
        for card_name, pos_info in self.card_positions.items():
            if card_name in self.card_img_ids:
                row = pos_info['row']
                col = pos_info['col']
                
                # Calculate new position
                x = col * (self.card_display_width + actual_spacing)
                y = row * (self.card_display_height + self.card_spacing)
                
                # Update canvas item position
                img_id = self.card_img_ids[card_name]
                self.card_grid_canvas.coords(img_id, x, y)
                
                # Adjust z-order: higher column index = higher z-order (drawn on top)
                # This makes cards on the left appear behind cards on the right
                self.card_grid_canvas.tag_raise(img_id)
        
        # Also update modifier positions
        self._recalculate_modifier_positions()
    
    def _recalculate_modifier_positions(self):
        """Recalculate modifier positions grouped by category with dynamic spacing"""
        if not hasattr(self, 'modifier_positions') or not hasattr(self, 'modifier_img_ids'):
            return
        
        # Match the playing cards canvas width exactly
        canvas_width = self.card_grid_canvas.winfo_width()
        if canvas_width <= 1:  # Canvas not yet rendered
            return
        
        # Update modifiers canvas to match playing cards width
        self.modifiers_canvas.config(width=canvas_width)
        
        # Group modifiers by category
        categories = {
            'enhancement': [],
            'edition': [],
            'seal': [],
            'debuff': []
        }
        
        for modifier_key, display_idx in self.modifier_positions.items():
            mod_type = self.modifier_types.get(modifier_key, '')
            if 'enhancement' in mod_type:
                categories['enhancement'].append((modifier_key, display_idx))
            elif 'debuff' in mod_type:
                categories['debuff'].append((modifier_key, display_idx))
            elif 'edition' in mod_type:
                categories['edition'].append((modifier_key, display_idx))
            elif 'seal' in mod_type:
                categories['seal'].append((modifier_key, display_idx))
        
        # Sort each category by display index
        for cat in categories.values():
            cat.sort(key=lambda x: x[1])
        
        # Constants
        category_gap = 10  # Gap between categories
        max_spacing = self.card_spacing
        min_spacing = -self.card_display_width * 0.7
        
        # Seal spacing limits (can overlap but not as much as cards)
        max_seal_spacing = 5  # Maximum spacing between seals
        min_seal_spacing = -10  # Minimum spacing (allow some overlap)
        
        # Count total items
        total_overlap_items = len(categories['enhancement']) + len(categories['edition']) + len(categories['debuff'])
        total_seal_items = len(categories['seal'])
        
        # Count gaps (only between non-empty categories)
        non_empty_cats = [cat for cat in ['enhancement', 'edition', 'seal', 'debuff'] if categories[cat]]
        total_gaps = (len(non_empty_cats) - 1) * category_gap if len(non_empty_cats) > 1 else 0
        
        # Calculate total width needed at maximum spacing
        total_seal_width_max = 0
        if categories['seal']:
            for modifier_key, _ in categories['seal']:
                total_seal_width_max += self.modifier_display_widths.get(modifier_key, self.card_display_width)
            total_seal_width_max += (total_seal_items - 1) * max_seal_spacing if total_seal_items > 1 else 0
        
        total_overlap_width_max = total_overlap_items * self.card_display_width
        if total_overlap_items > 1:
            total_overlap_width_max += (total_overlap_items - 1) * max_spacing
        
        # Available width
        available_width = canvas_width - 20
        total_needed = total_seal_width_max + total_overlap_width_max + total_gaps
        
        # Calculate dynamic spacing
        if total_needed > available_width:
            # Need to compress - calculate how much space we have
            available_for_items = available_width - total_gaps
            
            # Calculate seal widths (sum of actual widths)
            seal_widths_sum = sum(self.modifier_display_widths.get(mk, self.card_display_width) for mk, _ in categories['seal'])
            
            # Calculate spacing for both categories
            if total_overlap_items > 0 and total_seal_items > 0:
                # Distribute remaining space proportionally
                total_items = total_overlap_items + total_seal_items
                total_gaps_needed = (total_overlap_items - 1) + (total_seal_items - 1) if total_items > 1 else 0
                
                if total_gaps_needed > 0:
                    avg_spacing = (available_for_items - (total_overlap_items * self.card_display_width) - seal_widths_sum) / total_gaps_needed
                    overlap_spacing = max(min_spacing, min(max_spacing, avg_spacing))
                    seal_spacing = max(min_seal_spacing, min(max_seal_spacing, avg_spacing))
                else:
                    overlap_spacing = max_spacing
                    seal_spacing = max_seal_spacing
            elif total_overlap_items > 0:
                calculated_spacing = (available_for_items - (total_overlap_items * self.card_display_width)) / (total_overlap_items - 1) if total_overlap_items > 1 else 0
                overlap_spacing = max(min_spacing, min(max_spacing, calculated_spacing))
                seal_spacing = max_seal_spacing
            else:
                overlap_spacing = max_spacing
                calculated_seal_spacing = (available_for_items - seal_widths_sum) / (total_seal_items - 1) if total_seal_items > 1 else 0
                seal_spacing = max(min_seal_spacing, min(max_seal_spacing, calculated_seal_spacing))
        else:
            # Plenty of space - use maximum spacing
            overlap_spacing = max_spacing
            seal_spacing = max_seal_spacing
        
        # Position modifiers by category
        x_offset = 0
        
        for cat_name in ['enhancement', 'edition', 'seal', 'debuff']:
            cat_modifiers = categories[cat_name]
            if not cat_modifiers:
                continue
            
            # Track position within seal category
            seal_x_offset = 0
            
            for i, (modifier_key, display_idx) in enumerate(cat_modifiers):
                if modifier_key in self.modifier_img_ids:
                    # Calculate position within category
                    if cat_name == 'seal':
                        x = x_offset + seal_x_offset
                        # Add this seal's width for next seal
                        seal_x_offset += self.modifier_display_widths.get(modifier_key, self.card_display_width) + seal_spacing
                    else:
                        x = x_offset + (i * (self.card_display_width + overlap_spacing))
                    
                    # Update canvas item position
                    img_id = self.modifier_img_ids[modifier_key]
                    self.modifiers_canvas.coords(img_id, x, 0)
                    
                    # Adjust z-order: lower index = higher z-order (leftmost on top)
                    self.modifiers_canvas.tag_lower(img_id)
            
            # Move offset for next category
            if cat_name == 'seal':
                # Use actual seal widths
                category_width = sum(self.modifier_display_widths.get(mk, self.card_display_width) for mk, _ in cat_modifiers)
                category_width += (len(cat_modifiers) - 1) * seal_spacing if len(cat_modifiers) > 1 else 0
                x_offset += category_width + category_gap
            else:
                if len(cat_modifiers) > 0:
                    x_offset += self.card_display_width + (len(cat_modifiers) - 1) * (self.card_display_width + overlap_spacing) + category_gap
    
    def _load_card_order_config(self):
        """Load card order configuration from JSON file"""
        config_path = Path("card_order_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load card order config: {e}")
        return None
    
    def _auto_size_window(self, canvas_width, canvas_height):
        """Auto-size window to fit all cards, respecting screen size"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate required window size (canvas + padding + UI elements)
        # Components:
        # - Title: ~40px
        # - Modifiers row: card_display_height + 10px padding
        # - Card grid: canvas_height + 20px padding
        # - Separator: ~20px
        # - "Card Order:" label: ~30px
        # - Order canvas: 95px + 5px padding
        # - Buttons: ~50px
        # - Extra padding: 20px
        
        required_width = canvas_width + 40  # 20px padding on each side
        required_height = (40 +  # title
                          self.card_display_height + 10 +  # modifiers
                          canvas_height + 20 +  # card grid
                          20 +  # separator
                          30 +  # order label
                          100 +  # order canvas + padding
                          50 +  # buttons
                          20)  # extra padding
        
        # Limit to 90% of screen size
        max_width = int(screen_width * 0.9)
        max_height = int(screen_height * 0.9)
        
        window_width = min(required_width, max_width)
        window_height = min(required_height, max_height)
        
        # Center window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")


def main():
    root = tk.Tk()
    app = BalatroTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
