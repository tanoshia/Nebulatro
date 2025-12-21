# Balatro AI Agent – Vision + Decision System Plan

This document defines the architecture, data formats, and implementation plan for building an AI agent that can:
1) Read Balatro game state from screen images/video
2) Learn to play the game using that state

The system is intentionally split into **perception** and **decision-making** layers.

---

## High-Level Architecture

### Core Pipeline
```
Screen Capture
↓
Vision / Perception Layer
↓
Structured State JSON
↓
Policy / Decision Agent
↓
Input Controller (mouse / keyboard)
```

**Amazon Nova** is used as:
- A vision-based state extractor (early + fallback)
- A consistency checker and teacher
- A planning assistant, not the main RL policy

---

## Data Formats

### Canonical Game State JSON (Model Input)
This is the only format the policy agent sees.

```json
{
  "screen": {
    "type": "play",
    "substate": "select_cards"
  },
  "hand": [
    {
      "id": "A_spades",
      "rank": "A",
      "suit": "spades",
      "edition": "polychrome",
      "enhancements": [],
      "seal": null
    }
  ],
  "played_cards": [],
  "jokers": [
    {
      "id": "blue_joker",
      "slot": 0,
      "edition": null
    }
  ],
  "economy": {
    "money": 14,
    "interest_cap": 5
  },
  "round": {
    "ante": 3,
    "blind": "big",
    "hands_left": 1,
    "discards_left": 0
  },
  "score": {
    "current": 320,
    "required": 450
  },
  "rng_visible": false
}
```

### Action Space Definition (Policy Output)
Policy outputs actions, not clicks.

```json
{
  "action": "play_cards",
  "hand_indices": [0, 2, 4]
}
```

Other actions: `discard_cards`, `buy_shop_item`, `sell_joker`, `reroll_shop`, `end_round`, `skip_pack`

---

## Implementation Phases

### ✅ **Phase 1: Data Collection & Validation (COMPLETE)**
- Manual labeling GUI with modifier support
- Canonical state JSON generation with schema validation
- Annotation JSON system for rich metadata
- Dual data format architecture

### ✅ **Phase 2: Data Management (COMPLETE)**
- Dataset writer system with atomic operations
- Comprehensive error handling and rollback capabilities
- Batch operations with transaction support
- Dataset indexer with statistics and integrity checking

### ✅ **Phase 2.1: Data Management Extensions (COMPLETE)**
- Schema migration system for version handling
- Advanced reporting and dataset analysis dashboards
- Performance optimization with incremental indexing
- Training readiness assessment and scoring

### 🚧 **Phase 3: Enhanced Card Detection (NEXT)**
**Objective**: Implement robust card detection that can accurately crop individual playing cards from full-screen Balatro screenshots with >95% accuracy.

#### Phase 3.1: Advanced Computer Vision Card Detection
- **YOLOv8-based card detection** trained specifically for Balatro cards
- **Enhanced template matching** using game sprites with rotation/scale invariance
- **Hybrid detection pipeline** combining deep learning + template matching + traditional CV
- **Card region refinement** for exact boundaries and quality assessment

##### 3.1.info: Why YOLOv8 for Card Detection

**YOLOv8 (You Only Look Once v8)** is ideal for Balatro card detection because:
**Real-time Performance**: YOLOv8 can process images in <50ms, enabling real-time screenshot analysis during gameplay.
**Multi-object Detection**: Detects all cards in a single pass rather than sliding window approaches. Perfect for Balatro hands with 1-8 cards.
**Robust to Visual Effects**: Pre-trained on diverse datasets, YOLOv8 handles Balatro's visual effects (foil, holographic, polychrome) better than traditional CV methods.
**Transfer Learning**: We'll fine-tune a pre-trained YOLOv8 model on Balatro-specific data rather than training from scratch, requiring only ~500-1000 annotated screenshots.
**Bounding Box Precision**: YOLOv8 outputs precise bounding boxes with confidence scores, enabling quality filtering and fallback to other methods when confidence is low.
**Implementation Strategy**:
1. Use `ultralytics` Python package for easy YOLOv8 integration
2. Create custom dataset with Nova-generated annotations
3. Fine-tune on Balatro screenshots with data augmentation
4. Deploy with confidence thresholding (>0.7 for auto-accept, <0.7 for template matching fallback)

#### Phase 3.2: Nova-Assisted Card Detection Training
- **Nova card annotation** to generate bounding box training data automatically
- **Active learning pipeline** for continuous model improvement
- **Synthetic data generation** using existing sprite system
- **Custom model training** on Balatro-specific data

#### Phase 3.3: Pipeline Integration
- **Enhanced screenshot processor** with advanced detection methods
- **Card extraction pipeline**: screenshot → individual card crops
- **Performance optimization** with GPU acceleration and batch processing
- **Quality filtering** and validation with metadata extraction

**Success Metrics**: >95% detection accuracy, <500ms processing time, <2% false positives

### 📋 **Phase 4: AI Pipeline Foundation (PLANNED)**

#### Phase 4.1: Nova Integration Setup
- **Nova client integration** with AWS SDK and rate limiting
- **Nova state extractor** converting screenshots to canonical state JSON
- **Integration testing** and performance benchmarking

#### Phase 4.2: Automated Screenshot Processing Pipeline
- **Enhanced screenshot processor** with Nova state extraction
- **Auto-labeling pipeline** with confidence-based filtering
- **Training data pipeline** with augmentation and balancing

#### Phase 4.3: Hybrid CV + Nova System
- **Local CV pipeline** with confidence scoring
- **Nova referee system** for low-confidence cases
- **Hybrid decision engine** orchestrating local CV + Nova workflow

#### Phase 4.4: Policy Agent Foundation
- **State encoder** converting canonical JSON to model tensors
- **Action space implementation** with validation and legality checking
- **Nova demonstration generator** for expert state-action pairs
- **Basic policy network** architecture and training foundation

#### Phase 4.5: Integration and Testing
- **End-to-end pipeline**: Screenshot → State → Action
- **Quality assurance** with comprehensive testing and benchmarking
- **Documentation and examples** for all components

**Success Metrics**: <2s Nova response time, >80% auto-labeling accuracy, >90% state extraction accuracy

---

## Current Status (2025-12-14)

**Foundation Complete**: Phases 1, 2, and 2.1 provide robust data management infrastructure with:
- Schema validation and migration
- Advanced reporting and integrity checking
- Performance-optimized incremental indexing
- Comprehensive dataset analysis and training readiness assessment

**Next Priority**: Phase 3 (Enhanced Card Detection) is critical foundation work. Without accurate card extraction from screenshots, the entire AI pipeline will be built on poor quality data.

**Implementation Sequence**: 
1. **Phase 3**: Accurate Card Detection (3 weeks)
2. **Phase 4**: Nova Integration → State Extraction → Policy Training (10 weeks)

---

## Design Principles

### Data Quality First
- No UI geometry, pixels, or natural language in canonical state
- Deterministic ordering and explicit null values
- Comprehensive validation and schema enforcement

### Modular Architecture
- Clear separation between perception and decision layers
- Nova as teacher/referee, not primary policy
- Fallback hierarchies and confidence scoring

### Performance & Scalability
- GPU acceleration for batch processing
- Incremental indexing and caching
- Real-time processing capabilities

### Cost Management
- Efficient Nova usage with caching and rate limiting
- Local CV models for high-frequency operations
- Quality filtering to minimize manual labeling

The foundation is solid and ready for Phase 3 enhanced card detection.