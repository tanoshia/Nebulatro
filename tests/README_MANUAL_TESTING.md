# Manual Testing for Ground Truth Annotation Integration

This directory contains comprehensive manual tests for the ground truth annotation integration features.

## Manual Test Suite

### `manual_test_ground_truth_annotation.py`

A comprehensive manual test suite that covers all implemented features for the ground truth annotation integration system.

**Features Tested:**
- ✅ Task 1: Annotation window management infrastructure
- ✅ Task 2: Secondary annotation window with zoom/pan functionality  
- ✅ Bounding box drawing and coordinate conversion
- ✅ State management and workflow coordination
- ✅ Error handling and edge cases
- ✅ Complete end-to-end workflow testing

### Usage

```bash
# Run from the Balatro-Calc root directory
python tests/manual_test_ground_truth_annotation.py
```

### Prerequisites

1. **Test Screenshots**: Place Balatro screenshots in `dataset/raw/` directory
   - Supported formats: PNG, JPG, JPEG
   - Recommended: High-resolution screenshots (e.g., 5120x2880)
   - At least one screenshot required for comprehensive testing

2. **Python Environment**: Ensure virtual environment is activated
   ```bash
   source venv/bin/activate
   ```

3. **Dependencies**: All required packages should be installed
   ```bash
   pip install -r requirements.txt
   ```

### Test Structure

The manual test suite is organized into 6 main test categories:

#### Test 1: Annotation Window Management Infrastructure
- Manager initialization and state tracking
- Window spawning with valid/invalid paths
- Window lifecycle management
- **Manual Verification**: Window display and basic functionality

#### Test 2: Secondary Annotation Window Functionality
- Image loading and canvas setup
- Zoom functionality (mouse wheel, keyboard shortcuts)
- Pan functionality (middle mouse button)
- Coordinate system initialization
- **Manual Verification**: Interactive zoom/pan testing

#### Test 3: Bounding Box Functionality
- Bounding box drawing setup and state management
- Coordinate conversion between canvas and image coordinates
- Minimum size validation
- Cancellation functionality
- **Manual Verification**: Drawing boxes at different zoom levels

#### Test 4: State Management and Workflow
- AnnotationStateManager initialization and operations
- Pending annotation workflow
- Card selection handling
- State synchronization between components

#### Test 5: Error Handling and Edge Cases
- Invalid screenshot paths
- Multiple window spawning
- Card selection without pending bounding box
- State manager error conditions

#### Test 6: Comprehensive Workflow Testing
- Complete end-to-end annotation workflow
- Integration between all components
- **Manual Verification**: Full user workflow simulation

### Interactive Testing

The test suite includes interactive prompts where you'll be asked to:

1. **Verify Visual Elements**: Confirm windows display correctly
2. **Test User Interactions**: Try zoom, pan, and bounding box drawing
3. **Validate Workflows**: Complete full annotation sequences
4. **Report Issues**: Mark tests as failed if problems are found

### Expected Results

- **Automated Tests**: Should pass without user intervention
- **Manual Verification**: Requires user interaction and confirmation
- **Success Criteria**: All core functionality works as expected in real-world usage

### Troubleshooting

#### No Test Screenshots Found
```
⚠️  Warning: No test screenshots found in dataset/raw/
```
**Solution**: Add Balatro screenshots to the `dataset/raw/` directory

#### Import Errors
```
ModuleNotFoundError: No module named 'managers.annotation_window_manager'
```
**Solution**: Run the test from the Balatro-Calc root directory

#### Window Display Issues
- Ensure you have a GUI environment (not running headless)
- Check that tkinter is properly installed
- Verify screenshot files are valid image formats

### Critical Testing Principle

**EVERY VISUAL/INTERACTIVE FEATURE REQUIRES TWO TESTS:**

1. **Fully Automatic Test**: Validates logic, initialization, and basic functionality
2. **Manual Test**: Runs automatic test first, then validates real-world user experience

### Why This Two-Stage Approach?

**The Problem with Automated-Only Testing:**
- Automated tests often use mocks that hide visual/interactive issues
- Visual elements frequently pass automated tests but fail in reality
- The zoom functionality bug is a perfect example: automated tests passed, but zoom didn't actually work

**The Manual Test Process:**
1. **Run Automated Tests First**: Ensures basic functionality works before manual validation
2. **Proceed to Manual Validation**: Tests real-world user experience and visual elements
3. **Catch Integration Issues**: Problems between components often only appear during actual usage

### Why Manual Testing?

Manual testing is essential for this feature because:

1. **User Experience**: Automated tests can't verify that zoom/pan feels smooth and responsive
2. **Visual Validation**: Coordinate conversion bugs only manifest during actual drawing
3. **Real-World Usage**: Edge cases appear when users interact with the system naturally
4. **Integration Issues**: Problems between components often only show up during manual workflows
5. **Mocking Limitations**: Automated tests with mocks can miss critical visual/interactive failures

### Reporting Issues

If manual testing reveals problems:

1. **Note the specific test that failed**
2. **Describe the expected vs actual behavior**
3. **Include screenshot information** (size, format, etc.)
4. **Document steps to reproduce**

### Integration with Automated Tests

This manual test suite complements the automated property-based tests in `test_annotation_window_manager.py`:

- **Automated Tests**: Verify logic correctness and handle edge cases
- **Manual Tests**: Verify user experience and real-world functionality
- **Together**: Provide comprehensive coverage of the annotation system

Run both test suites to ensure complete validation of the ground truth annotation integration features.