# Nebulatro Architecture

## Overview

Nebulatro uses a modular Python package architecture with clear separation of concerns. The main application file (`src/main.py`) is a lean orchestrator (~215 lines) that coordinates specialized manager components organized into logical packages. The system now includes comprehensive ML infrastructure, computer vision capabilities, and advanced data management systems.

## Package Structure

```
src/
├── main.py                    # Application entry point and orchestrator
├── managers/                  # Business logic managers
│   ├── card_manager.py        # Card loading, display, and tracking
│   ├── modifier_manager.py    # Modifier system (enhancements, editions, seals)
│   ├── design_manager.py      # Card designs (contrast, collaborations)
│   ├── labeling_manager.py    # Data labeling workflow and UI
│   ├── card_display_manager.py # Card display logic and rendering
│   └── mode_manager.py        # Mode switching (manual/labeling)
├── ui/                        # User interface components
│   ├── components.py          # UI layout and widget creation
│   └── layout_manager.py      # Dynamic positioning and window resizing
├── utils/                     # Utility modules
│   └── sprite_loader.py       # Sprite sheet loading with resource mapping
├── vision/                    # Computer vision pipeline
│   ├── screen_capture.py      # Screen/image capture for card recognition
│   └── card_recognizer.py     # Computer vision for card detection
├── ml/                        # Machine learning infrastructure
│   ├── card_classifier.py     # CNN models for card recognition
│   ├── modifier_classifier.py # Multi-label classifier for modifiers
│   ├── data_generator.py      # Synthetic training data generation
│   ├── trainer.py             # PyTorch training loops and utilities
│   ├── state_schema.py        # JSON schema validation for canonical state
│   ├── state_builder.py       # Builds canonical state JSON from labeling
│   ├── annotation_builder.py  # Builds annotation JSON from metadata
│   ├── dataset_writer.py      # Centralized dataset writing with atomic ops
│   ├── dataset_indexer.py     # Dataset statistics and integrity checking
│   ├── schema_migrator.py     # Schema version migration system
│   └── dataset_reporter.py    # Advanced reporting and analysis dashboards
└── tools/                     # Standalone processing tools
    ├── improved_screenshot_processor.py  # Advanced screenshot analysis
    ├── batch_screenshot_processor.py     # Batch processing with tuning
    ├── extract_cards_from_screenshot.py  # Legacy compatibility wrapper
    ├── label_single_card.py              # Single card labeling tool
    └── batch_label_cards.py              # Batch card labeling tool
```

## Core Application Components

### src/main.py (215 lines)
**Main orchestrator** - Coordinates all components and handles high-level application flow
- Initializes all managers
- Handles event routing between UI and business logic
- Manages application lifecycle and configuration loading
- Coordinates mode switching between manual tracking and data labeling

### src/ui/components.py (146 lines)
**UI layout and setup** - Creates and manages all UI widgets
- Main window layout with mode selection dropdown
- Title and filter controls
- Canvas setup (modifiers, cards, order display)
- Button creation and event binding
- Filter variable management

### src/ui/layout_manager.py (174 lines)
**Dynamic positioning** - Handles window resizing and layout calculations
- Recalculates card positions on resize with dynamic spacing
- Manages card overlap (up to 70% when window is narrow)
- Positions modifiers by category with proper gaps
- Auto-sizes window to fit content
- Handles z-ordering for overlapping elements

## Business Logic Managers

### src/managers/card_manager.py (303 lines)
**Card loading and tracking** - Manages card display and order tracking
- Loads cards from sprite sheets with compositing
- Creates clickable card buttons with proper event handling
- Tracks card order with applied modifiers
- Updates order display with thumbnails and numbering
- Saves card sequences to timestamped CSV files
- Card name conversion (sprite index → readable format)

### src/managers/modifier_manager.py (315 lines)
**Modifier system** - Handles all modifier functionality
- Loads modifiers (enhancements, editions, seals, debuff)
- Manages modifier selection state (one per category)
- Applies modifiers to cards with advanced blend modes
- Handles filter modes (All Modifiers, Scoring Only)
- Implements blend modes (normal, multiply, color)
- Manages render modes (overlay, background)

### src/managers/design_manager.py (171 lines)
**Card designs** - Manages card appearance options
- Opens design popup window for customization
- Handles contrast switching (Standard/High Contrast)
- Manages face card collaborations (24 variants across 4 suits)
- Loads collab options from resource_mapping.json
- Applies collab sprites to face cards (J, Q, K) with proper compositing

### src/managers/labeling_manager.py (617 lines)
**Data labeling workflow** - Manages the data labeling interface and workflow
- Handles card loading from extracted screenshot directories
- Manages labeling interface with navigation controls
- Processes card labeling with modifier support
- Saves labeled data to appropriate category directories
- Integrates with canonical state and annotation JSON generation
- Handles keyboard shortcuts and streamlined workflow

### src/managers/card_display_manager.py (219 lines)
**Card display logic** - Handles card rendering and visual presentation
- Manages card grid layout and positioning
- Handles card image caching and memory management
- Processes card compositing with modifiers
- Manages visual feedback for card selection
- Handles responsive card sizing and spacing

### src/managers/mode_manager.py (242 lines)
**Mode switching** - Manages transitions between manual tracking and data labeling modes
- Handles UI layout changes between modes
- Manages component visibility and positioning
- Coordinates window resizing for different modes
- Handles keyboard shortcut binding/unbinding
- Ensures clean state transitions

## Utility Components

### src/utils/sprite_loader.py
**Sprite loading** - Loads sprites from sheets with resource mapping
- Parses sprite sheet filenames using COLSxROWS convention
- Extracts sprites from grids with automatic dimension calculation
- Composites card faces with backing textures
- Manages resource mapping between game assets and sprite definitions
- Handles transparency and RGBA conversion

## Computer Vision Pipeline

### src/vision/screen_capture.py
**Screen/image capture** - Handles screenshot capture and image loading
- Captures full screen or specific regions
- Loads images from files for processing
- Handles different image formats and resolutions
- Provides image preprocessing utilities

### src/vision/card_recognizer.py
**Card detection and recognition** - Computer vision for card identification
- Uses OpenCV for card detection and region extraction
- Implements ORB feature matching for robust recognition
- Falls back to template matching for low-feature images
- Compares detected cards against sprite database
- Handles visual effects and modifier recognition

## Machine Learning Infrastructure

### src/ml/card_classifier.py
**CNN models for card recognition** - PyTorch-based card classification
- ResNet18 backbone for high-accuracy recognition (11M params)
- Lightweight CNN for fast inference (2M params)
- Handles 52 playing card classes with modifier support
- GPU optimization with automatic device detection

### src/ml/modifier_classifier.py
**Multi-label modifier classification** - Separate classifier for modifiers
- Multi-head CNN for enhancement/edition/seal detection
- Handles complex modifier combinations
- Trained on full card images including visual effects

### src/ml/data_generator.py
**Synthetic training data generation** - Creates training data from game assets
- Generates synthetic card images with modifiers
- Applies realistic transformations and augmentations
- Creates balanced datasets for all card classes

### dataset/generate_variants.py
**Augmented card variant generator** - Creates training data with realistic transforms
- Generates 4x4 grids of 16 variants per card with rotation, perspective warping, shadows, and CRT effects
- Loads sprite sheets from `config/resource_mapping.json` for zero-configuration processing
- Creates meaningful filenames like `3H_glass.png` (rank+suit+enhancement)
- Supports all card types: playing cards, collab face cards, jokers, tarots, enhancers
- `--modifiers` flag: Generate all enhancement variants (base, glass, gold, etc.) - 8x more files
- Without flag: Only generates base cards for smaller datasets
- Usage: `python dataset/generate_variants.py --all --render-scale 4` (base only, ~1.3GB)
- Usage: `python dataset/generate_variants.py --all --modifiers --render-scale 3` (all variants, ~6GB)

### src/ml/trainer.py
**PyTorch training system** - Complete training pipeline
- Automatic checkpointing and model saving
- Learning rate scheduling and optimization
- Training curve visualization
- GPU memory management and batch sizing

### src/ml/state_schema.py
**JSON schema validation** - Validates canonical game state JSON
- Loads and validates against schema/state_schema.json
- Provides clear error messages for validation failures
- Ensures data consistency across the system

### src/ml/state_builder.py
**Canonical state construction** - Builds canonical state JSON from labeling data
- Maps card classes (0-51) to rank/suit combinations
- Applies modifiers from modifier manager
- Includes metadata and validation
- Creates training-ready state representations

### src/ml/annotation_builder.py
**Annotation metadata construction** - Builds rich annotation JSON
- Captures complete labeling context and session information
- Includes modifier details and human-readable names
- Provides debugging and analysis metadata
- Supports workflow analysis and quality assessment

### src/ml/dataset_writer.py
**Centralized dataset writing** - Robust data writing with atomic operations
- Atomic file operations with temporary files and moves
- Comprehensive error handling and rollback capabilities
- Batch operations with transaction support
- Statistics tracking and performance monitoring

### src/ml/dataset_indexer.py
**Dataset statistics and integrity** - Comprehensive dataset management
- Maintains dataset/index.json with file metadata
- Performs integrity checking (orphaned files, schema violations)
- Incremental indexing for performance optimization
- Automated file analysis and categorization

### src/ml/schema_migrator.py
**Schema version migration** - Handles schema evolution and backward compatibility
- Automatic migration of state JSON files between versions
- Migration rule system with validation
- Backup creation and rollback support
- Dataset-wide migration capabilities

### src/ml/dataset_reporter.py
**Advanced reporting and analysis** - Dataset analysis and reporting dashboards
- Comprehensive dataset analysis with quality metrics
- HTML dashboard generation with visualizations
- Training readiness assessment and scoring
- Actionable recommendations for dataset improvement

## Processing Tools

### src/tools/improved_screenshot_processor.py
**Advanced screenshot analysis** - Enhanced screenshot processing with region division
- Accurate layout detection for any resolution
- Advanced multi-method card detection algorithms
- Parameter tuning and optimization
- Debug visualizations and verification

### src/tools/batch_screenshot_processor.py
**Batch processing system** - Processes multiple screenshots with analysis
- Automatic parameter optimization using test screenshots
- Comprehensive statistics and quality metrics
- Resolution analysis and detection accuracy reporting

### src/tools/extract_cards_from_screenshot.py
**Legacy compatibility wrapper** - Maintains backward compatibility
- Wraps improved screenshot processing algorithms
- Provides consistent interface for existing workflows

### src/tools/label_single_card.py
**Single card labeling** - Standalone tool for individual card labeling
- Command-line interface for single card processing
- Integrates with main labeling workflow

### src/tools/batch_label_cards.py
**Batch card labeling** - Processes multiple cards in batch operations
- Automated labeling workflows
- Integration with dataset writing system

## Standalone Scripts

### nebulatro.py
**Application launcher** - Entry point script that launches the main application

### collect_training_data.py
**Data collection tool** - Legacy data labeling tool for screenshots

### setup_ml.py
**ML environment setup** - Checks dependencies and sets up ML environment

### train_card_classifier.py
**Training script** - Main script for training card classification models

### compare_cards.py
**Card comparison tool** - Debugging tool for comparing card recognition results

### test_vision.py
**Vision pipeline testing** - Tests computer vision components

### view_card.py
**Card visualization** - Tool for viewing and analyzing individual cards

## Data Flow

```
User Action
    ↓
src/main.py (orchestrator)
    ↓
├─→ src/managers/mode_manager.py (mode switching)
├─→ src/ui/components.py (UI events)
├─→ src/managers/card_manager.py (card clicks)
├─→ src/managers/modifier_manager.py (modifier selection)
├─→ src/managers/design_manager.py (design changes)
├─→ src/managers/labeling_manager.py (data labeling)
└─→ src/ui/layout_manager.py (window resize)
    ↓
├─→ src/utils/sprite_loader.py (sprite loading)
├─→ src/ml/dataset_writer.py (data persistence)
├─→ src/ml/state_builder.py (canonical state)
└─→ src/ml/annotation_builder.py (metadata)
```

## ML Training Pipeline

```
Screenshot
    ↓
src/tools/improved_screenshot_processor.py (card extraction)
    ↓
src/managers/labeling_manager.py (manual labeling)
    ↓
├─→ src/ml/state_builder.py (canonical state JSON)
├─→ src/ml/annotation_builder.py (annotation JSON)
└─→ src/ml/dataset_writer.py (atomic file operations)
    ↓
src/ml/dataset_indexer.py (indexing and integrity)
    ↓
src/ml/trainer.py (model training)
    ↓
src/ml/card_classifier.py (trained models)
```

## Configuration and Schema

### config/card_order_config.json
**Card display configuration** - Defines card order, modifiers, and display settings
- Playing card sprite mapping and display order
- Modifier definitions (enhancements, editions, seals, debuff)
- Suit configuration and visual settings

### config/resource_mapping.json
**Resource mapping** - Maps game resources to sprite definitions
- Primary resource paths (resources/textures/1x/)
- Fallback asset paths (assets/)
- Collaboration face card definitions
- Sprite sheet configurations

### schema/state_schema.json
**Canonical state schema** - JSON schema for validating game state
- Defines required fields and data types
- Validates card instances, jokers, economy, and round state
- Ensures consistency across training data

## Key Design Principles

1. **Separation of Concerns** - Each module has a single, well-defined responsibility
2. **Loose Coupling** - Modules communicate through the orchestrator, not directly
3. **Clear Interfaces** - Managers expose simple methods for the orchestrator to call
4. **Event-Driven** - UI events flow through the orchestrator to appropriate managers
5. **Data Integrity** - Atomic operations and validation ensure data consistency
6. **Extensibility** - Modular design allows easy addition of new features
7. **Performance** - Incremental processing and caching optimize large datasets

## Benefits

- **Maintainability** - Easy to locate and modify specific functionality
- **Readability** - Main file clearly shows application flow
- **Extensibility** - New features can be added as new managers or ML components
- **Debugging** - Issues isolated to specific modules
- **Collaboration** - Multiple developers can work on different modules
- **Data Quality** - Comprehensive validation and integrity checking
- **ML Ready** - Complete pipeline from data collection to model training

## Adding New Features

To add a new feature:

1. Determine which manager/component it belongs to (or create a new one)
2. Add methods to the appropriate manager
3. Add event handlers in `src/main.py`
4. Wire up UI elements in `src/ui/components.py` if needed
5. Update schema and validation if data structures change
6. Add tests and update documentation
7. Update knowledgebase.md with the changes

## Module Dependencies

```
src/main.py
├── src/managers/
│   ├── card_manager.py → src/utils/sprite_loader.py
│   ├── modifier_manager.py → src/utils/sprite_loader.py
│   ├── design_manager.py → src/utils/sprite_loader.py
│   ├── labeling_manager.py → src/ml/dataset_writer.py
│   ├── card_display_manager.py → src/utils/sprite_loader.py
│   └── mode_manager.py
├── src/ui/
│   ├── components.py
│   └── layout_manager.py
├── src/vision/
│   ├── screen_capture.py
│   └── card_recognizer.py → src/utils/sprite_loader.py
└── src/ml/
    ├── dataset_writer.py → src/ml/state_schema.py
    ├── dataset_indexer.py → src/ml/dataset_writer.py
    ├── state_builder.py → src/ml/state_schema.py
    ├── annotation_builder.py
    ├── schema_migrator.py → src/ml/state_schema.py
    └── dataset_reporter.py → src/ml/dataset_indexer.py
```

All managers are independent of each other and only communicate through the main orchestrator, maintaining clean separation of concerns and testability.