# Product Requirements Document: Plot Type Example Data Files

## Overview
Generate example CSV data files for each plot type in the pandastable plotting dropdown menu that does not already have example data in the project.

## Plot Types Analysis

### All Available Plot Types (from `plotting.py` line 3761-3762)

**2D Plot Types:**
1. `line`
2. `scatter`
3. `bar`
4. `barh`
5. `pie`
6. `histogram`
7. `boxplot`
8. `violinplot`
9. `dotplot`
10. `heatmap`
11. `area`
12. `hexbin`
13. `contour`
14. `imshow`
15. `scatter_matrix`
16. `density`
17. `radviz`
18. `venn`
19. `shmoo`
20. `bathtub`
21. `sparam`
22. `gantt`
23. `eye`
24. `jitter`

**3D Plot Types (from line 3955):**
1. `scatter` (3D)
2. `bar` (3D)
3. `contour` (3D)
4. `wireframe`
5. `surface`

### Existing Example Files

| Plot Type | Existing Files | Status |
|-----------|----------------|--------|
| `bathtub` | `bathtub_example_1_single.csv`, `bathtub_example_2_dual.csv`, `bathtub_example_3_voltage.csv` | **EXISTS** |
| `density` | `density_example_1_single.csv` through `density_example_10_skewed.csv` (10 files) | **EXISTS** |
| `eye` | `eye_example_1_pcie_gen4.csv` | **EXISTS** |
| `gantt` | `gantt_example_1_simple.csv`, `gantt_example_2_duration.csv`, `gantt_example_3_phases.csv` | **EXISTS** |
| `jitter` | `jitter_example_1_tj.csv` | **EXISTS** |
| `shmoo` | `shmoo_example_1_voltage_current.csv` through `shmoo_example_10_ber.csv` (10 files) | **EXISTS** |
| `sparam` | `sparam_example_1_s21.csv`, `sparam_example_2_multi.csv`, `sparam_example_3_pcie_gen4.csv` | **EXISTS** |

### Plot Types Needing Example Files

| Priority | Plot Type | Description | Data Requirements |
|----------|-----------|-------------|-------------------|
| P1 | `line` | Line plot | Time series or sequential numeric data |
| P1 | `scatter` | Scatter plot | Two numeric columns (X, Y) with optional size/color |
| P1 | `bar` | Vertical bar chart | Categories + numeric values |
| P1 | `barh` | Horizontal bar chart | Categories + numeric values |
| P1 | `pie` | Pie chart | Categories + numeric values (proportions) |
| P1 | `histogram` | Histogram | Single numeric column with distribution |
| P2 | `boxplot` | Box and whisker plot | Numeric data with groups/categories |
| P2 | `violinplot` | Violin plot | Numeric data with groups/categories |
| P2 | `dotplot` | Dot plot | Numeric data with groups/categories |
| P2 | `heatmap` | Heat map | Matrix of numeric values |
| P2 | `area` | Area chart | Time series or sequential data |
| P2 | `hexbin` | Hexagonal binning | Two numeric columns (X, Y) with density |
| P3 | `contour` | Contour plot | X, Y, Z grid data |
| P3 | `imshow` | Image display | Matrix/grid of values |
| P3 | `scatter_matrix` | Scatter matrix | Multiple numeric columns |
| P3 | `radviz` | RadViz plot | Multiple numeric columns + category |
| P3 | `venn` | Venn diagram | Set membership data |
| P4 | `wireframe` (3D) | 3D wireframe | X, Y, Z grid data |
| P4 | `surface` (3D) | 3D surface | X, Y, Z grid data |

---

## Example File Specifications

### P1: Basic Plot Types

#### 1. `line_example_1_timeseries.csv`
**Purpose:** Demonstrate line plot with time series data
**Columns:**
- `Date` - Date values (YYYY-MM-DD)
- `Temperature` - Temperature readings
- `Humidity` - Humidity percentage
- `Pressure` - Atmospheric pressure

**Rows:** 30 (one month of daily data)

#### 2. `line_example_2_multiline.csv`
**Purpose:** Multiple lines on same plot
**Columns:**
- `X` - Sequential values 0-100
- `Sin` - sin(x) values
- `Cos` - cos(x) values
- `Tan_clipped` - tan(x) clipped to [-2, 2]

**Rows:** 100

#### 3. `scatter_example_1_correlation.csv`
**Purpose:** Show correlation between variables
**Columns:**
- `Height_cm` - Height in centimeters
- `Weight_kg` - Weight in kilograms
- `Age` - Age in years
- `Gender` - M/F for color coding

**Rows:** 100

#### 4. `scatter_example_2_clusters.csv`
**Purpose:** Show clustered data
**Columns:**
- `X` - X coordinate
- `Y` - Y coordinate
- `Cluster` - Cluster label (A, B, C)
- `Size` - Point size value

**Rows:** 150 (50 per cluster)

#### 5. `bar_example_1_sales.csv`
**Purpose:** Simple bar chart
**Columns:**
- `Product` - Product names
- `Q1_Sales` - Q1 sales figures
- `Q2_Sales` - Q2 sales figures
- `Q3_Sales` - Q3 sales figures
- `Q4_Sales` - Q4 sales figures

**Rows:** 8 products

#### 6. `barh_example_1_ranking.csv`
**Purpose:** Horizontal bar chart for rankings
**Columns:**
- `Country` - Country names
- `Score` - Performance score
- `Category` - Category label

**Rows:** 15 countries

#### 7. `pie_example_1_market_share.csv`
**Purpose:** Pie chart for proportions
**Columns:**
- `Company` - Company names
- `Market_Share` - Market share percentage
- `Revenue` - Revenue in millions

**Rows:** 6 companies

#### 8. `histogram_example_1_distribution.csv`
**Purpose:** Show normal distribution
**Columns:**
- `Value` - Normally distributed values
- `Category` - Optional grouping

**Rows:** 500

#### 9. `histogram_example_2_bimodal.csv`
**Purpose:** Show bimodal distribution
**Columns:**
- `Measurement` - Bimodal distributed values
- `Source` - Source A or B

**Rows:** 400

---

### P2: Statistical Plot Types

#### 10. `boxplot_example_1_groups.csv`
**Purpose:** Compare distributions across groups
**Columns:**
- `Value` - Numeric measurement
- `Group` - Group label (Control, Treatment_A, Treatment_B, Treatment_C)
- `Replicate` - Replicate number

**Rows:** 200 (50 per group)

#### 11. `violinplot_example_1_comparison.csv`
**Purpose:** Show distribution shape with violin plot
**Columns:**
- `Score` - Test scores
- `Method` - Teaching method (Traditional, Online, Hybrid)
- `Subject` - Subject area

**Rows:** 300

#### 12. `dotplot_example_1_measurements.csv`
**Purpose:** Individual data points with categories
**Columns:**
- `Measurement` - Numeric value
- `Sample` - Sample ID
- `Condition` - Experimental condition

**Rows:** 60

#### 13. `heatmap_example_1_correlation.csv`
**Purpose:** Correlation matrix visualization
**Columns:**
- `Var1` through `Var10` - 10 numeric variables

**Rows:** 50 (for computing correlations)

#### 14. `heatmap_example_2_expression.csv`
**Purpose:** Gene expression-style heatmap
**Columns:**
- `Gene` - Gene identifier
- `Sample_1` through `Sample_8` - Expression values

**Rows:** 30 genes

#### 15. `area_example_1_stacked.csv`
**Purpose:** Stacked area chart
**Columns:**
- `Month` - Month name
- `Product_A` - Sales for Product A
- `Product_B` - Sales for Product B
- `Product_C` - Sales for Product C

**Rows:** 12 months

#### 16. `hexbin_example_1_density.csv`
**Purpose:** Show density with hexagonal binning
**Columns:**
- `X` - X coordinate (normally distributed)
- `Y` - Y coordinate (correlated with X)

**Rows:** 5000

---

### P3: Advanced Plot Types

#### 17. `contour_example_1_surface.csv`
**Purpose:** 2D contour plot
**Columns:**
- `X` - X grid values
- `Y` - Y grid values
- `Z` - Z values (function of X, Y)

**Rows:** 400 (20x20 grid)

#### 18. `imshow_example_1_matrix.csv`
**Purpose:** Image/matrix display
**Columns:**
- `Row` - Row index
- `Col` - Column index
- `Value` - Pixel/cell value

**Rows:** 256 (16x16 grid)

#### 19. `scatter_matrix_example_1_iris.csv`
**Purpose:** Multi-variable scatter matrix
**Columns:**
- `Sepal_Length` - Sepal length
- `Sepal_Width` - Sepal width
- `Petal_Length` - Petal length
- `Petal_Width` - Petal width
- `Species` - Species category

**Rows:** 150

#### 20. `radviz_example_1_multivar.csv`
**Purpose:** RadViz multivariate visualization
**Columns:**
- `Feature_1` through `Feature_6` - Numeric features
- `Class` - Class label (A, B, C)

**Rows:** 120

#### 21. `venn_example_1_sets.csv`
**Purpose:** Venn diagram data
**Columns:**
- `Item` - Item identifier
- `Set_A` - Boolean membership in Set A
- `Set_B` - Boolean membership in Set B
- `Set_C` - Boolean membership in Set C

**Rows:** 100

---

### P4: 3D Plot Types

#### 22. `surface_example_1_3d.csv`
**Purpose:** 3D surface plot
**Columns:**
- `X` - X coordinate
- `Y` - Y coordinate
- `Z` - Z value (height)

**Rows:** 441 (21x21 grid)

#### 23. `wireframe_example_1_3d.csv`
**Purpose:** 3D wireframe plot
**Columns:**
- `X` - X coordinate
- `Y` - Y coordinate
- `Z` - Z value

**Rows:** 441 (21x21 grid)

---

## Implementation Plan

### Phase 1: P1 Files (Basic Plots)
1. Create `line_example_1_timeseries.csv`
2. Create `line_example_2_multiline.csv`
3. Create `scatter_example_1_correlation.csv`
4. Create `scatter_example_2_clusters.csv`
5. Create `bar_example_1_sales.csv`
6. Create `barh_example_1_ranking.csv`
7. Create `pie_example_1_market_share.csv`
8. Create `histogram_example_1_distribution.csv`
9. Create `histogram_example_2_bimodal.csv`

### Phase 2: P2 Files (Statistical Plots)
10. Create `boxplot_example_1_groups.csv`
11. Create `violinplot_example_1_comparison.csv`
12. Create `dotplot_example_1_measurements.csv`
13. Create `heatmap_example_1_correlation.csv`
14. Create `heatmap_example_2_expression.csv`
15. Create `area_example_1_stacked.csv`
16. Create `hexbin_example_1_density.csv`

### Phase 3: P3 Files (Advanced Plots)
17. Create `contour_example_1_surface.csv`
18. Create `imshow_example_1_matrix.csv`
19. Create `scatter_matrix_example_1_iris.csv`
20. Create `radviz_example_1_multivar.csv`
21. Create `venn_example_1_sets.csv`

### Phase 4: P4 Files (3D Plots)
22. Create `surface_example_1_3d.csv`
23. Create `wireframe_example_1_3d.csv`

---

## File Location
All example files should be created in the project root directory:
`c:\Users\juesh\jules\pandastable0\`

## Naming Convention
`{plottype}_example_{number}_{description}.csv`

## Data Quality Requirements
1. All numeric data should be realistic and meaningful
2. Categories should be descriptive and relevant
3. Data should demonstrate the plot type's key features
4. Files should be small enough for quick loading (<1MB)
5. Include variety in data patterns (trends, clusters, distributions)

---

## Summary

| Priority | Count | Plot Types |
|----------|-------|------------|
| P1 | 9 files | line, scatter, bar, barh, pie, histogram |
| P2 | 7 files | boxplot, violinplot, dotplot, heatmap, area, hexbin |
| P3 | 5 files | contour, imshow, scatter_matrix, radviz, venn |
| P4 | 2 files | surface, wireframe |
| **Total** | **23 files** | |

**Already Existing:** 7 plot types with 32 example files
- bathtub (3), density (10), eye (1), gantt (3), jitter (1), shmoo (10), sparam (3)
