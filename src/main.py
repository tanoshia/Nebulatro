#!/usr/bin/env python3
"""
Nebulatro - Balatro Card Order Tracker
Main application orchestrator (cleaned up version)
"""

import tkinter as tk
from tkinter import messagebox
import json
from pathlib import Path
from PIL import Image

from src.utils import SpriteLoader
from src.ui import UIComponents, LayoutManager
from src.managers import CardManager, ModifierManager, DesignManager
from src.managers.labeling_manager import LabelingManager
from src.managers.card_display_manager import CardDisplayManager
from src.managers.mode_manager import ModeManager
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
        
        # Load configuration
        self._load_config()
        
        # Initialize components
        self._setup_ui()
        self._setup_managers()
        self._setup_layout()
        
        # Set up event handlers
        self._setup_event_handlers()
        
        # Initialize display
        self._initialize_display()
    
    def _load_config(self):
        """Load configuration from JSON files"""
        try:
            with open('config/card_order_config.json', 'r') as f:
                self.card_order_config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load card order config: {e}")
            self.card_order_config = {}
    
    def _setup_ui(self):
        """Initialize UI components"""
        self.ui = UIComponents(self.root, self.bg_color, self.canvas_bg)
        self.ui.set_app_icon()
        
        # Setup main layout
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
    
    def _setup_managers(self):
        """Initialize all manager components"""
        # Sprite loader
        self.sprite_loader = SpriteLoader()
        
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
        self.modifier_manager.set_layout_callback(lambda: self._on_window_resize())
        
        # Design manager
        self.design_manager = DesignManager(
            self.root,
            self.sprite_loader,
            self.bg_color,
            self.ui.card_contrast,
            self.ui.face_card_collabs
        )
        self.design_manager.set_design_change_handler(self._on_design_change)
        
        # Card display manager
        self.card_display_manager = CardDisplayManager(
            self.ui, 
            self.card_manager, 
            self.modifier_manager, 
            self.card_order_config
        )
        
        # Labeling manager (needs card_display_manager)
        self.labeling_manager = LabelingManager(self.ui, self.modifier_manager, self.card_display_manager)
        
        # Mode manager
        self.mode_manager = ModeManager(
            self.ui, 
            self.card_manager, 
            self.labeling_manager, 
            self.card_display_manager,
            self.card_order_config,
            self.sprite_loader
        )
    
    def _setup_layout(self):
        """Initialize layout manager"""
        self.layout_manager = LayoutManager(
            self.ui.card_grid_canvas,
            self.ui.modifiers_canvas,
            self.card_display_width,
            self.card_display_height,
            self.card_spacing
        )
    
    def _setup_event_handlers(self):
        """Setup all event handlers and mode switching"""
        # Initialize in manual tracking mode
        self.mode_manager.switch_mode("Manual Tracking")
    
    def _initialize_display(self):
        """Initialize the display with cards and modifiers"""
        try:
            # Load and display cards
            self.card_manager.load_cards()
            
            # Load and display modifiers
            self.modifier_manager.load_modifiers()
            
            # Setup window resizing with proper callbacks
            self.root.bind('<Configure>', self._on_window_resize)
            
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Could not initialize display: {e}")
    
    # Event Handlers
    def _on_card_click(self, card_name, card_class):
        """Handle card click events"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            # Get the base sprite and apply modifiers
            if card_name in self.card_manager.base_card_sprites:
                base_sprite = self.card_manager.base_card_sprites[card_name]
                card_face = self.card_manager.card_faces.get(card_name)
                final_sprite = self.modifier_manager.apply_modifiers_to_card(base_sprite, card_face)
                modifiers_applied = self.modifier_manager.get_selected_modifiers()
                
                # Add card to order with sprite and modifiers
                self.card_manager.add_card_to_order(card_name, final_sprite, modifiers_applied)
        elif current_mode == "Data Labeling":
            # Check if annotation window has pending bounding box
            if (hasattr(self.labeling_manager, 'annotation_window_manager') and 
                self.labeling_manager.annotation_window_manager.is_annotation_window_active() and
                self.labeling_manager.annotation_window_manager.state_manager.pending_bbox):
                # Complete annotation with selected card
                success = self.labeling_manager.annotation_window_manager.handle_card_selection(card_class)
                if success:
                    self.card_display_manager.update_matched_card_display(card_class, "confirmed")
                else:
                    messagebox.showerror("Error", "Failed to complete annotation")
            else:
                # Set selected card for labeling (existing behavior)
                self.labeling_manager.selected_card_class = card_class
                self.card_display_manager.update_matched_card_display(card_class, "selected")
    
    def _on_modifier_change(self):
        """Handle modifier selection changes"""
        # Refresh card display to show modifier changes
        self.card_manager.refresh_card_display(self.modifier_manager)
    
    def _on_design_change(self):
        """Handle design changes (contrast, face cards)"""
        # Reload cards with new design settings
        self.card_manager.load_cards(
            use_high_contrast=(self.ui.card_contrast.get() == "High Contrast"),
            design_manager=self.design_manager
        )
    
    def _on_window_resize(self, event=None):
        """Handle window resize events"""
        if event and event.widget != self.root:
            return  # Only handle root window resize
        
        # Update card spacing based on new window size
        if hasattr(self.card_manager, 'card_positions') and self.card_manager.card_positions:
            self.layout_manager.recalculate_card_positions(
                self.card_manager.card_positions,
                self.card_manager.card_img_ids
            )
        
        # Update modifier spacing
        if hasattr(self.modifier_manager, 'modifier_positions') and self.modifier_manager.modifier_positions:
            self.layout_manager.recalculate_modifier_positions(
                self.modifier_manager.modifier_positions,
                self.modifier_manager.modifier_img_ids,
                self.modifier_manager.modifier_types,
                self.modifier_manager.modifier_display_widths
            )
        
        # Restore matched card display if needed
        self.card_display_manager.restore_matched_card_display()
    
    def _on_modifier_filter_change(self, event=None):
        """Handle modifier filter changes"""
        self.modifier_manager.load_modifiers(self.ui.modifier_filter.get())
    
    def _on_card_design_click(self):
        """Handle card design popup"""
        self.design_manager.open_design_popup()
    
    def _on_clear(self):
        """Handle clear order"""
        self.card_manager.clear_order()
    
    def _on_undo(self):
        """Handle undo last card"""
        self.card_manager.undo_last()
    
    def _on_save(self):
        """Handle save order"""
        self.card_manager.save_order()
    
    def _on_capture_hand(self):
        """Handle capture hand / load cards based on mode"""
        current_mode = self.ui.app_mode.get()
        
        if current_mode == "Manual Tracking":
            # Capture hand functionality
            try:
                if not hasattr(self, 'screen_capture'):
                    self.screen_capture = ScreenCapture()
                if not hasattr(self, 'card_recognizer'):
                    self.card_recognizer = CardRecognizer()
                
                # Capture and recognize cards
                screenshot = self.screen_capture.capture_screen()
                if screenshot:
                    recognized_cards = self.card_recognizer.recognize_cards_in_image(screenshot)
                    for card_name in recognized_cards:
                        self.card_manager.add_card_to_order(card_name)
                        
            except Exception as e:
                messagebox.showerror("Capture Error", f"Could not capture hand: {e}")
        
        elif current_mode == "Data Labeling":
            # Load cards for labeling
            self.labeling_manager.load_cards_for_labeling()
    
    def _on_mode_change(self, event=None):
        """Handle mode switching"""
        current_mode = self.ui.app_mode.get()
        
        # Close annotation window if switching away from Data Labeling mode
        if (current_mode != "Data Labeling" and 
            hasattr(self.labeling_manager, '_annotation_window_manager') and
            self.labeling_manager._annotation_window_manager is not None):
            self.labeling_manager.annotation_window_manager.close_annotation_window()
        
        self.mode_manager.switch_mode(current_mode)
    

    



def main():
    """Main entry point"""
    root = tk.Tk()
    app = BalatroTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()