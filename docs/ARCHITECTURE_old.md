# Nebulatro Architecture

## Overview

Nebulatro uses a modular Python package architecture with clear separation of concerns. The main application file (`src/main.py`) is a lean orchestrator (~215 lines) that coordinates specialized manager components organized into logical packages.

## Package Structure

```
src/
├── main.py              # Application entry point
├── managers/            # Business logic
│   ├── card_manager.py
│   ├── modifier_manager.py
│   └── design_manager.py
├── ui/                  # User interface
│   ├── components.py
│   └── layout_manager.py
└── utils/               # Utilities
    └── sprite_loader.py
```

## Component Breakdown

### src/main.py (215 lines)
**Main orchestrator** - Coordinates all components and handles high-level application flow
- Initializes all managers
- Handles event routing
- Manages application lifecycle
- Loads configuration

### src/ui/components.py (146 lines)
**UI layout and setup** - Creates and manages all UI widgets
- Main window layout
- Title and filter controls
- Canvas setup (modifiers, cards, order display)
- Button creation
- Filter variable management

### src/managers/card_manager.py (303 lines)
**Card loading and tracking** - Manages card display and order tracking
- Loads cards from sprite sheets
- Creates clickable card buttons
- Tracks card order with modifiers
- Updates order display
- Saves card sequences to CSV
- Card name conversion (sprite index → readable format)

### src/managers/modifier_manager.py (315 lines)
**Modifier system** - Handles all modifier functionality
- Loads modifiers (enhancements, editions, seals, debuff)
- Manages modifier selection state
- Applies modifiers to cards with blend modes
- Handles filter modes (All Modifiers, Scoring Only)
- Implements blend modes (normal, multiply, color)
- Manages render modes (overlay, background)

### src/managers/design_manager.py (171 lines)
**Card designs** - Manages card appearance options
- Opens design popup window
- Handles contrast switching (Standard/High Contrast)
- Manages face card collaborations (24 variants)
- Loads collab options from resource_mapping.json
- Applies collab sprites to face cards (J, Q, K)

### src/ui/layout_manager.py (174 lines)
**Dynamic positioning** - Handles window resizing and layout calculations
- Recalculates card positions on resize
- Manages dynamic spacing (up to 70% overlap)
- Positions modifiers by category with gaps
- Auto-sizes window to fit content
- Handles z-ordering for overlapping elements

### src/utils/sprite_loader.py
**Sprite loading** - Loads sprites from sheets with resource mapping
- Parses sprite sheet filenames
- Extracts sprites from grids
- Composites card faces with backing
- Manages resource mapping

## Data Flow

```
User Action
    ↓
src/main.py (orchestrator)
    ↓
├─→ src/ui/components.py (UI events)
├─→ src/managers/card_manager.py (card clicks)
├─→ src/managers/modifier_manager.py (modifier selection)
├─→ src/managers/design_manager.py (design changes)
└─→ src/ui/layout_manager.py (window resize)
    ↓
src/utils/sprite_loader.py (loads sprites)
```

## Key Design Principles

1. **Separation of Concerns** - Each module has a single, well-defined responsibility
2. **Loose Coupling** - Modules communicate through the orchestrator, not directly
3. **Clear Interfaces** - Managers expose simple methods for the orchestrator to call
4. **Event-Driven** - UI events flow through the orchestrator to appropriate managers
5. **Testability** - Modular design makes individual components easier to test

## Benefits

- **Maintainability** - Easy to locate and modify specific functionality
- **Readability** - Main file clearly shows application flow
- **Extensibility** - New features can be added as new managers
- **Debugging** - Issues isolated to specific modules
- **Collaboration** - Multiple developers can work on different modules

## Adding New Features

To add a new feature:

1. Determine which manager it belongs to (or create a new one)
2. Add methods to the appropriate manager
3. Add event handlers in `nebulatro.py`
4. Wire up UI elements in `ui_components.py` if needed
5. Update knowledgebase.md with the changes

## Module Dependencies

```
src/main.py
├── src/ui/components.py
├── src/managers/card_manager.py
│   └── src/utils/sprite_loader.py
├── src/managers/modifier_manager.py
│   └── src/utils/sprite_loader.py
├── src/managers/design_manager.py
│   └── src/utils/sprite_loader.py
└── src/ui/layout_manager.py
```

All managers are independent of each other and only communicate through the main orchestrator.

## Configuration Files

Configuration files are organized in the `config/` directory:
- `config/card_order_config.json` - Card display order and modifier settings
- `config/resource_mapping.json` - Maps game resources to sprite definitions
