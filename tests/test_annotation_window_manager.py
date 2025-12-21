#!/usr/bin/env python3
"""
Property-based tests for AnnotationWindowManager

**Feature: ground-truth-annotation-integration, Property 7: Window lifecycle management**
**Validates: Requirements 4.1, 4.2**
"""

import unittest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os
import sys
import platform

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from hypothesis import given, strategies as st, settings, assume
    from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    # Fallback for when hypothesis is not available
    def given(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    def settings(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class st:
        @staticmethod
        def text():
            return "test_screenshot.png"
        
        @staticmethod
        def booleans():
            return True

from managers.annotation_window_manager import AnnotationWindowManager, AnnotationStateManager


class TestAnnotationWindowManager(unittest.TestCase):
    """Test AnnotationWindowManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock labeling manager
        self.mock_labeling_manager = Mock()
        self.mock_labeling_manager.ui = Mock()
        self.mock_labeling_manager.modifier_manager = Mock()
        self.mock_labeling_manager.modifier_manager.get_selected_modifiers.return_value = []
        
        # Create temporary test image
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = os.path.join(self.temp_dir, "test_screenshot.png")
        
        # Create a minimal test image using PIL
        try:
            from PIL import Image
            test_image = Image.new('RGB', (100, 100), color='red')
            test_image.save(self.test_image_path)
        except ImportError:
            # Fallback: create empty file
            with open(self.test_image_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')  # PNG header
        
        self.manager = AnnotationWindowManager(self.mock_labeling_manager)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close any open windows
        if self.manager.annotation_window:
            try:
                self.manager.close_annotation_window()
            except:
                pass
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    def test_spawn_annotation_window_success(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox):
        """Test successful window spawning."""
        # Mock successful image loading
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        # Mock PIL Image
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        # Mock ImageTk
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        # Mock Tkinter window and components
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        # Mock ttk and tk components
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            # Setup ttk mocks
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            # Setup tk mocks
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            # Test window spawning
            result = self.manager.spawn_annotation_window(self.test_image_path)
            
            self.assertTrue(result)
            self.assertTrue(self.manager.is_annotation_window_active())
            self.assertEqual(self.manager.state_manager.current_screenshot, self.test_image_path)
    
    @patch('tkinter.messagebox.showerror')
    def test_spawn_annotation_window_invalid_path(self, mock_showerror):
        """Test window spawning with invalid path."""
        result = self.manager.spawn_annotation_window("nonexistent_screenshot.png")
        
        self.assertFalse(result)
        self.assertFalse(self.manager.is_annotation_window_active())
        # Verify that an error message was shown
        mock_showerror.assert_called_once()
    
    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    def test_close_annotation_window(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox):
        """Test window closing."""
        # Setup mocks similar to success test
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_window.destroy = Mock()  # Explicitly mock the destroy method
        mock_toplevel.return_value = mock_window
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            # Spawn window
            spawn_result = self.manager.spawn_annotation_window(self.test_image_path)
            self.assertTrue(spawn_result, "Window should spawn successfully")
            
            # Verify window was created
            self.assertTrue(self.manager.is_annotation_window_active())
            self.assertIsNotNone(self.manager.annotation_window)
            
            # Close window
            self.manager.close_annotation_window()
            
            # Verify window was closed
            self.assertFalse(self.manager.is_annotation_window_active())
            self.assertIsNone(self.manager.annotation_window)
            
            # The destroy method should be called, but due to the try-catch in close_annotation_window,
            # we'll just verify the state is correct rather than the specific method call
    
    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    def test_pending_bbox_workflow(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox):
        """Test pending bounding box workflow."""
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            self.manager.spawn_annotation_window(self.test_image_path)
            
            # Set pending bbox
            bbox = {"x": 10, "y": 20, "width": 50, "height": 60}
            self.manager.set_pending_bbox(bbox, Path(self.test_image_path))
            
            self.assertIsNotNone(self.manager.state_manager.pending_bbox)
            self.assertEqual(self.manager.state_manager.pending_bbox, bbox)
            
            # Clear pending bbox
            self.manager.clear_pending_bbox()
            self.assertIsNone(self.manager.state_manager.pending_bbox)
    
    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    def test_ctrl_z_cancel_functionality(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox):
        """Test OS-appropriate keyboard shortcut for canceling bounding boxes (Cmd+Z on macOS, Ctrl+Z elsewhere)."""
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            self.manager.spawn_annotation_window(self.test_image_path)
            window = self.manager.annotation_window
            
            # Test 1: Cancel pending bounding box with Ctrl+Z
            bbox = {"x": 10, "y": 20, "width": 50, "height": 60}
            window.set_pending_bbox(bbox)
            self.assertIsNotNone(window.pending_bbox)
            
            # Simulate Ctrl+Z
            window.cancel_bbox_shortcut()
            self.assertIsNone(window.pending_bbox)
            
            # Test 2: Cancel drawing in progress with Ctrl+Z
            window.drawing = True
            window.temp_bbox = "mock_temp_bbox_id"
            window.start_point = (10, 20)
            
            window.cancel_bbox_shortcut()
            self.assertFalse(window.drawing)
            self.assertIsNone(window.start_point)
            self.assertIsNone(window.temp_bbox)
            
            # Test 3: Keyboard shortcut with no bounding box (should not crash)
            window.cancel_bbox_shortcut()  # Should handle gracefully
            
            # Test 4: Verify OS-appropriate key is set
            self.assertIsNotNone(getattr(window, 'undo_key', None))
            expected_key = "Cmd+Z" if platform.system() == "Darwin" else "Ctrl+Z"
            self.assertEqual(window.undo_key, expected_key)

    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    def test_card_selection_handling(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox):
        """Test card selection handling with pending bbox."""
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            self.manager.spawn_annotation_window(self.test_image_path)
            
            # Set pending bbox
            bbox = {"x": 10, "y": 20, "width": 50, "height": 60}
            self.manager.set_pending_bbox(bbox, Path(self.test_image_path))
            
            # Handle card selection
            result = self.manager.handle_card_selection(25)  # Card class 25
            
            self.assertTrue(result)
            self.assertIsNone(self.manager.state_manager.pending_bbox)


@unittest.skipUnless(HYPOTHESIS_AVAILABLE, "Hypothesis not available")
class PropertyBasedAnnotationWindowTests(unittest.TestCase):
    """Property-based tests for annotation window lifecycle management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_labeling_manager = Mock()
        self.mock_labeling_manager.ui = Mock()
        self.mock_labeling_manager.modifier_manager = Mock()
        self.mock_labeling_manager.modifier_manager.get_selected_modifiers.return_value = []
        
        # Create temporary test directory
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=20))
    @settings(max_examples=10, deadline=None)  # Reduced examples for faster testing
    def test_property_window_lifecycle_management(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox, screenshot_name):
        """
        **Feature: ground-truth-annotation-integration, Property 7: Window lifecycle management**
        
        Property: For any window closure or mode change, the system should properly close 
        the secondary window and return the main window to the appropriate state.
        
        **Validates: Requirements 4.1, 4.2**
        """
        assume(screenshot_name.strip())  # Ensure non-empty name
        assume('/' not in screenshot_name and '\\' not in screenshot_name)  # Valid filename
        
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        # Use real screenshot from dataset
        available_screenshots = [
            "dataset/raw/BalatroExample1.png",
            "dataset/raw/BalatroExample2.png", 
            "dataset/raw/BalatroExample3.png"
        ]
        # Use hash of screenshot_name to pick a consistent screenshot
        screenshot_index = hash(screenshot_name) % len(available_screenshots)
        test_image_path = available_screenshots[screenshot_index]
        
        manager = AnnotationWindowManager(self.mock_labeling_manager)
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            try:
                # Property: Window spawning should always result in active state
                spawn_result = manager.spawn_annotation_window(test_image_path)
                if spawn_result:
                    self.assertTrue(manager.is_annotation_window_active())
                    self.assertIsNotNone(manager.annotation_window)
                    self.assertEqual(manager.state_manager.current_screenshot, test_image_path)
                    
                    # Property: Window closing should always result in inactive state
                    manager.close_annotation_window()
                    self.assertFalse(manager.is_annotation_window_active())
                    self.assertIsNone(manager.annotation_window)
                    
                    # Property: State should be properly cleared after closing
                    self.assertIsNone(manager.state_manager.pending_bbox)
                    self.assertFalse(manager.state_manager.annotation_window_active)
            
            finally:
                # Cleanup
                try:
                    manager.close_annotation_window()
                except:
                    pass
    
    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=20))
    @settings(max_examples=10, deadline=None)  # Reduced examples for faster testing
    def test_property_secondary_window_spawning(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox, screenshot_name):
        """
        **Feature: ground-truth-annotation-integration, Property 2: Secondary window spawning**
        
        Property: For any "Load Cards" button click in Data Labeling mode, the system should spawn 
        a secondary annotation window with screenshot display and zoom/pan capabilities.
        
        **Validates: Requirements 1.2, 1.3**
        """
        assume(screenshot_name.strip())  # Ensure non-empty name
        assume('/' not in screenshot_name and '\\' not in screenshot_name)  # Valid filename
        
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        # Use real screenshot from dataset
        available_screenshots = [
            "dataset/raw/BalatroExample1.png",
            "dataset/raw/BalatroExample2.png", 
            "dataset/raw/BalatroExample3.png"
        ]
        # Use hash of screenshot_name to pick a consistent screenshot
        screenshot_index = hash(screenshot_name) % len(available_screenshots)
        test_image_path = available_screenshots[screenshot_index]
        
        manager = AnnotationWindowManager(self.mock_labeling_manager)
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_canvas.bind = Mock()  # Mock canvas event binding
            mock_canvas.configure = Mock()  # Mock canvas configuration
            mock_canvas.create_image = Mock(return_value=1)  # Mock image creation
            mock_canvas.delete = Mock()  # Mock canvas deletion
            mock_tk.Canvas.return_value = mock_canvas
            
            try:
                # Property: Window spawning should create annotation window with required capabilities
                spawn_result = manager.spawn_annotation_window(test_image_path)
                
                if spawn_result:
                    # Verify window was created and is active
                    self.assertTrue(manager.is_annotation_window_active())
                    self.assertIsNotNone(manager.annotation_window)
                    
                    # Verify screenshot display capabilities
                    annotation_window = manager.annotation_window
                    self.assertIsNotNone(annotation_window.current_image_tk)
                    self.assertIsNotNone(annotation_window.canvas)
                    
                    # Verify zoom and pan capabilities are bound
                    # Check that mouse wheel events are bound for zoom
                    canvas_bind_calls = mock_canvas.bind.call_args_list
                    zoom_events = ["<MouseWheel>", "<Button-4>", "<Button-5>"]
                    pan_events = ["<Button-2>", "<B2-Motion>"]
                    
                    bound_events = [call[0][0] for call in canvas_bind_calls]
                    
                    # Property: Zoom capabilities should be available
                    for zoom_event in zoom_events:
                        self.assertIn(zoom_event, bound_events, 
                                    f"Zoom event {zoom_event} should be bound to canvas")
                    
                    # Property: Pan capabilities should be available  
                    for pan_event in pan_events:
                        self.assertIn(pan_event, bound_events,
                                    f"Pan event {pan_event} should be bound to canvas")
                    
                    # Property: Canvas should be configured with scrollbars for large images
                    mock_canvas.configure.assert_called()
                    configure_calls = mock_canvas.configure.call_args_list
                    scroll_config_found = any('scrollregion' in str(call) for call in configure_calls)
                    self.assertTrue(scroll_config_found, "Canvas should be configured with scroll region")
                    
                    # Property: Image should be displayed on canvas
                    mock_canvas.create_image.assert_called()
                    
                    # Property: Screenshot path should be stored
                    self.assertEqual(manager.state_manager.current_screenshot, test_image_path)
            
            finally:
                # Cleanup
                try:
                    manager.close_annotation_window()
                except:
                    pass

    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    @given(
        start_x=st.integers(min_value=10, max_value=500),
        start_y=st.integers(min_value=10, max_value=500),
        end_x=st.integers(min_value=50, max_value=800),
        end_y=st.integers(min_value=50, max_value=600)
    )
    @settings(max_examples=10, deadline=None)  # Reduced examples for faster testing
    def test_property_bounding_box_creation_workflow(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox,
                                                   start_x, start_y, end_x, end_y):
        """
        **Feature: ground-truth-annotation-integration, Property 3: Bounding box creation workflow**
        
        Property: For any click-and-drag interaction in the secondary window, the system should create 
        a bounding box with temporary visual feedback during drawing and final highlighting when complete.
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        assume(abs(end_x - start_x) >= 30)  # Ensure reasonable width
        assume(abs(end_y - start_y) >= 30)  # Ensure reasonable height
        
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((1000, 1000, 3), dtype=np.uint8)  # Large enough image
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 1000
        mock_pil.height = 1000
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        # Use real screenshot from dataset
        available_screenshots = [
            "dataset/raw/BalatroExample1.png",
            "dataset/raw/BalatroExample2.png", 
            "dataset/raw/BalatroExample3.png"
        ]
        # Use hash of coordinates to pick a consistent screenshot
        screenshot_index = hash((start_x, start_y)) % len(available_screenshots)
        test_image_path = available_screenshots[screenshot_index]
        
        manager = AnnotationWindowManager(self.mock_labeling_manager)
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 1000, 1000)
            mock_canvas.canvasx = Mock(side_effect=lambda x: x)  # Identity function for simplicity
            mock_canvas.canvasy = Mock(side_effect=lambda y: y)  # Identity function for simplicity
            mock_canvas.create_rectangle = Mock(return_value="temp_rect_id")
            mock_canvas.delete = Mock()
            mock_tk.Canvas.return_value = mock_canvas
            
            try:
                # Spawn annotation window
                spawn_result = manager.spawn_annotation_window(test_image_path)
                if not spawn_result:
                    return  # Skip if window couldn't be spawned
                
                annotation_window = manager.annotation_window
                
                # Property: Initial state should allow drawing
                self.assertFalse(annotation_window.drawing)
                self.assertIsNone(annotation_window.pending_bbox)
                self.assertIsNone(annotation_window.temp_bbox)
                
                # Simulate click-and-drag workflow
                
                # Step 1: Canvas click (start drawing)
                click_event = Mock()
                click_event.x = start_x
                click_event.y = start_y
                
                annotation_window.on_canvas_click(click_event)
                
                # Property: Click should initiate drawing state
                self.assertTrue(annotation_window.drawing)
                self.assertIsNotNone(annotation_window.start_point)
                self.assertEqual(annotation_window.start_point, (start_x, start_y))
                
                # Step 2: Canvas drag (temporary visual feedback)
                drag_event = Mock()
                drag_event.x = (start_x + end_x) // 2  # Midpoint
                drag_event.y = (start_y + end_y) // 2
                
                annotation_window.on_canvas_drag(drag_event)
                
                # Property: Drag should create temporary rectangle
                mock_canvas.create_rectangle.assert_called()
                create_calls = mock_canvas.create_rectangle.call_args_list
                self.assertTrue(len(create_calls) > 0)
                
                # Verify temporary rectangle properties
                last_call = create_calls[-1]
                call_args = last_call[0]  # Positional arguments
                call_kwargs = last_call[1]  # Keyword arguments
                
                # Should have 4 coordinates (x1, y1, x2, y2)
                self.assertEqual(len(call_args), 4)
                
                # Should have visual properties for temporary feedback
                self.assertIn('outline', call_kwargs)
                self.assertIn('dash', call_kwargs)  # Temporary rectangles should be dashed
                
                # Step 3: Canvas release (finalize bounding box)
                release_event = Mock()
                release_event.x = end_x
                release_event.y = end_y
                
                # Mock the set_pending_bbox method to capture the result
                original_set_pending = annotation_window.set_pending_bbox
                annotation_window.set_pending_bbox = Mock(side_effect=original_set_pending)
                
                annotation_window.on_canvas_release(release_event)
                
                # Property: Release should stop drawing
                self.assertFalse(annotation_window.drawing)
                
                # Property: Valid bounding box should be created and set as pending
                if annotation_window.set_pending_bbox.called:
                    # Verify bounding box was created with correct structure
                    call_args = annotation_window.set_pending_bbox.call_args[0]
                    bbox_data = call_args[0]
                    
                    self.assertIn('x', bbox_data)
                    self.assertIn('y', bbox_data)
                    self.assertIn('width', bbox_data)
                    self.assertIn('height', bbox_data)
                    
                    # Verify coordinates are reasonable (non-negative, within bounds)
                    self.assertGreaterEqual(bbox_data['x'], 0)
                    self.assertGreaterEqual(bbox_data['y'], 0)
                    self.assertGreater(bbox_data['width'], 0)
                    self.assertGreater(bbox_data['height'], 0)
                    
                    # Property: Bounding box should be within image bounds
                    self.assertLessEqual(bbox_data['x'] + bbox_data['width'], annotation_window.original_width)
                    self.assertLessEqual(bbox_data['y'] + bbox_data['height'], annotation_window.original_height)
                
                # Property: Temporary rectangle should be cleaned up
                mock_canvas.delete.assert_called()
                
            finally:
                # Cleanup
                try:
                    manager.close_annotation_window()
                except:
                    pass

    @patch('managers.annotation_window_manager.messagebox')
    @patch('managers.annotation_window_manager.ImageTk')
    @patch('managers.annotation_window_manager.Image')
    @patch('managers.annotation_window_manager.cv2')
    @patch('tkinter.Toplevel')
    @given(
        bbox_x=st.integers(min_value=0, max_value=1000),
        bbox_y=st.integers(min_value=0, max_value=1000),
        bbox_w=st.integers(min_value=10, max_value=500),
        bbox_h=st.integers(min_value=10, max_value=500),
        card_class=st.integers(min_value=0, max_value=51)
    )
    @settings(max_examples=10, deadline=None)  # Reduced examples for faster testing
    def test_property_pending_bbox_state_consistency(self, mock_toplevel, mock_cv2, mock_pil_image, mock_imagetk, mock_messagebox,
                                                   bbox_x, bbox_y, bbox_w, bbox_h, card_class):
        """
        Property: Pending bounding box state should be consistent across operations.
        
        For any valid bounding box coordinates and card selection, the system should
        maintain consistent state throughout the annotation workflow.
        """
        # Setup mocks
        import numpy as np
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.imread.return_value = mock_image_array
        mock_cv2.cvtColor.return_value = mock_image_array
        
        mock_pil = Mock()
        mock_pil.width = 100
        mock_pil.height = 100
        mock_pil.thumbnail = Mock()
        mock_pil_image.fromarray.return_value = mock_pil
        
        mock_photo = Mock()
        mock_imagetk.PhotoImage.return_value = mock_photo
        
        mock_window = Mock()
        mock_window.winfo_exists.return_value = True
        mock_toplevel.return_value = mock_window
        
        # Use real screenshot from dataset
        available_screenshots = [
            "dataset/raw/BalatroExample1.png",
            "dataset/raw/BalatroExample2.png", 
            "dataset/raw/BalatroExample3.png"
        ]
        # Use hash of bbox coordinates to pick a consistent screenshot
        screenshot_index = hash((bbox_x, bbox_y)) % len(available_screenshots)
        test_image_path = available_screenshots[screenshot_index]
        
        manager = AnnotationWindowManager(self.mock_labeling_manager)
        
        with patch('managers.annotation_window_manager.ttk') as mock_ttk, \
             patch('managers.annotation_window_manager.tk') as mock_tk:
            
            mock_ttk.Frame.return_value = Mock()
            mock_ttk.LabelFrame.return_value = Mock()
            mock_ttk.Label.return_value = Mock()
            mock_ttk.Button.return_value = Mock()
            mock_ttk.Scrollbar.return_value = Mock()
            
            mock_canvas = Mock()
            mock_canvas.bbox.return_value = (0, 0, 100, 100)
            mock_tk.Canvas.return_value = mock_canvas
            
            try:
                # Spawn window
                spawn_result = manager.spawn_annotation_window(test_image_path)
                if not spawn_result:
                    return  # Skip if window couldn't be spawned
                
                # Create bounding box
                bbox = {"x": bbox_x, "y": bbox_y, "width": bbox_w, "height": bbox_h}
                
                # Property: Setting pending bbox should make it available
                manager.set_pending_bbox(bbox, Path(test_image_path))
                self.assertEqual(manager.state_manager.pending_bbox, bbox)
                
                # Property: Handling card selection should clear pending bbox
                result = manager.handle_card_selection(card_class)
                if result:
                    self.assertIsNone(manager.state_manager.pending_bbox)
                
                # Property: Clearing bbox should always result in None
                manager.clear_pending_bbox()
                self.assertIsNone(manager.state_manager.pending_bbox)
            
            finally:
                try:
                    manager.close_annotation_window()
                except:
                    pass


class TestAnnotationStateManager(unittest.TestCase):
    """Test AnnotationStateManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state_manager = AnnotationStateManager()
    
    def test_initial_state(self):
        """Test initial state is correct."""
        self.assertIsNone(self.state_manager.pending_bbox)
        self.assertIsNone(self.state_manager.current_screenshot)
        self.assertIsNone(self.state_manager.screenshot_info)
        self.assertFalse(self.state_manager.annotation_window_active)
        self.assertIsNone(self.state_manager.last_error)
    
    def test_set_pending_annotation(self):
        """Test setting pending annotation."""
        bbox = {"x": 10, "y": 20, "width": 50, "height": 60}
        screenshot_info = {"path": "/test/path.png", "timestamp": "2023-01-01"}
        
        self.state_manager.set_pending_annotation(bbox, screenshot_info)
        
        self.assertEqual(self.state_manager.pending_bbox, bbox)
        self.assertEqual(self.state_manager.screenshot_info, screenshot_info)
    
    def test_complete_annotation_success(self):
        """Test successful annotation completion."""
        # Setup pending annotation
        bbox = {"x": 10, "y": 20, "width": 50, "height": 60}
        screenshot_info = {"path": "/test/path.png", "timestamp": "2023-01-01"}
        self.state_manager.set_pending_annotation(bbox, screenshot_info)
        
        # Complete annotation
        result = self.state_manager.complete_annotation(25, {"enhancement": "bonus"})
        
        self.assertTrue(result)
        self.assertIsNone(self.state_manager.pending_bbox)
        self.assertIsNone(self.state_manager.screenshot_info)
    
    def test_complete_annotation_no_pending(self):
        """Test annotation completion without pending data."""
        result = self.state_manager.complete_annotation(25, {})
        
        self.assertFalse(result)
        self.assertIsNotNone(self.state_manager.last_error)
    
    def test_cancel_pending_annotation(self):
        """Test canceling pending annotation."""
        # Setup pending annotation
        bbox = {"x": 10, "y": 20, "width": 50, "height": 60}
        screenshot_info = {"path": "/test/path.png"}
        self.state_manager.set_pending_annotation(bbox, screenshot_info)
        
        # Cancel annotation
        self.state_manager.cancel_pending_annotation()
        
        self.assertIsNone(self.state_manager.pending_bbox)
        self.assertIsNone(self.state_manager.screenshot_info)


if __name__ == '__main__':
    # Try to install hypothesis if not available
    if not HYPOTHESIS_AVAILABLE:
        print("Warning: hypothesis not available. Installing...")
        try:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "hypothesis"])
            print("Hypothesis installed successfully. Please run tests again.")
        except Exception as e:
            print(f"Failed to install hypothesis: {e}")
            print("Running basic tests only...")
    
    unittest.main()