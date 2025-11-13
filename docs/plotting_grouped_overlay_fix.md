# Fix: Grouped overlay when deselecting "multiple subplots"

- Date: 2025-11-12
- Files changed: `pandastable/plotting.py`
- Function changed: `plot2D`

## Problem
When `group by` was set and the user unchecked `multiple subplots`, the grouped case incorrectly fell through to the non‑grouped code path. This caused the grouping column(s) to be plotted as data, creating vertical line artifacts and generally “messed up” overlay plots.

## Root cause
- The non‑grouped branch (`by == ''`) was being used even when `by != ''` and `subplots == False`.
- The grouped column(s) were not dropped before plotting on the single axis.

## Solution
Explicitly handle the grouped overlay path when `by != ''` and `subplots == False`:
- Create `g = data.groupby(by)` (supporting optional `by2`).
- For overlay mode:
  - For `line`, `bar`, `barh`:
    - Iterate groups, drop grouping column(s) from each `group`, assign a unique color per group, call `_doplot(group, self.ax, kind, False, ...)`.
  - For `scatter`:
    - Determine numeric `xcol` and `ycols` after dropping grouping column(s), and scatter each `(group, ycol)` with distinct colors and optional legend.
  - For unsupported kinds in overlay mode, show a warning suggesting multiple subplots.
- Keep the existing multi‑subplot logic unchanged.
- Only use the non‑grouped branch when `by == ''`.

## Exact code locations
- Function: `plot2D(self, redraw=True)` in `pandastable/plotting.py`.
- Main structure after the change:

1) Ensure grouping columns exist (join from `self.table.model.df` if needed) and build `g = data.groupby(by)`.
2) If `kwargs['subplots']` is True: run existing multi‑subplot path (axes grid, titles, optional shared axes, figure legend).
3) Else (overlay mode): overlay each group on the single axis as described above.
4) Else (no grouping): fall back to the non‑grouped `_doplot(...)` path.

## Minimal conceptual diff
- Move the “non‑grouped plot” logic under `else` of `if by != ''`.
- Add an overlay branch under the grouped case (`kwargs['subplots'] == False`) that:
  - Iterates over `for name, group in data.groupby(by):`
  - Drops `by`/`by2` from each `group` prior to plotting
  - Assigns `kwargs['color']` per group and calls `_doplot` on `self.ax`

## Why this works
- Prevents grouping columns from being plotted as data.
- Ensures grouped traces are overlaid on a single axis with consistent coloring, matching expected behavior from earlier subplots logic.

## Testing checklist
- Line overlay: Set `group by` to a categorical column, uncheck “multiple subplots”; expect multiple colored lines on one axis.
- Scatter overlay: Same expectation with scatter; optional legend entries per `(group, y)` series.
- Bar/barh overlay: Overlays grouped bars on the same axis.
- Multi‑subplots: Check “multiple subplots”; groups appear on separate axes; uncheck to return to overlay.
- `group by 2`: With subplots on, grid sizing (including `grid_width`) remains as before.

## Notes on legends
A benign warning may appear if `legend()` is called when no labeled artists exist yet. Toggling “legend” or ensuring plot kinds provide labels typically resolves it.
