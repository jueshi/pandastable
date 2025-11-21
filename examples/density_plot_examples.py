"""
Density Plot Examples for Pandastable
======================================

This script demonstrates the density plot functionality.
Run after applying the density plot patch to plotting.py

Author: AI Assistant
Date: 2025-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Example 1: Single Column Density Plot
# ======================================
print("Example 1: Single Column Density Plot")
print("-" * 50)

# Generate sample data
np.random.seed(42)
df1 = pd.DataFrame({
    'temperature': np.random.normal(20, 5, 1000)
})

print(f"Data shape: {df1.shape}")
print(f"Data statistics:\n{df1.describe()}\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select the 'temperature' column
# 3. Choose 'density' from plot type dropdown
# 4. The plot will show the distribution of temperatures

# Example 2: Multiple Columns with Different Distributions
# =========================================================
print("\nExample 2: Multiple Columns Density Plot")
print("-" * 50)

df2 = pd.DataFrame({
    'normal_dist': np.random.normal(0, 1, 1000),
    'uniform_dist': np.random.uniform(-3, 3, 1000),
    'exponential_dist': np.random.exponential(1, 1000),
    'bimodal_dist': np.concatenate([
        np.random.normal(-2, 0.5, 500),
        np.random.normal(2, 0.5, 500)
    ])
})

print(f"Data shape: {df2.shape}")
print(f"Columns: {list(df2.columns)}\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select multiple columns (or all)
# 3. Choose 'density' from plot type dropdown
# 4. Enable legend to see which curve corresponds to which column
# 5. The plot will show overlaid density curves

# Example 3: Comparing Bandwidth Methods
# =======================================
print("\nExample 3: Bandwidth Method Comparison")
print("-" * 50)

df3 = pd.DataFrame({
    'data': np.random.gamma(2, 2, 500)
})

print(f"Data shape: {df3.shape}")
print("Try different bandwidth methods:")
print("  - scott: Default, good for most cases")
print("  - silverman: Alternative default method")
print("  - 0.1: Narrow bandwidth (more detail, noisier)")
print("  - 0.5: Medium bandwidth")
print("  - 1.0: Wide bandwidth (smoother, less detail)\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select the 'data' column
# 3. Choose 'density' from plot type dropdown
# 4. Change bandwidth method in options
# 5. Observe how the curve changes

# Example 4: Density Plot with Fill
# ==================================
print("\nExample 4: Filled Density Plot")
print("-" * 50)

df4 = pd.DataFrame({
    'group_a': np.random.normal(10, 2, 800),
    'group_b': np.random.normal(15, 3, 800),
    'group_c': np.random.normal(20, 2.5, 800)
})

print(f"Data shape: {df4.shape}")
print("Enable 'fill under curve' option for better visualization\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select all columns
# 3. Choose 'density' from plot type dropdown
# 4. Enable 'fill under curve' checkbox
# 5. Adjust alpha for transparency

# Example 5: Density Plot with Rug Plot
# ======================================
print("\nExample 5: Density with Rug Plot")
print("-" * 50)

df5 = pd.DataFrame({
    'measurements': np.random.lognormal(0, 0.5, 200)
})

print(f"Data shape: {df5.shape}")
print("Rug plot shows actual data points along the x-axis\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select the 'measurements' column
# 3. Choose 'density' from plot type dropdown
# 4. Enable 'show rug plot' checkbox
# 5. The rug plot shows where actual data points are located

# Example 6: Subplots for Multiple Columns
# =========================================
print("\nExample 6: Density Subplots")
print("-" * 50)

df6 = pd.DataFrame({
    'sensor_1': np.random.normal(25, 3, 1000),
    'sensor_2': np.random.normal(30, 4, 1000),
    'sensor_3': np.random.normal(28, 2, 1000),
    'sensor_4': np.random.normal(32, 5, 1000)
})

print(f"Data shape: {df6.shape}")
print("Subplots create separate density plots for each column\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select all sensor columns
# 3. Choose 'density' from plot type dropdown
# 4. Enable 'multiple subplots' checkbox
# 5. Each sensor gets its own subplot

# Example 7: Real-World Use Case - Iris Dataset
# ==============================================
print("\nExample 7: Iris Dataset Density Analysis")
print("-" * 50)

# Create a sample similar to iris dataset
df7 = pd.DataFrame({
    'sepal_length': np.concatenate([
        np.random.normal(5.0, 0.35, 50),
        np.random.normal(5.9, 0.52, 50),
        np.random.normal(6.6, 0.64, 50)
    ]),
    'sepal_width': np.concatenate([
        np.random.normal(3.4, 0.38, 50),
        np.random.normal(2.8, 0.31, 50),
        np.random.normal(3.0, 0.32, 50)
    ]),
    'petal_length': np.concatenate([
        np.random.normal(1.5, 0.17, 50),
        np.random.normal(4.3, 0.47, 50),
        np.random.normal(5.6, 0.55, 50)
    ]),
    'petal_width': np.concatenate([
        np.random.normal(0.2, 0.11, 50),
        np.random.normal(1.3, 0.20, 50),
        np.random.normal(2.0, 0.27, 50)
    ])
})

print(f"Data shape: {df7.shape}")
print(f"Columns: {list(df7.columns)}")
print("\nThis dataset shows multimodal distributions")
print("(multiple peaks due to different species)\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select columns to compare
# 3. Choose 'density' from plot type dropdown
# 4. Notice the multiple peaks in distributions

# Example 8: Time Series Density
# ===============================
print("\nExample 8: Time Series Value Distribution")
print("-" * 50)

dates = pd.date_range('2024-01-01', periods=1000, freq='H')
df8 = pd.DataFrame({
    'timestamp': dates,
    'value': np.random.normal(100, 15, 1000) + np.sin(np.linspace(0, 4*np.pi, 1000)) * 20
})

print(f"Data shape: {df8.shape}")
print("Density plot shows distribution of values over time\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select only the 'value' column (not timestamp)
# 3. Choose 'density' from plot type dropdown
# 4. This shows the overall distribution of values

# Example 9: Comparing Groups with Density
# =========================================
print("\nExample 9: Group Comparison")
print("-" * 50)

df9 = pd.DataFrame({
    'control_group': np.random.normal(50, 10, 500),
    'treatment_group': np.random.normal(55, 12, 500)
})

print(f"Data shape: {df9.shape}")
print("Compare distributions between control and treatment\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select both columns
# 3. Choose 'density' from plot type dropdown
# 4. Enable legend
# 5. Compare the distributions visually

# Example 10: Handling Skewed Data
# =================================
print("\nExample 10: Skewed Distribution")
print("-" * 50)

df10 = pd.DataFrame({
    'income': np.random.pareto(2, 1000) * 30000 + 20000,
    'age': np.random.gamma(5, 5, 1000) + 18
})

print(f"Data shape: {df10.shape}")
print("Skewed distributions are common in real-world data\n")

# To use in pandastable:
# 1. Load this dataframe
# 2. Select columns
# 3. Choose 'density' from plot type dropdown
# 4. Notice the long tail in the distribution

# Save example datasets
# =====================
print("\nSaving example datasets...")
print("-" * 50)

try:
    df1.to_csv('density_example_1_single.csv', index=False)
    df2.to_csv('density_example_2_multiple.csv', index=False)
    df3.to_csv('density_example_3_bandwidth.csv', index=False)
    df4.to_csv('density_example_4_fill.csv', index=False)
    df5.to_csv('density_example_5_rug.csv', index=False)
    df6.to_csv('density_example_6_subplots.csv', index=False)
    df7.to_csv('density_example_7_iris.csv', index=False)
    df8.to_csv('density_example_8_timeseries.csv', index=False)
    df9.to_csv('density_example_9_groups.csv', index=False)
    df10.to_csv('density_example_10_skewed.csv', index=False)
    
    print("✓ All example datasets saved successfully!")
    print("\nYou can now:")
    print("1. Open pandastable")
    print("2. Load any of the example CSV files")
    print("3. Select columns to plot")
    print("4. Choose 'density' from plot type dropdown")
    print("5. Experiment with different options")
    
except Exception as e:
    print(f"Error saving files: {e}")

print("\n" + "=" * 70)
print("Density Plot Feature Summary")
print("=" * 70)
print("""
Key Features:
-------------
1. Single or multiple column density plots
2. Adjustable bandwidth (scott, silverman, or custom)
3. Fill under curve option
4. Rug plot to show data points
5. Subplots for comparing multiple columns
6. Automatic handling of NaN values
7. Works with grouped data (by parameter)
8. Graceful fallback if scipy not available

Best Practices:
---------------
- Use scott or silverman bandwidth for most cases
- Enable fill for better visualization of overlapping densities
- Use rug plot for smaller datasets (<500 points)
- Use subplots when comparing many columns
- Adjust alpha for transparency with multiple curves

Common Use Cases:
-----------------
- Visualizing data distribution
- Comparing distributions between groups
- Identifying multimodal distributions
- Detecting outliers and skewness
- Quality control and process monitoring
- Exploratory data analysis
""")

print("\nFor more information, see:")
print("- PLOTTING_FEATURES_PRD.md")
print("- density_plot_implementation.py")
print("- test_density_plot.py")
print("=" * 70)
