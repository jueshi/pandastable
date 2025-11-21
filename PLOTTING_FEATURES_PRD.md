# Product Requirements Document: Pandastable Plotting Features

**Version:** 1.0  
**Date:** 2025-10-04  
**Status:** Approved for Implementation

---

## Executive Summary

This PRD outlines the implementation plan for completing incomplete plotting features in the pandastable library. Four main features have been identified as incomplete or missing: Density Plot (Complete), 2D Shmoo Plot, Data Streaming, and Enhanced 3D Plotting capabilities.

---

## 1. Feature: Density Plot Implementation

### 1.1 Overview
**Priority:** HIGH (Quick Win)  
**Effort:** 1-2 days  
**Status:** Missing Implementation

### 1.2 Current State
- Listed in valid plot types (`valid_kwds` line 72)
- Appears in UI plot type selector (line 1464)
- Configuration options defined
- **No backend implementation** - falls through to default line plot

### 1.3 Requirements

#### Functional Requirements
- FR1.1: Support kernel density estimation for single and multiple columns
- FR1.2: Allow bandwidth parameter customization (scott, silverman, custom)
- FR1.3: Support fill under curve option
- FR1.4: Enable multiple density overlays with transparency
- FR1.5: Optional rug plot to show actual data points
- FR1.6: Support for both univariate and bivariate density plots

#### Technical Requirements
- TR1.1: Use `scipy.stats.gaussian_kde` for KDE computation
- TR1.2: Fallback to pandas built-in density plot if scipy unavailable
- TR1.3: Handle NaN values gracefully
- TR1.4: Support all standard matplotlib styling options

#### UI Requirements
- UR1.1: Add bandwidth selection dropdown (auto/scott/silverman/custom)
- UR1.2: Add custom bandwidth numeric entry
- UR1.3: Add "fill under curve" checkbox
- UR1.4: Add "show rug plot" checkbox

### 1.4 Implementation Details

```python
def density(self, df, ax, kwds):
    """Create kernel density estimation plot"""
    
    # Extract parameters
    bw_method = kwds.get('bw_method', 'scott')
    fill = kwds.get('fill', False)
    show_rug = kwds.get('show_rug', False)
    alpha = kwds.get('alpha', 0.7)
    
    # Implementation steps:
    # 1. Validate numeric data
    # 2. Compute KDE for each column
    # 3. Plot density curves
    # 4. Optionally fill under curves
    # 5. Optionally add rug plot
    # 6. Style and return axes
```

### 1.5 Acceptance Criteria
- AC1.1: Density plot appears correctly for single column
- AC1.2: Multiple columns show overlaid densities with legend
- AC1.3: Bandwidth parameter affects curve smoothness
- AC1.4: Fill option works correctly
- AC1.5: Rug plot shows data distribution
- AC1.6: Works with grouped data (by parameter)

---

## 2. Feature: 2D Shmoo Plot Implementation

### 2.1 Overview
**Priority:** HIGH (Engineering Essential)  
**Effort:** 2-3 days  
**Status:** Not Implemented

### 2.2 Current State
- Not listed in plot types
- No implementation exists
- Common requirement for semiconductor/hardware testing
- Used for visualizing parameter sweeps and pass/fail regions

### 2.3 Requirements

#### Functional Requirements
- FR2.1: Support 2D parameter sweep visualization (X vs Y with color-coded Z values)
- FR2.2: Display pass/fail regions with customizable thresholds
- FR2.3: Support continuous and discrete data
- FR2.4: Overlay contour lines for value levels
- FR2.5: Support multiple shmoo plots in subplots
- FR2.6: Interactive threshold adjustment
- FR2.7: Export shmoo data with pass/fail statistics

#### Technical Requirements
- TR2.1: Use matplotlib's `pcolormesh` or `imshow` for fast rendering
- TR2.2: Support irregular grid interpolation using scipy
- TR2.3: Handle NaN values as "not tested" regions
- TR2.4: Efficient rendering for large parameter sweeps (>10000 points)
- TR2.5: Support both heatmap and contour representations

#### UI Requirements
- UR2.1: X-axis parameter selection dropdown
- UR2.2: Y-axis parameter selection dropdown  
- UR2.3: Z-value (color) parameter selection dropdown
- UR2.4: Pass/fail threshold entry fields (min/max)
- UR2.5: Colormap selection for pass/fail visualization
- UR2.6: Contour lines checkbox
- UR2.7: Grid interpolation method selection
- UR2.8: Show statistics checkbox (pass rate, margin, etc.)

### 2.4 Implementation Details

```python
def shmoo(self, df, ax, kwds):
    """
    Create 2D shmoo plot for parameter sweep visualization.
    
    Parameters:
    - df: DataFrame with X, Y, and Z columns
    - ax: matplotlib axes
    - kwds: plot keywords including:
      - x_param: X-axis parameter column name
      - y_param: Y-axis parameter column name
      - z_param: Z-value parameter column name
      - threshold_min: Minimum passing threshold
      - threshold_max: Maximum passing threshold
      - colormap: Colormap for visualization
      - show_contours: Whether to overlay contour lines
      - interpolation: 'none', 'nearest', 'bilinear', 'cubic'
      - show_stats: Display pass/fail statistics
    """
```

### 2.5 Acceptance Criteria
- AC2.1: Shmoo plot displays correctly for regular grid data
- AC2.2: Irregular grid data is interpolated smoothly
- AC2.3: Pass/fail regions are clearly distinguished
- AC2.4: Threshold changes update visualization
- AC2.5: Contour lines overlay correctly
- AC2.6: Statistics display shows pass rate and margins
- AC2.7: Works with grouped data for multiple shmoos
- AC2.8: Export includes pass/fail summary

---

## 3. Feature: Data Streaming

### 3.1 Overview
**Priority:** MEDIUM (High Value)  
**Effort:** 3-5 days  
**Status:** Stub Implementation (line ~2100)

### 2.2 Current State
- Method exists: `AnimateOptions.stream()`
- Marked as "not implemented yet"
- Has placeholder code with empty endpoints
- Basic threading infrastructure exists

### 2.3 Requirements

#### Functional Requirements
- FR2.1: Support HTTP/HTTPS endpoint streaming
- FR2.2: Support multiple data formats (JSON, CSV, XML)
- FR2.3: Configurable refresh intervals (0.1s to 60s)
- FR2.4: Authentication support (API keys, Bearer tokens, Basic Auth)
- FR2.5: Automatic reconnection on connection failure
- FR2.6: Data validation and error handling
- FR2.7: Buffer management for historical data
- FR2.8: Start/Stop/Pause controls

#### Technical Requirements
- TR2.1: Use `requests` library for HTTP streaming
- TR2.2: Implement async/threaded data fetching
- TR2.3: Queue-based data buffer (max 10000 points)
- TR2.4: Exponential backoff for reconnection (1s, 2s, 4s, 8s, max 30s)
- TR2.5: Timeout handling (30s default)
- TR2.6: Memory management for long-running streams

#### UI Requirements
- UR2.1: Endpoint URL text entry
- UR2.2: Authentication method dropdown
- UR2.3: API key/token secure entry field
- UR2.4: Refresh interval slider (0.1-60s)
- UR2.5: Start/Stop/Pause buttons
- UR2.6: Connection status indicator (connected/disconnected/error)
- UR2.7: Data format selector (JSON/CSV/XML)
- UR2.8: Buffer size configuration
- UR2.9: Error message display area

### 2.4 Implementation Details

```python
def stream(self):
    """Stream data from external source and update plot in real-time"""
    
    # Configuration
    endpoint = self.kwds.get('endpoint', '')
    refresh_rate = self.kwds.get('refresh_rate', 1.0)
    auth_type = self.kwds.get('auth_type', 'none')
    auth_token = self.kwds.get('auth_token', '')
    data_format = self.kwds.get('data_format', 'json')
    
    # Implementation phases:
    # Phase 1: Connection management
    # Phase 2: Data fetching loop
    # Phase 3: Data parsing and validation
    # Phase 4: Table/plot update
    # Phase 5: Error handling and reconnection
```

### 2.5 Acceptance Criteria
- AC2.1: Successfully connects to valid HTTP endpoint
- AC2.2: Parses JSON and CSV data correctly
- AC2.3: Updates plot at specified refresh rate
- AC2.4: Handles authentication correctly
- AC2.5: Reconnects automatically on connection loss
- AC2.6: Displays appropriate error messages
- AC2.7: Stop button terminates streaming cleanly
- AC2.8: No memory leaks during long-running streams
- AC2.9: Performance: handles up to 100 updates/second

---

## 3. Feature: Enhanced 3D Plotting

### 3.1 Overview
**Priority:** LOW (Enhancement)  
**Effort:** 3-4 days  
**Status:** Partial Implementation

### 3.2 Current State
- Basic 3D plotting exists (scatter, bar, contour, wireframe, surface)
- Parametric mode defined but not implemented
- Limited data shape handling
- Basic viewing controls exist

### 3.3 Requirements

#### Functional Requirements
- FR3.1: Implement parametric mode for 3D curves
- FR3.2: Support 3D line plots
- FR3.3: Add 3D filled contour plots
- FR3.4: Support irregular grid data
- FR3.5: Multiple interpolation methods
- FR3.6: Animated 3D rotation
- FR3.7: Preset viewing angles

#### Technical Requirements
- TR3.1: Use scipy.interpolate for irregular grids
- TR3.2: Support parametric equations: x(t), y(t), z(t)
- TR3.3: Efficient meshgrid generation
- TR3.4: Animation frame rate control
- TR3.5: Export 3D plots as interactive HTML (plotly)

#### UI Requirements
- UR3.1: Parametric equation entry fields (x(t), y(t), z(t))
- UR3.2: Parameter range controls (t_min, t_max, steps)
- UR3.3: Interpolation method dropdown
- UR3.4: Animation controls (play/pause/speed)
- UR3.5: Viewing angle presets (top/side/isometric/custom)
- UR3.6: Export to HTML button

### 3.4 Implementation Details

```python
def plot3D_parametric(self, ax, kwds):
    """Plot parametric 3D curves"""
    
    # Parse parametric equations
    x_expr = kwds.get('x_param', 't')
    y_expr = kwds.get('y_param', 't')
    z_expr = kwds.get('z_param', 't')
    t_min = kwds.get('t_min', 0)
    t_max = kwds.get('t_max', 10)
    steps = kwds.get('steps', 100)
    
    # Implementation:
    # 1. Parse expressions safely
    # 2. Generate parameter array
    # 3. Evaluate expressions
    # 4. Plot 3D curve
    # 5. Handle errors
```

### 3.5 Acceptance Criteria
- AC3.1: Parametric mode plots curves correctly
- AC3.2: 3D line plots work with time series data
- AC3.3: Irregular grid interpolation produces smooth surfaces
- AC3.4: Animation rotates plot smoothly
- AC3.5: Preset angles work correctly
- AC3.6: HTML export creates interactive plot

---

## 4. Implementation Phases

### Phase 1: Density Plot (Week 1)
**Days 1-2:**
- Implement density plot method
- Add to plot type switch statement
- Add configuration options
- Update UI widgets
- Write unit tests
- Documentation

### Phase 2: Data Streaming (Week 2-3)
**Days 3-7:**
- Design streaming architecture
- Implement connection management
- Add data parsing for JSON/CSV
- Implement UI controls
- Add authentication support
- Error handling and reconnection
- Performance testing
- Documentation

### Phase 3: Enhanced 3D Plotting (Week 4)
**Days 8-11:**
- Implement parametric mode
- Add 3D line plots
- Improve interpolation
- Add animation controls
- Implement HTML export
- Write tests
- Documentation

### Phase 4: Testing & Polish (Week 5)
**Days 12-14:**
- Integration testing
- Performance optimization
- Bug fixes
- User documentation
- Example notebooks
- Release preparation

---

## 5. Technical Architecture

### 5.1 Dependencies
```python
# Required
matplotlib >= 3.0
pandas >= 1.0
numpy >= 1.18

# Optional (with graceful degradation)
scipy >= 1.5  # For density plots and interpolation
requests >= 2.25  # For data streaming
plotly >= 5.0  # For interactive 3D exports
```

### 5.2 Code Organization
```
pandastable/
├── plotting.py (main file)
│   ├── PlotViewer class
│   │   ├── density() - NEW
│   │   ├── plot3D_parametric() - NEW
│   │   └── existing methods...
│   └── AnimateOptions class
│       ├── stream() - IMPLEMENT
│       └── existing methods...
├── streaming.py - NEW (optional: separate module)
└── tests/
    ├── test_density.py - NEW
    ├── test_streaming.py - NEW
    └── test_3d_plots.py - ENHANCED
```

---

## 6. Testing Strategy

### 6.1 Unit Tests
- Test each plot type independently
- Test with various data shapes and types
- Test error conditions
- Test parameter validation

### 6.2 Integration Tests
- Test plot type switching
- Test with real data sources
- Test streaming with mock server
- Test UI interactions

### 6.3 Performance Tests
- Large dataset handling (>100k points)
- Streaming performance (updates/second)
- Memory usage over time
- Rendering performance

### 6.4 User Acceptance Testing
- Create example notebooks
- Test with real-world use cases
- Gather feedback from beta users

---

## 7. Documentation Requirements

### 7.1 Code Documentation
- Docstrings for all new methods
- Inline comments for complex logic
- Type hints where applicable

### 7.2 User Documentation
- Updated user guide with new features
- Example notebooks for each feature
- API reference updates
- Migration guide (if breaking changes)

### 7.3 Developer Documentation
- Architecture diagrams
- Contribution guidelines
- Testing instructions

---

## 8. Success Metrics

### 8.1 Functionality
- All acceptance criteria met
- Zero critical bugs
- <5 minor bugs at release

### 8.2 Performance
- Density plot renders in <1s for 10k points
- Streaming handles 100 updates/second
- 3D plots render in <2s for 10k points

### 8.3 Quality
- 90%+ code coverage
- All tests passing
- Documentation complete

### 8.4 User Satisfaction
- Positive feedback from beta testers
- Feature requests addressed
- No major usability issues

---

## 9. Risks and Mitigation

### 9.1 Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| scipy dependency issues | Medium | Low | Graceful degradation, use pandas fallback |
| Streaming performance | High | Medium | Implement buffering, downsampling |
| 3D rendering performance | Medium | Medium | Add LOD, progressive rendering |
| Memory leaks in streaming | High | Medium | Implement buffer limits, cleanup |

### 9.2 Schedule Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Underestimated complexity | Medium | Medium | Prioritize features, phase release |
| Testing takes longer | Low | High | Parallel testing, automated tests |
| Dependency conflicts | Medium | Low | Virtual env testing, version pinning |

---

## 10. Release Plan

### 10.1 Version Strategy
- **v1.1.0** - Density plot implementation
- **v1.2.0** - Data streaming feature
- **v1.3.0** - Enhanced 3D plotting
- **v1.4.0** - Polish and optimization

### 10.2 Rollout Strategy
1. Alpha release to core contributors
2. Beta release to selected users
3. Release candidate with full documentation
4. General availability release
5. Post-release monitoring and hotfixes

---

## 11. Appendix

### 11.1 References
- Matplotlib documentation: https://matplotlib.org/
- Pandas plotting: https://pandas.pydata.org/docs/reference/plotting.html
- Scipy KDE: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html

### 11.2 Change Log
- 2025-10-04: Initial PRD created
- 2025-10-04: Approved for implementation

---

**Approved by:** Development Team  
**Next Review:** After Phase 1 completion
