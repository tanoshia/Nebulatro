# Nebulatro

A Balatro card order tracker with modifier overlays, custom card designs, and advanced computer vision capabilities. Features manual card tracking, automated screenshot processing, and AI-powered card detection for training data generation.

## Setup

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install Python packages
pip3 install -r requirements.txt

# Install tkinter (macOS only)
brew install python-tk@3.13
```

### 2. Add Game Resources

**Option A: Use Game Resources (Recommended)**

Copy the `resources` folder from your Balatro game installation to this directory:

```
Balatro-Calc/
  resources/
    textures/
      1x/
        8BitDeck_opt2.png
        Enhancers.png
        Jokers.png
        Tarots.png
        boosters.png
        ...
```

The app will automatically use these files via `resource_mapping.json`.

**Option B: Use Fallback Assets**

If you don't have access to game resources, the app will fall back to sprite sheets in the `assets/` folder. These should follow the naming convention: `COLSxROWS Description.png` (e.g., `13x4 Playing Cards.png`).

### 3. Run the App

```bash
source venv/bin/activate
python3 nebulatro.py
```

## Usage

### Manual Card Tracking
- Click any card in the grid to add it to your sequence
- The order appears at the bottom with smaller card images
- Use "Undo Last" to remove the most recent card
- Use "Clear Order" to start over

### Computer Vision & Ground Truth Workflow

#### 1. Test Detection System
```bash
# Verify YOLOv8 and detection pipeline
python temp_scripts/test_phase3_1.py
```

#### 2. Create Ground Truth Annotations
```bash
# GUI-based annotation tool using Nebulatro interface
python label_data/annotate_ground_truth.py
```
- Load Balatro screenshots through file dialog
- Draw bounding boxes by clicking and dragging
- Select cards using the familiar Nebulatro card grid
- Apply modifiers using dropdown menus
- Automatic ground truth validation and saving

#### 3. Evaluate Detection Performance
```bash
# Compare detection results vs ground truth
python label_data/evaluate_detection.py
```
- Choose detection method (ensemble, yolo, template)
- Get precision, recall, F1-score metrics
- Identify false positives and missed detections

#### 4. Process Screenshots
```bash
# Extract cards from Balatro screenshots
python src/tools/improved_screenshot_processor.py dataset/raw/screenshot.png --debug
```

## Features

### Manual Card Tracking
- **Game Resource Integration**: Uses Balatro's own sprite sheets with fallback to custom assets
- **Card Modifiers**: Select Enhancements, Editions, and Seals that overlay onto cards
  - Background modifiers (Bonus, Mult, Wild) replace card backing
  - Blend modes for realistic effects (multiply, color)
  - Real-time preview on all cards
- **Dynamic Card Spacing**: Cards overlap when window is resized (up to 70%)
- **Click to Track**: Click cards to add to sequence with current modifiers applied
- **Export**: Save card order as CSV with modifiers (e.g., `AS+Mult+Foil,KS,QH+Red_Seal`)
- **Dark Theme**: Matches macOS dark mode
- **Undo/Clear**: Remove last card or reset entire sequence

### Advanced Computer Vision (Phase 3.1)
- **YOLOv8 Card Detection**: Real-time card detection with 37-57ms processing speed
- **Template Matching**: Fallback system using game sprites for robust detection
- **Hybrid Detection Pipeline**: Combines multiple methods with confidence voting
- **Multi-Scale Processing**: Handles different resolutions and visual effects
- **Ground Truth System**: Tools for creating and evaluating detection accuracy

### Data Labeling & Training
- **Integrated Labeling Mode**: Visual interface for labeling extracted cards
- **Screenshot Processing**: Automated card extraction from Balatro screenshots
- **Ground Truth Annotation**: Interactive tool for creating evaluation datasets
- **Performance Evaluation**: Precision, recall, F1-score, and IoU metrics
- **Training Data Pipeline**: Automated preparation for ML model training


## Configuration

### Resource Mapping (`resource_mapping.json`)

Maps game resource files to sprite sheet definitions. Edit this file to:
- Add new sprite sheets
- Update grid dimensions
- Define card names and positions

### Card Order (`card_order_config.json`)

Configures:
- Playing card display order (suits, ranks)
- Modifier indices and names
- Render modes (overlay, background)
- Blend modes (normal, multiply, color)
- Opacity values

## Project Structure

```
nebulatro.py                # Launcher script
src/
  main.py                   # Main orchestrator
  managers/                 # Business logic
    card_manager.py         # Card loading, display, and tracking
    modifier_manager.py     # Modifier system (enhancements, editions, seals)
    design_manager.py       # Card designs (contrast, collaborations)
  ui/                       # User interface
    components.py           # UI layout and widget creation
    layout_manager.py       # Dynamic positioning and window resizing
  utils/                    # Utilities
    sprite_loader.py        # Sprite sheet loading with resource mapping
  vision/                   # Computer vision pipeline
    card_detector.py        # YOLOv8-based card detection
    template_matcher.py     # Template matching with game sprites
    hybrid_detector.py      # Multi-method detection pipeline
  ml/                       # Machine learning infrastructure
    dataset_writer.py       # Centralized dataset writing
    dataset_indexer.py      # Dataset statistics and integrity
    schema_migrator.py      # Schema version migration
    dataset_reporter.py     # Advanced reporting and analysis
  tools/                    # Processing tools
    improved_screenshot_processor.py  # Advanced screenshot analysis
    batch_screenshot_processor.py     # Batch processing
temp_scripts/               # Temporary testing tools
  test_phase3_1.py          # Phase 3.1 detection system test
label_data/                 # Data labeling and evaluation tools
  annotate_ground_truth.py  # GUI-based ground truth annotation
  evaluate_detection.py     # Detection performance evaluation
dataset/                    # Training and evaluation data
  raw/                      # Original screenshots
  ground_truth/             # Manual annotations for evaluation
  processed/                # Labeled card images
  states/                   # Canonical game state JSON
config/                     # Configuration files
  card_order_config.json    # Card display and modifier settings
  resource_mapping.json     # Game resource to sprite mapping
schema/                     # JSON schemas
  state_schema.json         # Canonical game state validation
  ground_truth_schema.json  # Ground truth annotation format
resources/                  # Game resources (not included)
assets/                     # Fallback sprite sheets
requirements.txt            # Python dependencies
```

### Architecture

The app uses a modular Python package structure with clear separation of concerns:

- **src/main.py** - Main orchestrator that coordinates all components
- **src/managers/** - Business logic managers
  - **CardManager** - Card loading, display, and order tracking
  - **ModifierManager** - Modifier selection and application
  - **DesignManager** - Card design options (contrast, collabs)
- **src/ui/** - User interface components
  - **UIComponents** - UI layout, widgets, and filter controls
  - **LayoutManager** - Dynamic window resizing and positioning
- **src/utils/** - Utility modules
  - **SpriteLoader** - Sprite sheet loading with resource mapping

## Requirements

### Core Dependencies
- Python 3.13+
- Pillow (PIL) for image processing
- tkinter for GUI (requires python-tk on macOS)
- OpenCV for computer vision
- NumPy for numerical operations

### Machine Learning (Phase 3.1+)
- ultralytics (YOLOv8) for object detection
- PyTorch for neural networks
- jsonschema for data validation

### Optional
- GPU with CUDA support for faster YOLOv8 inference
- 4GB+ RAM recommended for large screenshot processing

## Notes

- The `resources/` folder is not included in the repository due to size and copyright
- Copy it from your Balatro game installation directory
- Fallback assets in `assets/` folder work if resources are unavailable
- Generated files (`card_order_*.txt`) are excluded from git

## License

This is a fan-made tool for Balatro. Game assets belong to their respective owners.
