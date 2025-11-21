# S-Parameter Plot - Product Requirements Document

## Executive Summary

**Feature:** S-Parameter Plot for Channel Characterization  
**Priority:** HIGH (Essential for SerDes SI analysis)  
**Effort:** MEDIUM (4-6 hours)  
**Value:** HIGH (Critical measurement)  
**Status:** Ready for Implementation

---

## 1. Overview

### What are S-Parameters?

S-Parameters (Scattering Parameters) describe the electrical behavior of linear networks when undergoing steady-state stimulation by electrical signals. They are fundamental for characterizing high-speed channels, connectors, and transmission lines.

**Common S-Parameters:**
- **S21 (Insertion Loss):** Signal transmission from port 1 to port 2
- **S11 (Return Loss):** Signal reflection at port 1
- **S12 (Reverse Insertion Loss):** Signal transmission from port 2 to port 1
- **S22 (Return Loss):** Signal reflection at port 2

### Why It Matters

- **Channel characterization:** Understand signal loss and reflections
- **SI analysis:** Identify bandwidth limitations
- **Compliance testing:** Verify channel meets specs
- **Debug tool:** Locate impedance mismatches and discontinuities
- **Equalization design:** Determine EQ requirements

---

## 2. User Stories

### Primary Users
- **SI Engineers:** Channel characterization
- **SerDes Validation Engineers:** Link analysis
- **Hardware Engineers:** PCB design validation
- **Test Engineers:** Compliance testing

### Use Cases

**UC1: Insertion Loss Analysis**
```
As an SI engineer,
I want to plot S21 vs frequency,
So that I can measure channel loss at Nyquist frequency.
```

**UC2: Return Loss Analysis**
```
As a hardware engineer,
I want to plot S11 vs frequency,
So that I can identify impedance mismatches.
```

**UC3: Multi-Parameter Comparison**
```
As a validation engineer,
I want to plot S11, S21, S12, S22 on the same plot,
So that I can see the complete channel response.
```

**UC4: Spec Limit Overlay**
```
As a test engineer,
I want to overlay spec limits on S-parameter plots,
So that I can verify compliance.
```

---

## 3. Functional Requirements

### 3.1 Core Functionality

**FR1: Basic S-Parameter Plot**
- Plot magnitude (dB) vs frequency (GHz)
- Support multiple S-parameters on same plot
- Log scale X-axis (frequency)
- Linear scale Y-axis (dB)

**FR2: Data Format Support**
```csv
# Format 1: Single S-parameter
Frequency_GHz, S21_dB
0.1, -0.5
1.0, -2.1
5.0, -8.5
10.0, -15.2
...

# Format 2: Multiple S-parameters
Frequency_GHz, S11_dB, S21_dB, S12_dB, S22_dB
0.1, -25.0, -0.5, -0.5, -25.0
1.0, -22.0, -2.1, -2.1, -22.0
...

# Format 3: With phase
Frequency_GHz, S21_dB, S21_Phase_deg
0.1, -0.5, -5.2
1.0, -2.1, -18.5
...
```

**FR3: Spec Limit Overlays**
- Add horizontal/vertical spec limit lines
- Configurable limit values
- Pass/fail region shading

**FR4: Multiple Traces**
- Support multiple channels/conditions
- Different line styles/colors
- Legend with trace identification

### 3.2 Plot Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **log_freq** | Checkbox | True | Logarithmic frequency axis |
| **show_phase** | Checkbox | False | Show phase on secondary Y-axis |
| **spec_limit** | Entry | "" | Spec limit value (dB) |
| **limit_type** | Dropdown | None | None/Horizontal/Vertical |
| **nyquist_marker** | Checkbox | False | Mark Nyquist frequency |
| **data_rate** | Entry | "" | Data rate for Nyquist (Gbps) |
| **freq_range** | Entry | "" | Frequency range (e.g., "0.1-30") |
| **db_range** | Entry | "" | dB range (e.g., "-40-0") |

### 3.3 Visual Elements

**Required:**
- Log scale X-axis (frequency in GHz)
- Linear Y-axis (magnitude in dB)
- Grid lines (major and minor)
- Legend
- Multiple trace support

**Optional:**
- Phase plot on secondary Y-axis
- Spec limit lines/shading
- Nyquist frequency marker
- Data point markers
- Smith chart view (future)

---

## 4. Technical Specifications

### 4.1 Input Data

**Minimum Requirements:**
- 2 columns: Frequency, S-parameter magnitude
- At least 10 frequency points
- Frequency in GHz or Hz (auto-detect)
- Magnitude in dB

**Optimal:**
- 100-10,000 frequency points
- Multiple S-parameters
- Phase data included
- Linear frequency spacing in log domain

### 4.2 Calculations

**Frequency Unit Conversion:**
```python
# Auto-detect and convert to GHz
if max(freq) > 1000:  # Likely in MHz or Hz
    if max(freq) > 1e6:
        freq_ghz = freq / 1e9  # Hz to GHz
    else:
        freq_ghz = freq / 1000  # MHz to GHz
else:
    freq_ghz = freq  # Already in GHz
```

**Nyquist Frequency:**
```python
# Calculate Nyquist from data rate
nyquist_ghz = data_rate_gbps / 2
```

**Spec Compliance:**
```python
# Check if S21 meets spec at Nyquist
s21_at_nyquist = interpolate(freq, s21, nyquist_ghz)
passes = s21_at_nyquist >= spec_limit
```

### 4.3 Plot Rendering

**X-Axis (Frequency):**
- Log scale (default) or linear
- Units: GHz
- Range: Auto or user-specified

**Y-Axis (Magnitude):**
- Linear scale in dB
- Range: Auto or user-specified
- Typical: -40 to 0 dB

**Secondary Y-Axis (Phase):**
- Linear scale in degrees
- Range: -180 to +180 degrees
- Optional display

---

## 5. User Interface

### 5.1 Plot Type Selection

Add to existing plot type dropdown:
```
kinds = [..., 'sparam']
```

### 5.2 Options Panel

**New "sparam" options group:**
```python
'sparam': [
    'log_freq',
    'show_phase',
    'spec_limit',
    'limit_type',
    'nyquist_marker',
    'data_rate',
    'freq_range',
    'db_range'
]
```

### 5.3 Column Selection

**Auto-detection:**
- First column: Frequency
- Remaining columns: S-parameters (magnitude)
- If column name contains "phase": Phase data

**Manual selection:**
- X parameter: Frequency column
- Y parameter: S-parameter column(s)

---

## 6. Implementation Plan

### Phase 1: Core Implementation (3 hours)

**Step 1: Add plot type**
- Add 'sparam' to kinds list
- Create sparam() method skeleton

**Step 2: Basic plotting**
- Plot magnitude vs frequency
- Log scale X-axis
- Handle multiple S-parameters

**Step 3: Auto-detection**
- Detect frequency units
- Identify S-parameter columns
- Handle phase data

### Phase 2: Enhanced Features (2 hours)

**Step 4: Options integration**
- Add sparam options group
- Implement option handlers
- Update UI

**Step 5: Spec limits**
- Horizontal/vertical limit lines
- Pass/fail shading
- Nyquist marker

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
✅ Plot S-parameters vs frequency with log scale  
✅ Support multiple S-parameters on same plot  
✅ Auto-detect frequency units  
✅ Grid and legend  
✅ Linear dB scale  

### Should Have
✅ Spec limit overlays  
✅ Nyquist frequency marker  
✅ Frequency range control  
✅ dB range control  

### Nice to Have
⭐ Phase plot on secondary axis  
⭐ Smith chart view  
⭐ Group delay calculation  
⭐ TDR/TDT conversion  

---

## 8. Test Cases

### TC1: Single S21 Plot
```csv
Frequency_GHz, S21_dB
0.1, -0.5
1.0, -2.0
5.0, -8.0
10.0, -15.0
20.0, -25.0
```
**Expected:** Smooth curve showing insertion loss vs frequency

### TC2: Multiple S-Parameters
```csv
Frequency_GHz, S11_dB, S21_dB, S22_dB
0.1, -25, -0.5, -25
1.0, -22, -2.0, -22
5.0, -18, -8.0, -18
10.0, -15, -15.0, -15
```
**Expected:** Three curves with legend

### TC3: With Phase
```csv
Frequency_GHz, S21_dB, S21_Phase
0.1, -0.5, -5
1.0, -2.0, -18
5.0, -8.0, -90
10.0, -15.0, -180
```
**Expected:** Magnitude + phase on dual Y-axes

### TC4: Spec Limit Overlay
```csv
Frequency_GHz, S21_dB
# With spec_limit = -10 dB at Nyquist (14 GHz for 28G)
```
**Expected:** Horizontal line at -10 dB, marker at 14 GHz

---

## 9. Dependencies

### Required
- matplotlib >= 3.0
- numpy >= 1.15
- pandas >= 1.0
- scipy >= 1.5 (for interpolation)

### Integration
- Uses existing pandastable plot infrastructure
- Follows same pattern as bathtub/shmoo plots
- Reuses option system

---

## 10. Example Use Cases

### PCIe Gen4 Channel Validation
**Requirement:** S21 > -10 dB at 8 GHz (Nyquist for 16 GT/s)

**Settings:**
- Plot: S21_dB vs Frequency_GHz
- spec_limit: -10
- data_rate: 16
- nyquist_marker: On

**Result:** Verify channel meets insertion loss spec

### Impedance Mismatch Detection
**Requirement:** S11 < -15 dB across band

**Settings:**
- Plot: S11_dB vs Frequency_GHz
- spec_limit: -15
- limit_type: Horizontal

**Result:** Identify frequency ranges with poor return loss

### Multi-Channel Comparison
**Data:** S21 for 4 different channels

**Settings:**
- Plot: Ch0_S21, Ch1_S21, Ch2_S21, Ch3_S21
- log_freq: On
- legend: On

**Result:** Compare channel-to-channel variation

---

## 11. Future Enhancements

### Version 2.0
- **Smith Chart:** Impedance visualization
- **Group Delay:** Calculate from phase
- **TDR/TDT:** Time domain conversion
- **De-embedding:** Remove fixtures

### Version 3.0
- **Touchstone Import:** Read .s2p files
- **Cascade Analysis:** Combine multiple S-parameters
- **Equalization Preview:** Show post-EQ response

---

## 12. Acceptance Criteria

**Definition of Done:**
- [ ] S-parameter plot type available in dropdown
- [ ] Plots magnitude vs frequency with log scale
- [ ] Supports multiple S-parameters
- [ ] Auto-detects frequency units
- [ ] Options panel with key settings
- [ ] Spec limit overlay working
- [ ] Handles edge cases gracefully
- [ ] Documentation complete
- [ ] Example data provided
- [ ] User guide created

---

## 13. Timeline

**Total Effort:** 6 hours

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Core Implementation | 3 hours | Basic S-param plot working |
| Enhanced Features | 2 hours | Spec limits and options |
| Polish & Docs | 1 hour | Complete and documented |

**Target Completion:** 1 day

---

## 14. Metrics

**Success Metrics:**
- Time to create S-param plot: < 30 seconds
- Frequency range: 0.01 GHz to 100 GHz
- Magnitude range: -60 dB to +20 dB
- User satisfaction: 9/10

---

## Appendix A: S-Parameter Basics

### Common Measurements

| Parameter | Name | Typical Range | Good Value |
|-----------|------|---------------|------------|
| **S21** | Insertion Loss | -30 to 0 dB | > -10 dB at Nyquist |
| **S11** | Input Return Loss | -40 to 0 dB | < -15 dB |
| **S22** | Output Return Loss | -40 to 0 dB | < -15 dB |
| **S12** | Reverse Isolation | -60 to 0 dB | < -30 dB |

### Interpretation

- **S21 close to 0 dB:** Low loss (good)
- **S21 very negative:** High loss (bad)
- **S11 very negative:** Good impedance match
- **S11 close to 0 dB:** Poor impedance match

---

**Status:** ✅ Ready for Implementation  
**Next Step:** Begin Phase 1 - Core Implementation
