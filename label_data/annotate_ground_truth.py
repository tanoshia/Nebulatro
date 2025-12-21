#!/usr/bin/env python3
"""
Ground Truth Annotation Tool - GUI Integration

Interactive tool for creating ground truth annotations for Balatro screenshots.
Integrates with the main Nebulatro GUI for efficient card and modifier selection.
"""

import sys
import cv2
import numpy as np
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageTk

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

class GroundTruthGUI:
    """GUI-based ground truth annotation tool using Nebulatro components."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Nebulatro - Ground Truth Annotation")
        self.root.geometry("1400x900")
        
        # Import Nebulatro components
        try:
            from managers.card_manager import CardManager
            from managers.modifier_manager import ModifierManager
            from utils.sprite_loader import SpriteLoader
            
            self.sprite_loader = SpriteLoader()
            self.card_manager = CardManager(None, self.sprite_loader)  # No main app reference needed
            self.modifier_manager = ModifierManager(None, self.sprite_loader)
            
        except ImportError as e:
            messagebox.showerror("Import Error", f"Failed to import Nebulatro components: {e}")
            sys.exit(1)
        
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
        
    def setup_ui(self):
        """Set up the GUI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File controls
        file_frame = ttk.LabelFrame(controls_frame, text="File Operations")
        file_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(file_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=5)
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
        
        # Stats
        stats_frame = ttk.LabelFrame(controls_frame, text="Statistics")
        stats_frame.pack(side=tk.LEFT)
        
        self.stats_label = ttk.Label(stats_frame, text="Cards: 0, Jokers: 0")
        self.stats_label.pack(padx=5)
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Image canvas
        image_frame = ttk.LabelFrame(content_frame, text="Screenshot")
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Canvas with scrollbars
        canvas_frame = ttk.Frame(image_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg='gray')
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Right side - Nebulatro card selection
        selection_frame = ttk.LabelFrame(content_frame, text="Card Selection")
        selection_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 0))
        selection_frame.configure(width=400)
        
        # Create card selection area using Nebulatro components
        self.setup_card_selection(selection_frame)
        
        # Bottom - Current annotation details
        details_frame = ttk.LabelFrame(main_frame, text="Current Annotation")
        details_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.details_text = tk.Text(details_frame, height=4, wrap=tk.WORD)
        details_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scroll.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Instructions
        instructions = """Instructions:
1. Load a Balatro screenshot using 'Load Image'
2. Select annotation mode (Cards or Jokers)
3. Draw bounding boxes by clicking and dragging on the image
4. Click the corresponding card in the selection area (right panel)
5. Apply modifiers if needed using the modifier controls
6. Save annotations when complete"""
        
        self.details_text.insert(tk.END, instructions)
        self.details_text.configure(state=tk.DISABLED)
    
    def setup_card_selection(self, parent):
        """Set up the card selection area using Nebulatro components."""
        # Modifier controls (simplified from main app)
        modifier_frame = ttk.LabelFrame(parent, text="Modifiers")
        modifier_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Enhancement selection
        enh_frame = ttk.Frame(modifier_frame)
        enh_frame.pack(fill=tk.X, pady=2)
        ttk.Label(enh_frame, text="Enhancement:").pack(side=tk.LEFT)
        
        self.enhancement_var = tk.StringVar()
        enhancement_combo = ttk.Combobox(enh_frame, textvariable=self.enhancement_var, width=15)
        enhancement_combo['values'] = ['None', 'bonus', 'mult', 'wild', 'glass', 'steel', 'stone', 'gold', 'lucky']
        enhancement_combo.set('None')
        enhancement_combo.pack(side=tk.RIGHT)
        
        # Edition selection
        ed_frame = ttk.Frame(modifier_frame)
        ed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ed_frame, text="Edition:").pack(side=tk.LEFT)
        
        self.edition_var = tk.StringVar()
        edition_combo = ttk.Combobox(ed_frame, textvariable=self.edition_var, width=15)
        edition_combo['values'] = ['None', 'foil', 'holographic', 'polychrome']
        edition_combo.set('None')
        edition_combo.pack(side=tk.RIGHT)
        
        # Seal selection
        seal_frame = ttk.Frame(modifier_frame)
        seal_frame.pack(fill=tk.X, pady=2)
        ttk.Label(seal_frame, text="Seal:").pack(side=tk.LEFT)
        
        self.seal_var = tk.StringVar()
        seal_combo = ttk.Combobox(seal_frame, textvariable=self.seal_var, width=15)
        seal_combo['values'] = ['None', 'gold', 'red', 'blue', 'purple']
        seal_combo.set('None')
        seal_combo.pack(side=tk.RIGHT)
        
        # Debuff checkbox
        self.debuff_var = tk.BooleanVar()
        ttk.Checkbutton(modifier_frame, text="Debuffed", variable=self.debuff_var).pack(pady=2)
        
        # Card grid (simplified version)
        cards_frame = ttk.LabelFrame(parent, text="Playing Cards")
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create card buttons in a grid
        self.card_buttons = {}
        self.setup_card_grid(cards_frame)
        
        # Joker input (for joker mode)
        joker_frame = ttk.LabelFrame(parent, text="Joker Name")
        joker_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.joker_name_var = tk.StringVar()
        joker_entry = ttk.Entry(joker_frame, textvariable=self.joker_name_var, width=30)
        joker_entry.pack(padx=5, pady=5)
        
        ttk.Button(joker_frame, text="Add Joker", command=self.add_joker_annotation).pack(pady=5)
    
    def setup_card_grid(self, parent):
        """Create a simplified card grid."""
        # Create a scrollable frame for cards
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create card buttons by suit
        for suit_idx, suit in enumerate(self.suits):
            suit_frame = ttk.LabelFrame(scrollable_frame, text=suit.title())
            suit_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Create buttons for each rank
            rank_frame = ttk.Frame(suit_frame)
            rank_frame.pack(fill=tk.X, padx=5, pady=5)
            
            for rank_idx, rank in enumerate(self.ranks):
                card_class = suit_idx * 13 + rank_idx
                button_text = f"{rank}{suit[0].upper()}"
                
                btn = ttk.Button(rank_frame, text=button_text, width=4,
                               command=lambda cc=card_class, r=rank, s=suit: self.select_card(cc, r, s))
                btn.pack(side=tk.LEFT, padx=1)
                
                self.card_buttons[card_class] = btn
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def load_image(self):
        """Load an image for annotation."""
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
            max_width, max_height = 800, 600
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
                outline=color, width=2
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
                
                if self.current_mode == "cards":
                    self.show_card_selection_prompt()
                else:
                    self.show_joker_selection_prompt()
            
            # Clean up temp bbox
            if self.temp_bbox:
                self.canvas.delete(self.temp_bbox)
                self.temp_bbox = None
    
    def show_card_selection_prompt(self):
        """Show prompt to select card for the drawn bounding box."""
        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"Bounding box drawn at ({self.pending_bbox['x']}, {self.pending_bbox['y']}, {self.pending_bbox['width']}, {self.pending_bbox['height']})\n\n")
        self.details_text.insert(tk.END, "Please select the corresponding card from the grid on the right, then apply any modifiers if needed.")
        self.details_text.configure(state=tk.DISABLED)
    
    def show_joker_selection_prompt(self):
        """Show prompt to enter joker name for the drawn bounding box."""
        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"Bounding box drawn at ({self.pending_bbox['x']}, {self.pending_bbox['y']}, {self.pending_bbox['width']}, {self.pending_bbox['height']})\n\n")
        self.details_text.insert(tk.END, "Please enter the joker name in the text field on the right and click 'Add Joker'.")
        self.details_text.configure(state=tk.DISABLED)
    
    def select_card(self, card_class: int, rank: str, suit: str):
        """Handle card selection from the grid."""
        if not hasattr(self, 'pending_bbox'):
            messagebox.showwarning("No Bounding Box", "Please draw a bounding box first.")
            return
        
        # Get modifiers
        enhancement = self.enhancement_var.get() if self.enhancement_var.get() != 'None' else None
        edition = self.edition_var.get() if self.edition_var.get() != 'None' else None
        seal = self.seal_var.get() if self.seal_var.get() != 'None' else None
        debuff = self.debuff_var.get()
        
        # Create card annotation
        card_annotation = {
            "bbox": self.pending_bbox,
            "rank": rank,
            "suit": suit,
            "card_class": card_class,
            "modifiers": {
                "enhancement": enhancement,
                "edition": edition,
                "seal": seal,
                "debuff": debuff
            },
            "visibility": "full",
            "confidence": "certain"
        }
        
        self.annotations["cards"].append(card_annotation)
        
        # Draw permanent bbox on canvas
        self.draw_annotation_bbox(self.pending_bbox, "green", f"{rank}{suit[0].upper()}")
        
        # Clear pending bbox
        delattr(self, 'pending_bbox')
        
        # Reset modifiers
        self.enhancement_var.set('None')
        self.edition_var.set('None')
        self.seal_var.set('None')
        self.debuff_var.set(False)
        
        self.update_stats()
        
        # Update details
        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"Added card: {rank} of {suit} (class {card_class})\n")
        if enhancement or edition or seal or debuff:
            self.details_text.insert(tk.END, f"Modifiers: {enhancement or ''} {edition or ''} {seal or ''} {'debuff' if debuff else ''}")
        self.details_text.configure(state=tk.DISABLED)
    
    def add_joker_annotation(self):
        """Add joker annotation."""
        if not hasattr(self, 'pending_bbox'):
            messagebox.showwarning("No Bounding Box", "Please draw a bounding box first.")
            return
        
        joker_name = self.joker_name_var.get().strip()
        if not joker_name:
            messagebox.showwarning("No Joker Name", "Please enter a joker name.")
            return
        
        # Get modifiers
        edition = self.edition_var.get() if self.edition_var.get() != 'None' else None
        debuff = self.debuff_var.get()
        
        # Create joker annotation
        joker_annotation = {
            "bbox": self.pending_bbox,
            "joker_name": joker_name,
            "joker_id": joker_name.lower().replace(" ", "_"),
            "modifiers": {
                "edition": edition,
                "debuff": debuff
            },
            "visibility": "full",
            "confidence": "certain"
        }
        
        self.annotations["jokers"].append(joker_annotation)
        
        # Draw permanent bbox on canvas
        self.draw_annotation_bbox(self.pending_bbox, "blue", joker_name[:10])
        
        # Clear pending bbox and joker name
        delattr(self, 'pending_bbox')
        self.joker_name_var.set("")
        
        # Reset modifiers
        self.edition_var.set('None')
        self.debuff_var.set(False)
        
        self.update_stats()
        
        # Update details
        self.details_text.configure(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, f"Added joker: {joker_name}\n")
        if edition or debuff:
            self.details_text.insert(tk.END, f"Modifiers: {edition or ''} {'debuff' if debuff else ''}")
        self.details_text.configure(state=tk.DISABLED)
    
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
        if hasattr(self, 'pending_bbox'):
            delattr(self, 'pending_bbox')
        
        if self.temp_bbox:
            self.canvas.delete(self.temp_bbox)
            self.temp_bbox = None
    
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
    
    def save_annotations(self):
        """Save annotations to ground truth file."""
        if not self.current_image_path or not self.annotations["cards"] and not self.annotations["jokers"]:
            messagebox.showwarning("No Data", "No image loaded or no annotations to save.")
            return
        
        try:
            # Create ground truth structure (same as before)
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
                    "annotated_by": "gui_annotation",
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
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load existing annotations: {e}")
    
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()

def main():
    """Main entry point."""
    app = GroundTruthGUI()
    app.run()

if __name__ == "__main__":
    main()