# Shmoo Plot Parameter Reference

## Thresholds

- **min threshold / max threshold**: Optional numeric bounds defining the acceptable Z-value window. When both are provided, the renderer builds a pass/fail color scale and the statistics panel reports pass counts and margins using these limits. Leave blank to disable threshold logic. (@pandastable/plotting.py#2296-2515)

## Contours

- **show contours**: Overlays iso-lines of constant Z onto the heatmap. Works when the shmoo data is either a regular grid or has been interpolated. (@pandastable/plotting.py#2420-2479)
- **contour levels**: Integer passed to Matplotlib’s contour generator to control how many contour bands are drawn. Higher values produce more detail. (@pandastable/plotting.py#2420-2479)

## Interpolation

- **interpolation**: Determines how irregular or sparse samples are turned into a 2D surface.
  - `none`: skips gridding and renders only scatter markers.
  - `nearest`: blocky expansion of each measurement to its nearest grid cell.
  - `bilinear`: smooth linear interpolation across a dense grid.
  - `cubic`: smoother surface (requires denser data and SciPy). (@pandastable/plotting.py#2486-2525)

## Markers

- **marker size**: Slider (10–200) setting the pixel size for the optional scatter overlay. Larger values make individual measurement points more prominent. (@pandastable/plotting.py#2931-2941)
- **show markers**: Toggles display of the original (X, Y) samples on top of the heatmap/interpolated surface using the selected marker size. (@pandastable/plotting.py#2442-2484)
