# RX GUI Modernization Plan (Look & Feel Only)

This plan modernizes the Tkinter GUI in `EV_T4_snps_EVB/RX_char_ATE_GUI_v1.6_looking.py` using themed `ttk` widgets, improved layout with `grid`, optional icons, and responsive UI touches. We will not change behavior or business logic. Each step creates a new `.py` file that subclasses/loads the original GUI to keep changes incremental and low-risk.

## Guiding Principles
- Keep functionality identical. Only adjust styling and layout.
- Use `ttk.Style` for theme, fonts, paddings, and accent buttons.
- Prefer `pack()` for outer containers and `grid()` inside frames for alignment and responsiveness.
- Group related controls into `ttk.LabelFrame` sections for scan-friendly hierarchy.
- Optional, non-breaking enhancements: icons on buttons/tabs, progress indicator during long runs.
- Refactor via subclassing/loading to avoid modifying the original file (which contains dots in its filename, making normal imports awkward).

## Step-by-step Roadmap

1) Step 1: Theme + Style Initialization (no layout changes)
- Create subclass `RXCharGUI` that calls `_init_style()` before building the UI.
- Apply theme (`clam`), palette, fonts, padding constants, and define `Accent.TButton` and `Status.TLabel` styles.
- Save as `EV_T4_snps_EVB/RX_char_ATE_GUI_v1_6_mod_step1.py`.

2) Step 2: Engineer Tab layout polish with `grid`
- Override `_create_engineer_tab()` in subclass to use `grid` inside frames while preserving all variables, commands, and logic.
- Align labels/fields into columns. Use `state="readonly"` for comboboxes. Keep `pack()` for high-level containers.
- Assign references to key buttons like `self._btn_run`, `self._btn_save`, `self._btn_load` for later UI-only enhancements.
- Save as `EV_T4_snps_EVB/RX_char_ATE_GUI_v1_6_mod_step2.py`.

3) Step 3: Operator Tab layout polish with `grid`
- Override `_create_operator_tab()` to use `grid` inside frames for consistent paddings and better resizing.
- Keep `Panedwindow` usage; apply style paddings and column configuration.
- Save as `EV_T4_snps_EVB/RX_char_ATE_GUI_v1_6_mod_step3.py`.

4) Step 4: Optional icons/images
- Add `_load_icons()` that loads optional PNG icons from `EV_T4_snps_EVB/resources/`. Use `compound="left"` on buttons/tabs.
- Do not fail if icons are missing.
- Save as `EV_T4_snps_EVB/RX_char_ATE_GUI_v1_6_mod_step4.py`.

5) Step 5: Responsiveness for long runs
- Add `ttk.Progressbar` (indeterminate) shown during long operations.
- Temporarily disable primary action buttons to prevent duplicates.
- Save as `EV_T4_snps_EVB/RX_char_ATE_GUI_v1_6_mod_step5.py`.

6) Optional: CustomTkinter variant (if desired later)
- Provide an alternative module that uses `customtkinter` for a larger visual refresh, keeping all callbacks identical.
- Save as `EV_T4_snps_EVB/RX_char_ATE_GUI_v1_6_mod_ctk_optional.py`.

## Notes
- No changes to your business logic, file IO, or instrument interactions.
- All modifications remain UI-only. Each step can be tested independently by swapping the import/class used to create the GUI.
