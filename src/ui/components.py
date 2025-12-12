#!/usr/bin/env python3
"""
UI Components - Handles all UI setup and layout for Nebulatro
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path


class UIComponents:
    """Manages UI layout and components"""
    
    def __init__(self, root, bg_color='#2b2b2b', canvas_bg='#1e1e1e'):
        self.root = root
        self.bg_color = bg_color
        self.canvas_bg = canvas_bg
        
        # UI elements (will be set by setup methods)
        self.modifiers_canvas = None
        self.card_grid_canvas = None
        self.order_canvas = None
        self.order_frame = None
        
        # Filter variables
        self.modifier_filter = tk.StringVar(value="All Modifiers")
        self.card_contrast = tk.StringVar(value="Standard")
        self.face_card_collabs = {
            'spades': tk.StringVar(value="Default"),
            'hearts': tk.StringVar(value="Default"),
            'clubs': tk.StringVar(value="Default"),
            'diamonds': tk.StringVar(value="Default")
        }
        
        # Mode selection
        self.app_mode = tk.StringVar(value="Manual Tracking")
    
    def set_app_icon(self):
        """Set application icon"""
        try:
            for icon_file in ["app_icon.icns", "app_icon.png"]:
                icon_path = Path(icon_file)
                if icon_path.exists():
                    icon_img = Image.open(icon_path)
                    if icon_img.size[0] > 256 or icon_img.size[1] > 256:
                        icon_img.thumbnail((256, 256), Image.Resampling.LANCZOS)
                    icon_photo = ImageTk.PhotoImage(icon_img)
                    self.root.iconphoto(True, icon_photo)
                    self.root._icon_photo = icon_photo
                    break
        except Exception as e:
            print(f"Warning: Could not set app icon: {e}")
    
    def setup_main_layout(self, card_display_width, card_display_height, 
                         on_modifier_filter_change, on_card_design_click,
                         on_clear, on_undo, on_save, on_capture=None, on_mode_change=None):
        """Create the main UI layout"""
        # Configure root
        self.root.configure(bg=self.bg_color)
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title and filter row
        self._setup_title_and_filters(main_frame, on_modifier_filter_change, on_card_design_click, on_mode_change)
        
        # Modifiers canvas
        self.modifiers_canvas = tk.Canvas(main_frame, bg=self.bg_color, highlightthickness=0)
        self.modifiers_canvas.grid(row=1, column=0, pady=(0, 5))
        
        # Card area frame (contains suits and playing cards)
        self.card_area_frame = tk.Frame(main_frame, bg=self.bg_color)
        self.card_area_frame.grid(row=2, column=0, pady=10)
        
        # Suits canvas (will be gridded when needed)
        self.suits_canvas = tk.Canvas(self.card_area_frame, bg=self.bg_color, highlightthickness=0)
        
        # Card grid canvas (always visible)
        self.card_grid_canvas = tk.Canvas(self.card_area_frame, bg=self.bg_color, highlightthickness=0)
        self.card_grid_canvas.grid(row=0, column=1, sticky=(tk.W, tk.E))  # Always in column 1
        
        # Configure grid weights so canvas expands
        self.card_area_frame.columnconfigure(1, weight=1)
        
        # Separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Order list
        self._setup_order_list(main_frame)
        
        # Buttons
        self._setup_buttons(main_frame, on_clear, on_undo, on_save, on_capture)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
    
    def update_title_for_mode(self, mode):
        """Update title text based on current mode"""
        if mode == "Manual Tracking":
            self.title_label.configure(text="Click a card to add to sequence")
            self.order_label.configure(text="Card Order:")
        elif mode == "Data Labeling":
            self.title_label.configure(text="Click the matching card to label the image")
            # Data label title is now in the left column of labeling area, not in order_label
    
    def setup_labeling_area(self, parent):
        """Setup the data labeling area with compact layout"""
        # Create labeling frame
        self.labeling_frame = tk.Frame(parent, bg=self.bg_color)
        
        # Main content area with four columns: left controls, center image, matched card, right actions
        content_frame = tk.Frame(self.labeling_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left column - Navigation controls (vertical stack)
        left_frame = tk.Frame(content_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Data to label title (moved to left column)
        self.data_label_title = tk.Label(left_frame, text="Data to label:", 
                                        font=('Arial', 12, 'bold'),
                                        bg=self.bg_color, fg='white')
        self.data_label_title.pack(pady=(0, 10))
        
        # Navigation buttons (vertical, top to bottom)
        self.not_card_btn = ttk.Button(left_frame, text="Not a Card (⌫)", 
                                      state=tk.DISABLED, width=15)
        self.not_card_btn.pack(pady=2)
        
        self.skip_card_btn = ttk.Button(left_frame, text="Skip (X)", 
                                       state=tk.DISABLED, width=15)
        self.skip_card_btn.pack(pady=2)
        
        # Additional label category buttons
        self.card_backs_btn = ttk.Button(left_frame, text="Card Backs", 
                                        state=tk.DISABLED, width=15)
        self.card_backs_btn.pack(pady=2)
        
        self.booster_packs_btn = ttk.Button(left_frame, text="Booster Packs", 
                                           state=tk.DISABLED, width=15)
        self.booster_packs_btn.pack(pady=2)
        
        self.consumables_btn = ttk.Button(left_frame, text="Consumables", 
                                         state=tk.DISABLED, width=15)
        self.consumables_btn.pack(pady=2)
        
        self.jokers_btn = ttk.Button(left_frame, text="Jokers", 
                                    state=tk.DISABLED, width=15)
        self.jokers_btn.pack(pady=2)
        

        
        # Center column - Image display (expandable)
        center_frame = tk.Frame(content_frame, bg=self.bg_color, relief=tk.RAISED, bd=2)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Filename display (above image)
        self.filename_display = tk.Label(center_frame, text="", 
                                        font=('Arial', 10, 'bold'),
                                        bg=self.bg_color, fg='white')
        self.filename_display.pack(pady=(10, 5))
        
        # Image display
        self.label_image_display = tk.Label(center_frame, 
                                           text="No card loaded\n\nClick 'Load Cards' to start labeling", 
                                           font=('Arial', 10),
                                           bg=self.bg_color, fg='#cccccc')
        self.label_image_display.pack(padx=10, pady=(5, 10))
        
        # Card info (below image)
        self.label_info = tk.Label(center_frame, text="", 
                                  font=('Arial', 9),
                                  bg=self.bg_color, fg='#aaaaaa')
        self.label_info.pack(pady=(0, 20))
        
        # Matched card column - Shows selected/confirmed card
        matched_frame = tk.Frame(content_frame, bg=self.bg_color, relief=tk.RAISED, bd=2)
        matched_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=(0, 10))
        
        # Matched card title
        matched_title = tk.Label(matched_frame, text="Selected Card", 
                                font=('Arial', 10, 'bold'),
                                bg=self.bg_color, fg='white')
        matched_title.pack(pady=(10, 5))
        
        # Matched card display using same system as main cards
        self.matched_card_canvas = tk.Canvas(matched_frame, 
                                           width=150, height=200,
                                           bg=self.bg_color, highlightthickness=0)
        self.matched_card_canvas.pack(padx=10, pady=10)
        
        # Default text for no selection
        self.matched_card_canvas.create_text(75, 100, text="No selection", 
                                           fill='#cccccc', font=('Arial', 9),
                                           tags="default_text")
        
        # Match status
        self.match_status = tk.Label(matched_frame, text="", 
                                   font=('Arial', 8),
                                   bg=self.bg_color, fg='#aaaaaa')
        self.match_status.pack(pady=(0, 20))
        
        # Right column - Action buttons (vertical stack, right-justified)
        right_frame = tk.Frame(content_frame, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Action buttons (vertical, right-justified)
        self.save_label_btn = ttk.Button(right_frame, text="Confirm Label (C)", 
                                        state=tk.DISABLED, width=15)
        self.save_label_btn.pack(pady=2, anchor=tk.E)
        
        # Navigation buttons (moved from left to right column)
        self.prev_card_btn = ttk.Button(right_frame, text="← Previous (Q)", 
                                       state=tk.DISABLED, width=15)
        self.prev_card_btn.pack(pady=2, anchor=tk.E)
        
        self.next_card_btn = ttk.Button(right_frame, text="Next → (E)", 
                                       state=tk.DISABLED, width=15)
        self.next_card_btn.pack(pady=2, anchor=tk.E)
        
        self.load_cards_btn = ttk.Button(right_frame, text="Load Cards", 
                                        width=15)
        self.load_cards_btn.pack(pady=2, anchor=tk.E)
        
        return self.labeling_frame
    
    def _setup_title_and_filters(self, parent, on_modifier_filter_change, on_card_design_click, on_mode_change):
        """Setup title and filter controls"""
        title_frame = tk.Frame(parent, bg=self.bg_color)
        title_frame.grid(row=0, column=0, pady=10)
        
        # Mode selector (leftmost)
        mode_label = tk.Label(title_frame, text="Mode:", 
                             font=('Arial', 11),
                             bg=self.bg_color, fg='white')
        mode_label.pack(side=tk.LEFT, padx=(0, 5))
        
        mode_dropdown = ttk.Combobox(title_frame, textvariable=self.app_mode,
                                    values=["Manual Tracking", "Data Labeling"],
                                    state="readonly", width=15)
        mode_dropdown.pack(side=tk.LEFT, padx=(0, 20))
        if on_mode_change:
            mode_dropdown.bind('<<ComboboxSelected>>', on_mode_change)
        
        # Dynamic title based on mode
        self.title_label = tk.Label(title_frame, text="Click a card to add to sequence", 
                                   font=('Arial', 14, 'bold'),
                                   bg=self.bg_color, fg='white')
        self.title_label.pack(side=tk.LEFT, padx=(0, 20))
        
        filter_label = tk.Label(title_frame, text="Filters:", 
                               font=('Arial', 11),
                               bg=self.bg_color, fg='white')
        filter_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Modifier filter dropdown
        modifier_options = ["All Modifiers", "Scoring Only"]
        modifier_menu = ttk.Combobox(title_frame, textvariable=self.modifier_filter,
                                    values=modifier_options, state='readonly', width=15)
        modifier_menu.pack(side=tk.LEFT, padx=5)
        modifier_menu.bind('<<ComboboxSelected>>', on_modifier_filter_change)
        
        # Card designs button
        card_design_btn = ttk.Button(title_frame, text="Card Designs...", 
                                     command=on_card_design_click)
        card_design_btn.pack(side=tk.LEFT, padx=5)
    
    def _setup_order_list(self, parent):
        """Setup card order display area"""
        self.order_label = tk.Label(parent, text="Card Order:", 
                                   font=('Arial', 12, 'bold'),
                                   bg=self.bg_color, fg='white')
        self.order_label.grid(row=4, column=0, sticky=tk.W)
        
        order_container = tk.Frame(parent, bg=self.bg_color)
        order_container.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.order_canvas = tk.Canvas(order_container, height=90, 
                                     bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(order_container, orient='horizontal', 
                                 command=self.order_canvas.xview)
        self.order_frame = tk.Frame(self.order_canvas, bg=self.bg_color)
        
        self.order_canvas.configure(xscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.order_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.order_canvas.create_window((0, 0), window=self.order_frame, anchor='nw')
    
    def _setup_buttons(self, parent, on_clear, on_undo, on_save, on_capture=None):
        """Setup action buttons"""
        self.button_frame = ttk.Frame(parent)
        self.button_frame.grid(row=6, column=0, pady=10)
        
        self.clear_btn = ttk.Button(self.button_frame, text="Clear Order", command=on_clear)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.undo_btn = ttk.Button(self.button_frame, text="Undo Last", command=on_undo)
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(self.button_frame, text="Save", command=on_save)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Add capture button if handler provided
        if on_capture:
            self.capture_btn = ttk.Button(self.button_frame, text="Capture Hand", command=on_capture)
            self.capture_btn.pack(side=tk.LEFT, padx=5)
    
    def update_buttons_for_mode(self, mode):
        """Update button text based on current mode"""
        if mode == "Manual Tracking":
            self.clear_btn.configure(text="Clear Order")
            self.undo_btn.configure(text="Undo Last")
            self.save_btn.configure(text="Save")
            if hasattr(self, 'capture_btn'):
                self.capture_btn.configure(text="Capture Hand")
        elif mode == "Data Labeling":
            # In data labeling mode, the main buttons have different functions
            # but the dedicated labeling buttons handle the core functionality
            self.clear_btn.configure(text="Clear Selection")
            self.undo_btn.configure(text="Previous Card")
            self.save_btn.configure(text="Save Label")
            if hasattr(self, 'capture_btn'):
                self.capture_btn.configure(text="Load Cards")
