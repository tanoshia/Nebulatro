#!/usr/bin/env python3
"""
Labeling Manager - Handles all data labeling functionality for ML training
"""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import cv2
from PIL import Image, ImageTk


class LabelingManager:
    """Manages data labeling workflow and operations"""
    
    def __init__(self, ui, modifier_manager, card_display_manager=None):
        self.ui = ui
        self.modifier_manager = modifier_manager
        self.card_display_manager = card_display_manager
        
        # Labeling state
        self.labeling_cards = []
        self.current_labeling_index = 0
        self.selected_card_class = None
        self.current_labeling_image = None
        
        # Annotation window manager (lazy initialization)
        self._annotation_window_manager = None
    
    @property
    def annotation_window_manager(self):
        """Get the annotation window manager, creating it if needed."""
        if self._annotation_window_manager is None:
            from .annotation_window_manager import AnnotationWindowManager
            self._annotation_window_manager = AnnotationWindowManager(self)
        return self._annotation_window_manager
        
    def load_cards_for_labeling(self):
        """Load screenshot for annotation in secondary window"""
        from tkinter import filedialog
        
<<<<<<< Updated upstream
        # Ask user to select directory containing cards to label
        cards_dir = filedialog.askdirectory(
            title="Select directory containing cards to label",
            initialdir="training_data/debug_cards"
=======
        # Ask user to select a screenshot for annotation
        screenshot_path = filedialog.askopenfilename(
            title="Select Balatro screenshot for annotation",
            initialdir="dataset/raw",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPG files", "*.jpg"),
                ("JPEG files", "*.jpeg"),
                ("All image files", "*.png *.jpg *.jpeg")
            ]
>>>>>>> Stashed changes
        )
        
        if not screenshot_path:
            return
        
        # Spawn annotation window with the selected screenshot
        success = self.annotation_window_manager.spawn_annotation_window(screenshot_path)
        
        if success:
            # Update UI to indicate annotation mode is active
            if hasattr(self.ui, 'status_label'):
                self.ui.status_label.config(text="Annotation window opened - Draw bounding boxes and select cards")
        else:
            messagebox.showerror("Error", "Failed to open annotation window")
        
        # Enable additional label category buttons
        self.ui.card_backs_btn.configure(state=tk.NORMAL)
        self.ui.booster_packs_btn.configure(state=tk.NORMAL)
        self.ui.consumables_btn.configure(state=tk.NORMAL)
        self.ui.jokers_btn.configure(state=tk.NORMAL)
        
        # Load first card
        self.load_current_card()
        
        print(f"Loaded {len(self.labeling_cards)} cards for labeling")
    
    def load_current_card(self):
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
            window_width = self.ui.root.winfo_width()
            window_height = self.ui.root.winfo_height()
            
            # Get actual heights of UI elements
            try:
                # Force UI update to get accurate measurements
                self.ui.root.update_idletasks()
                
                # Calculate used vertical space more accurately
                title_height = 120  # Title and mode selector area
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
            is_labeled, labeled_card_name = self.get_card_label_status(card_path)
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
                self.show_existing_label_in_matched_display(labeled_card_name, card_path)
            else:
                self.clear_matched_card_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load card: {e}")
    
    def get_card_label_status(self, card_path):
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
                            card_name = self.class_to_card_name(class_num)
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
    
    def class_to_card_name(self, class_num):
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
    
    def card_name_to_class(self, card_name):
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
    
    def show_existing_label_in_matched_display(self, labeled_card_name, card_path):
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
                if hasattr(self.ui, 'suit_sprites') and suit_name in self.ui.suit_sprites:
                    from PIL import ImageTk
                    suit_sprite = self.ui.suit_sprites[suit_name]
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
                card_class = self.card_name_to_class(labeled_card_name)
                if card_class is not None:
                    # Use the existing card display system
                    self.update_matched_card_display(card_class, "Already Labeled")
                else:
                    # Fallback for unknown card names
                    self.ui.matched_card_canvas.create_text(75, 100, text=labeled_card_name, 
                                                           fill='#4caf50', font=('Arial', 9, 'bold'))
                    self.ui.match_status.configure(text="Status: Already Labeled")
                    
        except Exception as e:
            print(f"Error showing existing label: {e}")
            self.clear_matched_card_display()
    
    def clear_matched_card_display(self):
        """Clear the matched card display"""
        if self.card_display_manager:
            self.card_display_manager.clear_matched_card_display()
        else:
            # Fallback if no card display manager
            self.ui.matched_card_canvas.delete("all")
            self.ui.matched_card_canvas.create_text(75, 100, text="No selection", 
                                                   fill='#cccccc', font=('Arial', 9))
            self.ui.match_status.configure(text="")
    
    def update_matched_card_display(self, card_class, status="selected"):
        """Update the matched card display to show selected/confirmed card"""
        if self.card_display_manager:
            self.card_display_manager.update_matched_card_display(card_class, status)
        else:
            # Fallback if no card display manager
            self.ui.matched_card_canvas.delete("all")
            self.ui.matched_card_canvas.create_text(75, 100, text=f"Card {card_class}", 
                                                   fill='#4caf50', font=('Arial', 9, 'bold'))
            self.ui.match_status.configure(text=f"Status: {status.title()}")
    
    # Navigation methods
    def on_prev_card(self):
        """Go to previous labeling card"""
        if self.current_labeling_index > 0:
            self.current_labeling_index -= 1
            self.load_current_card()
    
    def on_next_card(self):
        """Go to next labeling card"""
        if self.current_labeling_index < len(self.labeling_cards) - 1:
            self.current_labeling_index += 1
            self.load_current_card()
    
    def on_skip_card(self):
        """Skip current card without labeling"""
        self.on_next_card()
    
    def on_label_not_card(self):
        """Label current card as not a card"""
        self.selected_card_class = "not_card"
        self.save_current_label()
    
    def on_label_card_backs(self):
        """Label current card as card backs"""
        self.save_label_to_category("card_backs", "Card Backs")
    
    def on_label_booster_packs(self):
        """Label current card as booster packs"""
        self.save_label_to_category("booster_packs", "Booster Packs")
    
    def on_label_consumables(self):
        """Label current card as consumables"""
        self.save_label_to_category("consumables", "Consumables")
    
    def on_label_jokers(self):
        """Label current card as jokers"""
        self.save_label_to_category("jokers", "Jokers")
    
    def save_current_label(self):
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
                output_path = self.save_special_label(card_path, self.selected_card_class)
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
                from src.tools.label_single_card import save_labeled_card
                output_path = save_labeled_card(card_path, self.selected_card_class)
                label_text = f"Class {self.selected_card_class}"
            
            # Save to modifier folders if modifiers are applied
            modifier_count = self.save_modifier_labels(card_path, label_text)
            
            # Show save status in console (no popup)
            modifier_info = f" (+ {modifier_count} modifier folders)" if modifier_count > 0 else ""
            print(f"✓ Card labeled as: {label_text} -> {output_path}{modifier_info}")
            
            # Update matched card display to show confirmed status
            if self.selected_card_class is not None:
                self.update_matched_card_display(self.selected_card_class, "confirmed")
            
            # Move to next card automatically
            self.on_next_card()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save label: {e}")
            import traceback
            traceback.print_exc()
    
    def save_special_label(self, card_path, label_type):
        """Save card with special label (not_card, suit_only)"""
        try:
            import cv2
            
            # Determine output directory
            if label_type == "not_card":
                special_dir = Path("training_data/processed/not_card")
            elif str(label_type).startswith("suit_only"):
                suit_part = str(label_type).replace("suit_only_", "")
                special_dir = Path(f"training_data/processed/suit_only_{suit_part}")
            else:
                raise ValueError(f"Unknown special label type: {label_type}")
            
            # Create directory
            special_dir.mkdir(parents=True, exist_ok=True)
            
            # Load and save image
            image = cv2.imread(str(card_path))
            h, w = image.shape[:2]
            # Save image
            output_path = special_dir / f"{card_path.stem}.png"
            cv2.imwrite(str(output_path), image)
            
            return output_path
            
        except Exception as e:
            print(f"Error saving special label: {e}")
            raise
    
    def save_label_to_category(self, category_folder, category_name):
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
            self.show_category_in_matched_display(category_name)
            
            # Auto-advance to next card
            if self.current_labeling_index < len(self.labeling_cards) - 1:
                self.current_labeling_index += 1
                self.load_current_card()
            else:
                print("✓ All cards labeled!")
                
        except Exception as e:
            print(f"Error saving label: {e}")
            messagebox.showerror("Error", f"Could not save label: {e}")
    
    def show_category_in_matched_display(self, category_name):
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
    
    def save_modifier_labels(self, card_path, card_name):
        """Save card to modifier-specific folders if modifiers are applied"""
        try:
            # Get currently selected modifiers
            selected_modifiers = self.modifier_manager.get_selected_modifiers()
            if not selected_modifiers:
                return 0  # No modifiers applied
            
            import shutil
            saved_count = 0
            
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
                    saved_count += 1
                    
            return saved_count
                    
        except Exception as e:
            print(f"Warning: Could not save modifier labels: {e}")
            return 0