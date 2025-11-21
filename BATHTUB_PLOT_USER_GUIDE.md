# Bathtub Curve Plot User Guide

## Overview

The **Bathtub Curve Plot** is a critical visualization tool for high-speed SerDes (Serializer/Deserializer) characterization. It shows **Bit Error Rate (BER)** as a function of **sampling point position**, revealing timing and voltage margins in serial communication links.

**Common uses:**
- SerDes link validation
- Timing margin measurement
- Voltage margin analysis
- PCIe, USB, Ethernet compliance testing
- Link budget analysis
- Jitter characterization

---

## Quick Start

### Basic Usage

1. **Load your CSV file** with sample point and BER data
2. **Click the "Plot" button** in the toolbar
3. **Select "bathtub"** from the plot type dropdown
4. **Click "Apply Options"** to generate the plot

### What You'll See

A U-shaped curve (resembling a bathtub) showing:
- **Low BER at center** = Optimal sampling point
- **High BER at edges** = Timing/voltage limits
- **Margin annotation** = Usable window at target BER

---

## Data Format

### Format 1: Single Bathtub Curve

```csv
Sample_UI,BER
-0.50,1.00E-03
-0.40,1.00E-04
-0.30,1.00E-08
-0.20,1.00E-12
-0.10,1.00E-15
0.00,1.00E-16
0.10,1.00E-15
0.20,1.00E-12
0.30,1.00E-08
0.40,1.00E-04
0.50,1.00E-03
```

**Columns:**
- **Sample_UI**: Sampling point position in Unit Intervals (-0.5 to +0.5)
- **BER**: Bit Error Rate (scientific notation)

### Format 2: Dual Bathtub (Left/Right Edges)

```csv
Sample_UI,BER_Left,BER_Right
-0.50,1.00E-03,1.00E-03
-0.40,1.00E-04,1.50E-04
-0.30,1.00E-08,2.00E-08
-0.20,1.00E-12,2.00E-12
0.00,1.00E-16,1.50E-16
0.20,1.00E-12,2.00E-12
0.30,1.00E-08,2.00E-08
0.40,1.00E-04,1.50E-04
0.50,1.00E-03,1.00E-03
```

**Columns:**
- **Sample_UI**: Sampling point position
- **BER_Left**: BER for left edge of eye
- **BER_Right**: BER for right edge of eye

### Format 3: Voltage Bathtub

```csv
Voltage_mV,BER
-250,1.00E-02
-200,1.00E-03
-150,1.00E-05
-100,1.00E-08
-50,1.00E-12
0,1.00E-16
50,1.00E-12
100,1.00E-08
150,1.00E-05
200,1.00E-03
250,1.00E-02
```

**Columns:**
- **Voltage_mV**: Voltage offset in millivolts
- **BER**: Bit Error Rate

---

## Plot Options

### Basic Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **BER target** | Entry | 1e-12 | Target BER for margin calculation |
| **show margins** | Checkbox | On | Display margin annotations |
| **X-axis type** | Dropdown | UI | Unit type: UI / Time (ps) / Voltage (mV) |
| **show target line** | Checkbox | On | Horizontal line at target BER |
| **margin style** | Dropdown | arrows | Annotation style: arrows/lines/shaded |
| **dual curve (L/R)** | Checkbox | Off | Enable left/right edge plotting |

### Additional Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **grid** | Checkbox | On | Show grid lines |
| **legend** | Checkbox | On | Show legend |
| **linewidth** | Slider | 2.0 | Width of BER curve |
| **alpha** | Slider | 1.0 | Curve transparency |

---

## Understanding the Plot

### Bathtub Shape

```
BER
 ^
 |     ╱‾‾‾‾‾‾‾‾‾‾‾‾‾╲
 |    ╱               ╲
 |   ╱                 ╲
 |  ╱                   ╲
 | ╱                     ╲
 |╱_______________________╲
 +--------------------------> Sample Point
   Left    Center    Right
   Edge              Edge
```

### Key Features

- **Center (bottom)**: Optimal sampling point with lowest BER
- **Edges (sides)**: Timing/voltage limits where BER increases
- **Width at target BER**: Usable margin (eye opening)
- **Depth**: BER range (deeper = better signal quality)

### Margin Interpretation

**Timing Margin Example:**
- Target BER: 1e-12
- Left crossing: -0.25 UI
- Right crossing: +0.25 UI
- **Total margin: 0.50 UI** (50% of bit period)

**Good margins:**
- **> 0.4 UI**: Excellent (>40% margin)
- **0.3-0.4 UI**: Good (30-40% margin)
- **0.2-0.3 UI**: Acceptable (20-30% margin)
- **< 0.2 UI**: Marginal (needs improvement)

---

## Examples

### Example 1: Basic Timing Bathtub

**Data:** `bathtub_example_1_single.csv`

**Settings:**
- BER target: 1e-12
- X-axis type: UI
- show margins: On
- margin style: arrows

**Result:** Classic bathtub showing timing margin of ~0.40 UI at 1e-12 BER.

**Use case:** PCIe Gen3 link validation (requires > 0.3 UI margin)

### Example 2: Asymmetric Dual Bathtub

**Data:** `bathtub_example_2_dual.csv`

**Settings:**
- BER target: 1e-12
- dual curve (L/R): On
- margin style: lines

**Result:** Two curves showing left and right edge BER separately, revealing asymmetric eye.

**Use case:** Identifying setup/hold time imbalance

### Example 3: Voltage Bathtub

**Data:** `bathtub_example_3_voltage.csv`

**Settings:**
- BER target: 1e-12
- X-axis type: Voltage (mV)
- margin style: shaded

**Result:** Voltage margin plot showing ±50mV margin at 1e-12 BER.

**Use case:** Receiver sensitivity analysis

### Example 4: Multiple Channels

**Data:** Multiple BER columns (Ch0_BER, Ch1_BER, Ch2_BER)

**Settings:**
- BER target: 1e-15
- show margins: Off (too cluttered)
- legend: On

**Result:** Overlay of multiple bathtubs for channel comparison.

**Use case:** Multi-lane SerDes characterization

---

## Margin Annotation Styles

### Arrows (Default)

```
        ←─────────────→
        Margin: 0.40 UI
```

**Best for:** Single curve, clear margin display

### Lines

```
        |             |
        |             |
     Left          Right
    Margin        Margin
```

**Best for:** Dual curves, precise edge identification

### Shaded

```
        ░░░░░░░░░░░░░
        ░  Margin  ░
        ░░░░░░░░░░░░░
```

**Best for:** Visual emphasis of usable region

---

## BER Target Selection

### Common BER Targets

| Application | Typical BER Target | Margin Requirement |
|-------------|-------------------|-------------------|
| **PCIe Gen3** | 1e-12 | > 0.3 UI |
| **PCIe Gen4/5** | 1e-15 | > 0.25 UI |
| **USB 3.x** | 1e-12 | > 0.3 UI |
| **10G Ethernet** | 1e-12 | > 0.35 UI |
| **25G/50G Ethernet** | 1e-15 | > 0.25 UI |
| **SATA** | 1e-12 | > 0.3 UI |

### Setting BER Target

**In the options panel:**
1. Find "BER target" entry field
2. Enter value in scientific notation: `1e-12`
3. Or decimal: `0.000000000001`
4. Click "Apply Options"

---

## Tips and Best Practices

### Data Collection

✅ **Recommended:**
- 20-50 sample points across the UI
- BER range: 1e-3 to 1e-16 or better
- Symmetric sampling around center
- Multiple measurements for averaging

❌ **Avoid:**
- Too few points (< 10)
- Narrow BER range (< 4 orders of magnitude)
- Asymmetric sampling
- Single-shot measurements

### Measurement Quality

**Good bathtub characteristics:**
- Smooth U-shape
- Symmetric left/right
- Deep center (low BER)
- Clear crossings at target BER

**Problem indicators:**
- Jagged curve = Insufficient data
- Asymmetric = Timing skew
- Shallow = High jitter/noise
- No clear bottom = Link issues

### Margin Analysis

**When analyzing margins:**
1. **Check both timing and voltage** bathtubs
2. **Compare to spec requirements**
3. **Look for asymmetry** (indicates problems)
4. **Verify at multiple BER targets**
5. **Test across temperature/voltage**

### Performance Optimization

**For large datasets:**
- Disable margin annotations initially
- Use "lines" style instead of "arrows"
- Reduce number of curves plotted
- Downsample data if > 100 points

---

## Troubleshooting

### Curve doesn't look like a bathtub

**Possible causes:**
- Wrong data format (X/Y swapped)
- BER not in log scale (should be 1e-12, not 0.000000000001)
- Insufficient data points
- Link not working properly

**Solutions:**
- Verify column order (Sample Point, BER)
- Use scientific notation for BER
- Collect more data points
- Check physical link

### Can't see margin annotation

**Possible causes:**
- BER target outside data range
- Curve doesn't cross target BER
- Margin style set to "shaded" with low alpha

**Solutions:**
- Adjust BER target to match data range
- Collect data with wider BER range
- Try "arrows" margin style
- Check "show margins" is enabled

### Margins seem wrong

**Possible causes:**
- Incorrect BER target
- X-axis type mismatch
- Interpolation issues with sparse data

**Solutions:**
- Verify BER target value
- Set correct X-axis type (UI/ps/mV)
- Collect more data points
- Check data for outliers

### Dual curve not showing

**Possible causes:**
- "dual curve (L/R)" not enabled
- Only 2 columns in data (need 3)
- Column names don't match expected format

**Solutions:**
- Enable "dual curve (L/R)" checkbox
- Ensure 3 columns: Sample, BER_Left, BER_Right
- Check data format

---

## Advanced Features

### 2D Bathtub Analysis

For complete eye characterization, create both:
1. **Horizontal bathtub** (timing)
2. **Vertical bathtub** (voltage)

Compare margins to understand limiting factor.

### Temperature Sweep

Plot bathtubs at different temperatures:
- Cold: -40°C
- Room: 25°C  
- Hot: 85°C or 125°C

Identify temperature-dependent margin degradation.

### Channel Comparison

Overlay bathtubs from multiple channels:
- Identify worst-case channel
- Check for systematic issues
- Validate channel-to-channel variation

### Margin vs Data Rate

Create bathtubs at different data rates:
- Plot margin vs frequency
- Find maximum operating frequency
- Characterize bandwidth limitations

---

## Integration with Other Plots

### Complementary Plots

**Eye Diagram:**
- Visual representation of signal quality
- Bathtub quantifies what eye shows qualitatively

**Jitter Histogram:**
- Shows jitter distribution
- Bathtub reveals impact on BER

**S-Parameters:**
- Channel frequency response
- Explains bathtub shape (loss, reflections)

**Shmoo Plot:**
- 2D parameter sweep (e.g., EQ settings)
- Use bathtub margin as Z-value

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+A** | Select all columns |
| **Mouse Wheel** | Scroll plot options |

---

## Dependencies

### Required
- **matplotlib** >= 3.0
- **pandas** >= 1.0
- **numpy** >= 1.15
- **scipy** >= 1.5 (for interpolation)

### Installation
```bash
pip install matplotlib pandas numpy scipy
```

---

## Export and Reporting

### Saving Plots

1. **Click save icon** in plot toolbar
2. **Choose format:** PNG, PDF, SVG
3. **Set DPI:** 300 for publications

### Margin Report

**Include in reports:**
- Bathtub plot image
- Margin value at target BER
- Test conditions (data rate, temperature, etc.)
- Comparison to spec requirements

---

## Compliance Testing

### PCIe Compliance

**Requirements:**
- Gen3: > 0.3 UI at 1e-12 BER
- Gen4: > 0.25 UI at 1e-15 BER
- Gen5: > 0.25 UI at 1e-15 BER

**Procedure:**
1. Collect bathtub data
2. Set BER target per spec
3. Measure margin
4. Verify > minimum requirement

### USB Compliance

**Requirements:**
- USB 3.0: > 0.3 UI at 1e-12 BER
- USB 3.1: > 0.3 UI at 1e-12 BER

---

## FAQ

**Q: What's a good timing margin?**  
A: Generally > 0.3 UI is good, > 0.4 UI is excellent. Check your specific standard.

**Q: Why is my bathtub asymmetric?**  
A: Could indicate setup/hold time imbalance, ISI, or duty cycle distortion.

**Q: Can I use this for PAM4?**  
A: Yes, but you'll need separate bathtubs for each eye (top, middle, bottom).

**Q: How many data points do I need?**  
A: Minimum 20, recommended 50-100 for smooth curves and accurate margins.

**Q: What if I can't measure to 1e-15?**  
A: Extrapolate from higher BER, but be cautious. Verify with longer tests if possible.

---

## Related Features

- **Shmoo Plot:** For 2D parameter sweeps
- **Density Plot:** For jitter distribution analysis
- **Scatter Plot:** For correlation analysis
- **Line Plot:** For trend analysis

---

## Version History

### Version 1.0.0 (2025-10-05)
- Initial implementation
- Single and dual curve support
- Margin calculation with interpolation
- Multiple annotation styles
- Flexible X-axis types (UI/ps/mV)
- Target BER line overlay
- Auto-detect data format

---

## Support

For issues, questions, or feature requests:
- Check troubleshooting section
- Review example data files
- Refer to main pandastable documentation

---

**Happy Testing!** 📊🔬
