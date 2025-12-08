#!/usr/bin/env python3
"""
Card Manager - Handles card loading, display, and tracking
"""

from PIL import Image, ImageTk
import tkinter as tk
from pathlib import Path
from datetime import datetime


class CardManager:
    """Manages card display and order tracking"""
    
    def __init__(self, sprite_loader, card_order_config, card_grid_canvas, order_canvas, order_frame,
                 card_display_width, card_display_height, card_spacing, bg_color):
        self.sprite_loader = sprite_loader
        self.card_order_config = card_order_config
        self.card_grid_canvas = card_grid_canvas
        self.order_canvas = order_canvas
        self.order_frame = order_frame
        self.card_display_width = card_display_width
        self.card_display_height = card_display_height
        self.card_spacing = card_spacing
        self.bg_color = bg_color
        
        # Card data
        self.card_order = []
        self.card_images = {}
        self.small_card_images = {}
        self.base_card_sprites = {}
        self.card_faces = {}
        self.card_img_ids = {}
        self.card_positions = {}
    
    def load_cards(self, use_high_contrast=False, design_manager=None):
        """Load cards from sprite sheets"""
        sheet_names = self.sprite_loader.get_sheet_names()
        if not sheet_names:
            raise ValueError("No sprite sheets found")
        
        # Select sheet based on contrast
        sheet_name = self._select_card_sheet(sheet_names, use_high_contrast)
        print(f"Loading cards from: {sheet_name} (High Contrast: {use_high_contrast})")
        
        # Load sprites
        use_composite = 'playing' in sheet_name.lower()
        sprites = self.sprite_loader.get_all_sprites(sheet_name, composite_back=use_composite)
        
        # Check for custom order
        use_custom_order = ('playing' in sheet_name.lower() and 
                           self.card_order_config and 
                           'playing_cards_order' in self.card_order_config)
        
        # Track which cards have been replaced with collabs
        collab_replaced_indices = set()
        collab_faces = {}
        
        if use_custom_order:
            order_indices = self.card_order_config['playing_cards_order']['sprite_sheet_mapping']['order']
            ordered_sprites = [sprites[i] for i in order_indices]
            cols, rows = 13, 4
            
            # Apply collab face cards if design_manager provided
            if design_manager:
                ordered_sprites, collab_replaced_indices, collab_faces = design_manager.apply_collab_face_cards(
                    ordered_sprites, order_indices)
        else:
            ordered_sprites = sprites
            sheet_info = self.sprite_loader.get_sheet_info(sheet_name)
            cols = sheet_info['cols']
            rows = (len(sprites) + cols - 1) // cols
        
        # Set canvas size
        canvas_width = cols * (self.card_display_width + self.card_spacing) - self.card_spacing
        canvas_height = rows * (self.card_display_height + self.card_spacing) - self.card_spacing
        self.card_grid_canvas.config(width=canvas_width, height=canvas_height)
        
        # Display cards
        for idx, sprite in enumerate(ordered_sprites):
            row = idx // cols
            col = idx % cols
            if use_custom_order:
                original_idx = order_indices[idx]
                card_name = f"{sheet_name}_{original_idx}"
            else:
                card_name = f"{sheet_name}_{idx}"
            
            # Check if this card was replaced with a collab
            is_collab = idx in collab_replaced_indices
            collab_face = collab_faces.get(idx) if is_collab else None
            self.create_card_button(card_name, sprite, row, col, is_collab, collab_face)
        
        return canvas_width, canvas_height
    
    def _select_card_sheet(self, sheet_names, use_high_contrast):
        """Select appropriate card sheet based on contrast setting"""
        if use_high_contrast:
            if 'playing_cards_high_contrast' in sheet_names:
                return 'playing_cards_high_contrast'
            for name in sheet_names:
                if 'high' in name.lower() and 'contrast' in name.lower() and 'playing' in name.lower():
                    return name
        else:
            if 'playing_cards' in sheet_names:
                return 'playing_cards'
            for name in sheet_names:
                name_lower = name.lower()
                if ('playing' in name_lower or '8bitdeck' in name_lower) and \
                   'high' not in name_lower and 'contrast' not in name_lower and \
                   'back' not in name_lower:
                    return name
        
        # Fallback
        for name in sheet_names:
            if 'playing' in name.lower() or 'card' in name.lower():
                return name
        return sheet_names[0]
    
    def create_card_button(self, card_name, sprite, row, col, is_collab=False, collab_face=None):
        """Create a clickable card button"""
        try:
            # Store base sprite and face
            self.base_card_sprites[card_name] = sprite
            
            # Extract card face (without backing)
            if self.sprite_loader and self.sprite_loader.card_back:
                try:
                    if is_collab and collab_face is not None:
                        # For collab cards, use the provided face without backing
                        self.card_faces[card_name] = collab_face
                    elif '_' in card_name and card_name.split('_')[-1].isdigit():
                        sprite_idx = int(card_name.split('_')[-1])
                        sheet_name = '_'.join(card_name.split('_')[:-1])
                        card_face = self.sprite_loader.get_sprite(sheet_name, sprite_idx, composite_back=False)
                        self.card_faces[card_name] = card_face
                except:
                    pass
            
            # Resize and create photo
            img = sprite.copy()
            img.thumbnail((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            self.card_images[card_name] = photo
            
            # Calculate position
            x = col * (self.card_display_width + self.card_spacing)
            y = row * (self.card_display_height + self.card_spacing)
            
            # Create on canvas
            img_id = self.card_grid_canvas.create_image(x, y, image=photo, anchor=tk.NW)
            
            self.card_img_ids[card_name] = img_id
            self.card_positions[card_name] = {'row': row, 'col': col}
            
            # Bind events
            self.card_grid_canvas.tag_bind(img_id, '<Button-1>', 
                lambda e, name=card_name: self._on_card_click(name))
            self.card_grid_canvas.tag_bind(img_id, '<Enter>', 
                lambda e: self.card_grid_canvas.config(cursor='hand2'))
            self.card_grid_canvas.tag_bind(img_id, '<Leave>', 
                lambda e: self.card_grid_canvas.config(cursor=''))
            
        except Exception as e:
            print(f"Error creating button for {card_name}: {e}")
    
    def _on_card_click(self, card_name):
        """Handle card click - to be overridden by main app"""
        pass
    
    def set_card_click_handler(self, handler):
        """Set the handler for card clicks"""
        self._on_card_click = handler
    
    def refresh_card_display(self, modifier_manager):
        """Refresh all cards with current modifiers"""
        for card_name, base_sprite in self.base_card_sprites.items():
            if card_name in self.card_img_ids:
                card_face = self.card_faces.get(card_name)
                display_sprite = modifier_manager.apply_modifiers_to_card(base_sprite, card_face)
                
                img = display_sprite.copy()
                img.thumbnail((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                img_id = self.card_img_ids[card_name]
                self.card_grid_canvas.itemconfig(img_id, image=photo)
                self.card_images[card_name] = photo
    
    def add_card_to_order(self, card_name, final_sprite, modifiers_applied):
        """Add a card to the order list"""
        self.card_order.append((card_name, final_sprite, modifiers_applied))
        self.update_order_display()
    
    def update_order_display(self):
        """Update the order list display"""
        for widget in self.order_frame.winfo_children():
            widget.destroy()
        
        for idx, item in enumerate(self.card_order):
            if len(item) == 2:
                card_name, card_source = item
                modifiers_applied = []
            else:
                card_name, card_source, modifiers_applied = item
            
            modifier_key = '+'.join([f"{mt}_{mi}" for mt, mi in modifiers_applied])
            cache_key = f"{card_name}_{modifier_key}_{idx}"
            
            if isinstance(card_source, Path):
                img = Image.open(card_source)
            else:
                img = card_source.copy()
            
            img.thumbnail((50, 70), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.small_card_images[cache_key] = photo
            
            card_frame = tk.Frame(self.order_frame, bg=self.bg_color)
            card_frame.pack(side=tk.LEFT, padx=3)
            
            num_label = tk.Label(card_frame, text=f"{idx+1}", 
                                font=('Arial', 7, 'bold'),
                                bg=self.bg_color, fg='white')
            num_label.pack()
            
            card_label = tk.Label(card_frame, image=photo,
                                 bg=self.bg_color, borderwidth=0,
                                 highlightthickness=0)
            card_label.pack()
        
        self.order_frame.update_idletasks()
        self.order_canvas.configure(scrollregion=self.order_canvas.bbox('all'))
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
            return False, "No cards to save"
        
        card_names = []
        for item in self.card_order:
            if len(item) == 2:
                card_name, card_source = item
                modifiers_applied = []
            else:
                card_name, card_source, modifiers_applied = item
            
            readable_parts = []
            if '_' in card_name and card_name.split('_')[-1].isdigit():
                sprite_idx = int(card_name.split('_')[-1])
                base_name = self._get_card_name_from_index(sprite_idx)
                readable_parts.append(base_name)
            else:
                readable_parts.append(card_name)
            
            for mod_type, mod_idx in modifiers_applied:
                mod_name = self._get_modifier_name_from_index(mod_type, mod_idx)
                readable_parts.append(mod_name)
            
            card_names.append('+'.join(readable_parts))
        
        csv_content = ','.join(card_names)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"card_order_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(csv_content)
            return True, f"Card order saved to:\n{filename}"
        except Exception as e:
            return False, f"Failed to save: {e}"
    
    def _get_card_name_from_index(self, sprite_idx):
        """Convert sprite index to readable card name"""
        suits = ['H', 'C', 'D', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suit_idx = sprite_idx // 13
        rank_idx = sprite_idx % 13
        if suit_idx < len(suits) and rank_idx < len(ranks):
            return f"{ranks[rank_idx]}{suits[suit_idx]}"
        return f"Card_{sprite_idx}"
    
    def _get_modifier_name_from_index(self, mod_type, sprite_idx):
        """Convert modifier index to readable name"""
        if not self.card_order_config or 'modifiers' not in self.card_order_config:
            return f"Modifier_{sprite_idx}"
        
        mod_config = self.card_order_config['modifiers']
        for category in ['enhancements', 'seals', 'editions']:
            if category in mod_config and mod_type in category:
                indices = mod_config[category]['indices']
                names = mod_config[category]['names']
                if sprite_idx in indices:
                    idx_pos = indices.index(sprite_idx)
                    if idx_pos < len(names):
                        return names[idx_pos]
        return f"Modifier_{sprite_idx}"
    
    def clear_cards(self):
        """Clear all card data and canvas"""
        self.card_grid_canvas.delete('all')
        self.card_images.clear()
        self.card_img_ids.clear()
        self.card_positions.clear()
        self.base_card_sprites.clear()
        self.card_faces.clear()
