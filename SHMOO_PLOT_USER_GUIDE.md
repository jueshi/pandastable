# Shmoo Plot User Guide

## Overview

The **Shmoo Plot** is a 2D visualization tool for parameter sweep data, commonly used in:
- Semiconductor testing
- Hardware validation
- System characterization
- Multi-parameter optimization

A shmoo plot displays how a measured value (Z) varies across a grid of two parameters (X and Y), typically showing pass/fail regions or performance characteristics.

---

## Quick Start

### Basic Usage

1. **Load your CSV file** with at least 3 numeric columns
2. **Click the "Plot" button** in the toolbar
3. **Select "shmoo"** from the plot type dropdown
4. **Configure X/Y/Z parameters** (optional - auto-selects if left blank)
5. **Click "Apply Options"** to generate the plot

### Column Selection

**You don't need to select specific columns!** The shmoo plot automatically uses all available columns. You can:
- Select any columns (or none)
- Use Ctrl+A to select all
- Select just one column
- **All methods work the same way**

---

## Choosing Columns to Plot

### Method 1: Use X/Y/Z Parameter Dropdowns (Recommended)

In the plot viewer, scroll down to the **"shmoo"** options section. You'll find three dropdowns:

| Parameter | Description | Example |
|-----------|-------------|---------|
| **X parameter** | Column for X-axis (horizontal) | Voltage |
| **Y parameter** | Column for Y-axis (vertical) | Current |
| **Z value** | Column for color/value | Measurement |

**Example with 5 columns:**

If your CSV has: `Voltage, Current, Temperature, Measurement, Power`

You can choose any combination:
- X parameter: "Voltage"
- Y parameter: "Temperature"
- Z value: "Power"

This creates a Voltage vs Temperature plot, colored by Power values.

### Method 2: Auto-Selection (Leave Blank)

If you leave X/Y/Z parameters **empty**, the plot automatically uses:
- **X parameter** = First numeric column
- **Y parameter** = Second numeric column
- **Z value** = Third numeric column

---

## Plot Options

### Basic Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **X parameter** | Dropdown | Auto | Column for X-axis |
| **Y parameter** | Dropdown | Auto | Column for Y-axis |
| **Z value** | Dropdown | Auto | Column for color values |
| **colormap** | Dropdown | RdYlGn | Color scheme for the plot |
| **grid** | Checkbox | On | Show grid lines |
| **colorbar** | Checkbox | On | Show color scale bar |

### Advanced Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **min threshold** | Entry | None | Minimum value threshold (colors values below) |
| **max threshold** | Entry | None | Maximum value threshold (colors values above) |
| **show contours** | Checkbox | Off | Overlay contour lines |
| **contour levels** | Entry | 10 | Number of contour lines |
| **interpolation** | Dropdown | nearest | Interpolation method (none/nearest/bilinear/cubic) |
| **show statistics** | Checkbox | Off | Display statistics on plot |
| **marker size** | Slider | 50 | Size of data point markers |
| **show markers** | Checkbox | Off | Show individual data points |

---

## Examples

### Example 1: Basic Voltage-Current Sweep

**Data:** `Voltage, Current, Measurement`

**Settings:**
- X parameter: Voltage
- Y parameter: Current
- Z value: Measurement
- colormap: RdYlGn

**Result:** Shows measurement values across voltage-current sweep, with green for high values and red for low values.

### Example 2: Temperature Characterization with Thresholds

**Data:** `Voltage, Temperature, Performance`

**Settings:**
- X parameter: Voltage
- Y parameter: Temperature
- Z value: Performance
- min threshold: 80
- max threshold: 95
- show contours: On

**Result:** Highlights regions where performance is below 80 (fail) or above 95 (excellent), with contour lines showing performance levels.

### Example 3: Multi-Parameter Analysis

**Data:** `Voltage, Current, Temperature, Measurement, Power`

**Settings:**
- X parameter: Voltage
- Y parameter: Temperature
- Z value: Measurement
- interpolation: bilinear
- show markers: On

**Result:** Smooth interpolated plot of measurement vs voltage and temperature, with markers showing actual data points.

---

## Tips and Best Practices

### Data Requirements

✅ **Minimum:** 3 numeric columns (X, Y, Z)
✅ **Recommended:** Regular grid data (evenly spaced X and Y values)
✅ **Optimal:** 100-10,000 data points

### Choosing Colormaps

| Colormap | Best For |
|----------|----------|
| **RdYlGn** | Pass/fail data (red=bad, green=good) |
| **viridis** | Continuous measurements |
| **coolwarm** | Data with positive/negative values |
| **Spectral** | Wide range of values |

### Interpolation Methods

| Method | When to Use |
|--------|-------------|
| **none** | Sparse data, want to see gaps |
| **nearest** | Discrete measurements, blocky appearance |
| **bilinear** | Smooth appearance, regular grid |
| **cubic** | Very smooth, dense data |

### Performance Tips

- **Large datasets (>10k points):** Use "nearest" interpolation
- **Sparse data:** Disable interpolation or use "nearest"
- **Dense data:** Use "bilinear" or "cubic" for smooth plots
- **Slow rendering:** Disable markers and contours

---

## Troubleshooting

### "Shmoo plot requires at least 3 numeric columns (X, Y, Z)"

**Cause:** Your data doesn't have enough numeric columns.

**Solution:**
- Check that your CSV has at least 3 columns with numeric data
- Remove or ignore non-numeric columns
- Verify data loaded correctly

### Plot appears blank or empty

**Cause:** Selected columns contain NaN or non-numeric values.

**Solution:**
- Choose different columns from the X/Y/Z dropdowns
- Check your data for missing values
- Ensure columns contain numeric data

### Colors don't match expected values

**Cause:** Threshold settings or colormap choice.

**Solution:**
- Adjust min/max thresholds
- Try a different colormap
- Check that Z values are in expected range

### Plot is too blocky/pixelated

**Cause:** Using "nearest" interpolation or sparse data.

**Solution:**
- Change interpolation to "bilinear" or "cubic"
- Collect more data points
- Use a finer grid spacing

### Contours don't show

**Cause:** Contour levels too high or data range too small.

**Solution:**
- Reduce number of contour levels
- Check that Z values have sufficient variation
- Adjust threshold settings

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+A** | Select all columns in table |
| **Mouse Wheel** | Scroll through plot options |

---

## Technical Details

### Data Processing

1. **Column Selection:** Uses specified X/Y/Z parameters or auto-selects first 3 numeric columns
2. **NaN Handling:** Automatically removes rows with NaN values in X, Y, or Z
3. **Grid Creation:** Creates 2D grid from unique X and Y values
4. **Interpolation:** Fills grid using specified interpolation method
5. **Rendering:** Displays as heatmap with optional contours and markers

### Supported Data Formats

- **CSV files** with numeric columns
- **Pandas DataFrames** with numeric data
- **Regular grids** (recommended)
- **Irregular grids** (supported with interpolation)

### Output

- **Interactive matplotlib plot** with zoom, pan, save capabilities
- **Color bar** showing value scale
- **Optional contours** for level visualization
- **Optional markers** for data point locations
- **Optional statistics** overlay

---

## Related Features

- **Density Plot:** For 1D distribution visualization
- **Scatter Plot:** For general X-Y relationships
- **Heatmap:** For correlation matrices
- **Contour Plot:** For 3D surface visualization

---

## Version History

### Version 1.0.0 (2025-10-05)
- Initial implementation
- X/Y/Z parameter selection
- Threshold support
- Contour overlays
- Multiple interpolation methods
- Statistics display
- Marker overlay
- Auto-column selection for <3 column selections

---

## Support

For issues, questions, or feature requests, please refer to the main pandastable documentation or submit an issue to the project repository.

---

**Happy Plotting!** 📊🎨
