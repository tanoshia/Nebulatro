#!/usr/bin/env python3
"""
Layout Manager - Handles dynamic window resizing and positioning
"""


class LayoutManager:
    """Manages dynamic layout calculations and positioning"""
    
    def __init__(self, card_grid_canvas, modifiers_canvas, card_display_width, 
                 card_display_height, card_spacing):
        self.card_grid_canvas = card_grid_canvas
        self.modifiers_canvas = modifiers_canvas
        self.card_display_width = card_display_width
        self.card_display_height = card_display_height
        self.card_spacing = card_spacing
    
    def recalculate_card_positions(self, card_positions, card_img_ids):
        """Recalculate card positions based on available width"""
        canvas_width = self.card_grid_canvas.winfo_width()
        if canvas_width <= 1:
            return
        
        cols = 13
        available_width = canvas_width - 20
        calculated_spacing = (available_width - (cols * self.card_display_width)) / (cols - 1)
        
        max_spacing = self.card_spacing
        min_spacing = -self.card_display_width * 0.7
        actual_spacing = max(min_spacing, min(max_spacing, calculated_spacing))
        
        for card_name, pos_info in card_positions.items():
            if card_name in card_img_ids:
                row = pos_info['row']
                col = pos_info['col']
                
                x = col * (self.card_display_width + actual_spacing)
                y = row * (self.card_display_height + self.card_spacing)
                
                img_id = card_img_ids[card_name]
                self.card_grid_canvas.coords(img_id, x, y)
                self.card_grid_canvas.tag_raise(img_id)
    
    def recalculate_modifier_positions(self, modifier_positions, modifier_img_ids, 
                                      modifier_types, modifier_display_widths):
        """Recalculate modifier positions grouped by category"""
        canvas_width = self.card_grid_canvas.winfo_width()
        if canvas_width <= 1:
            return
        
        self.modifiers_canvas.config(width=canvas_width)
        
        # Group by category
        categories = {'enhancement': [], 'edition': [], 'seal': [], 'debuff': []}
        for modifier_key, display_idx in modifier_positions.items():
            mod_type = modifier_types.get(modifier_key, '')
            if 'enhancement' in mod_type:
                categories['enhancement'].append((modifier_key, display_idx))
            elif 'debuff' in mod_type:
                categories['debuff'].append((modifier_key, display_idx))
            elif 'edition' in mod_type:
                categories['edition'].append((modifier_key, display_idx))
            elif 'seal' in mod_type:
                categories['seal'].append((modifier_key, display_idx))
        
        for cat in categories.values():
            cat.sort(key=lambda x: x[1])
        
        # Calculate spacing
        category_gap = 10
        max_spacing = self.card_spacing
        min_spacing = -self.card_display_width * 0.7
        max_seal_spacing = 5
        min_seal_spacing = -10
        
        total_overlap_items = len(categories['enhancement']) + len(categories['edition']) + len(categories['debuff'])
        total_seal_items = len(categories['seal'])
        
        non_empty_cats = [cat for cat in ['enhancement', 'edition', 'seal', 'debuff'] if categories[cat]]
        total_gaps = (len(non_empty_cats) - 1) * category_gap if len(non_empty_cats) > 1 else 0
        
        total_seal_width_max = 0
        if categories['seal']:
            for modifier_key, _ in categories['seal']:
                total_seal_width_max += modifier_display_widths.get(modifier_key, self.card_display_width)
            total_seal_width_max += (total_seal_items - 1) * max_seal_spacing if total_seal_items > 1 else 0
        
        total_overlap_width_max = total_overlap_items * self.card_display_width
        if total_overlap_items > 1:
            total_overlap_width_max += (total_overlap_items - 1) * max_spacing
        
        available_width = canvas_width - 20
        total_needed = total_seal_width_max + total_overlap_width_max + total_gaps
        
        if total_needed > available_width:
            available_for_items = available_width - total_gaps
            seal_widths_sum = sum(modifier_display_widths.get(mk, self.card_display_width) 
                                 for mk, _ in categories['seal'])
            
            if total_overlap_items > 0 and total_seal_items > 0:
                total_items = total_overlap_items + total_seal_items
                total_gaps_needed = (total_overlap_items - 1) + (total_seal_items - 1) if total_items > 1 else 0
                
                if total_gaps_needed > 0:
                    avg_spacing = (available_for_items - (total_overlap_items * self.card_display_width) - 
                                  seal_widths_sum) / total_gaps_needed
                    overlap_spacing = max(min_spacing, min(max_spacing, avg_spacing))
                    seal_spacing = max(min_seal_spacing, min(max_seal_spacing, avg_spacing))
                else:
                    overlap_spacing = max_spacing
                    seal_spacing = max_seal_spacing
            elif total_overlap_items > 0:
                calculated_spacing = (available_for_items - (total_overlap_items * self.card_display_width)) / \
                                    (total_overlap_items - 1) if total_overlap_items > 1 else 0
                overlap_spacing = max(min_spacing, min(max_spacing, calculated_spacing))
                seal_spacing = max_seal_spacing
            else:
                overlap_spacing = max_spacing
                calculated_seal_spacing = (available_for_items - seal_widths_sum) / \
                                         (total_seal_items - 1) if total_seal_items > 1 else 0
                seal_spacing = max(min_seal_spacing, min(max_seal_spacing, calculated_seal_spacing))
        else:
            overlap_spacing = max_spacing
            seal_spacing = max_seal_spacing
        
        # Position modifiers
        x_offset = 0
        for cat_name in ['enhancement', 'edition', 'seal', 'debuff']:
            cat_modifiers = categories[cat_name]
            if not cat_modifiers:
                continue
            
            seal_x_offset = 0
            for i, (modifier_key, display_idx) in enumerate(cat_modifiers):
                if modifier_key in modifier_img_ids:
                    if cat_name == 'seal':
                        x = x_offset + seal_x_offset
                        seal_x_offset += modifier_display_widths.get(modifier_key, self.card_display_width) + seal_spacing
                    else:
                        x = x_offset + (i * (self.card_display_width + overlap_spacing))
                    
                    img_id = modifier_img_ids[modifier_key]
                    self.modifiers_canvas.coords(img_id, x, 0)
                    self.modifiers_canvas.tag_lower(img_id)
            
            if cat_name == 'seal':
                category_width = sum(modifier_display_widths.get(mk, self.card_display_width) 
                                   for mk, _ in cat_modifiers)
                category_width += (len(cat_modifiers) - 1) * seal_spacing if len(cat_modifiers) > 1 else 0
                x_offset += category_width + category_gap
            else:
                if len(cat_modifiers) > 0:
                    x_offset += self.card_display_width + (len(cat_modifiers) - 1) * \
                               (self.card_display_width + overlap_spacing) + category_gap
    
    def auto_size_window(self, root, canvas_width, canvas_height):
        """Auto-size window to fit all cards"""
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        required_width = canvas_width + 40
        required_height = (40 + self.card_display_height + 10 + canvas_height + 20 + 
                          20 + 30 + 100 + 50 + 20)
        
        max_width = int(screen_width * 0.95)
        max_height = int(screen_height * 0.95)
        
        window_width = min(required_width, max_width)
        window_height = min(required_height, max_height)
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
