# Shmoo Plot Value Display Implementation

## Summary

The shmoo plot now supports overlaying each cell's Z-value directly on the chart when the **Show values** checkbox is enabled. This feature helps correlate numeric measurements with the heatmap color and is especially useful when reviewers request exact pass/fail margins without hovering over every point.

### Option Wiring (Log)

1. **Valid keywords** – `show_values` is registered in the shmoo entry of `valid_kwds`, ensuring the option flows through the plotting pipeline. (@pandastable/plotting.py#88-92)
2. **UI grouping** – The shmoo option group inside `MPLBaseOptions` now lists `show_values`, so the checkbox renders with the rest of the shmoo controls. (@pandastable/plotting.py#2870-2889)
3. **Widget definition** – A `checkbutton` widget with a default value of `0` defines the new option, keeping behavior off by default. (@pandastable/plotting.py#2928-2942)

## Rendering Logic

- `PlotViewer.shmoo` reads `show_values` from `kwds` just like other boolean toggles. (@pandastable/plotting.py#2290-2308)
- After the main plot (pcolormesh or scatter) and optional statistics, the renderer deduplicates points with an `OrderedDict` to avoid overlapping labels and formats each Z-value with `"{value:.3g}"`. (@pandastable/plotting.py#2517-2522)
- Text labels use `ax.text(..., ha='center', va='center')` so they remain anchored to the data coordinate, and a `matplotlib.patheffects.withStroke` outline (imported at the top of the file) improves legibility regardless of the underlying color. (@pandastable/plotting.py#33-44, @pandastable/plotting.py#2517-2522)

### Usage (Log)

1. Open the Plot Viewer and choose **shmoo** as the plot type.
2. Scroll to the **shmoo** section of the options panel.
3. Enable **Show values**.
4. (Optional) Keep **Show markers** enabled if you want to emphasize the point locations together with the values.
5. Click **Apply Options** to refresh the plot.

### Testing Checklist for Show Values

- Enable **Show values** with both regular-grid (pcolormesh) and irregular (scatter/interpolation) datasets to verify text placement.
- Toggle the checkbox off and confirm labels disappear without affecting other options.
- Combine with **Show statistics**, **Show markers**, and different colormaps to ensure the outlined text remains readable.
- Run the example `examples/csv_browser_v6.x1.2_search_columns.py`, load `shmoo_example_1_voltage_current.csv`, enable **Show values**, and confirm labels match the CSV entries.

## Future Enhancements

- Provide formatting controls (decimal places, font size) alongside the checkbox for advanced tuning.
- Add a collision-avoidance strategy for dense grids where multiple values share similar coordinates.
- Offer an option to display only values that fall inside the threshold band to reduce clutter when highlighting pass/fail regions.

### Log Y-Axis Checkbox Behavior

Enabling **log y** in the base options now shares the same clamping logic introduced for shmoo's `log_z_scale`. When the checkbox is active, any non-positive Y data points are replaced with `safe_floor = min_positive / 10`, where `min_positive` is the smallest strictly positive value (or the smallest non-zero magnitude, with a final fallback to `1.0`). This sanitization occurs before the plot method runs, so bar/line/area series, grouped plots, and dot/violin/box plots no longer crash when data includes zeros or negatives. Scatter plots treat the first numeric column as X data and clamp only the Y columns. This keeps log scaling numerically stable without mutating the underlying DataFrame; the transformation lives only in the plotting copy.

---

## Shmoo Plot Logarithmic Value Scaling

### Summary (Log Scale)

The shmoo plot now includes a **log10 scale (Z)** checkbox that transforms the Z-axis values before rendering. This is useful when measurement spans multiple orders of magnitude (e.g., BER sweeps) and the linear colormap hides useful detail.

## Option Wiring

- Added `log_z_scale` to the shmoo entry in `valid_kwds` so the setting propagates through the plotting pipeline. (@pandastable/plotting.py#87-100)
- The shmoo options group in `MPLBaseOptions` includes the new checkbox, and the widget definition sets the default to `0` (linear behavior). (@pandastable/plotting.py#2870-2942)

### Data Handling (Log)

1. After cleaning NaNs, the renderer finds the smallest strictly positive Z value. If none exist, it falls back to the smallest non-zero absolute value, and finally to `1.0` as a last resort.
2. The algorithm defines **`safe_floor = min_positive / 10`** and replaces every Z value ≤ 0 with this floor before applying `log10`. This guarantees all transformed values are finite while keeping replaced points one decade below the smallest original positive measurement.
3. Thresholds (if provided) are run through the same `max(value, safe_floor)` and `log10` calculation so statistics and contour logic stay consistent with the transformed data.
4. The colorbar label changes to `log10(<Z column>)`, and the plot title mirrors the transformed scale for clarity. (@pandastable/plotting.py#2355-2506)

## Usage

1. Enable the **log10 scale (Z)** checkbox in the shmoo options.
2. Configure other options (markers, contours, thresholds) as needed.
3. Click **Apply Options** to re-render the plot using the transformed data.

## Testing Checklist

- Plot a dataset that contains zeros or negative Z values and verify they render without errors (they should appear one decade below the smallest positive point).
- Confirm threshold-based coloring/statistics produce the same pass/fail classification as a manual log10 transformation in Python.
- Toggle the checkbox off and back on to ensure linear/log behavior is reversible without restarting the viewer.
- Combine with **Show values** to check that annotations display the original Z scale (current behavior) and decide whether future work should log-transform labels as well.
