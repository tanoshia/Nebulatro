#!/usr/bin/env python3
"""
Ground Truth Manager - Handles ground truth annotation workflow

This manager creates a secondary window for screenshot annotation that works
alongside the main Nebulatro interface for card and modifier selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Callable
from PIL import Image, ImageTk


class GroundTruthAnnotationWindow:
    """Secondary window for ground truth annotation of Balatro screenshots."""
    
    def __init__(self, parent_app, card_selection_callback: Callable, modifier_callback: Callable):
        """Initialize the ground truth annotation window.
        
        Args:
            parent_app: Reference to main Nebulatro app
            card_selection_callback: Callback to get selected card from main app
            modifier_callback: Callback to get selected modifiers from main app
        """
        self.parent_app = parent_app
        self.card_selection_callback = card_selection_callback
        self.modifier_callback = modifier_callback
        
        # Create secondary window
        self.window = tk.Toplevel()
        self.window.title("Ground Truth Annotation - Balatro Screenshots")
        self.window.geometry("1000x700")
        self.window.configure(bg='#2b2b2b')
        
        # State
        self.current_image = None
        self.current_image_path = None
        self.current_image_tk = None
        self.annotations = {"cards": [], "jokers": []}
        self.current_mode = "cards"  # "cards" or "jokers"
        self.drawing = False
        self.start_point = None
        self.temp_bbox = None
        self.canvas_scale = 1.0
        self.pending_bbox = None
        
        # Card mapping
        self.ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.suits = ["hearts", "clubs", "diamonds", "spades"]
        
        # Create card class lookup
        self.card_class_lookup = {}
        for suit_idx, suit in enumerate(self.suits):
            for rank_idx, rank in enumerate(self.ranks):
                card_class = suit_idx * 13 + rank_idx
                self.card_class_lookup[f"{rank}_{suit}"] = card_class
        
        self.setup_ui()
        
        # Handle window closing
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Set up the annotation window UI."""
        # Main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File controls
        file_frame = ttk.LabelFrame(controls_frame, text="File Operations")
        file_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(file_frame, text="Load Screenshot", command=self.load_screenshot).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Save Annotations", command=self.save_annotations).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Clear All", command=self.clear_annotations).pack(side=tk.LEFT, padx=5)
        
        # Mode controls
        mode_frame = ttk.LabelFrame(controls_frame, text="Annotation Mode")
        mode_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.mode_var = tk.StringVar(value="cards")
        ttk.Radiobutton(mode_frame, text="Cards", variable=self.mode_var, 
                       value="cards", command=self.change_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Jokers", variable=self.mode_var, 
                       value="jokers", command=self.change_mode).pack(side=tk.LEFT, padx=5)
        
        # Stats and instructions
        info_frame = ttk.LabelFrame(controls_frame, text="Status")
        info_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stats_label = ttk.Label(info_frame, text="Cards: 0, Jokers: 0")
        self.stats_label.pack(padx=5)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(controls_frame, text="Instructions")
        instructions_frame.pack(side=tk.LEFT)
        
        instructions_text = \"\"\"1. Load Balatro screenshot
2. Select Cards or Jokers mode
3. Draw bounding box (click & drag)
4. Use main Nebulatro window to select card/modifiers
5. Click 'Confirm Selection' below\"\"\"
        
        ttk.Label(instructions_frame, text=instructions_text, font=('Arial', 8)).pack(padx=5, pady=2)
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Screenshot canvas with scrollbars
        canvas_frame = ttk.LabelFrame(content_frame, text="Balatro Screenshot")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Canvas container
        canvas_container = ttk.Frame(canvas_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas with scrollbars
        self.canvas = tk.Canvas(canvas_container, bg='#1e1e1e')
        h_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Right side - Selection confirmation
        selection_frame = ttk.LabelFrame(content_frame, text="Selection Confirmation")
        selection_frame.pack(side=tk.RIGHT, fill=tk.Y)
        selection_frame.configure(width=250)
        
        # Current selection display
        current_frame = ttk.LabelFrame(selection_frame, text="Current Selection")
        current_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.selection_label = ttk.Label(current_frame, text="No selection", 
                                       font=('Arial', 10, 'bold'))
        self.selection_label.pack(pady=5)
        
        self.modifiers_label = ttk.Label(current_frame, text="No modifiers", 
                                       font=('Arial', 9))
        self.modifiers_label.pack(pady=2)
        
        # Pending bbox info
        self.bbox_label = ttk.Label(current_frame, text="No bounding box", 
                                  font=('Arial', 8), foreground='gray')
        self.bbox_label.pack(pady=2)
        
        # Action buttons
        action_frame = ttk.Frame(selection_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.confirm_btn = ttk.Button(action_frame, text="Confirm Selection", 
                                    command=self.confirm_selection, state=tk.DISABLED)
        self.confirm_btn.pack(fill=tk.X, pady=2)
        
        self.refresh_btn = ttk.Button(action_frame, text="Refresh from Main App", 
                                    command=self.refresh_selection)
        self.refresh_btn.pack(fill=tk.X, pady=2)
        
        # Joker name entry (for joker mode)
        joker_frame = ttk.LabelFrame(selection_frame, text="Joker Name (Joker Mode)")
        joker_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.joker_name_var = tk.StringVar()
        self.joker_entry = ttk.Entry(joker_frame, textvariable=self.joker_name_var)
        self.joker_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Bottom status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready - Load a screenshot to begin", 
                                    font=('Arial', 9))
        self.status_label.pack()
        
        # Start with refresh to show current selection
        self.refresh_selection()
    
    def load_screenshot(self):
        """Load a Balatro screenshot for annotation."""
        file_path = filedialog.askopenfilename(
            title="Select Balatro Screenshot",
            filetypes=[("PNG files", "*.png"), ("JPG files", "*.jpg"), ("All files", "*.*")],
            initialdir="dataset/raw"
        )
        
        if file_path:
            self.load_image_from_path(Path(file_path))
    
    def load_image_from_path(self, image_path: Path):
        """Load image from specified path."""
        try:
            # Load with OpenCV for processing
            self.current_image = cv2.imread(str(image_path))
            if self.current_image is None:
                messagebox.showerror("Error", f"Failed to load image: {image_path}")
                return
            
            self.current_image_path = image_path
            
            # Convert for Tkinter display
            image_rgb = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            
            # Scale image to fit canvas if too large
            max_width, max_height = 800, 500
            if pil_image.width > max_width or pil_image.height > max_height:
                pil_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                self.canvas_scale = min(max_width / self.current_image.shape[1], 
                                      max_height / self.current_image.shape[0])
            else:
                self.canvas_scale = 1.0
            
            self.current_image_tk = ImageTk.PhotoImage(pil_image)
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_tk)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Clear previous annotations
            self.annotations = {"cards": [], "jokers": []}
            self.update_stats()
            
            # Check for existing ground truth
            gt_path = Path("dataset/ground_truth") / f"{image_path.stem}.json"
            if gt_path.exists():
                response = messagebox.askyesno("Existing Annotations", 
                                             f"Ground truth exists for {image_path.name}. Load existing annotations?")
                if response:
                    self.load_existing_annotations(gt_path)
            
            self.status_label.config(text=f"Loaded: {image_path.name} (Scale: {self.canvas_scale:.2f})")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def on_canvas_click(self, event):
        """Handle canvas click to start drawing bounding box."""
        self.drawing = True
        self.start_point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self.temp_bbox = None
    
    def on_canvas_drag(self, event):
        """Handle canvas drag to update bounding box."""
        if self.drawing and self.start_point:
            current_point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            
            # Remove previous temp bbox
            if self.temp_bbox:
                self.canvas.delete(self.temp_bbox)
            
            # Draw new temp bbox
            color = "green" if self.current_mode == "cards" else "blue"
            self.temp_bbox = self.canvas.create_rectangle(
                self.start_point[0], self.start_point[1],
                current_point[0], current_point[1],
                outline=color, width=2, dash=(5, 5)
            )
    
    def on_canvas_release(self, event):
        """Handle canvas release to finalize bounding box."""
        if self.drawing and self.start_point:
            self.drawing = False
            end_point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            
            # Calculate bbox in image coordinates
            x1, y1 = self.start_point
            x2, y2 = end_point
            
            # Normalize coordinates
            bbox_x = int(min(x1, x2) / self.canvas_scale)
            bbox_y = int(min(y1, y2) / self.canvas_scale)
            bbox_w = int(abs(x2 - x1) / self.canvas_scale)
            bbox_h = int(abs(y2 - y1) / self.canvas_scale)
            
            if bbox_w > 10 and bbox_h > 10:  # Minimum size
                self.pending_bbox = {"x": bbox_x, "y": bbox_y, "width": bbox_w, "height": bbox_h}
                self.bbox_label.config(text=f"Bbox: {bbox_w}×{bbox_h} at ({bbox_x},{bbox_y})")
                self.confirm_btn.config(state=tk.NORMAL)
                
                # Update status
                mode_text = "card" if self.current_mode == "cards" else "joker"
                self.status_label.config(text=f"Bounding box ready - Select {mode_text} in main app, then confirm")
            else:
                self.bbox_label.config(text="Bounding box too small")
                self.confirm_btn.config(state=tk.DISABLED)
            
            # Clean up temp bbox
            if self.temp_bbox:
                self.canvas.delete(self.temp_bbox)
                self.temp_bbox = None
    
    def refresh_selection(self):
        """Refresh the current selection from the main app."""
        try:
            # Get current selection from main app
            if self.current_mode == "cards":
                # Get selected card from main app
                selected_card = self.card_selection_callback()
                modifiers = self.modifier_callback()
                
                if selected_card:
                    card_class, rank, suit = selected_card
                    self.selection_label.config(text=f"{rank} of {suit} (Class {card_class})")
                else:
                    self.selection_label.config(text="No card selected")
                
                # Format modifiers
                if modifiers and any(modifiers.values()):
                    mod_text = []
                    for mod_type, mod_value in modifiers.items():
                        if mod_value:
                            if mod_type == 'debuff' and mod_value:
                                mod_text.append("Debuffed")
                            elif mod_value != True:  # Skip boolean True values except debuff
                                mod_text.append(f"{mod_type.title()}: {mod_value}")
                    
                    self.modifiers_label.config(text=", ".join(mod_text) if mod_text else "No modifiers")
                else:
                    self.modifiers_label.config(text="No modifiers")
            
            else:  # jokers mode
                joker_name = self.joker_name_var.get().strip()
                if joker_name:
                    self.selection_label.config(text=f"Joker: {joker_name}")
                else:
                    self.selection_label.config(text="Enter joker name above")
                
                # Get edition modifier for jokers
                modifiers = self.modifier_callback()
                edition = modifiers.get('edition') if modifiers else None
                debuff = modifiers.get('debuff', False) if modifiers else False
                
                mod_text = []
                if edition:
                    mod_text.append(f"Edition: {edition}")
                if debuff:
                    mod_text.append("Debuffed")
                
                self.modifiers_label.config(text=", ".join(mod_text) if mod_text else "No modifiers")
                
        except Exception as e:
            self.selection_label.config(text="Error getting selection")
            self.modifiers_label.config(text=str(e))
    
    def confirm_selection(self):
        """Confirm the current selection and add annotation."""
        if not self.pending_bbox:
            messagebox.showwarning("No Bounding Box", "Please draw a bounding box first.")
            return
        
        try:
            if self.current_mode == "cards":
                # Get card selection
                selected_card = self.card_selection_callback()
                if not selected_card:
                    messagebox.showwarning("No Card Selected", "Please select a card in the main Nebulatro window.")
                    return
                
                card_class, rank, suit = selected_card
                modifiers = self.modifier_callback()
                
                # Create card annotation
                card_annotation = {
                    "bbox": self.pending_bbox,
                    "rank": rank,
                    "suit": suit,
                    "card_class": card_class,
                    "modifiers": {
                        "enhancement": modifiers.get('enhancement'),
                        "edition": modifiers.get('edition'),
                        "seal": modifiers.get('seal'),
                        "debuff": modifiers.get('debuff', False)
                    },
                    "visibility": "full",
                    "confidence": "certain"
                }
                
                self.annotations["cards"].append(card_annotation)
                
                # Draw permanent bbox on canvas
                self.draw_annotation_bbox(self.pending_bbox, "green", f"{rank}{suit[0].upper()}")
                
                self.status_label.config(text=f"Added card: {rank} of {suit}")
            
            else:  # jokers mode
                joker_name = self.joker_name_var.get().strip()
                if not joker_name:
                    messagebox.showwarning("No Joker Name", "Please enter a joker name.")
                    return
                
                modifiers = self.modifier_callback()
                
                # Create joker annotation
                joker_annotation = {
                    "bbox": self.pending_bbox,
                    "joker_name": joker_name,
                    "joker_id": joker_name.lower().replace(" ", "_"),
                    "modifiers": {
                        "edition": modifiers.get('edition'),
                        "debuff": modifiers.get('debuff', False)
                    },
                    "visibility": "full",
                    "confidence": "certain"
                }
                
                self.annotations["jokers"].append(joker_annotation)
                
                # Draw permanent bbox on canvas
                self.draw_annotation_bbox(self.pending_bbox, "blue", joker_name[:10])
                
                self.status_label.config(text=f"Added joker: {joker_name}")
                
                # Clear joker name for next annotation
                self.joker_name_var.set("")
            
            # Clear pending bbox
            self.pending_bbox = None
            self.bbox_label.config(text="No bounding box")
            self.confirm_btn.config(state=tk.DISABLED)
            
            self.update_stats()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add annotation: {e}")
    
    def draw_annotation_bbox(self, bbox: Dict, color: str, label: str):
        """Draw annotation bounding box on canvas."""
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        
        # Scale to canvas coordinates
        canvas_x = x * self.canvas_scale
        canvas_y = y * self.canvas_scale
        canvas_w = w * self.canvas_scale
        canvas_h = h * self.canvas_scale
        
        # Draw rectangle
        self.canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x + canvas_w, canvas_y + canvas_h,
            outline=color, width=2
        )
        
        # Draw label
        self.canvas.create_text(
            canvas_x, canvas_y - 5, anchor=tk.SW,
            text=label, fill=color, font=("Arial", 10, "bold")
        )
    
    def change_mode(self):
        """Handle mode change between cards and jokers."""
        self.current_mode = self.mode_var.get()
        
        # Clear any pending bbox
        self.pending_bbox = None
        self.bbox_label.config(text="No bounding box")
        self.confirm_btn.config(state=tk.DISABLED)
        
        if self.temp_bbox:
            self.canvas.delete(self.temp_bbox)
            self.temp_bbox = None
        
        # Refresh selection for new mode
        self.refresh_selection()
        
        mode_text = "cards" if self.current_mode == "cards" else "jokers"
        self.status_label.config(text=f"Switched to {mode_text} mode")
    
    def update_stats(self):
        """Update statistics display."""
        card_count = len(self.annotations["cards"])
        joker_count = len(self.annotations["jokers"])
        self.stats_label.config(text=f"Cards: {card_count}, Jokers: {joker_count}")
    
    def clear_annotations(self):
        """Clear all annotations."""
        if messagebox.askyesno("Clear Annotations", "Are you sure you want to clear all annotations?"):
            self.annotations = {"cards": [], "jokers": []}
            
            # Redraw image without annotations
            if self.current_image_tk:
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_tk)
            
            self.update_stats()
            self.status_label.config(text="Cleared all annotations")
    
    def save_annotations(self):
        """Save annotations to ground truth file."""
        if not self.current_image_path or (not self.annotations["cards"] and not self.annotations["jokers"]):
            messagebox.showwarning("No Data", "No image loaded or no annotations to save.")
            return
        
        try:
            # Create ground truth structure
            height, width = self.current_image.shape[:2]
            
            # Calculate regions
            data_region = {"x": 0, "y": 0, "width": int(width * 0.25), "height": height}
            jokers_region = {"x": int(width * 0.25), "y": 0, "width": int(width * 0.75), "height": int(height * 0.30)}
            cards_region = {"x": int(width * 0.25), "y": int(height * 0.30), "width": int(width * 0.75), "height": int(height * 0.70)}
            
            ground_truth = {
                "image_id": self.current_image_path.stem,
                "image_info": {
                    "width": width,
                    "height": height,
                    "file_path": str(self.current_image_path),
                    "resolution_category": self.get_resolution_category(width, height)
                },
                "regions": {
                    "data_region": data_region,
                    "jokers_region": jokers_region,
                    "cards_region": cards_region
                },
                "cards": self.annotations["cards"],
                "jokers": self.annotations["jokers"],
                "metadata": {
                    "annotated_by": "nebulatro_ground_truth",
                    "annotation_date": datetime.now().isoformat(),
                    "game_state": "play",
                    "difficulty_level": "medium",
                    "notes": ""
                }
            }
            
            # Save to file
            output_path = Path("dataset/ground_truth") / f"{self.current_image_path.stem}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with output_path.open("w") as f:
                json.dump(ground_truth, f, indent=2)
            
            messagebox.showinfo("Success", f"Ground truth saved to:\n{output_path}")
            self.status_label.config(text=f"Saved ground truth: {output_path.name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save annotations: {e}")
    
    def get_resolution_category(self, width: int, height: int) -> str:
        """Categorize image resolution."""
        if width >= 3840:
            return "4K"
        elif width >= 2560:
            return "1440p"
        elif width >= 1920:
            return "1080p"
        else:
            return "other"
    
    def load_existing_annotations(self, gt_path: Path):
        """Load existing ground truth annotations."""
        try:
            with gt_path.open() as f:
                ground_truth = json.load(f)
            
            self.annotations = {
                "cards": ground_truth.get("cards", []),
                "jokers": ground_truth.get("jokers", [])
            }
            
            # Draw existing annotations
            for card in self.annotations["cards"]:
                label = f"{card['rank']}{card['suit'][0].upper()}"
                self.draw_annotation_bbox(card["bbox"], "green", label)
            
            for joker in self.annotations["jokers"]:
                label = joker["joker_name"][:10]
                self.draw_annotation_bbox(joker["bbox"], "blue", label)
            
            self.update_stats()
            self.status_label.config(text=f"Loaded existing annotations: {len(self.annotations['cards'])} cards, {len(self.annotations['jokers'])} jokers")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load existing annotations: {e}")
    
    def on_closing(self):
        """Handle window closing."""
        if self.annotations["cards"] or self.annotations["jokers"]:
            if messagebox.askyesno("Unsaved Changes", "You have unsaved annotations. Close anyway?"):
                self.window.destroy()
        else:
            self.window.destroy()


class GroundTruthManager:
    """Manages ground truth annotation workflow integration with main app."""
    
    def __init__(self, parent_app):
        """Initialize ground truth manager.
        
        Args:
            parent_app: Reference to main Nebulatro application
        """
        self.parent_app = parent_app
        self.annotation_window = None
    
    def open_ground_truth_window(self):
        """Open the ground truth annotation window."""
        if self.annotation_window and self.annotation_window.window.winfo_exists():
            # Window already exists, bring to front
            self.annotation_window.window.lift()
            self.annotation_window.window.focus_force()
            return
        
        # Create new annotation window
        self.annotation_window = GroundTruthAnnotationWindow(
            self.parent_app,
            self.get_selected_card,
            self.get_selected_modifiers
        )
    
    def get_selected_card(self) -> Optional[Tuple[int, str, str]]:
        """Get the currently selected card from the main app.
        
        Returns:
            Tuple of (card_class, rank, suit) or None if no selection
        """
        try:
            # Check if we have a selected card class from labeling manager
            if hasattr(self.parent_app, 'labeling_manager') and self.parent_app.labeling_manager.selected_card_class is not None:
                card_class = self.parent_app.labeling_manager.selected_card_class
                
                # Convert card class to rank and suit
                suit_idx = card_class // 13
                rank_idx = card_class % 13
                
                suits = ["hearts", "clubs", "diamonds", "spades"]
                ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
                
                if 0 <= suit_idx < len(suits) and 0 <= rank_idx < len(ranks):
                    return (card_class, ranks[rank_idx], suits[suit_idx])
            
            return None
            
        except Exception as e:
            print(f"Error getting selected card: {e}")
            return None
    
    def get_selected_modifiers(self) -> Dict[str, any]:
        """Get the currently selected modifiers from the main app.
        
        Returns:
            Dictionary of selected modifiers
        """
        try:
            if hasattr(self.parent_app, 'modifier_manager'):
                return self.parent_app.modifier_manager.get_selected_modifiers()
            return {}
            
        except Exception as e:
            print(f"Error getting selected modifiers: {e}")
            return {}