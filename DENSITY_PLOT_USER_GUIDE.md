# Density Plot User Guide

## Overview

The **Density Plot** (also called Kernel Density Estimation or KDE plot) visualizes the probability density function of continuous data. It's a smoothed version of a histogram that shows the distribution shape of your data.

**Common uses:**
- Understanding data distribution
- Identifying peaks and modes
- Detecting outliers
- Comparing multiple distributions
- Statistical analysis

---

## Quick Start

### Basic Usage

1. **Load your CSV file** with numeric columns
2. **Select columns** you want to analyze (or use Ctrl+A for all)
3. **Click the "Plot" button** in the toolbar
4. **Select "density"** from the plot type dropdown
5. **Click "Apply Options"** to generate the plot

### What You'll See

A smooth curve showing:
- **Peaks** = Most common values
- **Width** = Data spread/variance
- **Shape** = Distribution pattern (normal, skewed, bimodal, etc.)

---

## Plot Options

### Basic Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **bandwidth method** | Dropdown | scott | Method for calculating smoothness |
| **fill under curve** | Checkbox | Off | Fill area under the density curve |
| **show rug plot** | Checkbox | Off | Show individual data points along x-axis |
| **alpha** | Slider | 0.7 | Transparency (0=transparent, 1=opaque) |
| **colormap** | Dropdown | tab10 | Color scheme for multiple curves |
| **linewidth** | Slider | 1.5 | Width of the density curve |
| **grid** | Checkbox | Off | Show grid lines |
| **legend** | Checkbox | On | Show legend for multiple curves |
| **subplots** | Checkbox | Off | Create separate plot for each column |

### Bandwidth Methods

The bandwidth controls how smooth the curve is:

| Method | Description | When to Use |
|--------|-------------|-------------|
| **scott** | Scott's rule (default) | General purpose, works for most data |
| **silverman** | Silverman's rule | Alternative automatic method |
| **0.1** | Very narrow bandwidth | Detailed view, large datasets |
| **0.2** | Narrow bandwidth | More detail, less smoothing |
| **0.5** | Medium bandwidth | Balanced smoothing |
| **1.0** | Wide bandwidth | Very smooth, hides detail |

**Rule of thumb:**
- **Lower bandwidth** (0.1-0.2) = More detail, less smooth
- **Higher bandwidth** (0.5-1.0) = More smooth, less detail

---

## Examples

### Example 1: Single Column Distribution

**Data:** `Temperature` column with 1000 measurements

**Settings:**
- Select: Temperature column
- bandwidth method: scott
- fill under curve: On
- alpha: 0.5

**Result:** Smooth curve showing temperature distribution with filled area underneath.

### Example 2: Comparing Multiple Distributions

**Data:** `Height_Male, Height_Female, Height_Child` columns

**Settings:**
- Select: All three columns
- bandwidth method: scott
- fill under curve: Off
- legend: On
- alpha: 0.7

**Result:** Three overlapping curves showing height distributions for different groups.

### Example 3: Detailed Analysis with Rug Plot

**Data:** `Response_Time` column with 500 measurements

**Settings:**
- Select: Response_Time column
- bandwidth method: 0.2 (narrow)
- show rug plot: On
- fill under curve: On

**Result:** Detailed density curve with individual data points shown as ticks along the x-axis.

### Example 4: Multiple Subplots

**Data:** `Q1_Score, Q2_Score, Q3_Score, Q4_Score` (quarterly scores)

**Settings:**
- Select: All four columns
- bandwidth method: scott
- subplots: On
- fill under curve: On

**Result:** Four separate density plots arranged in a grid, one for each quarter.

---

## Interpreting Density Plots

### Distribution Shapes

| Shape | What It Means | Example |
|-------|---------------|---------|
| **Single peak (unimodal)** | Data clusters around one value | Normal distribution, test scores |
| **Two peaks (bimodal)** | Two distinct groups | Male/female heights combined |
| **Multiple peaks** | Multiple distinct groups | Multi-modal data |
| **Skewed right** | Long tail to the right | Income distribution |
| **Skewed left** | Long tail to the left | Age at retirement |
| **Uniform/flat** | Evenly distributed | Random numbers |

### Key Features

- **Peak height** = Probability density (higher = more common)
- **Peak location** = Most common value (mode)
- **Curve width** = Data spread (wider = more variance)
- **Area under curve** = Always equals 1 (100% probability)

---

## Tips and Best Practices

### Data Size Recommendations

| Dataset Size | Recommended Settings |
|--------------|---------------------|
| **< 100 points** | Any settings, enable rug plot |
| **100-1,000 points** | Default settings work well |
| **1,000-10,000 points** | Disable rug plot |
| **> 10,000 points** | Consider histogram instead or use wider bandwidth |

### Choosing Bandwidth

**Start with default (scott)**, then adjust if needed:

✅ **Use narrower bandwidth (0.1-0.2) when:**
- You have lots of data (>1000 points)
- You want to see fine details
- You suspect multiple peaks

✅ **Use wider bandwidth (0.5-1.0) when:**
- You have sparse data (<100 points)
- Data is very noisy
- You want general trend only

### Comparing Distributions

**Best practices:**
- Use same bandwidth for all curves
- Enable legend
- Use transparency (alpha < 1) for overlapping curves
- Consider fill under curve for better visibility
- Use subplots if curves overlap too much

### Performance Optimization

- **Disable rug plot** for datasets > 500 points
- **Use wider bandwidth** for faster rendering
- **Use subplots** instead of overlapping many curves
- **Downsample** very large datasets before plotting

---

## Troubleshooting

### Curve looks too jagged/bumpy

**Cause:** Bandwidth too narrow for the data.

**Solution:**
- Increase bandwidth (try 0.5 or 1.0)
- Use 'scott' or 'silverman' method
- Check if you have enough data points

### Curve looks too smooth/flat

**Cause:** Bandwidth too wide.

**Solution:**
- Decrease bandwidth (try 0.1 or 0.2)
- Use 'scott' method
- Verify data has actual variation

### Can't see multiple curves

**Cause:** Curves overlapping or same color.

**Solution:**
- Reduce alpha to 0.5-0.7 for transparency
- Enable fill under curve
- Use subplots instead
- Change colormap

### Rug plot cluttered/unreadable

**Cause:** Too many data points.

**Solution:**
- Disable rug plot for large datasets
- Use only for < 500 points
- Consider histogram instead

### "No numeric data" error

**Cause:** Selected columns are not numeric.

**Solution:**
- Select only numeric columns
- Check data types in your CSV
- Remove or convert non-numeric columns

### Plot is blank

**Cause:** All values are the same or NaN.

**Solution:**
- Check data has variation
- Remove NaN values
- Verify correct columns selected

---

## Comparison: Density Plot vs Histogram

| Feature | Density Plot | Histogram |
|---------|--------------|-----------|
| **Appearance** | Smooth curve | Bars |
| **Bin dependency** | No bins needed | Requires bin selection |
| **Smoothness** | Adjustable via bandwidth | Fixed by bin width |
| **Overlapping** | Easy to compare multiple | Harder to overlap |
| **Best for** | Continuous distributions | Discrete counts |
| **Data size** | Works well with any size | Better for large datasets |

**When to use Density Plot:**
- Comparing multiple distributions
- Want smooth, professional appearance
- Continuous data
- Need to see distribution shape clearly

**When to use Histogram:**
- Want exact counts
- Very large datasets (>100k points)
- Discrete or categorical data
- Need to see actual frequencies

---

## Advanced Features

### Fill Under Curve

**Purpose:** Makes individual distributions more visible when comparing multiple curves.

**Settings:**
- fill under curve: On
- alpha: 0.3-0.5 (for transparency)

**Best for:** Comparing 2-4 distributions

### Rug Plot

**Purpose:** Shows exact location of each data point.

**Settings:**
- show rug plot: On
- Recommended for: < 500 points

**Best for:** 
- Identifying outliers
- Seeing data concentration
- Small to medium datasets

### Subplots

**Purpose:** Creates separate plot for each column.

**Settings:**
- subplots: On
- Automatic grid layout

**Best for:**
- Comparing many distributions (>4)
- When curves overlap too much
- Detailed individual analysis

---

## Statistical Interpretation

### What Density Values Mean

- **Y-axis value** = Probability density (not probability!)
- **Area under curve** = Probability
- **Peak height** = Relative frequency

**Example:**
If density = 0.5 at x = 10, it means:
- Values near 10 are relatively common
- NOT that there's a 50% probability at x = 10

### Common Patterns

| Pattern | Statistical Term | Interpretation |
|---------|-----------------|----------------|
| Single peak, symmetric | Normal/Gaussian | Random variation around mean |
| Single peak, right skew | Positive skew | Few high outliers |
| Single peak, left skew | Negative skew | Few low outliers |
| Two peaks | Bimodal | Two distinct groups |
| Flat | Uniform | No preferred values |
| Multiple peaks | Multimodal | Multiple groups/clusters |

---

## Dependencies

### Required
- **matplotlib** >= 3.0
- **pandas** >= 1.0
- **numpy** >= 1.15

### Optional
- **scipy** >= 1.5 (for KDE computation)
  - If scipy not installed, falls back to pandas KDE
  - Install: `pip install scipy`

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+A** | Select all columns in table |
| **Mouse Wheel** | Scroll through plot options |

---

## Related Features

- **Histogram:** For discrete frequency counts
- **Box Plot:** For quartile-based distribution view
- **Violin Plot:** Combines box plot with density
- **Scatter Plot:** For relationship between variables

---

## Version History

### Version 1.0.0 (2025-10-05)
- Initial implementation
- Basic density plot with KDE
- Bandwidth selection (scott, silverman, custom)
- Fill under curve option
- Rug plot for data points
- Multiple curve support
- Subplot layout
- Scipy and pandas KDE support

---

## Examples Gallery

### Example Code Snippets

```python
# Example 1: Basic density plot
import pandas as pd
from pandastable import Table
import tkinter as tk

df = pd.read_csv('data.csv')
root = tk.Tk()
table = Table(root, dataframe=df)
table.show()
# Click Plot → Select 'density' → Apply Options
```

### Sample Data Format

```csv
Temperature,Humidity,Pressure
23.5,45.2,1013.2
24.1,46.8,1012.8
23.8,44.5,1013.5
...
```

---

## Support

For issues, questions, or feature requests:
- Check the troubleshooting section above
- Refer to main pandastable documentation
- Submit issues to the project repository

---

## Quick Reference Card

### Most Common Settings

**General exploration:**
- bandwidth: scott
- fill: Off
- rug: Off (unless < 500 points)

**Comparing distributions:**
- bandwidth: scott
- fill: On
- alpha: 0.5
- legend: On

**Detailed analysis:**
- bandwidth: 0.2
- fill: On
- rug: On (if < 500 points)
- grid: On

**Many columns:**
- bandwidth: scott
- subplots: On
- fill: On

---

**Happy Analyzing!** 📊📈
