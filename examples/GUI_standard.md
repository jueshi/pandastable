# GUI Standards

This document defines standards for building modern, consistent, and maintainable GUIs in this codebase using Tkinter and ttk (with optional CustomTkinter variants). It is focused on look-and-feel, structure, and UX patterns without changing business logic.

## Goals
- Consistency in visual hierarchy, paddings, and control alignment.
- Separation of concerns: UI layout vs. business logic.
- Responsiveness: non-blocking UI during long tasks.
- Incremental adoption: safe to apply section-by-section.

---

## 1. Styling & Theme

- Initialize styles early in each main window class via `_init_style()`.
- Prefer the `clam` theme for a neutral modern baseline.
- Define shared paddings on `self`:
  - `self.PADX = 8`, `self.PADY = 6`, `self.IPADX = 6`, `self.IPADY = 4`.
- Palette (light):
  - Background: `#F5F6FA`
  - Text: `#1F2933`
  - Secondary text: `#4B5563`
  - Accent (primary action): `#2563EB`
- Styles to define:
  - `TNotebook` and `TNotebook.Tab` with readable padding.
  - `TLabelframe` and `TLabelframe.Label` with subtle border and bolder titles.
  - `TLabel`, `TEntry`, `TCombobox`, `TCheckbutton` with coherent colors.
  - `TButton` for normal actions, `Accent.TButton` for primary actions.
  - `Status.TLabel` for status/footers.

Example snippet:
```python
style = ttk.Style(self.root)
try:
    style.theme_use('clam')
except Exception:
    pass
self.PADX, self.PADY = 8, 6
self.IPADX, self.IPADY = 6, 4
bg, fg, subfg, accent = "#F5F6FA", "#1F2933", "#4B5563", "#2563EB"
self.root.configure(bg=bg)
style.configure("TNotebook", tabmargins=[4, 4, 4, 0])
style.configure("TNotebook.Tab", padding=[12, 6])
style.configure("TLabelframe", background=bg, borderwidth=1, relief="solid")
style.configure("TLabelframe.Label", background=bg, foreground=subfg)
style.configure("TLabel", background=bg, foreground=fg)
style.configure("TEntry", padding=(6, 4))
style.configure("TCombobox", padding=(6, 4))
style.configure("TCheckbutton", background=bg, foreground=fg)
style.configure("TButton", padding=(10, 6))
style.configure("Accent.TButton", background=accent, foreground="#fff")
style.configure("Status.TLabel", background="#fff", foreground=subfg, relief="sunken", anchor="w")
```

---

## 2. Layout Patterns

- Use `pack()` only for high-level containers (e.g., notebook pages, outer frames).
- Inside each section (`ttk.LabelFrame`), use `grid()` for alignment and responsiveness.
- Always define column weights with `columnconfigure()`.
- Apply `sticky="nsew"` to resizable elements (e.g., `Text`, `Treeview`).
- Use consistent paddings everywhere: `padx=self.PADX`, `pady=self.PADY`.

Example:
```python
section = ttk.LabelFrame(parent, text="Configuration", padding=self.PADX)
section.pack(fill=tk.X, pady=self.PADY)
for c in range(6):
    section.columnconfigure(c, weight=1)

r = 0
ttk.Label(section, text="Protocol:").grid(row=r, column=0, padx=self.PADX, pady=4, sticky="e")
self.protocol_var = tk.StringVar(value="100GBASE-KR")
ttk.Combobox(section, textvariable=self.protocol_var, values=["100GBASE-KR", "50GBASE-KR"],
             state="readonly", width=16).grid(row=r, column=1, padx=self.PADX, pady=4, sticky="w")
```

---

## 3. Widget Conventions

- `ttk.Combobox`: use `state="readonly"` to prevent accidental typing.
- Primary actions: use `style="Accent.TButton"`.
- Long text/log areas: place in a frame with `rowconfigure/columnconfigure` and pair with a scrollbar.
- Keep variable names stable across the app (`lane_var`, `protocol_var`, etc.).
- Label text: concise, sentence case or Title Case; avoid abbreviations unless domain-specific.

Log with scrollbar:
```python
log_frame = ttk.LabelFrame(parent, text="Log", padding=self.PADX)
log_frame.pack(fill=tk.BOTH, expand=True, pady=self.PADY)
log_frame.rowconfigure(0, weight=1)
log_frame.columnconfigure(0, weight=1)

scroll = ttk.Scrollbar(log_frame, orient="vertical")
scroll.grid(row=0, column=1, sticky="ns")
self.log_text = tk.Text(log_frame, wrap=tk.WORD, yscrollcommand=scroll.set)
self.log_text.grid(row=0, column=0, sticky="nsew")
scroll.config(command=self.log_text.yview)
```

---

## 4. Tabs, Sections, and Panes

- Use `ttk.Notebook` for high-level separation (e.g., Engineer vs. Operator).
- Inside tabs, group related controls with `ttk.LabelFrame`.
- Use `ttk.Panedwindow` for resizable split views (e.g., list on left, details/logs on right).

---

## 5. Icons and Images (Optional)

- Store under `EV_T4_snps_EVB/resources/` as `.png`.
- Load with `tk.PhotoImage` and keep references on `self` (avoid GC).
- Apply with `compound="left"`.
- Icons are optional—code should be robust if missing.

```python
base = Path(__file__).resolve().parent / "resources"
try:
    self.icons = {
        "run": tk.PhotoImage(file=str(base / "play.png")),
        "save": tk.PhotoImage(file=str(base / "save.png")),
    }
    self._btn_run.configure(image=self.icons["run"], compound="left")
except Exception:
    pass
```

---

## 6. Responsiveness for Long-Running Tasks

- Never block the UI thread with long operations.
- Wrap the action in a thread and use a small indeterminate `ttk.Progressbar`.
- Temporarily disable primary buttons, re-enable on completion.

Pattern:
```python
def _ui_run(self):
    if getattr(self, "_running", False):
        return
    self._running = True
    self._btn_run.configure(state="disabled")
    self._pb = self._pb or ttk.Progressbar(self.root, mode="indeterminate")
    self._pb.place(relx=1.0, rely=1.0, x=-220, y=-28, anchor="se")
    self._pb.start(10)

    threading.Thread(target=self._worker, daemon=True).start()

def _worker(self):
    try:
        self.run_test()  # existing behavior
    finally:
        self.root.after(0, self._finish_run)

def _finish_run(self):
    self._pb.stop(); self._pb.place_forget()
    self._btn_run.configure(state="normal")
    self._running = False
```

---

## 7. Separation of Concerns

- UI methods should build widgets, wire callbacks, and manage UI state only.
- Move non-UI logic into helper functions or classes (e.g., instrument control, file IO).
- Keep a clear boundary: callbacks call business logic helpers.

---

## 8. Naming and Structure

- Class names: `PascalCase` (e.g., `RXCharGUI`).
- Methods: `snake_case` with clear intent (e.g., `_build_connection_section`).
- Private helpers prefixed with `_`.
- File names: avoid problematic characters; favor `_v1_6` style if versioning is needed.

---

## 9. Dark Mode (Optional)

- Provide a toggleable palette and re-apply styles.
- Suggested dark palette:
  - Background: `#111827`
  - Surface: `#1F2937`
  - Text: `#E5E7EB`
  - Secondary: `#9CA3AF`
  - Accent: `#60A5FA`

Example application:
```python
def _apply_dark_mode(self, enable: bool):
    if enable:
        bg, fg, subfg, accent = "#111827", "#E5E7EB", "#9CA3AF", "#60A5FA"
    else:
        bg, fg, subfg, accent = "#F5F6FA", "#1F2933", "#4B5563", "#2563EB"
    style = ttk.Style(self.root)
    self.root.configure(bg=bg)
    style.configure("TLabelframe", background=bg)
    style.configure("TLabelframe.Label", background=bg, foreground=subfg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.configure("TButton")  # keep defaults
    style.configure("Accent.TButton", background=accent, foreground="#fff")
```

---

## 10. Accessibility & Usability Tips

- Respect platform font scaling if applicable.
- Ensure sufficient color contrast in both light and dark modes.
- Provide focus indicators (ttk does by default; avoid removing them).
- Keep labels short and clear; add tooltips if necessary (custom tooltip helper).

---

## 11. Testing & Verification

- Verify no functionality changes when applying UI refactors.
- Check resizing behavior (min/max window sizes) and long-log scenarios.
- Test on Windows default theme; verify clarity in both light/dark if implemented.

---

## 12. CustomTkinter (Optional Path)

- For a larger visual upgrade, consider a CTk variant with identical logic and callbacks.
- Suggested minimal changes: `CTk` window, `CTkFrame`, `CTkButton`, `CTkComboBox`, `CTkTabview`, `CTkTextbox`.
- Keep a separate module (e.g., `*_ctk.py`) to avoid churn in ttk-based code.

---

## References
- Implementation example: `RX_char_ATE_GUI_v1.6_looking.py` (updated styling & Engineer tab grid)
- Modernization plan: `RX_GUI_modernization_plan.md`
- Change log summary: `GUI_guidline.md`
