#!/usr/bin/env python3
"""
Nebulatro - Balatro Card Order Tracker
Main application orchestrator
"""

import tkinter as tk
from tkinter import messagebox
import json
from pathlib import Path

from src.utils import SpriteLoader
from src.ui import UIComponents, LayoutManager
from src.managers import CardManager, ModifierManager, DesignManager
from src.vision import CardRecognizer, ScreenCapture


class BalatroTracker:
    """Main application class - orchestrates all components"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Nebulatro")
        
        # Configuration
        self.card_display_width = 71
        self.card_display_height = 95
        self.card_spacing = 2
        self.bg_color = '#2b2b2b'
        self.canvas_bg = '#1e1e1e'
        
        # Set minimum window size
        min_width = int(13 * self.card_display_width - 12 * (self.card_display_width * 0.55)) + 15
        min_height = 710
        self.root.minsize(min_width, min_height)
        
        # Load configuration
        self.card_order_config = self._load_config()
        
        # Initialize sprite loader
        self.sprite_loader = SpriteLoader()
        
        # Initialize vision system
        self.screen_capture = ScreenCapture()
        self.card_recognizer = CardRecognizer(self.sprite_loader)
        
        # Initialize UI components
        self.ui = UIComponents(self.root, self.bg_color, self.canvas_bg)
        self.ui.set_app_icon()
        self.ui.setup_main_layout(
            self.card_display_width, 
            self.card_display_height,
            self._on_modifier_filter_change,
            self._on_card_design_click,
            self._on_clear,
            self._on_undo,
            self._on_save,
            self._on_capture_hand,
            self._on_mode_change
        )
        
        # Initialize managers
        self._setup_managers()
        
        # Initialize data labeling
        self._setup_data_labeling()
        
        # Initialize suits for data labeling
        self.suit_sprites = {}
        self.suit_img_ids = []
        
        # Store matched card info for persistence
        self.matched_card_info = None
        self.matched_card_sprite = None  # Store PIL image for recreation
        
        # Load initial content
        self._load_initial_content()
        
        # Setup event handlers
        self.root.bind('<Configure>', self._on_window_resize)
        self.root.after(100, self._recalculate_positions)
    
    def _setup_managers(self):
        """Initialize all manager components"""
        # Card manager
        self.card_manager = CardManager(
            self.sprite_loader,
            self.card_order_config,
            self.ui.card_grid_canvas,
            self.ui.order_canvas,
            self.ui.order_frame,
            self.card_display_width,
            self.card_display_height,
            self.card_spacing,
            self.bg_color
        )
        self.card_manager.set_card_click_handler(self._on_card_click)
        
        # Modifier manager
        self.modifier_manager = ModifierManager(
            self.sprite_loader,
            self.card_order_config,
            self.ui.modifiers_canvas,
            self.card_display_width,
            self.card_display_height,
            self.card_spacing,
            self.bg_color
        )
        self.modifier_manager.set_modifier_change_handler(self._on_modifier_change)
        
        # Design manager
        self.design_manager = DesignManager(
            self.root,
            self.sprite_loader,
            self.bg_color,
            self.ui.card_contrast,
            self.ui.face_card_collabs
        )
        self.design_manager.set_design_change_handler(self._on_design_change)
        
        # Layout manager
        self.layout_manager = LayoutManager(
            self.ui.card_grid_canvas,
            self.ui.modifiers_canvas,
            self.card_display_width,
            self.card_display_height,
            self.card_spacing
        )
    
    def _load_initial_content(self):
        """Load modifiers and cards"""
        # Load modifiers
        filter_mode = self.ui.modifier_filter.get()
        self.modifier_manager.load_modifiers(filter_mode)
        
        # Load cards
        use_high_contrast = self.ui.card_contrast.get() == "High Contrast"
        canvas_width, canvas_height = self.card_manager.load_cards(use_high_contrast, self.design_manager)
        
        # Auto-size window
        self.layout_manager.auto_size_window(self.root, canvas_width, canvas_height)
    
    # Event Handlers
    
    def _on_card_click(self, card_name):
        """Handle card click - behavior depends on current mode"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            self._handle_tracking_card_click(card_name)
        elif current_mode == "Data Labeling":
            self._handle_labeling_card_click(card_name)
    
    def _handle_tracking_card_click(self, card_name):
        """Handle card click in manual tracking mode"""
        if card_name not in self.card_manager.base_card_sprites:
            return
        
        base_sprite = self.card_manager.base_card_sprites[card_name]
        card_face = self.card_manager.card_faces.get(card_name)
        
        # Apply modifiers
        final_sprite = self.modifier_manager.apply_modifiers_to_card(base_sprite, card_face)
        modifiers_applied = self.modifier_manager.get_selected_modifiers()
        
        # Add to order
        self.card_manager.add_card_to_order(card_name, final_sprite, modifiers_applied)
    
    def _handle_labeling_card_click(self, card_name):
        """Handle card click in data labeling mode"""
        if not self.labeling_cards or self.current_labeling_index >= len(self.labeling_cards):
            messagebox.showwarning("No Card", "No card loaded for labeling")
            return
        
        # Get the sprite index for this card
        card_order = self.card_order_config['playing_cards_order']['sprite_sheet_mapping']['order']
        
        # Find the sprite index for this card name
        sprite_idx = None
        for i, name in enumerate(self.card_manager.base_card_sprites.keys()):
            if name == card_name:
                sprite_idx = card_order[i]
                break
        
        if sprite_idx is not None:
            self.selected_card_class = sprite_idx
            
            # Get card info for display
            suits = ["Hearts", "Clubs", "Diamonds", "Spades"]
            ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
            suit_idx = sprite_idx // 13
            rank_idx = sprite_idx % 13
            
            if suit_idx < len(suits) and rank_idx < len(ranks):
                card_desc = f"{ranks[rank_idx]} of {suits[suit_idx]}"
            else:
                card_desc = f"Card {sprite_idx}"
            
            # Show current modifiers if any
            modifiers = self.modifier_manager.get_selected_modifiers()
            modifier_text = ""
            if modifiers:
                if isinstance(modifiers, dict):
                    active_mods = [k for k, v in modifiers.items() if v]
                elif isinstance(modifiers, list):
                    active_mods = [str(m) for m in modifiers if m]
                else:
                    active_mods = [str(modifiers)]
                
                if active_mods:
                    modifier_text = f"\nWith modifiers: {', '.join(active_mods)}"
            
            # Update matched card display
            self._update_matched_card_display(sprite_idx, "selected")
            
            # Console feedback
            print(f"Selected: {card_desc} (Class: {sprite_idx}){modifier_text}")
        else:
            messagebox.showerror("Error", f"Could not find sprite index for {card_name}")
    
    def _on_modifier_change(self):
        """Handle modifier selection change - refresh card display"""
        self.card_manager.refresh_card_display(self.modifier_manager)
    
    def _on_modifier_filter_change(self, event=None):
        """Handle modifier filter change"""
        filter_value = self.ui.modifier_filter.get()
        self.modifier_manager.clear_modifiers()
        self.modifier_manager.load_modifiers(filter_value)
        self._recalculate_positions()
    
    def _on_card_design_click(self):
        """Open card design popup"""
        self.design_manager.open_design_popup()
    
    def _on_design_change(self):
        """Handle design change - reload cards"""
        self.card_manager.clear_cards()
        use_high_contrast = self.ui.card_contrast.get() == "High Contrast"
        self.card_manager.load_cards(use_high_contrast, self.design_manager)
    
    def _on_clear(self):
        """Clear card order or selection"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            self.card_manager.clear_order()
        elif current_mode == "Data Labeling":
            self.selected_card_class = None
            messagebox.showinfo("Cleared", "Card selection cleared")
    
    def _on_undo(self):
        """Undo last card or go to previous card"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            self.card_manager.undo_last()
        elif current_mode == "Data Labeling":
            self._on_prev_labeling_card()
    
    def _on_save(self):
        """Save card order or label current card"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            success, message = self.card_manager.save_order()
            title = "Saved!" if success else "Error"
            messagebox.showinfo(title, message)
        elif current_mode == "Data Labeling":
            self._save_current_label()
    
    def _save_current_label(self):
        """Save the current card label"""
        if self.selected_card_class is None:
            messagebox.showwarning("No Selection", "Please click on a card or select a special label first")
            return
        
        if not self.labeling_cards or self.current_labeling_index >= len(self.labeling_cards):
            messagebox.showwarning("No Card", "No card loaded for labeling")
            return
        
        try:
            card_path = self.labeling_cards[self.current_labeling_index]
            
            if (self.selected_card_class == "not_card" or 
                str(self.selected_card_class).startswith("suit_only")):
                # Handle special labels
                output_path = self._save_special_label(card_path, self.selected_card_class)
                if self.selected_card_class == "not_card":
                    label_text = "Not a Card"
                elif str(self.selected_card_class).startswith("suit_only"):
                    suit_part = str(self.selected_card_class).replace("suit_only_", "").replace("suit_only", "")
                    if suit_part:
                        suit_names = {"s": "Spades", "h": "Hearts", "c": "Clubs", "d": "Diamonds"}
                        suit_display = suit_names.get(suit_part, suit_part.title())
                        label_text = f"Suit Only ({suit_display})"
                    else:
                        label_text = "Suit Only"
            else:
                # Handle regular card labels
                from label_single_card import save_labeled_card
                output_path = save_labeled_card(card_path, self.selected_card_class)
                label_text = f"Class {self.selected_card_class}"
            
            # Update matched card display to show confirmed status
            if self.selected_card_class is not None:
                self._update_matched_card_display(self.selected_card_class, "confirmed")
            
            # Save to modifier folders if modifiers are applied
            self._save_modifier_labels(card_path, label_text)
            
            # Show save status in console (no popup)
            print(f"✓ Card labeled as: {label_text} -> {output_path}")
            
            # Move to next card automatically
            self._on_next_labeling_card()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save label: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_special_label(self, card_path, label_type):
        """Save special labels (not_card, suit_only)"""
        import cv2
        from pathlib import Path
        
        # Create special label directory
        special_dir = Path("training_data/processed") / label_type
        special_dir.mkdir(parents=True, exist_ok=True)
        
        # Load and process image
        image = cv2.imread(str(card_path))
        h, w = image.shape[:2]
        # Save image
        output_path = special_dir / f"{card_path.stem}.png"
        cv2.imwrite(str(output_path), image)
        
        return output_path
    
    def _update_matched_card_display(self, card_class, status="selected"):
        """Update the matched card display to show selected/confirmed card"""
        try:
            from PIL import ImageTk, Image
            if card_class == "not_card":
                # Show "Not a Card" indicator
                self.ui.matched_card_canvas.delete("all")
                self.ui.matched_card_canvas.create_text(75, 100, text="NOT A CARD", 
                                                       fill='#f44336', font=('Arial', 10, 'bold'))
                self.ui.match_status.configure(text=f"Status: {status.title()}")
                
            elif str(card_class).startswith("suit_only"):
                # Show suit symbol for suit-only selections
                suit_part = str(card_class).replace("suit_only_", "")
                suit_names = {"s": "♠", "h": "♥", "c": "♣", "d": "♦"}
                suit_symbol = suit_names.get(suit_part, "?")
                
                self.ui.matched_card_canvas.delete("all")
                self.ui.matched_card_canvas.create_text(75, 80, text="SUIT ONLY", 
                                                       fill='#ff9800', font=('Arial', 10, 'bold'))
                self.ui.matched_card_canvas.create_text(75, 120, text=suit_symbol, 
                                                       fill='#ff9800', font=('Arial', 24, 'bold'))
                self.ui.match_status.configure(text=f"Status: {status.title()}")
                
            elif isinstance(card_class, int) and 0 <= card_class <= 51:
                # Show actual card image
                card_order = self.card_order_config['playing_cards_order']['sprite_sheet_mapping']['order']
                
                # Find the card name by sprite index
                for i, sprite_idx in enumerate(card_order):
                    if sprite_idx == card_class:
                        # Get the card sprite and find the corresponding card name
                        card_sprite = self.sprite_loader.get_sprite('Playing Cards (High Contrast)', sprite_idx, composite_back=True)
                        if card_sprite:
                            # Use the card manager's naming system: playing_cards_X where X is sprite_idx
                            card_name = f"playing_cards_{sprite_idx}"
                            card_face = None
                            
                            # Get the card face from the card manager
                            if card_name in self.card_manager.base_card_sprites:
                                card_face = self.card_manager.card_faces.get(card_name)
                            
                            # Apply modifiers using the card manager system if we found the card
                            if card_face:
                                card_sprite = self.modifier_manager.apply_modifiers_to_card(card_sprite, card_face)
                            else:
                                # Fallback: apply modifiers without proper card face
                                card_sprite = self.modifier_manager.apply_modifiers_to_card(card_sprite, card_sprite)
                            
                            # Make matched card smaller and more constrained than input image
                            # Use a fixed, reasonable size that won't grow out of control
                            max_width = 150   # Fixed maximum width (slightly larger)
                            max_height = 200  # Fixed maximum height (slightly larger)
                            
                            # Calculate size maintaining aspect ratio
                            img_width, img_height = card_sprite.size
                            aspect_ratio = img_width / img_height
                            
                            # Scale to fit within constraints
                            if img_width > max_width or img_height > max_height:
                                scale_w = max_width / img_width
                                scale_h = max_height / img_height
                                scale = min(scale_w, scale_h)
                                
                                target_width = int(img_width * scale)
                                target_height = int(img_height * scale)
                            else:
                                target_width = img_width
                                target_height = img_height
                            
                            # Resize to calculated dimensions
                            card_sprite = card_sprite.resize((target_width, target_height), Image.Resampling.LANCZOS)
                            
                            # Store PIL image for recreation
                            self.matched_card_sprite = card_sprite.copy()
                            
                            # Convert to PhotoImage
                            card_photo = ImageTk.PhotoImage(card_sprite)
                            
                            # Clear canvas and display image
                            self.ui.matched_card_canvas.delete("all")
                            
                            # Center the image on canvas
                            canvas_center_x = 75  # 150/2
                            canvas_center_y = 100  # 200/2
                            
                            img_id = self.ui.matched_card_canvas.create_image(
                                canvas_center_x, canvas_center_y, 
                                image=card_photo, anchor=tk.CENTER
                            )
                            
                            # Store reference to prevent garbage collection
                            self.ui.matched_card_canvas.image = card_photo
                            
                            # Store info for persistence
                            self.matched_card_info = {
                                'card_class': card_class,
                                'status': status,
                                'sprite_idx': sprite_idx
                            }
                            
                            # Update status with card name
                            suits = ["Hearts", "Clubs", "Diamonds", "Spades"]
                            ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
                            suit_idx = card_class // 13
                            rank_idx = card_class % 13
                            
                            if suit_idx < len(suits) and rank_idx < len(ranks):
                                card_name = f"{ranks[rank_idx]} of {suits[suit_idx]}"
                            else:
                                card_name = f"Class {card_class}"
                            
                            # Add modifier information to status
                            modifier_text = self._get_modifier_status_text()
                            status_text = f"{card_name}{modifier_text}\nStatus: {status.title()}"
                            self.ui.match_status.configure(text=status_text)
                        break
            else:
                # Unknown selection
                self.ui.matched_card_canvas.delete("all")
                self.ui.matched_card_canvas.create_text(75, 100, text="Unknown", 
                                                       fill='#cccccc', font=('Arial', 9))
                self.ui.match_status.configure(text=f"Status: {status.title()}")
                
        except Exception as e:
            print(f"Error updating matched card display: {e}")
            self.ui.matched_card_canvas.delete("all")
            self.ui.matched_card_canvas.create_text(75, 100, text="Error", 
                                                   fill='#f44336', font=('Arial', 9))
    
    def _clear_matched_card_display(self):
        """Clear the matched card display"""
        self.ui.matched_card_canvas.delete("all")
        self.ui.matched_card_canvas.create_text(75, 100, text="No selection", 
                                               fill='#cccccc', font=('Arial', 9))
        self.ui.match_status.configure(text="")
        self.matched_card_info = None
        self.matched_card_sprite = None
    
    def _show_existing_label_in_matched_display(self, labeled_card_name, card_path):
        """Show the existing label in the matched card display"""
        try:
            from PIL import Image
            self.ui.matched_card_canvas.delete("all")
            
            if labeled_card_name == "Not a Card":
                # Show "Not a Card" indicator
                self.ui.matched_card_canvas.create_text(75, 100, text="NOT A CARD", 
                                                       fill='#f44336', font=('Arial', 10, 'bold'))
                self.ui.match_status.configure(text="Status: Already Labeled")
                
            elif labeled_card_name.startswith("Suit Only"):
                # Show suit image for suit-only labels
                suit_name = labeled_card_name.replace("Suit Only (", "").replace(")", "")
                
                self.ui.matched_card_canvas.create_text(75, 60, text="SUIT ONLY", 
                                                       fill='#ff9800', font=('Arial', 10, 'bold'))
                
                # Use actual suit sprite if available
                if hasattr(self, 'suit_sprites') and suit_name in self.suit_sprites:
                    from PIL import ImageTk
                    suit_sprite = self.suit_sprites[suit_name]
                    # Resize suit for matched display (smaller than full card)
                    display_suit = suit_sprite.resize((60, 80), Image.Resampling.LANCZOS)
                    suit_photo = ImageTk.PhotoImage(display_suit)
                    
                    self.ui.matched_card_canvas.create_image(75, 130, image=suit_photo, anchor=tk.CENTER)
                    self.ui.matched_card_canvas.image = suit_photo  # Keep reference
                else:
                    # Fallback to text symbol if sprites not available
                    suit_symbols = {"Hearts": "♥", "Clubs": "♣", "Diamonds": "♦", "Spades": "♠"}
                    suit_symbol = suit_symbols.get(suit_name, "?")
                    self.ui.matched_card_canvas.create_text(75, 130, text=suit_symbol, 
                                                           fill='#ff9800', font=('Arial', 24, 'bold'))
                
                self.ui.match_status.configure(text=f"{labeled_card_name}\nStatus: Already Labeled")
                
            elif labeled_card_name in ["Card Backs", "Booster Packs", "Consumables", "Jokers"]:
                # Show category labels with appropriate colors
                colors = {"Card Backs": '#2196f3', "Booster Packs": '#ff9800', 
                         "Consumables": '#9c27b0', "Jokers": '#4caf50'}
                color = colors.get(labeled_card_name, '#cccccc')
                
                self.ui.matched_card_canvas.create_text(75, 100, text=labeled_card_name.upper(), 
                                                       fill=color, font=('Arial', 10, 'bold'))
                self.ui.match_status.configure(text=f"Status: Already Labeled")
                
            else:
                # Try to show the actual card if it's a specific card
                card_class = self._card_name_to_class(labeled_card_name)
                if card_class is not None:
                    # Show the card without applying current modifiers (it's already labeled)
                    self._show_existing_card_without_modifiers(card_class, labeled_card_name)
                else:
                    # Fallback for unknown card names
                    self.ui.matched_card_canvas.create_text(75, 100, text=labeled_card_name, 
                                                           fill='#4caf50', font=('Arial', 9, 'bold'))
                    self.ui.match_status.configure(text="Status: Already Labeled")
                    
        except Exception as e:
            print(f"Error showing existing label: {e}")
            self._clear_matched_card_display()
    
    def _card_name_to_class(self, card_name):
        """Convert card name back to class number"""
        try:
            # Parse card name like "6 of Diamonds" 
            if " of " not in card_name:
                return None
                
            rank_str, suit_str = card_name.split(" of ")
            
            # Map suits to indices
            suit_map = {"Hearts": 0, "Clubs": 1, "Diamonds": 2, "Spades": 3}
            if suit_str not in suit_map:
                return None
                
            # Map ranks to indices
            rank_map = {"2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5, "8": 6, "9": 7, 
                       "10": 8, "Jack": 9, "Queen": 10, "King": 11, "Ace": 12}
            if rank_str not in rank_map:
                return None
                
            # Calculate class number: suit_idx * 13 + rank_idx
            class_num = suit_map[suit_str] * 13 + rank_map[rank_str]
            return class_num
            
        except Exception as e:
            print(f"Error converting card name to class: {e}")
            return None
    
    def _apply_modifiers_to_preview(self, card_sprite):
        """Apply selected modifiers to card preview in matched display"""
        try:
            # Get currently selected modifiers
            selected_modifiers = self.modifier_manager.get_selected_modifiers()
            if not selected_modifiers:
                return card_sprite  # No modifiers to apply
            
            # Find the card name from the card manager system
            # We need to get the proper card face for modifier application
            card_face = None
            
            # Try to find the card in the card manager's system
            for card_name, base_sprite in self.card_manager.base_card_sprites.items():
                # Compare sprites to find matching card
                if base_sprite.size == card_sprite.size:
                    # Get the card face for this card
                    card_face = self.card_manager.card_faces.get(card_name)
                    if card_face:
                        break
            
            # If we couldn't find a proper card face, create one from the sprite
            if card_face is None:
                card_face = card_sprite.copy()
            
            # Apply modifiers using the existing system
            modified_sprite = self.modifier_manager.apply_modifiers_to_card(card_sprite, card_face)
            
            return modified_sprite
            
        except Exception as e:
            print(f"Warning: Could not apply modifiers to preview: {e}")
            import traceback
            traceback.print_exc()
            return card_sprite  # Return original if modifier application fails
    
    def _get_modifier_status_text(self):
        """Get text description of currently selected modifiers"""
        try:
            selected_modifiers = self.modifier_manager.get_selected_modifiers()
            if not selected_modifiers:
                return ""
            
            # Modifier name mappings for display
            modifier_display_names = {
                ('enhancement', 5): "Stone",
                ('enhancement', 6): "Gold", 
                ('enhancement', 8): "Bonus",
                ('enhancement', 9): "Mult",
                ('enhancement', 10): "Wild",
                ('enhancement', 11): "Lucky",
                ('enhancement', 12): "Glass",
                ('enhancement', 13): "Steel",
                ('seal', 2): "Gold Seal",
                ('seal', 32): "Purple Seal",
                ('seal', 33): "Red Seal", 
                ('seal', 34): "Blue Seal",
                ('edition', 1): "Foil",
                ('edition', 2): "Holographic",
                ('edition', 3): "Polychrome",
                ('debuff', 4): "Disabled"
            }
            
            modifier_names = []
            for modifier_category, modifier_idx in selected_modifiers:
                modifier_key = (modifier_category, modifier_idx)
                if modifier_key in modifier_display_names:
                    modifier_names.append(modifier_display_names[modifier_key])
            
            if modifier_names:
                return f"\n+ {', '.join(modifier_names)}"
            else:
                return ""
                
        except Exception as e:
            print(f"Warning: Could not get modifier status: {e}")
            return ""
    
    def _show_existing_card_without_modifiers(self, card_class, labeled_card_name):
        """Show an existing labeled card without applying current modifiers"""
        try:
            from PIL import Image, ImageTk
            card_order = self.card_order_config['playing_cards_order']['sprite_sheet_mapping']['order']
            
            # Find the sprite index for this card class
            for i, sprite_idx in enumerate(card_order):
                if sprite_idx == card_class:
                    # Get the base card sprite without current modifiers
                    card_sprite = self.sprite_loader.get_sprite('Playing Cards (High Contrast)', sprite_idx, composite_back=True)
                    if card_sprite:
                        # Resize for display (same logic as regular display)
                        max_width = 150
                        max_height = 200
                        
                        img_width, img_height = card_sprite.size
                        aspect_ratio = img_width / img_height
                        
                        if img_width > max_width or img_height > max_height:
                            scale_w = max_width / img_width
                            scale_h = max_height / img_height
                            scale = min(scale_w, scale_h)
                            
                            target_width = int(img_width * scale)
                            target_height = int(img_height * scale)
                        else:
                            target_width = img_width
                            target_height = img_height
                        
                        card_sprite = card_sprite.resize((target_width, target_height), Image.Resampling.LANCZOS)
                        
                        # Convert to PhotoImage and display
                        card_photo = ImageTk.PhotoImage(card_sprite)
                        
                        self.ui.matched_card_canvas.delete("all")
                        canvas_center_x = 75
                        canvas_center_y = 100
                        
                        self.ui.matched_card_canvas.create_image(
                            canvas_center_x, canvas_center_y, 
                            image=card_photo, anchor=tk.CENTER
                        )
                        
                        self.ui.matched_card_canvas.image = card_photo
                        
                        # Show status without current modifiers
                        self.ui.match_status.configure(text=f"{labeled_card_name}\nStatus: Already Labeled")
                    break
                    
        except Exception as e:
            print(f"Error showing existing card: {e}")
            # Fallback to text display
            self.ui.matched_card_canvas.create_text(75, 100, text=labeled_card_name, 
                                                   fill='#4caf50', font=('Arial', 9, 'bold'))
            self.ui.match_status.configure(text="Status: Already Labeled")
    
    def _save_modifier_labels(self, card_path, card_name):
        """Save card to modifier-specific folders if modifiers are applied"""
        try:
            # Get currently selected modifiers
            selected_modifiers = self.modifier_manager.get_selected_modifiers()
            if not selected_modifiers:
                return  # No modifiers applied
            
            import shutil
            
            # Modifier name mappings from card_order_config.json
            modifier_name_mappings = {
                # Enhancements
                ('enhancement', 5): "stone_enhancement",
                ('enhancement', 6): "gold_enhancement", 
                ('enhancement', 8): "bonus_enhancement",
                ('enhancement', 9): "mult_enhancement",
                ('enhancement', 10): "wild_enhancement",
                ('enhancement', 11): "lucky_enhancement",
                ('enhancement', 12): "glass_enhancement",
                ('enhancement', 13): "steel_enhancement",
                # Seals
                ('seal', 2): "gold_seal",
                ('seal', 32): "purple_seal",
                ('seal', 33): "red_seal", 
                ('seal', 34): "blue_seal",
                # Editions
                ('edition', 1): "foil_edition",
                ('edition', 2): "holographic_edition",
                ('edition', 3): "polychrome_edition",
                # Debuff (treated as edition)
                ('debuff', 4): "disabled_edition"
            }
            
            for modifier_category, modifier_idx in selected_modifiers:
                modifier_key = (modifier_category, modifier_idx)
                
                if modifier_key in modifier_name_mappings:
                    modifier_name = modifier_name_mappings[modifier_key]
                    
                    # Map categories to folder names
                    if modifier_category in ['enhancement']:
                        folder_category = "enhancements"
                    elif modifier_category in ['seal']:
                        folder_category = "seals"
                    elif modifier_category in ['edition', 'debuff']:
                        folder_category = "editions"
                    else:
                        continue
                    
                    # Create modifier directory
                    modifier_dir = Path(f"training_data/processed/modifiers/{folder_category}/{modifier_name}")
                    modifier_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save image to modifier folder
                    modifier_path = modifier_dir / f"{card_path.stem}.png"
                    shutil.copy2(card_path, modifier_path)
                    
                    print(f"✓ Modifier saved: {modifier_name} -> {modifier_path}")
                    
        except Exception as e:
            print(f"Warning: Could not save modifier labels: {e}")
    
    def _save_label_to_category(self, category_folder, category_name):
        """Save current card to a specific category folder"""
        if not self.labeling_cards or self.current_labeling_index >= len(self.labeling_cards):
            return
            
        try:
            card_path = self.labeling_cards[self.current_labeling_index]
            
            # Create category directory
            category_dir = Path("training_data/processed") / category_folder
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy the image to the category directory
            output_path = category_dir / f"{card_path.stem}.png"
            
            import shutil
            shutil.copy2(card_path, output_path)
            
            print(f"✓ Saved to: {output_path}")
            print(f"✓ Card labeled as: {category_name} -> {output_path}")
            
            # Update the matched card display
            self._show_category_in_matched_display(category_name)
            
            # Auto-advance to next card
            if self.current_labeling_index < len(self.labeling_cards) - 1:
                self.current_labeling_index += 1
                self._load_current_labeling_card()
            else:
                print("✓ All cards labeled!")
                
        except Exception as e:
            print(f"Error saving label: {e}")
            messagebox.showerror("Error", f"Could not save label: {e}")
    
    def _show_category_in_matched_display(self, category_name):
        """Show category label in the matched card display"""
        try:
            self.ui.matched_card_canvas.delete("all")
            
            # Show category name with appropriate styling
            if category_name == "Not a Card":
                color = '#f44336'  # Red
            elif category_name == "Card Backs":
                color = '#2196f3'  # Blue
            elif category_name == "Booster Packs":
                color = '#ff9800'  # Orange
            elif category_name == "Consumables":
                color = '#9c27b0'  # Purple
            elif category_name == "Jokers":
                color = '#4caf50'  # Green
            else:
                color = '#cccccc'  # Gray
            
            self.ui.matched_card_canvas.create_text(75, 100, text=category_name.upper(), 
                                                   fill=color, font=('Arial', 10, 'bold'))
            self.ui.match_status.configure(text=f"Status: Confirmed")
            
        except Exception as e:
            print(f"Error showing category in matched display: {e}")
    
    def _restore_matched_card_display(self):
        """Restore matched card display after window operations"""
        if self.matched_card_sprite and hasattr(self.ui, 'matched_card_canvas'):
            try:
                # Recreate PhotoImage from stored PIL image
                card_photo = ImageTk.PhotoImage(self.matched_card_sprite)
                
                # Clear canvas and redraw image
                self.ui.matched_card_canvas.delete("all")
                self.ui.matched_card_canvas.create_image(
                    75, 100, image=card_photo, anchor=tk.CENTER
                )
                
                # Store reference
                self.ui.matched_card_canvas.image = card_photo
                
            except Exception as e:
                print(f"Error restoring matched card display: {e}")
                # If restore fails, regenerate the display
                if self.matched_card_info and 'card_class' in self.matched_card_info:
                    self._update_matched_card_display(
                        self.matched_card_info['card_class'], 
                        self.matched_card_info['status']
                    )
    
    def _show_bottom_buttons(self):
        """Show the bottom button row"""
        if hasattr(self.ui, 'button_frame'):
            self.ui.button_frame.grid()
    
    def _hide_bottom_buttons(self):
        """Hide the bottom button row"""
        if hasattr(self.ui, 'button_frame'):
            self.ui.button_frame.grid_remove()
    
    def _load_suits_for_labeling(self):
        """Load and display suit symbols for data labeling mode"""
        if 'suits' not in self.card_order_config:
            return
        
        suits_config = self.card_order_config['suits']
        sprite_sheet_name = suits_config['sprite_sheet']
        
        # Load suit sprites
        try:
            # Try to load from assets
            from PIL import Image
            import os
            
            sprite_path = None
            for assets_dir in ['assets', 'resources/textures/1x']:
                test_path = os.path.join(assets_dir, sprite_sheet_name)
                if os.path.exists(test_path):
                    sprite_path = test_path
                    break
            
            if not sprite_path:
                print(f"Warning: Could not find suit sprite sheet: {sprite_sheet_name}")
                return
            
            # Load and split sprite sheet
            sprite_img = Image.open(sprite_path).convert('RGBA')
            img_width, img_height = sprite_img.size
            
            # 1x4 grid - 1 column, 4 rows (vertically stacked)
            suit_width = img_width // 1
            suit_height = img_height // 4
            
            # Extract each suit sprite
            suit_order = suits_config['order']  # ["S", "H", "C", "D"]
            suit_indices = suits_config['indices']  # [3, 0, 1, 2]
            
            for i, (suit_name, sprite_idx) in enumerate(zip(suit_order, suit_indices)):
                # Extract sprite (vertically stacked)
                left = 0
                top = sprite_idx * suit_height
                right = left + suit_width
                bottom = top + suit_height
                
                suit_sprite = sprite_img.crop((left, top, right, bottom))
                
                # Resize to match card height
                suit_sprite = suit_sprite.resize((self.card_display_width, self.card_display_height), Image.Resampling.LANCZOS)
                
                self.suit_sprites[suit_name] = suit_sprite
            
            # Display suits on canvas
            self._display_suits()
            
        except Exception as e:
            print(f"Warning: Could not load suit sprites: {e}")
    
    def _display_suits(self):
        """Display suit symbols on the suits canvas with proper card-like spacing"""
        if not self.suit_sprites:
            return
        
        # Clear existing suits
        self.ui.suits_canvas.delete("all")
        self.suit_img_ids = []
        
        # Calculate canvas size to match playing cards layout
        # 4 suits in a vertical column, same spacing as playing cards
        canvas_width = self.card_display_width + 10
        canvas_height = 4 * self.card_display_height + 3 * self.card_spacing + 10
        
        self.ui.suits_canvas.configure(width=canvas_width, height=canvas_height)
        
        # Display each suit with same spacing as playing cards
        suit_order = self.card_order_config['suits']['order']  # ["S", "H", "C", "D"]
        
        for i, suit_name in enumerate(suit_order):
            if suit_name in self.suit_sprites:
                suit_sprite = self.suit_sprites[suit_name]
                
                # Convert to PhotoImage
                from PIL import ImageTk
                suit_photo = ImageTk.PhotoImage(suit_sprite)
                
                # Calculate position with same spacing as cards
                x = 5  # Small margin from left
                y = i * (self.card_display_height + self.card_spacing) + 5  # Same spacing as cards
                
                # Create image on canvas
                img_id = self.ui.suits_canvas.create_image(x, y, anchor=tk.NW, image=suit_photo)
                
                # Store reference to prevent garbage collection
                self.suit_img_ids.append({
                    'id': img_id,
                    'photo': suit_photo,
                    'suit': suit_name
                })
                
                # Bind click event for suit selection
                self.ui.suits_canvas.tag_bind(img_id, '<Button-1>', 
                                            lambda e, suit=suit_name: self._on_suit_click(suit))
                self.ui.suits_canvas.tag_bind(img_id, '<Enter>', 
                                            lambda e: self.ui.suits_canvas.configure(cursor='hand2'))
                self.ui.suits_canvas.tag_bind(img_id, '<Leave>', 
                                            lambda e: self.ui.suits_canvas.configure(cursor=''))
    
    def _on_suit_click(self, suit_name):
        """Handle suit click for 'Suit Only' labeling"""
        current_mode = self.ui.app_mode.get()
        if current_mode != "Data Labeling":
            return
        
        if not self.labeling_cards or self.current_labeling_index >= len(self.labeling_cards):
            messagebox.showwarning("No Card", "No card loaded for labeling")
            return
        
        # Set as suit only with specific suit
        self.selected_card_class = f"suit_only_{suit_name.lower()}"
        
        suit_names = {"S": "Spades", "H": "Hearts", "C": "Clubs", "D": "Diamonds"}
        suit_display = suit_names.get(suit_name, suit_name)
        
        # Update matched card display
        self._update_matched_card_display(self.selected_card_class, "selected")
        
        print(f"Selected: {suit_display} Suit Only")
    
    def _on_mode_change(self, event=None):
        """Handle mode change between Manual Tracking and Data Labeling"""
        current_mode = self.ui.app_mode.get()
        
        # Update title and buttons
        self.ui.update_title_for_mode(current_mode)
        self.ui.update_buttons_for_mode(current_mode)
        
        # Allow window to grow naturally without size constraints
        # The UI will adapt to whatever size the user sets
        
        if current_mode == "Manual Tracking":
            # Show order list, hide labeling area and suits
            if hasattr(self.ui, 'labeling_frame'):
                self.ui.labeling_frame.grid_remove()
            self.ui.order_frame.grid()
            # Show order label in manual tracking mode
            self.ui.order_label.grid()
            # Show bottom buttons for manual tracking
            self._show_bottom_buttons()
            # Hide suits canvas and center cards
            self.ui.suits_canvas.grid_remove()
            self.ui.card_grid_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))  # Move to column 0 (centered)
            # Make column 0 expandable when suits are hidden
            self.ui.card_area_frame.columnconfigure(0, weight=1)
            self.ui.card_area_frame.columnconfigure(1, weight=0)
            
            # Unbind keyboard shortcuts
            self.root.unbind('<KeyPress-c>')
            self.root.unbind('<KeyPress-C>')
            self.root.unbind('<KeyPress-x>')
            self.root.unbind('<KeyPress-X>')
            self.root.unbind('<KeyPress-q>')
            self.root.unbind('<KeyPress-Q>')
            self.root.unbind('<KeyPress-e>')
            self.root.unbind('<KeyPress-E>')
            self.root.unbind('<BackSpace>')
        elif current_mode == "Data Labeling":
            # Hide order list, show labeling area
            self.ui.order_frame.grid_remove()
            if not hasattr(self.ui, 'labeling_frame'):
                # Create labeling area if it doesn't exist
                parent = self.ui.order_frame.master
                self.ui.labeling_frame = self.ui.setup_labeling_area(parent)
                
                # Setup labeling button handlers
                self.ui.prev_card_btn.configure(command=self._on_prev_labeling_card)
                self.ui.next_card_btn.configure(command=self._on_next_labeling_card)
                self.ui.skip_card_btn.configure(command=self._on_skip_labeling_card)
                self.ui.not_card_btn.configure(command=self._on_label_not_card)
                self.ui.save_label_btn.configure(command=self._save_current_label)
                self.ui.load_cards_btn.configure(command=self._load_cards_for_labeling)
                
                # Additional label category handlers
                self.ui.card_backs_btn.configure(command=self._on_label_card_backs)
                self.ui.booster_packs_btn.configure(command=self._on_label_booster_packs)
                self.ui.consumables_btn.configure(command=self._on_label_consumables)
                self.ui.jokers_btn.configure(command=self._on_label_jokers)

                
                # Bind keyboard shortcuts for data labeling
                self.root.bind('<KeyPress-c>', lambda e: self._save_current_label())
                self.root.bind('<KeyPress-C>', lambda e: self._save_current_label())
                self.root.bind('<KeyPress-x>', lambda e: self._on_skip_labeling_card())
                self.root.bind('<KeyPress-X>', lambda e: self._on_skip_labeling_card())
                self.root.bind('<KeyPress-q>', lambda e: self._on_prev_labeling_card())
                self.root.bind('<KeyPress-Q>', lambda e: self._on_prev_labeling_card())
                self.root.bind('<KeyPress-e>', lambda e: self._on_next_labeling_card())
                self.root.bind('<KeyPress-E>', lambda e: self._on_next_labeling_card())

                self.root.bind('<BackSpace>', lambda e: self._on_label_not_card())
            
            self.ui.labeling_frame.grid(row=4, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
            
            # Hide order label in data labeling mode (title moved to left column)
            self.ui.order_label.grid_remove()
            
            # Hide bottom buttons in data labeling mode (functionality moved to labeling area)
            self._hide_bottom_buttons()
            
            # Load and display suits for data labeling
            self._load_suits_for_labeling()
            # Show suits canvas in data labeling mode
            self.ui.suits_canvas.grid(row=0, column=0, padx=(0, 10))
            self.ui.card_grid_canvas.grid(row=0, column=1, sticky=(tk.W, tk.E))  # Move back to column 1
            # Reset column weights for side-by-side layout
            self.ui.card_area_frame.columnconfigure(0, weight=0)
            self.ui.card_area_frame.columnconfigure(1, weight=1)
    
    def _on_capture_hand(self):
        """Capture and recognize cards from game screen OR load cards for labeling"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            self._capture_hand_for_tracking()
        elif current_mode == "Data Labeling":
            self._load_cards_for_labeling()
    
    def _capture_hand_for_tracking(self):
        """Capture and recognize cards for manual tracking"""
        try:
            from tkinter import filedialog
            
            filepath = filedialog.askopenfilename(
                title="Select Balatro Screenshot",
                filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            # Load the image
            screenshot = self.screen_capture.capture_from_file(filepath)
            
            # Extract card region
            card_region = self.screen_capture.get_card_region(screenshot)
            
            if card_region is None:
                messagebox.showerror("Error", "Could not extract card region from image")
                return
            
            # Recognize cards
            recognized_cards = self.card_recognizer.recognize_hand(card_region)
            
            if not recognized_cards:
                messagebox.showinfo("No Cards Found", "No cards were detected in the image")
                return
            
            # Add recognized cards to order
            for card_info in recognized_cards:
                card_idx = card_info['index']
                
                # Get the card sprite
                if card_idx < len(self.card_manager.base_card_sprites):
                    card_names = list(self.card_manager.base_card_sprites.keys())
                    if card_idx < len(card_names):
                        card_name = card_names[card_idx]
                        
                        # Get sprites
                        base_sprite = self.card_manager.base_card_sprites[card_name]
                        card_face = self.card_manager.card_faces.get(card_name)
                        
                        # Apply modifiers (if detected)
                        final_sprite = self.modifier_manager.apply_modifiers_to_card(base_sprite, card_face)
                        modifiers_applied = self.modifier_manager.get_selected_modifiers()
                        
                        # Add to order
                        self.card_manager.add_card_to_order(card_name, final_sprite, modifiers_applied)
            
            messagebox.showinfo("Success", f"Added {len(recognized_cards)} cards to order")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture hand: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_cards_for_labeling(self):
        """Load cards for data labeling"""
        from tkinter import filedialog
        
        directory = filedialog.askdirectory(
            title="Select directory with card images to label",
            initialdir="training_data/raw_cards"
        )
        
        if not directory:
            return
        
        # Load card images
        directory = Path(directory)
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(directory.glob(ext))
        
        # Filter out preview/processed files
        image_files = [f for f in image_files if 'preview' not in f.name.lower() 
                      and 'comparison' not in f.name.lower()
                      and 'region' not in f.name.lower()]
        
        if not image_files:
            messagebox.showwarning("No Cards", f"No card images found in {directory}")
            return
        
        self.labeling_cards = sorted(image_files)
        self.current_labeling_index = 0
        
        # Enable navigation buttons
        self.ui.prev_card_btn.configure(state=tk.NORMAL)
        self.ui.next_card_btn.configure(state=tk.NORMAL)
        self.ui.skip_card_btn.configure(state=tk.NORMAL)
        self.ui.not_card_btn.configure(state=tk.NORMAL)
        self.ui.save_label_btn.configure(state=tk.NORMAL)
        
        # Enable additional label category buttons
        self.ui.card_backs_btn.configure(state=tk.NORMAL)
        self.ui.booster_packs_btn.configure(state=tk.NORMAL)
        self.ui.consumables_btn.configure(state=tk.NORMAL)
        self.ui.jokers_btn.configure(state=tk.NORMAL)

        
        # Load first card
        self._load_current_labeling_card()
        
        # Update UI to show loaded status (no popup)
        print(f"Loaded {len(self.labeling_cards)} cards for labeling")
    
    def _get_card_label_status(self, card_path):
        """Check if card is already labeled and return status and card name"""
        try:
            # Check if there's a corresponding labeled file in processed directories
            processed_base = Path("training_data/processed")
            
            # Look for the card in all class directories
            for class_dir in processed_base.glob("cards/*/"):
                if class_dir.is_dir():
                    # Check for files with matching stem
                    card_stem = card_path.stem
                    for labeled_file in class_dir.glob(f"{card_stem}*"):
                        if labeled_file.is_file():
                            # Get class number from directory name
                            class_num = int(class_dir.name)
                            # Convert class number to card name
                            card_name = self._class_to_card_name(class_num)
                            return True, card_name
            
            # Check suit_only directories
            for suit_dir in processed_base.glob("suit_only_*/"):
                if suit_dir.is_dir():
                    card_stem = card_path.stem
                    for labeled_file in suit_dir.glob(f"{card_stem}*"):
                        if labeled_file.is_file():
                            suit_name = suit_dir.name.replace("suit_only_", "").title()
                            return True, f"Suit Only ({suit_name})"
            
            # Check additional category directories
            categories = ["card_backs", "booster_packs", "consumables", "jokers", "not_card"]
            category_names = {"card_backs": "Card Backs", "booster_packs": "Booster Packs", 
                            "consumables": "Consumables", "jokers": "Jokers", "not_card": "Not a Card"}
            
            for category in categories:
                category_dir = processed_base / category
                if category_dir.exists():
                    card_stem = card_path.stem
                    for labeled_file in category_dir.glob(f"{card_stem}*"):
                        if labeled_file.is_file():
                            return True, category_names[category]
            
            return False, ""
            
        except Exception as e:
            print(f"Error checking label status: {e}")
            return False, ""
    
    def _class_to_card_name(self, class_num):
        """Convert class number to readable card name"""
        try:
            # Class mapping: 0-12 Hearts, 13-25 Clubs, 26-38 Diamonds, 39-51 Spades
            suits = ["Hearts", "Clubs", "Diamonds", "Spades"]
            ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]
            
            suit_idx = class_num // 13
            rank_idx = class_num % 13
            
            if 0 <= suit_idx < len(suits) and 0 <= rank_idx < len(ranks):
                return f"{ranks[rank_idx]} of {suits[suit_idx]}"
            else:
                return f"Class {class_num}"
        except:
            return f"Class {class_num}"

    def _load_current_labeling_card(self):
        """Load the current card for labeling"""
        if not self.labeling_cards or self.current_labeling_index >= len(self.labeling_cards):
            return
        
        card_path = self.labeling_cards[self.current_labeling_index]
        
        try:
            import cv2
            from PIL import ImageTk
            
            # Load image
            image = cv2.imread(str(card_path))
            if image is None:
                raise ValueError("Could not load image")
            
            # Show full image for labeling (model trains on full image)
            display_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            view_description = "Full image shown (model trains on full image)"
            
            # Convert to PIL for display
            from PIL import Image
            full_pil = Image.fromarray(display_rgb)
            
            # Calculate available space for image more accurately
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Get actual heights of UI elements
            try:
                # Force UI update to get accurate measurements
                self.root.update_idletasks()
                
                # Calculate used vertical space more accurately
                title_height = 180  # Title and mode selector area
                modifiers_height = self.ui.modifiers_canvas.winfo_reqheight() + 20  # Modifiers + padding
                cards_height = self.ui.card_grid_canvas.winfo_reqheight() + 20  # Cards + padding
                labeling_controls_height = 80  # Space for navigation buttons and padding
                
                used_height = title_height + modifiers_height + cards_height + labeling_controls_height
                available_height = max(window_height - used_height, 150)  # Minimum 150px
                
                # Allow larger images - use more of the available space
                max_width = int(window_width * 0.4)  # 40% of window width, no upper limit
                max_height = available_height  # Use full available height
                
            except:
                # Fallback to reasonable estimates if measurement fails
                max_width = 400
                max_height = 300
            
            # Ensure minimum size
            max_width = max(max_width, 150)
            max_height = max(max_height, 150)
            
            img_width, img_height = full_pil.size
            
            # Normalize all images to the same height (target height based on available space)
            target_height = max_height  # Use the calculated available height as target
            
            # Calculate width to maintain aspect ratio
            aspect_ratio = img_width / img_height
            target_width = int(target_height * aspect_ratio)
            
            # Check if target width exceeds max width, if so, scale down proportionally
            if target_width > max_width:
                target_width = max_width
                target_height = int(target_width / aspect_ratio)
            
            # Resize to normalized dimensions
            new_width = target_width
            new_height = target_height
            full_pil = full_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_labeling_image = ImageTk.PhotoImage(full_pil)
            
            # Update display - configure both image and compound to ensure proper display
            self.ui.label_image_display.configure(
                image=self.current_labeling_image, 
                text="",
                compound=tk.CENTER,
                width=new_width,
                height=new_height
            )
            
            # Store reference to prevent garbage collection
            self.ui.label_image_display.image = self.current_labeling_image
            
            # Check if card is already labeled and get label info
            is_labeled, labeled_card_name = self._get_card_label_status(card_path)
            checkmark = "✓ " if is_labeled else ""
            labeled_text = f"Labeled: {labeled_card_name}" if is_labeled else "Labeled: None"
            
            # Update filename display (above image)
            self.ui.filename_display.configure(text=f"{card_path.name} {checkmark}")
            
            # Update info with new format (below image)
            info_text = (f"Card {self.current_labeling_index + 1} of {len(self.labeling_cards)}\n"
                        f"{labeled_text}")
            self.ui.label_info.configure(text=info_text)
            
            # Reset selection and show existing label if available
            self.selected_card_class = None
            if is_labeled:
                self._show_existing_label_in_matched_display(labeled_card_name, card_path)
            else:
                self._clear_matched_card_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load card: {e}")
    
    def _on_prev_labeling_card(self):
        """Go to previous labeling card"""
        if self.current_labeling_index > 0:
            self.current_labeling_index -= 1
            self._load_current_labeling_card()
    
    def _on_next_labeling_card(self):
        """Go to next labeling card"""
        if self.current_labeling_index < len(self.labeling_cards) - 1:
            self.current_labeling_index += 1
            self._load_current_labeling_card()
    
    def _on_label_card_backs(self):
        """Label current card as card backs"""
        self._save_label_to_category("card_backs", "Card Backs")
    
    def _on_label_booster_packs(self):
        """Label current card as booster packs"""
        self._save_label_to_category("booster_packs", "Booster Packs")
    
    def _on_label_consumables(self):
        """Label current card as consumables"""
        self._save_label_to_category("consumables", "Consumables")
    
    def _on_label_jokers(self):
        """Label current card as jokers"""
        self._save_label_to_category("jokers", "Jokers")
    

    
    def _on_skip_labeling_card(self):
        """Skip current labeling card"""
        self._on_next_labeling_card()
    
    def _on_label_not_card(self):
        """Label current image as 'not a card'"""
        self.selected_card_class = "not_card"
        self._update_matched_card_display("not_card", "selected")
        print("Selected: Not a Card")
    

    
    def _on_window_resize(self, event):
        """Handle window resize with debounce"""
        if event.widget != self.root:
            return
        
        # Cancel previous resize timer if it exists
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        
        # Schedule recalculation with debounce
        self._resize_timer = self.root.after(50, self._handle_resize_debounced)
    
    def _handle_resize_debounced(self):
        """Handle resize after debounce delay"""
        self._recalculate_positions()
        
        # Update labeling image size if in data labeling mode
        current_mode = self.ui.app_mode.get()
        if current_mode == "Data Labeling" and hasattr(self, 'labeling_cards') and self.labeling_cards:
            # Delay to ensure UI has updated
            self.root.after(100, self._reload_current_image_size)
            # Restore matched card display if it disappeared
            self.root.after(150, self._restore_matched_card_display)
    
    def _reload_current_image_size(self):
        """Reload current labeling image with updated size"""
        if (hasattr(self, 'labeling_cards') and self.labeling_cards and 
            self.current_labeling_index < len(self.labeling_cards)):
            # Force UI to update geometry
            self.root.update_idletasks()
            self._load_current_labeling_card()
    
    def _recalculate_positions(self):
        """Recalculate all positions"""
        self.layout_manager.recalculate_card_positions(
            self.card_manager.card_positions,
            self.card_manager.card_img_ids
        )
        self.layout_manager.recalculate_modifier_positions(
            self.modifier_manager.modifier_positions,
            self.modifier_manager.modifier_img_ids,
            self.modifier_manager.modifier_types,
            self.modifier_manager.modifier_display_widths
        )
        
        # Recalculate suit positions if in data labeling mode
        current_mode = self.ui.app_mode.get()
        if current_mode == "Data Labeling" and hasattr(self, 'suit_img_ids'):
            self._recalculate_suit_positions()
    
    def _recalculate_suit_positions(self):
        """Recalculate suit positions to maintain proper spacing"""
        if not self.suit_img_ids:
            return
        
        # Update positions for each suit
        for i, suit_data in enumerate(self.suit_img_ids):
            x = 5  # Small margin from left
            y = i * (self.card_display_height + self.card_spacing) + 5
            
            # Update position on canvas
            self.ui.suits_canvas.coords(suit_data['id'], x, y)
    
    # Utility Methods
    
    def _setup_data_labeling(self):
        """Initialize data labeling functionality"""
        self.labeling_cards = []
        self.current_labeling_index = 0
        self.current_labeling_image = None
        self.selected_card_class = None
        
    def _load_config(self):
        """Load card order configuration"""
        config_path = Path("config/card_order_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load card order config: {e}")
        return None


def main():
    root = tk.Tk()
    app = BalatroTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
