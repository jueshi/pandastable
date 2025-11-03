
## General Tkinter/ttk Coding Guide

### 1) Styling and Theme
- **Initialize once**: Create a method like `_init_style()` and call it early in `__init__`.
- **Use `ttk.Style`**: Set a modern theme (e.g., `clam`), define shared paddings, and create reusable style classes.
- **Color palette**: Choose a neutral background with a single accent color for primary actions.
- **Primary action**: Provide an `Accent.TButton` style for main actions.
- **Status bar**: Use a dedicated style (e.g., `Status.TLabel`).

### 2) Layout Patterns
- **Pack for outer containers**, **Grid inside frames**.
- **LabelFrames**: Group related controls with `ttk.LabelFrame` and consistent `padding=PADX`.
- **Grid config**: Use `columnconfigure()` to set stretchy columns, and `sticky="nsew"` for resizable content.
- **Consistent spacing**: Use shared `PADX`/`PADY` constants everywhere; avoid magic numbers.

### 3) Widgets and Inputs
- **Readonly comboboxes**: `state="readonly"` avoids accidental freeform text.
- **Buttons**: Use text + optional icons (`compound="left"`) for clarity.
- **Text widgets**: Place with grid in a frame that has `rowconfigure/columnconfigure` for proper resizing.

### 4) Tabs and Sections
- **Notebook**: Keep high-level separation (e.g., Engineer/Operator).
- **Subsections**: Prefer multiple `LabelFrame`s or sub-tabs for dense UIs.
- **Panedwindow**: Use for resizable split areas.

### 5) Icons and Assets (Optional)
- Store icons under `EV_T4_snps_EVB/resources/`.
- Load icons safely (ignore if missing) and apply with `compound="left"`.
- Keep `PhotoImage` references on `self` to avoid garbage collection.

### 6) Responsiveness for Long-Running Tasks (UI only)
- Wrap long operations with a **progress indicator** (indeterminate `ttk.Progressbar`).
- **Disable primary buttons** during execution to prevent duplicate triggers; re-enable when done.
- Use **threads** for the workload, and return to the UI thread with `root.after()` to update UI state.

### 7) Maintainability
- **Modular builders**: Break UI into small builder methods per section (e.g., `_build_connection_section()`).
- **Keep logic separate**: UI callbacks should call non-UI helpers for business logic.
- **Naming**: Stable variable names for state (`lane_var`, `protocol_var`, etc.) to avoid regressions.

### 8) Incremental Adoption Strategy
- Start with `_init_style()`.
- Move frames to `grid` internally section-by-section.
- Introduce `Accent.TButton` to primary actions.
- Add optional icons and progress bar as non-breaking enhancements.

## Example Snippets

### Accent Button usage
```python
self._btn_run = ttk.Button(actions_frame, text="Run Test", style="Accent.TButton", command=self.run_test)
```

### Grid with resizable Text and scrollbar
```python
log_frame = ttk.LabelFrame(parent, text="Log", padding=PADX)
log_frame.pack(fill=tk.BOTH, expand=True, pady=PADY)
log_frame.rowconfigure(0, weight=1)
log_frame.columnconfigure(0, weight=1)

scroll = ttk.Scrollbar(log_frame, orient="vertical")
scroll.grid(row=0, column=1, sticky="ns")

log_text = tk.Text(log_frame, wrap=tk.WORD, yscrollcommand=scroll.set)
log_text.grid(row=0, column=0, sticky="nsew")
scroll.config(command=log_text.yview)
```

### Threaded run with progress (UI only)
```python
def _ui_run(self):
    if self._running:
        return
    self._running = True
    self._btn_run.config(state="disabled")
    self._pb.start(10)
    threading.Thread(target=self._worker, daemon=True).start()

def _worker(self):
    try:
        self.run_test()  # existing behavior
    finally:
        self.root.after(0, self._finish)

def _finish(self):
    self._pb.stop()
    self._btn_run.config(state="normal")
    self._running = False
```

