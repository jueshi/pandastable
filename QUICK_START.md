# Quick Start Guide - New Plotting Features

**Date:** 2025-10-05  
**Features:** Density Plot & 2D Shmoo Plot

---

## 🚀 Getting Started in 5 Minutes

### Step 1: Verify Installation

The features are already integrated into `pandastable/plotting.py`. No additional installation needed!

**Dependencies:**
- ✅ matplotlib (required)
- ✅ pandas (required)
- ✅ numpy (required)
- ⚠️ scipy (optional, for KDE and interpolation - graceful fallback if missing)

### Step 2: Test Density Plot

1. **Open pandastable** (or your CSV browser application)

2. **Load a test file:**
   ```
   density_example_1_single.csv
   ```

3. **Create density plot:**
   - Select the column(s)
   - Choose **'density'** from plot type dropdown
   - Click plot/refresh

4. **Try options:**
   - Bandwidth method: scott, silverman, 0.1-1.0
   - ☑ Fill under curve
   - ☑ Show rug plot
   - ☑ Multiple subplots

### Step 3: Test Shmoo Plot

1. **Load a test file:**
   ```
   shmoo_example_1_voltage_current.csv
   ```

2. **Create shmoo plot:**
   - Select 3 columns (or let auto-select)
   - Choose **'shmoo'** from plot type dropdown
   - Click plot/refresh

3. **Try options:**
   - X parameter: Voltage
   - Y parameter: Current
   - Z value: Measurement
   - Min threshold: 0.8
   - Max threshold: 1.0
   - ☑ Show statistics
   - ☑ Show contours

---

## 📊 Example Files Reference

### Density Plot Examples (10 files)

| File | Use Case | Columns | Recommended Settings |
|------|----------|---------|---------------------|
| density_example_1_single.csv | Single distribution | 1 | Default |
| density_example_2_multiple.csv | Compare distributions | 4 | Fill=On, Legend=On |
| density_example_3_bandwidth.csv | Bandwidth comparison | 1 | Try different bandwidths |
| density_example_4_fill.csv | Filled densities | 3 | Fill=On, Alpha=0.6 |
| density_example_5_rug.csv | Small dataset | 1 | Show_rug=On |
| density_example_6_subplots.csv | Multiple variables | 4 | Subplots=On |
| density_example_7_iris.csv | Multimodal data | 4 | Bandwidth=0.2 |
| density_example_8_timeseries.csv | Value distribution | 1 | Default |
| density_example_9_groups.csv | Group comparison | 2 | Fill=On, Legend=On |
| density_example_10_skewed.csv | Skewed distribution | 2 | Default |

### Shmoo Plot Examples (10 files)

| File | Use Case | Grid Type | Recommended Settings |
|------|----------|-----------|---------------------|
| shmoo_example_1_voltage_current.csv | Voltage sweep | Regular | threshold_min=0.8, max=1.0 |
| shmoo_example_2_temp_freq.csv | Temp characterization | Regular | threshold_min=20, contours=On |
| shmoo_example_3_power_supply.csv | Power analysis | Irregular | interpolation=cubic, markers=On |
| shmoo_example_4_signal_integrity.csv | Signal quality | Regular | threshold_min=100, contours=On |
| shmoo_example_5_process_corner.csv | Process corners | Regular | threshold_max=150, stats=On |
| shmoo_example_6_yield_analysis.csv | Yield map | Regular | threshold_min=0.5, max=1.5 |
| shmoo_example_7_optimization.csv | Parameter optimization | Regular | threshold_min=80, contours=On |
| shmoo_example_8_jitter.csv | Jitter analysis | Regular | threshold_max=50, contours=On |
| shmoo_example_9_thermal.csv | Thermal limits | Regular | threshold_max=125, stats=On |
| shmoo_example_10_ber.csv | Bit error rate | Regular | threshold_min=-12, contours=On |

---

## 🎯 Common Tasks

### Task 1: Visualize Data Distribution
```
1. Load: density_example_2_multiple.csv
2. Select: All columns
3. Plot type: density
4. Options: Fill=On, Legend=On
5. Result: Overlaid density curves
```

### Task 2: Compare Groups
```
1. Load: density_example_9_groups.csv
2. Select: control_group, treatment_group
3. Plot type: density
4. Options: Fill=On, Alpha=0.6
5. Result: Compare distributions visually
```

### Task 3: Parameter Sweep Analysis
```
1. Load: shmoo_example_1_voltage_current.csv
2. Plot type: shmoo
3. Set thresholds: min=0.8, max=1.0
4. Options: Show_stats=On
5. Result: Pass/fail regions with statistics
```

### Task 4: Thermal Characterization
```
1. Load: shmoo_example_9_thermal.csv
2. Plot type: shmoo
3. Set threshold: max=125
4. Options: Colormap=hot, Show_stats=On
5. Result: Safe operating region visualization
```

---

## 🔧 Troubleshooting

### Density Plot Issues

**Problem:** "No numeric data to plot"
- **Solution:** Select only numeric columns

**Problem:** Curve too smooth/rough
- **Solution:** Adjust bandwidth (lower=more detail, higher=smoother)

**Problem:** Can't see multiple curves
- **Solution:** Enable fill with transparency, or use subplots

### Shmoo Plot Issues

**Problem:** "Requires at least 3 numeric columns"
- **Solution:** Select 3 numeric columns (X, Y, Z)

**Problem:** Plot looks scattered/noisy
- **Solution:** Try different interpolation (nearest, bilinear, cubic)

**Problem:** Thresholds not working
- **Solution:** Enter numeric values (e.g., 0.8, not "0.8")

**Problem:** Slow rendering
- **Solution:** Use 'nearest' interpolation for large datasets

---

## 📖 Documentation Reference

### For Users
- **DENSITY_PLOT_QUICK_REFERENCE.md** - Density plot user guide
- **This file** - Quick start guide

### For Developers
- **PLOTTING_FEATURES_PRD.md** - Complete requirements
- **DENSITY_PLOT_IMPLEMENTATION_GUIDE.md** - Integration guide
- **SHMOO_PLOT_INTEGRATION_COMPLETE.md** - Shmoo plot details

### For Testing
- **test_density_plot.py** - Unit tests
- **examples/density_plot_examples.py** - Generate test data
- **examples/shmoo_plot_examples.py** - Generate test data

---

## 💡 Tips & Tricks

### Density Plot Tips

1. **For small datasets (<500 points):**
   - Enable rug plot to see actual data points

2. **For comparing many columns:**
   - Use subplots instead of overlay
   - Or use different colors with transparency

3. **For publication quality:**
   - Use scott bandwidth
   - Enable fill with alpha=0.6
   - Enable grid
   - Adjust figure size

4. **For exploring data:**
   - Try different bandwidths
   - Look for multiple peaks (multimodal)
   - Check for skewness

### Shmoo Plot Tips

1. **For regular grids:**
   - Data renders fastest
   - Use 'nearest' interpolation
   - Perfect for designed experiments

2. **For irregular grids:**
   - Use 'cubic' interpolation for smoothness
   - Enable markers to see actual test points
   - May need more data points for good interpolation

3. **For pass/fail analysis:**
   - Set both min and max thresholds
   - Use RdYlGn colormap (green=pass, red=fail)
   - Enable statistics to see pass rate and margins

4. **For optimization:**
   - Use contour lines to see level sets
   - Adjust contour levels for detail
   - Look for optimal regions (peaks/valleys)

---

## 🎓 Learning Path

### Beginner (15 minutes)
1. ✅ Load density_example_1_single.csv
2. ✅ Create basic density plot
3. ✅ Try different bandwidth methods
4. ✅ Load shmoo_example_1_voltage_current.csv
5. ✅ Create basic shmoo plot

### Intermediate (30 minutes)
1. ✅ Load density_example_2_multiple.csv
2. ✅ Compare multiple distributions
3. ✅ Use fill and rug options
4. ✅ Load shmoo_example_5_process_corner.csv
5. ✅ Set thresholds and view statistics
6. ✅ Try different interpolation methods

### Advanced (1 hour)
1. ✅ Load your own data
2. ✅ Create custom density plots
3. ✅ Create custom shmoo plots
4. ✅ Experiment with all options
5. ✅ Export high-quality plots
6. ✅ Integrate into your workflow

---

## 📞 Getting Help

### Check Documentation
1. Read DENSITY_PLOT_QUICK_REFERENCE.md
2. Review examples in examples/ directory
3. Check troubleshooting sections

### Run Examples
```bash
# Generate all test data
python examples/density_plot_examples.py
python examples/shmoo_plot_examples.py

# Run unit tests
python -m pytest test_density_plot.py -v
```

### Common Questions

**Q: Do I need scipy?**
A: No, but recommended. Density plot falls back to pandas. Shmoo plot uses scatter if scipy unavailable.

**Q: Can I use with my CSV browser?**
A: Yes! The features integrate with pandastable's plotting system.

**Q: How do I save plots?**
A: Use matplotlib's save button in the plot window, or File → Save.

**Q: Can I customize colors?**
A: Yes! Use the colormap option. Try 'viridis', 'plasma', 'RdYlGn', etc.

---

## ✅ Quick Checklist

### Before You Start
- [ ] Pandastable installed
- [ ] Example CSV files generated
- [ ] Documentation reviewed

### First Test (Density)
- [ ] Loaded example file
- [ ] Created density plot
- [ ] Tried different options
- [ ] Plot displays correctly

### First Test (Shmoo)
- [ ] Loaded example file
- [ ] Created shmoo plot
- [ ] Set thresholds
- [ ] Statistics display correctly

### Ready for Production
- [ ] Tested with your data
- [ ] Verified all options work
- [ ] Performance acceptable
- [ ] Integrated into workflow

---

## 🎉 Success!

If you can:
- ✅ Create density plots with your data
- ✅ Create shmoo plots with your data
- ✅ Adjust options and see results
- ✅ Export plots for reports

**You're ready to use the new features!**

---

## 📊 Feature Comparison

| Feature | Density Plot | Shmoo Plot |
|---------|--------------|------------|
| **Purpose** | Distribution visualization | Parameter sweep analysis |
| **Input** | 1+ numeric columns | 3 numeric columns (X,Y,Z) |
| **Output** | Smooth curve(s) | 2D heatmap/contour |
| **Best For** | Statistics, QC | Testing, validation |
| **Options** | 3 main | 11 main |
| **Speed** | Fast | Fast (regular), Moderate (irregular) |

---

**Ready to explore your data? Start with the examples above!**

*Last updated: 2025-10-05*  
*Version: 1.0*  
*Status: Production Ready ✅*
