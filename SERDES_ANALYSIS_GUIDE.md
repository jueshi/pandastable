# SerDes Analysis Guide

Complete guide for Eye Diagram and Jitter Histogram analysis in pandastable.

---

## Table of Contents

1. [Overview](#overview)
2. [Eye Diagram](#eye-diagram)
3. [Jitter Histogram](#jitter-histogram)
4. [Example Use Cases](#example-use-cases)
5. [Troubleshooting](#troubleshooting)

---

## Overview

SerDes (Serializer/Deserializer) analysis requires specialized visualization tools to assess signal quality and timing performance. This guide covers two essential plots:

- **Eye Diagram**: Visual representation of signal quality showing jitter, noise, and ISI
- **Jitter Histogram**: Statistical analysis of timing errors separating RJ and DJ components

---

## Eye Diagram

### What is an Eye Diagram?

An eye diagram overlays multiple signal transitions at the bit period (UI - Unit Interval), creating a pattern that resembles an eye. The "opening" of the eye indicates signal quality:

- **Wide eye opening**: Good signal quality, low jitter/noise
- **Narrow eye opening**: Poor signal quality, high jitter/noise
- **Closed eye**: Signal integrity failure

### Data Format

**Required Columns:**
- `Time`: Time samples (seconds, nanoseconds, etc.)
- `Voltage`: Signal amplitude

**Example:**
```csv
Time,Voltage
0.000,0.05
0.001,0.12
0.002,0.25
...
```

### Eye Diagram Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **persistence** | Slider | 100 | Histogram bins for density mode (10-1000) |
| **UI width** | Slider | 1.0 | Unit Interval width scaling (0.5-2.0) |
| **sample rate** | Entry | "" | Sample rate in GS/s (for UI calculation) |
| **bit rate** | Entry | "" | Bit rate in Gbps (for UI calculation) |
| **show mask** | Checkbox | Off | Show eye mask overlay |
| **mask margin** | Slider | 0.3 | Eye mask margin (0.1-0.5) |
| **color mode** | Dropdown | density | Display mode (density/overlay/single) |
| **overlay count** | Slider | 100 | Number of overlays in overlay mode (10-1000) |

### Color Modes

**1. Density Mode (Recommended)**
- Creates 2D histogram showing sample density
- Hot colors indicate high density areas
- Best for visualizing signal distribution
- Uses `persistence` parameter for resolution

**2. Overlay Mode**
- Overlays multiple signal traces
- Shows individual transitions
- Uses `overlay_count` to limit number of traces
- Good for debugging specific transitions

**3. Single Mode**
- Scatter plot of all samples
- Shows every data point
- Can be slow with large datasets

### Step-by-Step: Create Eye Diagram

**1. Prepare Data**
- Ensure you have Time and Voltage columns
- Time should be in consistent units
- Voltage should be normalized if needed

**2. Load Data**
```bash
python examples\csv_browser_v6.x1.2_search_columns.py
# Load: eye_example_1_pcie_gen4.csv
```

**3. Configure Plot**
- Click **Plot** button
- Select **'eye'** plot type
- Scroll to "eye" options section

**4. Set Parameters**
```
bit rate: 16          # PCIe Gen4 = 16 Gbps
persistence: 200      # Higher = more detail
color mode: density   # Best visualization
show mask: On         # Show compliance mask
mask margin: 0.3      # 30% margin
```

**5. Generate Plot**
- Click **"Apply Options"**
- Eye diagram displays

### Interpreting Eye Diagrams

**Eye Opening Measurements:**
- **Eye Height**: Vertical opening (voltage margin)
- **Eye Width**: Horizontal opening (timing margin)
- **Eye Crossing**: Center point where transitions cross

**Quality Indicators:**
- **Clean eye**: Sharp edges, wide opening
- **Jittery eye**: Fuzzy edges, timing uncertainty
- **Noisy eye**: Thick traces, amplitude uncertainty
- **ISI (Inter-Symbol Interference)**: Asymmetric eye, different rise/fall

**Pass/Fail Criteria:**
- Eye must be open at sampling point (UI center)
- Signal must stay outside mask region
- Adequate voltage and timing margins

---

## Jitter Histogram

### What is a Jitter Histogram?

A jitter histogram shows the distribution of timing errors in a signal. It separates:

- **RJ (Random Jitter)**: Unbounded, Gaussian distribution
- **DJ (Deterministic Jitter)**: Bounded, repeatable patterns
- **TJ (Total Jitter)**: RJ + DJ

### Data Format

**Required Column:**
- `Jitter`: Timing error measurements (picoseconds)

**Example:**
```csv
Jitter
-2.5
-2.3
-2.1
...
```

### Jitter Histogram Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **bins** | Slider | 100 | Number of histogram bins (20-500) |
| **show stats** | Checkbox | ✓ On | Show statistics text box |
| **show Gaussian** | Checkbox | ✓ On | Fit and show Gaussian curve |
| **show dual-Dirac** | Checkbox | Off | Show dual-Dirac model (RJ+DJ) |
| **TJ separation** | Entry | "" | Total jitter separation (ps) |
| **show components** | Checkbox | Off | Show RJ/DJ components separately |

### Jitter Analysis Methods

**1. Gaussian Fit (RJ Only)**
- Fits single Gaussian to data
- Assumes only random jitter present
- Reports σ (standard deviation)
- Use when DJ is negligible

**2. Dual-Dirac Model (RJ + DJ)**
- Models jitter as RJ + DJ
- Two Gaussians separated by DJ
- Requires `TJ separation` parameter
- More accurate for real signals

**3. Component Separation**
- Shows RJ and DJ separately
- Requires dual-Dirac model
- Helps identify jitter sources

### Step-by-Step: Create Jitter Histogram

**1. Prepare Data**
- Collect jitter measurements
- One column with timing errors
- Units typically in picoseconds

**2. Load Data**
```bash
python examples\csv_browser_v6.x1.2_search_columns.py
# Load: jitter_example_1_tj.csv
```

**3. Configure Plot**
- Click **Plot** button
- Select **'jitter'** plot type
- Scroll to "jitter" options section

**4. Set Parameters**

**For Simple Analysis:**
```
bins: 100
show stats: On
show Gaussian: On
```

**For Advanced Analysis:**
```
bins: 200
show stats: On
show Gaussian: On
show dual-Dirac: On
TJ separation: 5.0    # Estimated TJ in ps
show components: On
```

**5. Generate Plot**
- Click **"Apply Options"**
- Jitter histogram displays

### Interpreting Jitter Histograms

**Statistics Box Shows:**
- **Mean**: Average jitter (should be near 0)
- **Std Dev**: Standard deviation (RJ estimate)
- **RMS**: Root mean square jitter
- **Peak-Peak**: Total jitter range

**Gaussian Fit:**
- Red curve shows Gaussian fit
- σ value indicates RJ magnitude
- Good fit = mostly random jitter
- Poor fit = significant DJ present

**Dual-Dirac Fit:**
- Green dashed curve shows combined model
- Separates RJ and DJ components
- RJ value = unbounded jitter
- DJ value = bounded jitter

**Component Plots:**
- Blue dotted line = RJ component
- Shows pure random jitter distribution
- Helps identify jitter sources

---

## Example Use Cases

### Use Case 1: PCIe Gen4 Eye Diagram

**Requirement:** Verify eye opening meets PCIe Gen4 spec

**Data:** `eye_example_1_pcie_gen4.csv`

**Settings:**
```
Plot type: eye
bit rate: 16
persistence: 200
color mode: density
show mask: On
mask margin: 0.3
```

**Expected Result:**
- Clear eye opening
- Signal stays outside mask
- Eye height > 100 mV
- Eye width > 0.4 UI

**Pass/Fail:**
- ✓ PASS if eye is open and outside mask
- ✗ FAIL if eye is closed or touches mask

---

### Use Case 2: Jitter Budget Analysis

**Requirement:** Separate RJ and DJ for jitter budget

**Data:** `jitter_example_1_tj.csv`

**Settings:**
```
Plot type: jitter
bins: 200
show stats: On
show Gaussian: On
show dual-Dirac: On
TJ separation: 5.0
show components: On
```

**Expected Result:**
- Histogram with dual peaks (if DJ present)
- Gaussian fit (red) for RJ
- Dual-Dirac fit (green) for RJ+DJ
- Component separation (blue) for RJ only

**Analysis:**
- RJ value from dual-Dirac fit
- DJ value from dual-Dirac fit
- TJ = RJ + DJ at target BER

---

### Use Case 3: Signal Integrity Debug

**Objective:** Identify ISI and crosstalk issues

**Eye Diagram Settings:**
```
color mode: overlay
overlay count: 50
show mask: Off
```

**Look For:**
- Asymmetric eye (different rise/fall) = ISI
- Multiple eye levels = amplitude noise
- Horizontal spreading = timing jitter
- Vertical spreading = voltage noise

**Jitter Histogram Settings:**
```
bins: 100
show Gaussian: On
```

**Look For:**
- Non-Gaussian shape = DJ present
- Multiple peaks = periodic jitter
- Long tails = crosstalk or reflections

---

### Use Case 4: BER Prediction

**Objective:** Predict BER from jitter measurements

**Method:**
1. Measure TJ at target BER (e.g., 1E-12)
2. Use dual-Dirac model to separate RJ and DJ
3. Calculate BER from RJ and DJ components

**Settings:**
```
Plot type: jitter
show dual-Dirac: On
TJ separation: <measured TJ>
show components: On
```

**Calculation:**
```
TJ = RJ * Q(BER) + DJ
Where Q(1E-12) ≈ 7.03
```

---

## Troubleshooting

### Eye Diagram Issues

**Issue: Eye is completely closed**

**Causes:**
- Excessive jitter or noise
- Wrong bit rate setting
- Incorrect UI calculation

**Solutions:**
1. Verify bit rate: `bit rate = data rate in Gbps`
2. Check UI width: Try `ui_width = 0.5` or `2.0`
3. Verify data quality: Check signal amplitude
4. Reduce persistence: Lower value shows more detail

---

**Issue: Eye looks wrong/distorted**

**Causes:**
- Incorrect time units
- Wrong sample rate
- Data not synchronized

**Solutions:**
1. Check time column units (should be consistent)
2. Verify sample rate matches data
3. Ensure data starts at transition edge
4. Try different color modes

---

**Issue: No eye pattern visible**

**Causes:**
- Not enough data
- UI period too large/small
- Wrong columns selected

**Solutions:**
1. Ensure at least 100 samples per UI
2. Manually set bit rate
3. Check Time and Voltage columns exist
4. Verify data is numeric

---

**Issue: Mask not showing**

**Causes:**
- show_mask not enabled
- Mask outside plot range

**Solutions:**
1. Enable "show mask" checkbox
2. Adjust mask_margin (0.1-0.5)
3. Check voltage range covers mask

---

### Jitter Histogram Issues

**Issue: Gaussian fit fails**

**Causes:**
- Not enough data points
- Non-Gaussian distribution
- Extreme outliers

**Solutions:**
1. Collect more jitter samples (>100)
2. Remove outliers
3. Try dual-Dirac model instead
4. Increase bins for better resolution

---

**Issue: Dual-Dirac fit fails**

**Causes:**
- Wrong TJ separation value
- Insufficient DJ component
- Poor initial guess

**Solutions:**
1. Estimate TJ from histogram width
2. Try different TJ separation values
3. Ensure DJ is actually present
4. Use Gaussian fit first to estimate RJ

---

**Issue: Statistics look wrong**

**Causes:**
- Wrong units (ps vs ns)
- Outliers skewing results
- Insufficient data

**Solutions:**
1. Verify jitter units are consistent
2. Remove outliers (>3σ)
3. Collect more samples
4. Check for data errors

---

**Issue: Components not showing**

**Causes:**
- show_components not enabled
- Dual-Dirac not enabled
- No TJ separation specified

**Solutions:**
1. Enable "show dual-Dirac" first
2. Enter TJ separation value
3. Enable "show components"
4. Ensure dual-Dirac fit succeeded

---

## Best Practices

### Eye Diagram Best Practices

**1. Data Collection**
- Capture at least 1000 UIs
- Use high sample rate (>10 samples/UI)
- Ensure signal is properly terminated
- Minimize probe loading

**2. Analysis**
- Start with density mode
- Use overlay mode for debugging
- Enable mask for compliance testing
- Measure at UI center (0.5 UI)

**3. Reporting**
- Document bit rate and UI
- Report eye height and width
- Include mask margin results
- Note any anomalies

### Jitter Histogram Best Practices

**1. Data Collection**
- Collect >1000 jitter samples
- Use consistent measurement point
- Remove setup/hold violations
- Calibrate measurement equipment

**2. Analysis**
- Start with Gaussian fit
- Use dual-Dirac for real signals
- Separate RJ and DJ components
- Calculate TJ at target BER

**3. Reporting**
- Report RJ, DJ, and TJ values
- Include BER target
- Document measurement conditions
- Compare to specifications

---

## Quick Reference

### Eye Diagram Data Format

```csv
Time,Voltage
0.000,0.05
0.001,0.12
...
```

### Jitter Histogram Data Format

```csv
Jitter
-2.5
-2.3
...
```

### Common Bit Rates

| Standard | Bit Rate | UI Period |
|----------|----------|-----------|
| PCIe Gen3 | 8 Gbps | 125 ps |
| PCIe Gen4 | 16 Gbps | 62.5 ps |
| PCIe Gen5 | 32 Gbps | 31.25 ps |
| USB 3.2 Gen 2 | 10 Gbps | 100 ps |
| 100G Ethernet | 25.78 Gbps | 38.8 ps |

### Jitter Specifications

| Standard | TJ Spec (UI) | Notes |
|----------|--------------|-------|
| PCIe Gen4 | 0.3 UI | At 1E-12 BER |
| PCIe Gen5 | 0.25 UI | At 1E-12 BER |
| USB 3.2 | 0.35 UI | At 1E-12 BER |
| 100G Ethernet | 0.28 UI | At 1E-12 BER |

---

## Summary Checklist

### To Create Eye Diagram:

- [ ] Prepare CSV with Time and Voltage columns
- [ ] Load CSV in pandastable
- [ ] Click Plot button
- [ ] Select 'eye' plot type
- [ ] Set bit rate or sample rate
- [ ] Choose color mode (density recommended)
- [ ] Enable mask if needed
- [ ] Click "Apply Options"
- [ ] Analyze eye opening

### To Create Jitter Histogram:

- [ ] Prepare CSV with Jitter column
- [ ] Load CSV in pandastable
- [ ] Click Plot button
- [ ] Select 'jitter' plot type
- [ ] Set number of bins
- [ ] Enable Gaussian fit
- [ ] (Optional) Enable dual-Dirac with TJ separation
- [ ] (Optional) Show RJ/DJ components
- [ ] Click "Apply Options"
- [ ] Analyze jitter distribution

---

**Last Updated:** 2025-10-05  
**Version:** 1.0  
**Status:** ✅ Complete and Ready to Use
