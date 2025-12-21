#!/usr/bin/env python3
"""
Annotation Window Manager - Handles secondary window lifecycle for ground truth annotation

This manager creates and manages a secondary annotation window that works alongside
the main Nebulatro interface for card and modifier selection during data labeling.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable, Any
from PIL import Image, ImageTk


class AnnotationWindow:
    """Secondary window for screenshot display and bounding box drawing."""
    
    def __init__(self, parent_manager, screenshot_path: str):
        """Initialize the annotation window.
        
        Args:
            parent_manager: Reference to AnnotationWindowManager
            screenshot_path: Path to the screenshot to display
        """
        self.parent_manager = parent_manager
        self.screenshot_path = Path(screenshot_path)
        
        # Create secondary window
        self.window = tk.Toplevel()
        self.window.title(f"Ground Truth Annotation - {self.screenshot_path.name}")
        self.window.geometry("800x600")
        self.window.configure(bg='#2b2b2b')
        
        # State
        self.current_image = None
        self.current_image_pil = None  # Store PIL image for rescaling
        self.current_image_tk = None
        self.canvas_scale = 1.0
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.drawing = False
        self.start_point = None
        self.temp_bbox = None
        self.pending_bbox = None
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        # Setup UI and load image
        self.setup_ui()
        self.load_screenshot()
        
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
        
        # Instructions
        instructions_frame = ttk.LabelFrame(controls_frame, text="Instructions")
        instructions_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        # Determine OS-specific keyboard shortcut text
        if platform.system() == "Darwin":  # macOS
            undo_key_text = "Cmd+Z"
        else:  # Windows, Linux, and others
            undo_key_text = "Ctrl+Z"
        
        instructions_text = f"""1. Draw bounding box (click & drag)
2. Use main Nebulatro window to select card/modifiers
3. Annotation will be saved automatically

Zoom: Mouse wheel, +/- keys, 0 to reset
Pan: Middle mouse button + drag
Cancel: {undo_key_text} to cancel bounding box"""
        
        ttk.Label(instructions_frame, text=instructions_text, font=('Arial', 9)).pack(padx=5, pady=2)
        
        # Status
        status_frame = ttk.LabelFrame(controls_frame, text="Status")
        status_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Ready - Draw bounding box")
        self.status_label.pack(padx=5, pady=2)
        
        # Cancel button
        cancel_frame = ttk.Frame(controls_frame)
        cancel_frame.pack(side=tk.RIGHT)
        
        self.cancel_btn = ttk.Button(cancel_frame, text="Cancel Bounding Box", 
                                   command=self.cancel_current_bbox, state=tk.DISABLED)
        self.cancel_btn.pack(padx=5)
        
        # Screenshot canvas with scrollbars
        canvas_frame = ttk.LabelFrame(main_frame, text="Balatro Screenshot")
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
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
        
        # Enable zoom and pan
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux
        self.canvas.bind("<Button-2>", self.start_pan)  # Middle mouse button
        self.canvas.bind("<B2-Motion>", self.do_pan)
        
        # Keyboard shortcuts for zoom
        self.window.bind("<KeyPress-plus>", self.zoom_in)
        self.window.bind("<KeyPress-equal>", self.zoom_in)  # + key without shift
        self.window.bind("<KeyPress-minus>", self.zoom_out)
        self.window.bind("<KeyPress-0>", self.reset_zoom)
        
        # Keyboard shortcut for canceling bounding box (OS-specific)
        if platform.system() == "Darwin":  # macOS
            self.window.bind("<Command-z>", self.cancel_bbox_shortcut)
            self.undo_key = "Cmd+Z"
        else:  # Windows, Linux, and others
            self.window.bind("<Control-z>", self.cancel_bbox_shortcut)
            self.undo_key = "Ctrl+Z"
        
        # Make canvas focusable for keyboard events
        self.canvas.focus_set()
    
    def load_screenshot(self):
        """Load the screenshot for annotation."""
        try:
            # Load with OpenCV for processing
            self.current_image = cv2.imread(str(self.screenshot_path))
            if self.current_image is None:
                raise ValueError(f"Failed to load image: {self.screenshot_path}")
            
            # Store original image dimensions
            self.original_height, self.original_width = self.current_image.shape[:2]
            
            # Convert for Tkinter display
            image_rgb = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
            self.current_image_pil = Image.fromarray(image_rgb)
            
            # Calculate initial scale to fit canvas while maintaining aspect ratio
            canvas_width = 700
            canvas_height = 400
            
            # Calculate scale factors for width and height
            width_scale = canvas_width / self.current_image_pil.width
            height_scale = canvas_height / self.current_image_pil.height
            
            # Use the smaller scale to ensure image fits entirely
            self.canvas_scale = min(width_scale, height_scale, 1.0)  # Don't scale up initially
            
            # Initialize zoom factor to 1.0 (user zoom is separate from canvas scaling)
            self.zoom_factor = 1.0
            
            # Create initial display image
            self.update_image_display()
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_tk, tags="image")
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update status with image info
            self.status_label.config(text=f"Loaded: {self.screenshot_path.name} ({self.original_width}x{self.original_height}) - Draw bounding box")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load screenshot: {e}")
            self.window.destroy()
    
    def update_image_display(self):
        """Update the image display with current zoom and scale."""
        if self.current_image_pil is None:
            return
        
        # Calculate total scale (canvas scale * zoom factor)
        total_scale = self.canvas_scale * self.zoom_factor
        
        # Calculate new image size
        new_width = int(self.current_image_pil.width * total_scale)
        new_height = int(self.current_image_pil.height * total_scale)
        
        # Resize the image
        if new_width > 0 and new_height > 0:
            resized_image = self.current_image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.current_image_tk = ImageTk.PhotoImage(resized_image)
        else:
            # Fallback for very small sizes
            self.current_image_tk = ImageTk.PhotoImage(self.current_image_pil.resize((1, 1)))
    
    def on_canvas_click(self, event):
        """Handle canvas click to start drawing bounding box."""
        if self.pending_bbox:
            return  # Don't allow new bbox if one is pending
        
        self.drawing = True
        self.start_point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self.temp_bbox = None
    
    def on_canvas_drag(self, event):
        """Handle canvas drag to update bounding box."""
        if self.drawing and self.start_point and not self.pending_bbox:
            current_point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            
            # Remove previous temp bbox
            if self.temp_bbox:
                self.canvas.delete(self.temp_bbox)
            
            # Draw new temp bbox
            self.temp_bbox = self.canvas.create_rectangle(
                self.start_point[0], self.start_point[1],
                current_point[0], current_point[1],
                outline="yellow", width=2, dash=(5, 5)
            )
    
    def on_canvas_release(self, event):
        """Handle canvas release to finalize bounding box."""
        if self.drawing and self.start_point and not self.pending_bbox:
            self.drawing = False
            end_point = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            
            # Calculate bbox in canvas coordinates
            x1, y1 = self.start_point
            x2, y2 = end_point
            
            # Convert to original image coordinates
            # Canvas coordinates -> Original image coordinates
            # First undo zoom, then undo initial canvas scaling
            bbox_x = int(min(x1, x2) / self.zoom_factor / self.canvas_scale)
            bbox_y = int(min(y1, y2) / self.zoom_factor / self.canvas_scale)
            bbox_w = int(abs(x2 - x1) / self.zoom_factor / self.canvas_scale)
            bbox_h = int(abs(y2 - y1) / self.zoom_factor / self.canvas_scale)
            
            # Clamp to image boundaries
            bbox_x = max(0, min(bbox_x, self.original_width))
            bbox_y = max(0, min(bbox_y, self.original_height))
            bbox_w = min(bbox_w, self.original_width - bbox_x)
            bbox_h = min(bbox_h, self.original_height - bbox_y)
            
            # Calculate minimum size based on image dimensions (at least 1% of smaller dimension)
            min_size = min(self.original_width, self.original_height) * 0.01
            min_size = max(min_size, 20)  # At least 20 pixels
            
            if bbox_w > min_size and bbox_h > min_size:
                bbox_data = {"x": bbox_x, "y": bbox_y, "width": bbox_w, "height": bbox_h}
                self.set_pending_bbox(bbox_data)
            else:
                self.status_label.config(text="Bounding box too small - try again")
            
            # Clean up temp bbox
            if self.temp_bbox:
                self.canvas.delete(self.temp_bbox)
                self.temp_bbox = None
    
    def set_pending_bbox(self, bbox_data: Dict):
        """Set a pending bounding box and notify the parent manager."""
        self.pending_bbox = bbox_data
        
        # Draw permanent bbox in canvas coordinates
        x, y, w, h = bbox_data["x"], bbox_data["y"], bbox_data["width"], bbox_data["height"]
        
        # Convert from original image coordinates to current canvas coordinates
        # Original image -> Canvas coordinates (apply canvas scale then zoom)
        canvas_x = x * self.canvas_scale * self.zoom_factor
        canvas_y = y * self.canvas_scale * self.zoom_factor
        canvas_w = w * self.canvas_scale * self.zoom_factor
        canvas_h = h * self.canvas_scale * self.zoom_factor
        
        self.pending_bbox_rect = self.canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x + canvas_w, canvas_y + canvas_h,
            outline="red", width=3, tags="bbox"
        )
        
        # Update UI state
        self.status_label.config(text=f"Bounding box ready ({w}x{h}) - Select card in main window")
        self.cancel_btn.config(state=tk.NORMAL)
        
        # Notify parent manager
        self.parent_manager.set_pending_bbox(bbox_data, self.screenshot_path)
    
    def cancel_current_bbox(self):
        """Cancel the current pending bounding box."""
        if self.pending_bbox:
            # Remove visual bbox
            if hasattr(self, 'pending_bbox_rect'):
                self.canvas.delete(self.pending_bbox_rect)
            
            self.pending_bbox = None
            self.status_label.config(text="Bounding box cancelled - Draw new one")
            self.cancel_btn.config(state=tk.DISABLED)
            
            # Notify parent manager
            self.parent_manager.clear_pending_bbox()
    
    def clear_pending_bbox(self):
        """Clear the pending bounding box (called by parent manager)."""
        if self.pending_bbox:
            # Remove visual bbox
            if hasattr(self, 'pending_bbox_rect'):
                self.canvas.delete(self.pending_bbox_rect)
            
            self.pending_bbox = None
            self.status_label.config(text="Annotation saved - Draw next bounding box")
            self.cancel_btn.config(state=tk.DISABLED)
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming."""
        # Get mouse position relative to canvas
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            zoom_change = 1.1
        else:  # Zoom out
            zoom_change = 0.9
        
        # Calculate new zoom factor
        new_zoom = self.zoom_factor * zoom_change
        
        # Clamp zoom to limits
        if new_zoom < self.min_zoom:
            new_zoom = self.min_zoom
        elif new_zoom > self.max_zoom:
            new_zoom = self.max_zoom
        
        # Only update if zoom actually changed
        if new_zoom != self.zoom_factor:
            # Store old zoom for coordinate adjustment
            old_zoom = self.zoom_factor
            self.zoom_factor = new_zoom
            
            # Update the image display with new zoom
            self.update_image_display()
            
            # Update the image on canvas
            self.canvas.delete("image")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_tk, tags="image")
            
            # Scale existing bounding boxes
            if old_zoom != 0:
                zoom_ratio = new_zoom / old_zoom
                self.canvas.scale("bbox", canvas_x, canvas_y, zoom_ratio, zoom_ratio)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update status
            self.status_label.config(text=f"Zoom: {self.zoom_factor:.1f}x - Draw bounding box")
    
    def start_pan(self, event):
        """Start panning with middle mouse button."""
        self.canvas.scan_mark(event.x, event.y)
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def do_pan(self, event):
        """Pan the canvas."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        
        # Update status to show panning
        delta_x = event.x - self.pan_start_x
        delta_y = event.y - self.pan_start_y
        if abs(delta_x) > 5 or abs(delta_y) > 5:  # Only show if significant movement
            self.status_label.config(text=f"Panning... (Zoom: {self.zoom_factor:.1f}x)")
    
    def zoom_in(self, event=None):
        """Zoom in using keyboard shortcut."""
        try:
            # Create a mock event for the center of the canvas
            mock_event = type('MockEvent', (), {
                'x': self.canvas.winfo_width() // 2,
                'y': self.canvas.winfo_height() // 2,
                'delta': 120,  # Positive for zoom in
                'num': 4
            })()
            self.on_mouse_wheel(mock_event)
        except:
            # Fallback if canvas dimensions not available
            mock_event = type('MockEvent', (), {
                'x': 350, 'y': 200, 'delta': 120, 'num': 4
            })()
            self.on_mouse_wheel(mock_event)
    
    def zoom_out(self, event=None):
        """Zoom out using keyboard shortcut."""
        try:
            # Create a mock event for the center of the canvas
            mock_event = type('MockEvent', (), {
                'x': self.canvas.winfo_width() // 2,
                'y': self.canvas.winfo_height() // 2,
                'delta': -120,  # Negative for zoom out
                'num': 5
            })()
            self.on_mouse_wheel(mock_event)
        except:
            # Fallback if canvas dimensions not available
            mock_event = type('MockEvent', (), {
                'x': 350, 'y': 200, 'delta': -120, 'num': 5
            })()
            self.on_mouse_wheel(mock_event)
    
    def reset_zoom(self, event=None):
        """Reset zoom to fit image in canvas."""
        if self.current_image_pil:
            # Reset zoom factor to 1.0 (initial display scale)
            old_zoom = self.zoom_factor
            self.zoom_factor = 1.0
            
            # Update the image display
            self.update_image_display()
            
            # Update the image on canvas
            self.canvas.delete("image")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image_tk, tags="image")
            
            # Scale existing bounding boxes
            if old_zoom != 0:
                zoom_ratio = 1.0 / old_zoom
                self.canvas.scale("bbox", 0, 0, zoom_ratio, zoom_ratio)
            
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update status
            self.status_label.config(text=f"Reset zoom (fit to canvas) - Draw bounding box")
    
    def cancel_bbox_shortcut(self, event=None):
        """Cancel bounding box using OS-appropriate keyboard shortcut (Cmd+Z on macOS, Ctrl+Z elsewhere)."""
        undo_key = getattr(self, 'undo_key', 'Ctrl+Z')  # Fallback to Ctrl+Z if not set
        
        if self.pending_bbox:
            # Cancel the pending bounding box
            self.cancel_current_bbox()
            self.status_label.config(text=f"Bounding box cancelled ({undo_key}) - Draw new one")
        elif self.drawing and self.temp_bbox:
            # Cancel drawing in progress
            self.drawing = False
            self.start_point = None
            if self.temp_bbox:
                self.canvas.delete(self.temp_bbox)
                self.temp_bbox = None
            self.status_label.config(text=f"Drawing cancelled ({undo_key}) - Draw bounding box")
        else:
            # No bounding box to cancel
            self.status_label.config(text="No bounding box to cancel - Draw bounding box")
    
    def on_closing(self):
        """Handle window closing."""
        # Notify parent manager that window is closing
        self.parent_manager.close_annotation_window()


class AnnotationStateManager:
    """Manages annotation workflow state between windows."""
    
    def __init__(self):
        """Initialize the annotation state manager."""
        self.pending_bbox = None
        self.current_screenshot = None
        self.screenshot_info = None
        self.annotation_window_active = False
        self.last_error = None
    
    def set_pending_annotation(self, bbox: Dict, screenshot_info: Dict) -> None:
        """Set a pending annotation with bounding box and screenshot info."""
        self.pending_bbox = bbox
        self.screenshot_info = screenshot_info
    
    def complete_annotation(self, card_class: int, modifiers: Dict) -> bool:
        """Complete an annotation with card class and modifiers."""
        if not self.pending_bbox or not self.screenshot_info:
            self.last_error = "No pending bounding box or screenshot info"
            return False
        
        try:
            # Create annotation data
            annotation_data = {
                "bbox": self.pending_bbox,
                "card_class": card_class,
                "modifiers": modifiers,
                "screenshot_path": str(self.screenshot_info["path"]),
                "timestamp": self.screenshot_info.get("timestamp"),
                "confidence": "certain",
                "visibility": "full"
            }
            
            # Save annotation (implementation will be added in later tasks)
            success = self.save_ground_truth_data(annotation_data)
            
            if success:
                self.clear_pending_annotation()
                return True
            else:
                return False
                
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def cancel_pending_annotation(self) -> None:
        """Cancel the current pending annotation."""
        self.clear_pending_annotation()
    
    def clear_pending_annotation(self) -> None:
        """Clear the pending annotation state."""
        self.pending_bbox = None
        self.screenshot_info = None
        self.last_error = None
    
    def save_ground_truth_data(self, annotation_data: Dict) -> bool:
        """Save ground truth data (placeholder for now)."""
        # This will be implemented in task 7
        print(f"Ground truth data would be saved: {annotation_data}")
        return True


class AnnotationWindowManager:
    """Manages the lifecycle and communication of the secondary annotation window."""
    
    def __init__(self, labeling_manager):
        """Initialize the annotation window manager.
        
        Args:
            labeling_manager: Reference to the LabelingManager instance
        """
        self.labeling_manager = labeling_manager
        self.annotation_window = None
        self.state_manager = AnnotationStateManager()
    
    def spawn_annotation_window(self, screenshot_path: str) -> bool:
        """Create and display the secondary annotation window.
        
        Args:
            screenshot_path: Path to the screenshot to display
            
        Returns:
            True if window was created successfully, False otherwise
        """
        try:
            # Close existing window if it exists
            if self.annotation_window:
                self.close_annotation_window()
            
            # Validate screenshot path
            if not Path(screenshot_path).exists():
                messagebox.showerror("Error", f"Screenshot not found: {screenshot_path}")
                return False
            
            # Create new annotation window
            self.annotation_window = AnnotationWindow(self, screenshot_path)
            self.state_manager.annotation_window_active = True
            self.state_manager.current_screenshot = screenshot_path
            
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create annotation window: {e}")
            return False
    
    def close_annotation_window(self) -> None:
        """Close the secondary annotation window."""
        if self.annotation_window:
            try:
                self.annotation_window.window.destroy()
            except:
                pass  # Window may already be destroyed
            
            self.annotation_window = None
            self.state_manager.annotation_window_active = False
            self.state_manager.clear_pending_annotation()
    
    def set_pending_bbox(self, bbox: Dict, screenshot_path: Path) -> None:
        """Set a pending bounding box from the annotation window."""
        screenshot_info = {
            "path": screenshot_path,
            "timestamp": None  # Will be set when annotation is completed
        }
        self.state_manager.set_pending_annotation(bbox, screenshot_info)
        
        # Notify main window that card selection is required
        if hasattr(self.labeling_manager, 'ui'):
            # Update UI to indicate card selection is needed
            # This will be enhanced in later tasks
            pass
    
    def clear_pending_bbox(self) -> None:
        """Clear the pending bounding box."""
        self.state_manager.cancel_pending_annotation()
        
        if self.annotation_window:
            self.annotation_window.clear_pending_bbox()
    
    def is_annotation_window_active(self) -> bool:
        """Check if the annotation window is currently active."""
        return (self.annotation_window is not None and 
                self.state_manager.annotation_window_active)
    
    def handle_card_selection(self, card_class: int) -> bool:
        """Handle card selection from the main window when bbox is pending.
        
        Args:
            card_class: The selected card class
            
        Returns:
            True if annotation was completed successfully, False otherwise
        """
        if not self.state_manager.pending_bbox:
            return False
        
        try:
            # Get current modifiers from labeling manager
            modifiers = {}
            if hasattr(self.labeling_manager, 'modifier_manager'):
                selected_modifiers = self.labeling_manager.modifier_manager.get_selected_modifiers()
                # Convert to the format expected by ground truth schema
                modifiers = self._convert_modifiers_format(selected_modifiers)
            
            # Complete the annotation
            success = self.state_manager.complete_annotation(card_class, modifiers)
            
            if success and self.annotation_window:
                self.annotation_window.clear_pending_bbox()
            
            return success
            
        except Exception as e:
            self.state_manager.last_error = str(e)
            return False
    
    def _convert_modifiers_format(self, selected_modifiers: List[Tuple]) -> Dict:
        """Convert modifier format from manager to ground truth schema format."""
        modifiers = {
            "enhancement": None,
            "edition": None,
            "seal": None,
            "debuff": False
        }
        
        # This conversion logic will be refined based on the actual modifier format
        # For now, it's a placeholder
        for modifier_category, modifier_idx in selected_modifiers:
            if modifier_category == "enhancement":
                # Map enhancement indices to names
                enhancement_map = {
                    5: "stone", 6: "gold", 8: "bonus", 9: "mult",
                    10: "wild", 11: "lucky", 12: "glass", 13: "steel"
                }
                modifiers["enhancement"] = enhancement_map.get(modifier_idx)
            elif modifier_category == "edition":
                edition_map = {1: "foil", 2: "holographic", 3: "polychrome"}
                modifiers["edition"] = edition_map.get(modifier_idx)
            elif modifier_category == "seal":
                seal_map = {2: "gold", 32: "purple", 33: "red", 34: "blue"}
                modifiers["seal"] = seal_map.get(modifier_idx)
            elif modifier_category == "debuff":
                modifiers["debuff"] = True
        
        return modifiers