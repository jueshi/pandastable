# Density Plot - Quick Reference Card

**Feature:** Kernel Density Estimation Plot
**Status:** Ready for Integration
**Version:** 1.0.0

---

## Quick Start

1. Load dataset with numeric columns
2. Select columns to plot
3. Choose **'density'** from plot type dropdown
4. Adjust options as needed
5. Plot appears automatically

---

## Options Reference

### Bandwidth Method

Controls curve smoothness

| Option                    | Use When            | Result                       |
| ------------------------- | ------------------- | ---------------------------- |
| **scott** (default) | General use         | Balanced smoothness          |
| **silverman**       | Alternative default | Slightly different smoothing |
| **0.1**             | Need detail         | More peaks, noisier          |
| **0.5**             | Medium smoothing    | Moderate detail              |
| **1.0**             | Need smooth curve   | Very smooth, less detail     |

### Fill Under Curve

- ☐ Off: Line plot only
- ☑ On: Filled area under curve
- **Use:** Better for comparing multiple distributions

### Show Rug Plot

- ☐ Off: Density curve only
- ☑ On: Shows data points on x-axis
- **Use:** Small datasets (<500 points)
- **Avoid:** Large datasets (clutters plot)

### Multiple Subplots

- ☐ Off: All curves on one plot
- ☑ On: Separate plot per column
- **Use:** Comparing many columns (>3)

---

## Common Use Cases

### 1. Single Distribution

**Goal:** Visualize one variable's distribution

**Steps:**

1. Select one numeric column
2. Plot type: density
3. Default settings work well

### 2. Compare Groups

**Goal:** Compare distributions between groups

**Steps:**

1. Select multiple columns (one per group)
2. Plot type: density
3. Enable legend
4. Optional: Enable fill (adjust alpha)

### 3. Detailed Analysis

**Goal:** See fine details in distribution

**Steps:**

1. Select column
2. Plot type: density
3. Bandwidth: 0.1 or 0.2
4. Enable rug plot (if <500 points)

### 4. Smooth Overview

**Goal:** See general shape, ignore noise

**Steps:**

1. Select column
2. Plot type: density
3. Bandwidth: 0.5 or 1.0

### 5. Multiple Variables

**Goal:** Compare many distributions

**Steps:**

1. Select all columns
2. Plot type: density
3. Enable subplots
4. Grid layout automatic

---

## Keyboard Shortcuts

*(Standard matplotlib shortcuts apply)*

- **s**: Save figure
- **g**: Toggle grid
- **l**: Toggle log scale
- **Home**: Reset view
- **Arrow keys**: Pan
- **+/-**: Zoom

---

## Troubleshooting

### Problem: "No numeric data to plot"

**Solution:** Select numeric columns only

### Problem: Curve too smooth/rough

**Solution:** Adjust bandwidth method

### Problem: Can't see multiple curves

**Solution:**

- Enable legend
- Enable fill with transparency
- Use subplots

### Problem: Rug plot clutters view

**Solution:** Disable for large datasets

### Problem: Plot takes long to render

**Solution:**

- Use histogram for >50k points
- Reduce number of columns

---

## Tips & Tricks

### 💡 Tip 1: Identifying Outliers

Enable rug plot to see where data points cluster

### 💡 Tip 2: Comparing Distributions

Use fill with alpha=0.5 for better overlap visualization

### 💡 Tip 3: Multimodal Detection

Lower bandwidth (0.1-0.2) reveals multiple peaks

### 💡 Tip 4: Publication Quality

- Disable rug plot
- Use scott bandwidth
- Enable grid
- Adjust figure size

### 💡 Tip 5: Quick Exploration

Use subplots to quickly scan all variables

---

## Best Practices

### ✅ DO

- Use scott/silverman for most cases
- Enable fill for multiple curves
- Use subplots for >3 columns
- Remove NaN values beforehand
- Use rug plot for small datasets

### ❌ DON'T

- Use rug plot with >1000 points
- Set bandwidth too low (noisy)
- Set bandwidth too high (lose detail)
- Compare too many curves on one plot
- Forget to enable legend

---

## Performance Guide

| Dataset Size  | Recommended Settings               | Render Time |
| ------------- | ---------------------------------- | ----------- |
| <100          | All options OK                     | <0.1s       |
| 100-1,000     | Default settings                   | <0.5s       |
| 1,000-10,000  | Disable rug plot                   | <1s         |
| 10,000-50,000 | Disable rug, consider downsampling | 1-3s        |
| >50,000       | Use histogram instead              | N/A         |

---

## Example Workflows

### Workflow 1: Quality Control

```
Goal: Check if measurements are normally distributed
1. Load measurement data
2. Select measurement column
3. Plot type: density
4. Bandwidth: scott
5. Look for: Bell curve shape
```

### Workflow 2: A/B Testing

```
Goal: Compare control vs treatment groups
1. Load experiment data
2. Select control_group and treatment_group columns
3. Plot type: density
4. Enable fill
5. Enable legend
6. Look for: Separation between curves
```

### Workflow 3: Data Exploration

```
Goal: Understand all variables quickly
1. Load dataset
2. Select all numeric columns
3. Plot type: density
4. Enable subplots
5. Look for: Skewness, outliers, multimodal
```

### Workflow 4: Presentation

```
Goal: Create publication-ready plot
1. Select columns
2. Plot type: density
3. Bandwidth: scott
4. Fill: On, alpha: 0.6
5. Grid: On
6. Legend: On
7. Save as high-res PNG
```

---

## Comparison with Other Plot Types

| Feature            | Density              | Histogram      | Box Plot         |
| ------------------ | -------------------- | -------------- | ---------------- |
| Shows distribution | ✅ Smooth            | ✅ Binned      | ❌ Summary only  |
| Multiple overlays  | ✅ Easy              | ⚠️ Cluttered | ✅ Side-by-side  |
| Exact values       | ❌                   | ❌             | ✅ Quartiles     |
| Outlier detection  | ⚠️ With rug        | ❌             | ✅ Clear         |
| Best for           | Smooth distributions | Count data     | Comparing groups |

---

## When to Use Density Plot

### ✅ Use Density Plot When:

- Visualizing continuous distributions
- Comparing multiple distributions
- Data is numeric and continuous
- Want smooth representation
- Exploring data shape

### ❌ Use Alternative When:

- Data is categorical → Bar chart
- Need exact counts → Histogram
- Need quartiles → Box plot
- Data is discrete → Histogram
- Dataset is huge (>50k) → Histogram or downsample

---

## Keyboard Reference Card

```
┌─────────────────────────────────────┐
│     Density Plot Controls           │
├─────────────────────────────────────┤
│ s     Save figure                   │
│ g     Toggle grid                   │
│ l     Toggle log scale              │
│ Home  Reset view                    │
│ ←→↑↓  Pan                           │
│ +/-   Zoom in/out                   │
└─────────────────────────────────────┘
```

---

## Quick Checklist

Before creating density plot:

- [ ] Data is numeric
- [ ] NaN values handled
- [ ] Column(s) selected
- [ ] Appropriate bandwidth chosen
- [ ] Rug plot decision made
- [ ] Fill option considered
- [ ] Legend enabled (if multiple)

---

## Getting Help

1. **Documentation:** See DENSITY_PLOT_IMPLEMENTATION_GUIDE.md
2. **Examples:** Run examples/density_plot_examples.py
3. **Tests:** Check test_density_plot.py for usage patterns
4. **PRD:** See PLOTTING_FEATURES_PRD.md for detailed specs

---

## Version History

- **v1.0.0** (2025-10-04): Initial release
  - Basic density plot
  - Bandwidth selection
  - Fill and rug options
  - Subplots support

---

**Print this card for quick reference!**
