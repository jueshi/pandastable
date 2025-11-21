# Bathtub Curve Plot - Product Requirements Document

## Executive Summary

**Feature:** Bathtub Curve Plot for SerDes BER Analysis  
**Priority:** HIGH (Critical for SerDes validation)  
**Effort:** LOW (2-4 hours)  
**Value:** HIGH (Essential SerDes measurement)  
**Status:** Ready for Implementation

---

## 1. Overview

### What is a Bathtub Curve?

A bathtub curve is a fundamental plot in high-speed SerDes characterization that shows **Bit Error Rate (BER)** as a function of **sampling point position** within a Unit Interval (UI). The plot gets its name from its characteristic U-shape, resembling a bathtub when viewed from the side.

### Why It Matters

- **Critical for SerDes validation:** Shows timing margins at target BER
- **Compliance testing:** Required for PCIe, USB, Ethernet standards
- **Link budget analysis:** Quantifies timing margins
- **Debug tool:** Identifies jitter and noise issues

---

## 2. User Stories

### Primary Users
- **SerDes Validation Engineers:** Characterizing link performance
- **SI Engineers:** Analyzing timing margins
- **Test Engineers:** Compliance testing
- **Debug Engineers:** Troubleshooting link issues

### Use Cases

**UC1: Timing Margin Measurement**
```
As a validation engineer,
I want to measure timing margins at 1e-12 BER,
So that I can verify link meets spec requirements.
```

**UC2: Horizontal Eye Opening**
```
As an SI engineer,
I want to visualize the horizontal eye opening,
So that I can assess timing closure.
```

**UC3: Jitter Analysis**
```
As a debug engineer,
I want to see BER vs sample point,
So that I can identify jitter issues.
```

**UC4: Dual Bathtub (Voltage + Timing)**
```
As a validation engineer,
I want to plot both horizontal and vertical bathtubs,
So that I can see complete eye margins.
```

---

## 3. Functional Requirements

### 3.1 Core Functionality

**FR1: Basic Bathtub Plot**
- Plot BER (Y-axis, log scale) vs Sample Point (X-axis, UI)
- Support single or dual curves (left/right edge)
- Automatic log scale detection (1e-3 to 1e-18)

**FR2: Data Format Support**
```csv
# Format 1: Single curve
Sample_Point_UI, BER
-0.5, 1e-3
-0.4, 1e-6
...

# Format 2: Dual curve (left/right)
Sample_Point_UI, BER_Left, BER_Right
-0.5, 1e-3, 1e-3
...

# Format 3: Voltage bathtub
Voltage_mV, BER
-200, 1e-3
-150, 1e-6
...
```

**FR3: Margin Calculation**
- Calculate timing margin at target BER (default: 1e-12)
- Display margin value on plot
- Support custom BER targets

**FR4: Multiple Curves**
- Support multiple bathtub curves on same plot
- Different channels, conditions, or configurations
- Legend with curve identification

### 3.2 Plot Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **ber_target** | Entry | 1e-12 | Target BER for margin calculation |
| **show_margins** | Checkbox | True | Display margin annotations |
| **log_scale** | Checkbox | True | Use log scale for BER axis |
| **dual_curve** | Checkbox | Auto | Plot left/right edges separately |
| **x_axis_type** | Dropdown | UI | UI or Time (ps) or Voltage (mV) |
| **show_target_line** | Checkbox | True | Show horizontal line at target BER |
| **margin_style** | Dropdown | arrows | arrows/lines/shaded |
| **curve_style** | Dropdown | line | line/scatter/both |

### 3.3 Visual Elements

**Required:**
- Log scale Y-axis (BER)
- Linear X-axis (Sample Point in UI or ps)
- Grid lines
- Legend
- Target BER horizontal line

**Optional:**
- Margin arrows/annotations
- Shaded margin region
- Data point markers
- Spec limit lines
- Title with margin value

---

## 4. Technical Specifications

### 4.1 Input Data

**Minimum Requirements:**
- 2 columns: Sample_Point, BER
- At least 10 data points
- BER values in range 1e-18 to 1e-1

**Optimal:**
- 50-200 data points
- BER range covering target ±3 orders of magnitude
- Symmetric sampling around center

### 4.2 Calculations

**Margin Calculation:**
```python
# Find sample points where BER crosses target
left_margin = find_crossing(sample_points, ber_left, ber_target)
right_margin = find_crossing(sample_points, ber_right, ber_target)
total_margin = right_margin - left_margin
```

**Interpolation:**
- Linear interpolation in log(BER) space
- For finding exact crossing points

### 4.3 Plot Rendering

**Y-Axis (BER):**
- Log scale (10^-18 to 10^-1)
- Scientific notation labels
- Minor grid lines

**X-Axis (Sample Point):**
- Linear scale
- Units: UI (default), ps, or mV
- Centered at 0 (optimal sample point)

**Annotations:**
- Margin value in UI or ps
- Target BER value
- Optional: Eye opening percentage

---

## 5. User Interface

### 5.1 Plot Type Selection

Add to existing plot type dropdown:
```
kinds = [..., 'bathtub']
```

### 5.2 Options Panel

**New "bathtub" options group:**
```python
'bathtub': [
    'ber_target',
    'show_margins', 
    'x_axis_type',
    'show_target_line',
    'margin_style',
    'dual_curve'
]
```

### 5.3 Column Selection

**Auto-detection:**
- If 2 columns: Single bathtub
- If 3 columns: Dual bathtub (left/right)
- First column: X-axis (sample point)
- Remaining: BER values

**Manual selection:**
- X parameter: Sample point column
- Y parameter: BER column(s)

---

## 6. Implementation Plan

### Phase 1: Core Implementation (2 hours)

**Step 1: Add plot type**
- Add 'bathtub' to kinds list
- Create bathtub() method skeleton

**Step 2: Basic plotting**
- Plot BER vs sample point
- Log scale Y-axis
- Handle single/dual curves

**Step 3: Margin calculation**
- Find BER crossings
- Calculate margin
- Display on plot

### Phase 2: Enhanced Features (1 hour)

**Step 4: Options integration**
- Add bathtub options group
- Implement option handlers
- Update UI

**Step 5: Visual enhancements**
- Target BER line
- Margin annotations
- Styling options

### Phase 3: Polish (1 hour)

**Step 6: Error handling**
- Validate data format
- Handle edge cases
- User-friendly errors

**Step 7: Documentation**
- Code comments
- User guide
- Example data

---

## 7. Success Criteria

### Must Have (MVP)
✅ Plot BER vs sample point with log scale  
✅ Calculate and display timing margin  
✅ Support single and dual curves  
✅ Target BER line overlay  
✅ Auto-detect data format  

### Should Have
✅ Margin annotations with arrows  
✅ Multiple curve support  
✅ Customizable BER target  
✅ Grid and styling options  

### Nice to Have
⭐ Shaded margin region  
⭐ Export margin values  
⭐ Spec limit overlays  
⭐ Interactive margin adjustment  

---

## 8. Test Cases

### TC1: Single Bathtub Curve
```csv
Sample_UI, BER
-0.5, 1e-3
-0.3, 1e-9
0.0, 1e-15
0.3, 1e-9
0.5, 1e-3
```
**Expected:** U-shaped curve, margin ~0.6 UI at 1e-12

### TC2: Dual Bathtub (Left/Right)
```csv
Sample_UI, BER_Left, BER_Right
-0.5, 1e-3, 1e-3
-0.3, 1e-9, 1e-10
0.0, 1e-15, 1e-16
0.3, 1e-10, 1e-9
0.5, 1e-3, 1e-3
```
**Expected:** Two curves, separate margins

### TC3: Voltage Bathtub
```csv
Voltage_mV, BER
-200, 1e-3
-100, 1e-9
0, 1e-15
100, 1e-9
200, 1e-3
```
**Expected:** Voltage margin ~200mV at 1e-12

### TC4: Multiple Channels
```csv
Sample_UI, Ch0_BER, Ch1_BER, Ch2_BER
...
```
**Expected:** Three bathtub curves with legend

---

## 9. Dependencies

### Required
- matplotlib >= 3.0
- numpy >= 1.15
- pandas >= 1.0
- scipy >= 1.5 (for interpolation)

### Integration
- Uses existing pandastable plot infrastructure
- Follows same pattern as shmoo/density plots
- Reuses option system

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sparse data points | Inaccurate margins | Interpolation + warnings |
| BER range too narrow | Can't find crossing | Auto-extend range, warn user |
| Non-monotonic data | Incorrect margins | Data validation, sort by X |
| Very large BER range | Plot readability | Auto-adjust Y limits |

---

## 11. Future Enhancements

### Version 2.0
- **2D Bathtub:** Combined horizontal + vertical
- **Extrapolation:** Predict BER beyond measured range
- **Jitter separation:** RJ/DJ from bathtub shape
- **Confidence intervals:** Statistical error bars

### Version 3.0
- **Interactive:** Click to adjust BER target
- **Comparison mode:** Before/after optimization
- **Export:** Margin report generation
- **Templates:** Standard compliance overlays

---

## 12. Acceptance Criteria

**Definition of Done:**
- [ ] Bathtub plot type available in dropdown
- [ ] Plots BER vs sample point with log scale
- [ ] Calculates and displays timing margin
- [ ] Supports single and dual curves
- [ ] Options panel with key settings
- [ ] Handles edge cases gracefully
- [ ] Documentation complete
- [ ] Example data provided
- [ ] User guide created

---

## 13. Timeline

**Total Effort:** 4 hours

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Core Implementation | 2 hours | Basic bathtub plot working |
| Enhanced Features | 1 hour | Options and annotations |
| Polish & Docs | 1 hour | Complete and documented |

**Target Completion:** Same day

---

## 14. Metrics

**Success Metrics:**
- Time to create bathtub plot: < 30 seconds
- Margin accuracy: ±0.01 UI
- Supports BER range: 1e-18 to 1e-1
- User satisfaction: 9/10

---

## Appendix A: Example Use

```python
# Load bathtub data
df = pd.read_csv('bathtub_data.csv')

# Plot in pandastable
# 1. Click Plot button
# 2. Select 'bathtub' plot type
# 3. Set BER target: 1e-12
# 4. Enable margin display
# 5. Click Apply

# Result: Bathtub curve with margin annotation
```

## Appendix B: Data Format Examples

See `examples/bathtub_example_*.csv` for sample data files.

---

**Status:** ✅ Ready for Implementation  
**Next Step:** Begin Phase 1 - Core Implementation
