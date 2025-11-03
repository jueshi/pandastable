import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext, simpledialog
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict
import html
import json

class XMLViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("IP-XACT Register Viewer")
        
        # Enable debug mode
        self.debug_mode = True
        self.debug_log = []
        # Common namespace prefixes we recognize in IP-XACT style docs
        self.common_namespaces = {
            'spirit': 'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009',
            'ipxact': 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014',
            'ipxact2014': 'http://www.accellera.org/XMLSchema/IPXACT/1685-2014',
            'ipxact2010': 'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2010',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
        
        # Configure main window layout using grid for better control
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create paned window with sash positions
        self.main_pane = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for tree view
        self.tree_frame = ttk.Frame(self.main_pane, padding="5")
        self.details_frame = ttk.Frame(self.main_pane, padding="5")
        
        # Add frames to paned window with weights
        self.main_pane.add(self.tree_frame, weight=1)
        self.main_pane.add(self.details_frame, weight=1)
        
        # Set initial sash position to 50%
        self.main_pane.pane(0, weight=1)
        self.main_pane.pane(1, weight=1)
        
        # Initialize data holders early so event handlers never see missing attrs
        self._node_meta = {}
        self.registers = []
        self.current_regmap_path = None
        # Notes: base directory to store per-regmap notes files
        self.notes_dir = self._default_notes_dir()
        try:
            if self.notes_dir:
                os.makedirs(self.notes_dir, exist_ok=True)
        except Exception:
            pass
        # Initialize a default aggregate notes path (legacy); per-register files are computed dynamically
        self.notes_path = os.path.join(self.notes_dir, 'register_notes.md')
        # Create tree with columns (resizable with headings shown)
        self.tree = ttk.Treeview(self.tree_frame, columns=(
            'offset', 'size', 'access'
        ), show='tree headings')
        # Configure headings and make them clickable to auto-fit that column
        self.tree.heading('#0', text='Register', command=lambda: self._autofit_column('#0'))
        self.tree.heading('offset', text='Offset', command=lambda: self._autofit_column('offset'))
        self.tree.heading('size', text='Size (bits)', command=lambda: self._autofit_column('size'))
        self.tree.heading('access', text='Access', command=lambda: self._autofit_column('access'))
        # Initial column sizing; allow stretch
        self.tree.column('#0', width=320, minwidth=120, stretch=True)
        self.tree.column('offset', width=120, minwidth=60, stretch=True)
        self.tree.column('size', width=110, minwidth=60, stretch=True)
        self.tree.column('access', width=120, minwidth=60, stretch=True)
        # Row highlight tags
        try:
            import tkinter.font as tkfont
            self.tree.tag_configure('match', background='#FFF4C2')  # light highlight for matches
            # Yellow background + bold for registers that have notes
            bold_font = None
            try:
                base_font = tkfont.nametofont(self.tree.cget('font'))
                bold_font = tkfont.Font(root, base_font, weight='bold')
            except Exception:
                bold_font = None
            if bold_font is not None:
                self.tree.tag_configure('has_note', background='#FFF59D', font=bold_font)
            else:
                self.tree.tag_configure('has_note', background='#FFF59D')
        except Exception:
            pass
        
        # Add scrollbar
        self.y_scroll = ttk.Scrollbar(self.tree_frame, orient='vertical', command=self.tree.yview)
        self.x_scroll = ttk.Scrollbar(self.tree_frame, orient='horizontal', command=self.tree.xview)
        # We will wrap these later to refresh highlight overlay after scrolling
        self.tree.configure(yscrollcommand=self.y_scroll.set, xscrollcommand=self.x_scroll.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.y_scroll.grid(row=0, column=1, sticky='ns')
        self.x_scroll.grid(row=1, column=0, sticky='ew')

        # Highlight overlay canvas on top of tree to draw substring highlights
        # Determine a valid background color (empty string is invalid for Tk)
        try:
            style = ttk.Style()
            tree_bg = style.lookup('Treeview', 'background') or self.tree.cget('background') or '#ffffff'
        except Exception:
            tree_bg = '#ffffff'
        self._hl_canvas = tk.Canvas(self.tree, highlightthickness=0, bd=0, background=tree_bg)
        # Disable overlay for now to avoid obscuring Treeview text
        # self._hl_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Capture font for measuring text width in pixels
        try:
            import tkinter.font as tkfont
            self._tree_font = tkfont.nametofont(self.tree.cget('font'))
        except Exception:
            self._tree_font = None
        # Wrap scrollbar set methods to trigger overlay refresh
        self._orig_yset = self.y_scroll.set
        self._orig_xset = self.x_scroll.set
        def _yset(first, last):
            self._orig_yset(first, last)
            self._refresh_highlight_overlay()

        # _rebuild_snps_tree is defined as a class method below
        def _xset(first, last):
            self._orig_xset(first, last)
            self._refresh_highlight_overlay()
        self.tree.configure(yscrollcommand=_yset, xscrollcommand=_xset)
        # Bind redraws
        self.tree.bind('<Configure>', self._refresh_highlight_overlay)
        # Debounced details refresh
        self._details_after_id = None
        def _schedule_details_refresh(*_):
            try:
                if self._details_after_id:
                    self.root.after_cancel(self._details_after_id)
                self._details_after_id = self.root.after(30, self._on_tree_select)
            except Exception:
                self._on_tree_select()
        self.tree.bind('<<TreeviewSelect>>', lambda e: _schedule_details_refresh(), add=True)
        # Common interactions that change selection/focus
        self.tree.bind('<ButtonRelease-1>', lambda e: _schedule_details_refresh(), add=True)
        for key in ('<KeyRelease-Up>','<KeyRelease-Down>','<KeyRelease-Left>','<KeyRelease-Right>','<KeyRelease-Home>','<KeyRelease-End>','<KeyRelease-Return>'):
            self.tree.bind(key, lambda e: _schedule_details_refresh(), add=True)
        self.tree.bind('<Expose>', self._refresh_highlight_overlay)
        # Auto-fit handlers: when nodes open or after UI maps
        self.tree.bind('<<TreeviewOpen>>', lambda e: (self._autofit_tree_columns(), _schedule_details_refresh()))
        self.tree.bind('<<TreeviewClose>>', lambda e: _schedule_details_refresh())
        self.root.after(300, self._autofit_tree_columns)
        # Match spans map: item_id -> { column_id: [(start,end), ...] }
        # column_id in {'#0','offset','size','access'} but we render for '#0','offset','access'
        self._match_spans = {}
        
        # Configure grid weights
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Right panel split: Details (top) | Notes (bottom) with a draggable sash
        self.details_split = ttk.PanedWindow(self.details_frame, orient=tk.VERTICAL)
        self.details_split.pack(fill=tk.BOTH, expand=True)
        details_top = ttk.Frame(self.details_split)
        notes_bottom = ttk.Frame(self.details_split)
        self.details_split.add(details_top, weight=3)
        self.details_split.add(notes_bottom, weight=2)

        # Register details panel + zoom controls (in top pane)
        zoom_bar = ttk.Frame(details_top)
        zoom_bar.pack(fill=tk.X, padx=5, pady=(5,0))
        ttk.Label(zoom_bar, text="Details").pack(side=tk.LEFT)
        ttk.Button(zoom_bar, text="A-", width=3, command=lambda: self._adjust_details_zoom(-1)).pack(side=tk.RIGHT, padx=(2,0))
        ttk.Button(zoom_bar, text="A+", width=3, command=lambda: self._adjust_details_zoom(+1)).pack(side=tk.RIGHT)
        ttk.Button(zoom_bar, text="A=", width=3, command=lambda: self._adjust_details_zoom(0)).pack(side=tk.RIGHT, padx=(2,6))
        # Copy/Save and collapse toggle
        ttk.Button(zoom_bar, text="Copy", width=6, command=self._copy_details_to_clipboard).pack(side=tk.RIGHT, padx=(6,2))
        ttk.Button(zoom_bar, text="Save MD", width=7, command=self._save_details_markdown).pack(side=tk.RIGHT)
        self.details_collapse_long = True
        self._collapse_btn = ttk.Checkbutton(zoom_bar, text='Collapse long', command=self._toggle_collapse, style='Toolbutton')
        self._collapse_var = tk.BooleanVar(value=True)
        self._collapse_btn.config(variable=self._collapse_var)
        self._collapse_btn.pack(side=tk.RIGHT, padx=(6,2))
        self.details_text = scrolledtext.ScrolledText(
            details_top, wrap=tk.WORD, width=40, height=18
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2,2))
        # Details font and tags
        try:
            import tkinter.font as tkfont
            self._details_font = tkfont.nametofont(self.details_text.cget('font'))
            self._details_base_size = self._details_font.cget('size') or 10
        except Exception:
            self._details_font = None
            self._details_base_size = 10
        # Tags for formatting
        try:
            # Headings
            self.details_text.tag_configure('h1', font=(self.details_text.cget('font'), 0, 'bold'))
            self.details_text.tag_configure('h2', font=(self.details_text.cget('font'), 0, 'bold'))
            # Inline code / ttwrap
            self.details_text.tag_configure('code', background='#f6f8fa')
            # Monospace rows (tables)
            self.details_text.tag_configure('mono', font=('Courier New', 10))
            # Label/Value lines
            self.details_text.tag_configure('label', font=(self.details_text.cget('font'), 0, 'bold'))
            self.details_text.tag_configure('value')
            # Paragraph spacing
            self.details_text.tag_configure('p', spacing3=6)
            # Match highlight in details
            self.details_text.tag_configure('matchhl', background='#FFF4A3')
        except Exception:
            pass
        # Zoom with Ctrl+MouseWheel
        self.details_text.bind('<Control-MouseWheel>', self._on_details_mousewheel)
        # Zoom keyboard shortcuts
        self.root.bind('<Control-=>', lambda e: self._adjust_details_zoom(+1))
        self.root.bind('<Control-minus>', lambda e: self._adjust_details_zoom(-1))
        self.root.bind('<Control-0>', lambda e: self._adjust_details_zoom(0))
        # Learning notes UI
        ttk.Label(notes_bottom, text="Notes (markdown):").pack(anchor='w', padx=5)
        # Markdown toolbar
        md_toolbar = ttk.Frame(notes_bottom)
        md_toolbar.pack(fill=tk.X, padx=5, pady=(0,2))
        ttk.Button(md_toolbar, text='B', width=3, command=lambda: self._md_wrap_selection('**','**')).pack(side=tk.LEFT)
        ttk.Button(md_toolbar, text='I', width=3, command=lambda: self._md_wrap_selection('*','*')).pack(side=tk.LEFT, padx=(2,0))
        ttk.Button(md_toolbar, text='H1', width=3, command=lambda: self._md_insert_heading(1)).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(md_toolbar, text='H2', width=3, command=lambda: self._md_insert_heading(2)).pack(side=tk.LEFT)
        ttk.Button(md_toolbar, text='H3', width=3, command=lambda: self._md_insert_heading(3)).pack(side=tk.LEFT)
        ttk.Button(md_toolbar, text='•', width=3, command=lambda: self._md_prefix_selection_lines('- ')).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(md_toolbar, text='1.', width=3, command=lambda: self._md_prefix_selection_lines('1. ')).pack(side=tk.LEFT)
        ttk.Button(md_toolbar, text='`code`', width=6, command=lambda: self._md_wrap_selection('`','`')).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(md_toolbar, text='```', width=4, command=self._md_insert_code_block).pack(side=tk.LEFT)
        ttk.Button(md_toolbar, text='Link', width=5, command=self._md_insert_link).pack(side=tk.LEFT, padx=(6,0))
        ttk.Button(md_toolbar, text='Image', width=6, command=self._md_insert_image).pack(side=tk.LEFT)
        ttk.Button(md_toolbar, text='Undo', width=5, command=lambda: self.note_text.edit_undo()).pack(side=tk.LEFT, padx=(12,0))
        ttk.Button(md_toolbar, text='Redo', width=5, command=lambda: self.note_text.edit_redo()).pack(side=tk.LEFT)
        # Notes filter controls
        # Notes filter controls moved to top toolbar (Show only noted)

        # Notes notebook with Edit and Preview tabs
        self.notes_nb = ttk.Notebook(notes_bottom)
        self.notes_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,4))

        edit_tab = ttk.Frame(self.notes_nb)
        preview_tab = ttk.Frame(self.notes_nb)
        self.notes_nb.add(edit_tab, text="Edit")
        self.notes_nb.add(preview_tab, text="Preview")

        self.note_text = scrolledtext.ScrolledText(
            edit_tab, wrap=tk.WORD, width=40, height=8
        )
        # Enable undo/redo on the text widget
        try:
            self.note_text.config(undo=True, autoseparators=True, maxundo=-1)
        except Exception:
            pass
        self.note_text.pack(fill=tk.BOTH, expand=True)

        # Preview widgets: prefer HTML if libs are present; fallback to text
        self._preview_html_label = None
        self._preview_text = None
        try:
            from tkhtmlview import HTMLLabel  # type: ignore
            self._preview_html_label = HTMLLabel(preview_tab, html="", background='white')
            self._preview_html_label.pack(fill=tk.BOTH, expand=True)
        except Exception:
            self._preview_text = scrolledtext.ScrolledText(preview_tab, wrap=tk.WORD, state='disabled')
            self._preview_text.pack(fill=tk.BOTH, expand=True)

        # Debounced preview update on changes
        self._preview_after_id = None
        def _schedule_preview_update(*_):
            try:
                if self._preview_after_id:
                    self.root.after_cancel(self._preview_after_id)
                self._preview_after_id = self.root.after(200, self._update_md_preview)
            except Exception:
                self._update_md_preview()
        self.note_text.bind('<KeyRelease>', lambda e: _schedule_preview_update(), add=True)
        self.notes_nb.bind('<<NotebookTabChanged>>', lambda e: _schedule_preview_update(), add=True)
        # Keyboard shortcuts for markdown actions
        self.note_text.bind('<Control-b>', lambda e: (self._md_wrap_selection('**','**'), 'break'))
        self.note_text.bind('<Control-i>', lambda e: (self._md_wrap_selection('*','*'), 'break'))
        self.note_text.bind('<Control-k>', lambda e: (self._md_insert_link(), 'break'))
        self.note_text.bind('<Control-Shift-c>', lambda e: (self._md_insert_code_block(), 'break'))
        self.note_text.bind('<Control-Shift-1>', lambda e: (self._md_insert_heading(1), 'break'))
        self.note_text.bind('<Control-Shift-2>', lambda e: (self._md_insert_heading(2), 'break'))
        self.note_text.bind('<Control-Shift-3>', lambda e: (self._md_insert_heading(3), 'break'))
        # Save/reload/open buttons
        note_btns = ttk.Frame(notes_bottom)
        note_btns.pack(fill=tk.X, padx=5, pady=(0,5))
        ttk.Button(note_btns, text='Save Note', command=self.save_current_note).pack(side=tk.LEFT)
        ttk.Button(note_btns, text='Open Notes File', command=self.open_notes_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(note_btns, text='Open Folder', command=self.open_note_folder).pack(side=tk.LEFT)
        ttk.Button(note_btns, text='Copy Path', command=self.copy_current_note_path).pack(side=tk.LEFT, padx=5)
        ttk.Button(note_btns, text='Remove Note', command=self.remove_current_note).pack(side=tk.LEFT)
        ttk.Button(note_btns, text='Reload Note', command=self.reload_current_note).pack(side=tk.LEFT)
        
        # Create menu
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open IP-XACT File", command=self.open_file)
        filemenu.add_command(label="Open General XML", command=self.open_general_xml)
        filemenu.add_command(label="Open SNPS TC .dat", command=self.open_snps_tc_dat)
        filemenu.add_command(label="Save Registers to CSV", command=self.save_to_csv)
        filemenu.add_command(label="Convert XML to CSV (fast)", command=self.convert_xml_to_csv)
        filemenu.add_command(label="Convert DAT to CSV", command=self.convert_dat_to_csv)
        filemenu.add_command(label="Convert SNPS TC .dat to CSV", command=self.convert_snps_tc_dat_to_csv)
        filemenu.add_command(label="Convert Regdump CSV to Standard CSV", command=self.convert_regdump_to_csv)
        filemenu.add_command(label="Load Regmap CSV", command=self.load_regmap_csv)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)
        
        # Add toolbar with save and search controls
        toolbar = tk.Frame(root)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        save_btn = tk.Button(toolbar, text="Save Registers to CSV", command=self.save_to_csv)
        save_btn.pack(side=tk.LEFT, padx=2, pady=2)
        # Auto-fit and expand/collapse buttons
        tk.Button(toolbar, text="Auto-fit Columns", command=self._autofit_tree_columns).pack(side=tk.LEFT, padx=(6,2), pady=2)
        tk.Button(toolbar, text="Expand All", command=lambda: self._set_tree_open_state(True)).pack(side=tk.LEFT, padx=(2,2), pady=2)
        tk.Button(toolbar, text="Collapse All", command=lambda: self._set_tree_open_state(False)).pack(side=tk.LEFT, padx=(2,6), pady=2)
        # Search controls (restored)
        tk.Label(toolbar, text=" Search:").pack(side=tk.LEFT, padx=(8, 2))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=28)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        # Context menu for search usage/help
        self.search_menu = tk.Menu(self.root, tearoff=0)
        self.search_menu.add_command(label="Search Usage...", command=self._show_search_usage)
        def _popup_search_menu(event):
            try:
                self.search_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.search_menu.grab_release()
        self.search_entry.bind('<Button-3>', _popup_search_menu)
        self.search_entry.bind('<Button-2>', _popup_search_menu)
        tk.Label(toolbar, text=" in ").pack(side=tk.LEFT)
        self.search_scope = tk.StringVar(value='any')
        self.scope_combo = ttk.Combobox(
            toolbar,
            textvariable=self.search_scope,
            width=16,
            state='readonly',
            values=[
                'name', 'description', 'map', 'block', 'access', 'size',
                'field', 'field_access', 'field_bits', 'field_width', 'field_offset',
                'value', 'reset', 'address', 'offset', 'any'
            ]
        )
        self.scope_combo.pack(side=tk.LEFT, padx=2)
        # Search options
        self.case_var = tk.BooleanVar(value=False)
        self.exact_var = tk.BooleanVar(value=False)
        self.regex_var = tk.BooleanVar(value=False)
        tk.Checkbutton(toolbar, text="Case", variable=self.case_var).pack(side=tk.LEFT, padx=(8, 2))
        tk.Checkbutton(toolbar, text="Exact", variable=self.exact_var).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(toolbar, text="Regex", variable=self.regex_var).pack(side=tk.LEFT, padx=2)
        # Whitespace logic toggle: All terms (AND) vs Any term (OR)
        self.and_terms_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="All terms (AND)", variable=self.and_terms_var).pack(side=tk.LEFT, padx=(8, 2))
        # Notes-only toggle replaces separate toolbar buttons
        self.show_notes_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(toolbar, text="Show only noted", variable=self.show_notes_only_var, command=self._toggle_show_notes_only).pack(side=tk.LEFT, padx=(8, 2))
        # Action buttons
        tk.Button(toolbar, text="Search", command=self.perform_search).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Save Matches", command=self.save_matches_to_csv).pack(side=tk.LEFT, padx=6)
        tk.Button(toolbar, text="Save Matches (SNPS)", command=self.save_matches_to_snps_csv).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Query Builder", command=self.open_query_builder).pack(side=tk.LEFT, padx=2)
        # Save/Restore filter buttons
        tk.Button(toolbar, text="Save Filter", command=self.save_filter).pack(side=tk.LEFT, padx=(8,2))
        tk.Button(toolbar, text="Restore Filter", command=self.restore_filter).pack(side=tk.LEFT, padx=2)
        # Search status and live search
        self.search_status = tk.Label(toolbar, text="", foreground="#a00")
        self.search_status.pack(side=tk.LEFT, padx=(8, 2))
        # Live re-highlight in details when typing/toggling options
        try:
            self.search_entry.bind('<KeyRelease>', lambda e: self._apply_details_highlight_safe(), add=True)
            self.case_var.trace_add('write', lambda *a: self._apply_details_highlight_safe())
            self.exact_var.trace_add('write', lambda *a: self._apply_details_highlight_safe())
            self.regex_var.trace_add('write', lambda *a: self._apply_details_highlight_safe())
            self.and_terms_var.trace_add('write', lambda *a: self._apply_details_highlight_safe())
        except Exception:
            pass

    def _default_notes_dir(self) -> str:
        """Return a sensible default notes directory.
        Primary: C:\\Users\\juesh\\OneDrive\\Documents\\reg_maps\\
        Fallbacks: <home>\\OneDrive\\Documents\\reg_maps or <home>\\Documents\\reg_maps
        """
        try:
            # User-specified primary default
            primary = os.path.join(os.path.expanduser('~'), 'OneDrive', 'Documents', 'reg_maps')
            # If username casing differs, this still resolves via expanduser
            os.makedirs(primary, exist_ok=True)
            return primary
        except Exception:
            pass
        try:
            home = os.path.expanduser('~')
            candidates = [
                os.path.join(home, 'OneDrive', 'Documents', 'reg_maps'),
                os.path.join(home, 'Documents', 'reg_maps'),
            ]
            for c in candidates:
                try:
                    os.makedirs(c, exist_ok=True)
                    return c
                except Exception:
                    continue
            return candidates[-1]
        except Exception:
            # Last resort: current working directory
            return os.path.join(os.getcwd(), 'reg_maps')

        # Bottom status bar: left = messages, right = current file path
        self.status_bar = ttk.Frame(self.main_frame)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_msg = ttk.Label(self.status_bar, text="", anchor='w')
        self.status_msg.pack(side=tk.LEFT, padx=6, pady=2)
        self.status_path = ttk.Label(self.status_bar, text="", anchor='e')
        self.status_path.pack(side=tk.RIGHT, padx=6)
        self._search_after_id = None
        self.search_entry.bind('<KeyRelease>', self._on_search_key)
        # Cache for matched rows
        self.matched_registers = None

    # ========= Column Auto-fit Utilities =========
    def _autofit_column(self, col_id: str, padding: int = 16, max_width: int = 800):
        """Auto-size one column to fit header and visible items."""
        try:
            font = self._tree_font
        except Exception:
            font = None
        # Start with header text width
        try:
            header = self.tree.heading(col_id)['text']
        except Exception:
            header = ''
        max_px = 0
        if font is not None:
            try:
                max_px = font.measure(str(header))
            except Exception:
                max_px = len(str(header)) * 8
        else:
            max_px = len(str(header)) * 8
        # Iterate visible items only to keep it fast
        items = self.tree.get_children('')
        stack = list(items)
        while stack:
            iid = stack.pop()
            try:
                if col_id == '#0':
                    text = self.tree.item(iid, 'text')
                else:
                    vals = self.tree.item(iid, 'values')
                    cols = self.tree['columns']
                    try:
                        idx = cols.index(col_id)
                        text = vals[idx] if idx < len(vals) else ''
                    except ValueError:
                        text = ''
            except Exception:
                text = ''
            px = font.measure(str(text)) if font else len(str(text)) * 8
            if px > max_px:
                max_px = px
            # If node is open, traverse its children
            if self.tree.item(iid, 'open'):
                stack.extend(self.tree.get_children(iid))
        # Apply width with padding and clamp
        width = min(max_px + padding, max_width)
        try:
            self.tree.column(col_id, width=width)
        except Exception:
            pass

    def _autofit_tree_columns(self):
        """Auto-size all columns to fit content (visible rows) and headers."""
        try:
            all_cols = ['#0'] + list(self.tree['columns'])
        except Exception:
            all_cols = ['#0']
        for c in all_cols:
            self._autofit_column(c)
        # Track last selected register info for notes
        self._last_reg_info = None
    
    def _set_tree_open_state(self, open_state: bool):
        """Expand or collapse all nodes in the register tree."""
        try:
            # Breadth-first traversal to avoid deep recursion in very large trees
            queue = list(self.tree.get_children(''))
            while queue:
                item = queue.pop(0)
                try:
                    self.tree.item(item, open=open_state)
                except Exception:
                    pass
                # Always traverse children so we touch every node
                queue.extend(self.tree.get_children(item))
            # After changing open state, re-fit columns a bit later
            self.root.after(50, self._autofit_tree_columns)
        except Exception as e:
            self.debug_print(f"Expand/Collapse error: {e}")
    
    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("IP-XACT files", "*.xml"), ("All files", "*.*")],
            title="Select IP-XACT File"
        )
        if not file_path:
            return
            
        try:
            # First, verify the file exists and is not empty
            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"File not found: {file_path}")
                return
                
            if os.path.getsize(file_path) == 0:
                messagebox.showerror("Error", "The selected file is empty")
                return
                
            # Check if file contains XML content (don't require XML declaration)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # Check if the file appears to be XML (starts with < and contains >)
                if not (content.startswith('<') and '>' in content):
                    if not messagebox.askyesno(
                        "Warning", 
                        "This doesn't appear to be an XML file. Try to load it anyway?"
                    ):
                        return
            
            # Proceed with loading the file
            self._set_current_path(file_path)
            self.load_xml(file_path)
            
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to read file: {str(e)}")
    
    def detect_namespaces(self, root):
        """Detect and register all namespaces from the XML root element"""
        # First, register all common namespaces
        ns_map = {}
        
        # Extract namespaces from the root element
        for prefix, uri in root.attrib.items():
            if prefix.startswith('xmlns:'):
                ns_map[prefix[6:]] = uri
            elif prefix == 'xmlns':
                ns_map[''] = uri  # Default namespace
        
        # Register all found namespaces
        self.ns = {**self.common_namespaces, **ns_map}
        
        # Also register common namespaces with different prefixes if they point to the same URI
        uri_to_prefix = {}
        for prefix, uri in self.ns.items():
            if uri not in uri_to_prefix:
                uri_to_prefix[uri] = []
            uri_to_prefix[uri].append(prefix)
        
        # For each URI, make sure all prefixes are registered
        for uri, prefixes in uri_to_prefix.items():
            for prefix in prefixes:
                self.ns[prefix] = uri
    
    def parse_number(self, num_str, default=0):
        """Parse a number that could be in decimal, hex (0x), or Verilog hex ('h) format"""
        if not num_str:
            return default
            
        num_str = str(num_str).strip().strip("'").lower()
        
        # Handle Verilog-style hex (e.g., 'h20000 or h20000)
        if num_str.startswith('h'):
            try:
                return int(num_str[1:], 16)
            except (ValueError, IndexError):
                return default
        # Handle 0x hex format
        elif num_str.startswith('0x'):
            try:
                return int(num_str, 16)
            except ValueError:
                return default
        # Handle decimal
        else:
            try:
                return int(num_str)
            except ValueError:
                return default
    
    def find_element(self, parent, tag_name, default=''):
        """Find an element with the given tag name in any namespace.
        Prefer direct children; fall back to descendants. Avoid XPath predicates
        that aren't supported by ElementTree (e.g., local-name()).
        """
        def _local(t: str) -> str:
            return t.split('}', 1)[-1] if '}' in t else t

        # Direct children first
        for child in list(parent):
            if _local(child.tag) == tag_name and child.text is not None:
                return child.text.strip()

        # Fallback: search descendants
        for elem in parent.iter():
            if elem is parent:
                continue
            if _local(elem.tag) == tag_name and elem.text is not None:
                return elem.text.strip()
        return default
    
    def debug_print(self, *args):
        """Print debug messages if debug mode is enabled"""
        if hasattr(self, 'debug_mode') and self.debug_mode:
            message = ' '.join(str(arg) for arg in args)
            print(f"[DEBUG] {message}")
            self.debug_log.append(message)
            
            # Update the details panel with the last 20 debug messages
            self._set_details_content("Debug Log:\n" + "\n".join(self.debug_log[-20:]))

    def open_general_xml(self):
        """Open any XML file and show its hierarchical structure in the tree view."""
        file_path = filedialog.askopenfilename(
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            title="Select XML File"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Strip BOM if present and unescape HTML entities
            content = content.lstrip('\ufeff')
            if any(ent in content for ent in ('&lt;', '&gt;', '&amp;')):
                content = html.unescape(content)
            try:
                root = ET.fromstring(content)
                parse_mode = 'xml'
            except ET.ParseError:
                # Fallback: try tolerant vendor "Page/Subject/Byte/Bit" format
                root = None
                parse_mode = 'loose'
        except Exception as e:
            messagebox.showerror("XML Error", f"Failed to load XML: {e}")
            return
        # Clear current tree and details
        self.tree.delete(*self.tree.get_children())
        self.details_text.delete(1.0, tk.END)
        self.registers = []
        self._node_meta = {}
        if parse_mode == 'xml' and root is not None:
            # Insert root and recurse
            root_text = self._build_pretty_node_text(root)
            root_id = self.tree.insert('', 'end', text=root_text, open=True)
            self._node_meta[root_id] = {
                'mode': 'xml',
                'tag': root.tag,
                'attrib': dict(root.attrib),
                'text': (root.text or '').strip(),
                'element': root,
            }
            try:
                self._insert_xml_node(root, root_id)
            except Exception as e:
                self.debug_print(f"Error populating XML tree: {e}")
            self.root.title(f"General XML Viewer - {os.path.basename(file_path)}")
            self._set_current_path(file_path)
        else:
            # Loose parser path
            ok = self._open_loose_page_xml(content)
            if not ok:
                messagebox.showerror(
                    "XML Error",
                    "Failed to parse file as XML and as vendor Page/Subject/Byte/Bit format."
                )
                return
            self.root.title(f"General XML Viewer (Loose) - {os.path.basename(file_path)}")

    def open_snps_tc_dat(self):
        """Open a Synopsys TC tab-delimited registers .dat and show Module->Register->Field tree."""
        file_path = filedialog.askopenfilename(
            filetypes=[("SNPS TC dat", "*.dat"), ("All files", "*.*")],
            title="Select SNPS TC .dat File"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to read file: {e}")
            return
        self._populate_snps_tc_tree(content)
        self._set_current_path(file_path)
        self.root.title(f"SNPS TC Viewer - {os.path.basename(file_path)}")

    def _populate_snps_tc_tree(self, content: str):
        """Parse SNPS TC .dat content and populate the tree view."""
        import re
        self.tree.delete(*self.tree.get_children())
        self.details_text.delete(1.0, tk.END)
        self.registers = []
        self._node_meta = {}
        modules = {}
        # Lines are tab-delimited with fields. We expect at least name, bitrange, addr, reg, reset, access, desc, alias.
        for raw in content.splitlines():
            line = raw.strip()
            if not line:
                continue
            cols = line.split('\t')
            # Normalize to length >= 10
            while len(cols) < 10:
                cols.append('')
            full = cols[0]
            bitrange = cols[1]
            addr = cols[2]
            regname = cols[3]
            reset = cols[5]
            access = cols[6]
            desc = cols[8].strip('"')
            alias = cols[9]
            # full like MODULE.REGISTER.FIELD
            parts = full.split('.')
            if len(parts) < 2:
                module = 'ROOT'
                register = parts[0]
                field = parts[0]
            else:
                module = parts[0]
                register = parts[1] if len(parts) > 1 else ''
                field = parts[2] if len(parts) > 2 else ''
            mod = modules.setdefault(module, {})
            reg = mod.setdefault(register, [])
            reg.append({
                'field': field,
                'bitrange': bitrange,
                'address': addr,
                'reset': reset,
                'access': access,
                'desc': desc,
                'alias': alias,
                'full': full,
                'regname': regname,
            })
        # Build tree with computed register widths and end addresses
        def parse_bitrange_to_width(br: str):
            try:
                if not br:
                    return None, None, None
                if ':' in br or '-' in br:
                    msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                    width = abs(msb - lsb) + 1
                else:
                    msb = lsb = int(br)
                    width = 1
                return width, msb, lsb
            except Exception:
                return None, None, None
        def size_bytes_from_bits(bits: int):
            if bits is None or bits <= 0:
                return 4  # default heuristic
            if bits <= 8:
                return 1
            if bits <= 16:
                return 2
            if bits <= 32:
                return 4
            if bits <= 64:
                return 8
            # round up to nearest byte
            return (bits + 7) // 8
        for module, regs in modules.items():
            mid = self.tree.insert('', 'end', text=f"Module {module}", open=True)
            self._node_meta[mid] = {'mode': 'snps', 'kind': 'module', 'name': module}
            for reg, fields in regs.items():
                # Determine address, reset from first row
                addr = fields[0]['address']
                reglabel = reg or fields[0]['regname']
                # Compute register width heuristic based on fields
                max_width = 0
                max_msb = -1
                for ent in fields:
                    w, msb, lsb = parse_bitrange_to_width(ent.get('bitrange',''))
                    if w and w > max_width:
                        max_width = w
                    if msb is not None and msb > max_msb:
                        max_msb = msb
                # Another heuristic: if max_msb+1 is larger than width, take it
                if max_msb >= 0 and (max_msb + 1) > max_width:
                    max_width = max_msb + 1
                size_bytes = size_bytes_from_bits(max_width)
                # Compute end address (inclusive)
                addr_end_hex = ''
                try:
                    addr_int = int(addr, 16)
                    addr_end_int = addr_int + max(1, size_bytes) - 1
                    addr_end_hex = f"0x{addr_end_int:08X}"
                except Exception:
                    addr_int = None
                    addr_end_int = None
                # Tag register rows; include 'has_note' when a note file exists
                _tags = ['register']
                try:
                    if self._has_note_for({'name': reglabel, 'block': module, 'map': ''}):
                        _tags.append('has_note')
                except Exception:
                    pass
                rid = self.tree.insert(mid, 'end', text=f"Register {reglabel} @ {addr}", open=False, tags=tuple(_tags))
                self._node_meta[rid] = {
                    'mode': 'snps', 'kind': 'register', 'name': reglabel, 'address': addr,
                    'reg_width_bits': max_width, 'reg_size_bytes': size_bytes,
                    'addr_start_int': addr_int, 'addr_end_int': addr_end_int, 'addr_end_hex': addr_end_hex
                }
                for ent in fields:
                    flabel = ent['field'] or ent['full']
                    text = f"Field {flabel} [{ent['bitrange']}] {ent['access']} reset={ent['reset']}"
                    fid = self.tree.insert(rid, 'end', text=text, open=False, tags=('field',))
                    meta = ent.copy()
                    meta.update({'mode': 'snps', 'kind': 'field', 'module': module, 'register': reglabel})
                    self._node_meta[fid] = meta
        # Keep a copy for search/clear restore
        self._snps_modules = modules
        # Also synthesize self.registers for the search pipeline
        synthesized = []
        for module, regs in modules.items():
            for reg, fields in regs.items():
                # Compute width/offsets from bitrange for each field
                def _bo_bw(br: str):
                    try:
                        if not br:
                            return ('0','1')
                        if ':' in br or '-' in br:
                            msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                            return (str(lsb), str(abs(msb-lsb)+1))
                        idx = int(br, 0)
                        return (str(idx), '1')
                    except Exception:
                        return ('0','1')
                # Use first row for address and reg name fallback
                addr = fields[0].get('address','') if fields else ''
                reglabel = reg or (fields[0].get('regname','') if fields else '')
                # Reuse the width heuristic already computed above
                max_width = 0
                max_msb = -1
                for ent in fields:
                    br = ent.get('bitrange','')
                    try:
                        if br:
                            if ':' in br or '-' in br:
                                msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                                w = abs(msb - lsb) + 1
                                if w > max_width: max_width = w
                                if msb > max_msb: max_msb = msb
                            else:
                                msb = lsb = int(br)
                                if 1 > max_width: max_width = 1
                                if msb > max_msb: max_msb = msb
                    except Exception:
                        pass
                if max_msb >= 0 and (max_msb + 1) > max_width:
                    max_width = max_msb + 1
                reg_rec = {
                    'name': reglabel,
                    'absolute_address': addr,
                    'offset': addr,
                    'size': str(max_width) if max_width else '',
                    'access': '',
                    'description': '',
                    'map': '',
                    'block': module,
                    'fields': []
                }
                for ent in fields:
                    bo, bw = _bo_bw(ent.get('bitrange',''))
                    reg_rec['fields'].append({
                        'name': ent.get('field',''),
                        'bit_offset': bo,
                        'bit_width': bw,
                        'access': ent.get('access',''),
                        'reset_value': ent.get('reset',''),
                        'description': ent.get('desc','')
                    })
                synthesized.append(reg_rec)
        self.registers = synthesized
        self.matched_registers = None
        # Summary to details panel
        total_regs = sum(len(v) for v in modules.values())
        total_fields = sum(len(flds) for regs in modules.values() for flds in regs.values())
        self._set_details_content(f"SNPS TC parsed: modules={len(modules)} registers={total_regs} fields={total_fields}")

    def convert_snps_tc_dat_to_csv(self):
        """Convert a SNPS TC .dat file to CSV with columns: Module,Register,Field,BitRange,Address,Reset,Access,Description,Alias,FullPath"""
        file_path = filedialog.askopenfilename(
            filetypes=[("SNPS TC dat", "*.dat"), ("All files", "*.*")],
            title="Select SNPS TC .dat File"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to read file: {e}")
            return
        # Parse lines similar to population and compute register-level metrics
        rows = []
        # First pass: group by (module, register) to compute width/size/end
        by_reg = {}
        def parse_bitrange_to_width(br: str):
            try:
                if not br:
                    return None, None, None
                if ':' in br or '-' in br:
                    msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                    width = abs(msb - lsb) + 1
                else:
                    msb = lsb = int(br)
                    width = 1
                return width, msb, lsb
            except Exception:
                return None, None, None
        def size_bytes_from_bits(bits: int):
            if bits is None or bits <= 0:
                return 4
            if bits <= 8:
                return 1
            if bits <= 16:
                return 2
            if bits <= 32:
                return 4
            if bits <= 64:
                return 8
            return (bits + 7) // 8
        lines = [ln for ln in content.splitlines() if ln.strip()]
        parsed = []
        for raw in lines:
            cols = raw.strip().split('\t')
            while len(cols) < 10:
                cols.append('')
            full = cols[0]
            bitrange = cols[1]
            addr = cols[2]
            regname = cols[3]
            reset = cols[5]
            access = cols[6]
            desc = cols[8].strip('"')
            alias = cols[9]
            parts = full.split('.')
            if len(parts) >= 3:
                module, register, field = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                module, register = parts
                field = ''
            else:
                module, register, field = '', full, ''
            parsed.append((module, register or regname, field, bitrange, addr, reset, access, desc, alias, full))
            key = (module, register or regname, addr)
            info = by_reg.setdefault(key, {'max_width': 0, 'max_msb': -1})
            w, msb, lsb = parse_bitrange_to_width(bitrange)
            if w and w > info['max_width']:
                info['max_width'] = w
            if msb is not None and msb > info['max_msb']:
                info['max_msb'] = msb
        # Compute reg metrics
        reg_metrics = {}
        for (module, register, addr), info in by_reg.items():
            max_width = info['max_width']
            if info['max_msb'] >= 0 and (info['max_msb'] + 1) > max_width:
                max_width = info['max_msb'] + 1
            size_bytes = size_bytes_from_bits(max_width)
            try:
                addr_int = int(addr, 16)
                addr_end_int = addr_int + max(1, size_bytes) - 1
                addr_end_hex = f"0x{addr_end_int:08X}"
            except Exception:
                addr_int = None
                addr_end_int = None
                addr_end_hex = ''
            reg_metrics[(module, register, addr)] = {
                'reg_width_bits': max_width,
                'reg_size_bytes': size_bytes,
                'addr_start_int': addr_int,
                'addr_end_int': addr_end_int,
                'addr_end_hex': addr_end_hex,
            }
        # Second pass: emit rows with computed fields
        for module, register, field, bitrange, addr, reset, access, desc, alias, full in parsed:
            # Field derived
            fw, fmsb, flsb = parse_bitrange_to_width(bitrange)
            fmask_hex = ''
            fmask_dec = ''
            fshift = ''
            if fw is not None and flsb is not None and fw > 0 and flsb >= 0 and fw <= 64:
                mask = ((1 << fw) - 1) << flsb
                fmask_hex = f"0x{mask:X}"
                fmask_dec = str(mask)
                fshift = str(flsb)
            m = reg_metrics.get((module, register, addr), {})
            # Compose a concise details string (single-line, with \n escaped)
            details_txt = self._compose_details_snps_inline(
                module, register, field, bitrange, addr, reset, access, desc,
                m.get('reg_width_bits',''), m.get('reg_size_bytes',''), m.get('addr_end_hex','')
            )
            rows.append([
                module, register, field, bitrange, addr, reset, access, desc, alias, full,
                m.get('reg_width_bits',''), m.get('reg_size_bytes',''),
                m.get('addr_start_int',''), m.get('addr_end_hex',''), m.get('addr_end_int',''),
                fw if fw is not None else '', fmsb if fmsb is not None else '', flsb if flsb is not None else '',
                fmask_hex, fmask_dec, fshift,
                details_txt
            ])
        # Save CSV
        save_path = filedialog.asksaveasfilename(
            defaultextension='.csv', filetypes=[('CSV', '*.csv')], title='Save CSV As'
        )
        if not save_path:
            return
        try:
            import csv
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow([
                    'Module','Register','Field','BitRange','Address','Reset','Access','Description','Alias','FullPath',
                    'RegWidthBits','RegSizeBytes','AddrStartDec','AddrEndHex','AddrEndDec',
                    'FieldWidth','FieldMsb','FieldLsb','FieldMaskHex','FieldMaskDec','FieldShift','Details'
                ])
                w.writerows(rows)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save CSV: {e}")
            return
        messagebox.showinfo("Done", f"Saved {len(rows)} rows to {save_path}")

    def save_to_csv(self):
        """Save current view to CSV.
        - If SNPS TC .dat is loaded (tree nodes carry mode='snps'), export enriched CSV with computed fields.
        - Else if IP-XACT registers are present in self.registers, export legacy register/field CSV.
        """
        has_snps = any((isinstance(v, dict) and v.get('mode') == 'snps') for v in getattr(self, '_node_meta', {}).values())
        if not has_snps and not self.registers:
            messagebox.showwarning("No Data", "No register data to save. Please open a file first.")
            return
        # Options (only applies to legacy register export)
        opt = { 'skip_placeholders': tk.BooleanVar(value=True) }
        dlg = tk.Toplevel(self.root)
        dlg.title('Save CSV Options')
        dlg.transient(self.root)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Checkbutton(frm, text="Skip unnamed registers with no fields (legacy export)", variable=opt['skip_placeholders']).pack(anchor='w')
        chosen = {'ok': False}
        def ok():
            chosen['ok'] = True
            dlg.destroy()
        def cancel():
            dlg.destroy()
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(8,0))
        ttk.Button(btns, text='OK', command=ok).pack(side=tk.LEFT)
        ttk.Button(btns, text='Cancel', command=cancel).pack(side=tk.RIGHT)
        self.root.wait_window(dlg)
        if not chosen['ok']:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension='.csv', filetypes=[('CSV', '*.csv')], title='Save CSV As'
        )
        if not save_path:
            return
        try:
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                if has_snps:
                    w = csv.writer(f)
                    w.writerow([
                        'Module','Register','Field','BitRange','Address','Reset','Access','Description','Alias','FullPath',
                        'RegWidthBits','RegSizeBytes','AddrStartDec','AddrEndHex','AddrEndDec',
                        'FieldWidth','FieldMsb','FieldLsb','FieldMaskHex','FieldMaskDec','FieldShift','Details'
                    ])
                    # Walk SNPS tree
                    for mid in self.tree.get_children(''):
                        mmeta = self._node_meta.get(mid, {})
                        if mmeta.get('mode') != 'snps' or mmeta.get('kind') != 'module':
                            continue
                        module = mmeta.get('name','')
                        for rid in self.tree.get_children(mid):
                            rmeta = self._node_meta.get(rid, {})
                            if rmeta.get('kind') != 'register':
                                continue
                            reg = rmeta.get('name','')
                            reg_addr = rmeta.get('address','')
                            for fid in self.tree.get_children(rid):
                                fmeta = self._node_meta.get(fid, {})
                                if fmeta.get('kind') != 'field':
                                    continue
                                field = fmeta.get('field','')
                                br = fmeta.get('bitrange','')
                                addr = fmeta.get('address','') or reg_addr
                                reset = fmeta.get('reset','')
                                access = fmeta.get('access','')
                                desc = fmeta.get('desc','')
                                alias = fmeta.get('alias','')
                                full = fmeta.get('full','')
                                # Derive field width/mask
                                fw = fmsb = flsb = ''
                                fmask_hex = fmask_dec = fshift = ''
                                try:
                                    if br:
                                        if ':' in br or '-' in br:
                                            msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                                            fw = abs(msb - lsb) + 1
                                            fmsb, flsb = msb, lsb
                                        else:
                                            fw = 1
                                            fmsb = flsb = int(br)
                                        if fw and flsb is not None and int(fw) <= 64:
                                            mask = ((1 << int(fw)) - 1) << int(flsb)
                                            fmask_hex = f"0x{mask:X}"
                                            fmask_dec = str(mask)
                                            fshift = str(flsb)
                                except Exception:
                                    pass
                                details_txt = self._compose_details_snps_inline(
                                    module=module,
                                    register=reg,
                                    field=field,
                                    bitrange=br,
                                    addr=addr,
                                    reset=reset,
                                    access=access,
                                    desc=desc,
                                    reg_bits=rmeta.get('reg_width_bits',''),
                                    reg_bytes=rmeta.get('reg_size_bytes',''),
                                    end_hex=rmeta.get('addr_end_hex',''),
                                    alias=alias,
                                    full=full,
                                    field_msb=fmsb,
                                    field_lsb=flsb,
                                    field_width=fw,
                                    field_mask=fmask_hex,
                                    field_shift=fshift
                                )
                                w.writerow([
                                    module, reg, field, br, addr, reset, access, desc, alias, full,
                                    rmeta.get('reg_width_bits',''), rmeta.get('reg_size_bytes',''),
                                    rmeta.get('addr_start_int',''), rmeta.get('addr_end_hex',''), rmeta.get('addr_end_int',''),
                                    fw, fmsb, flsb, fmask_hex, fmask_dec, fshift,
                                    details_txt
                                ])
                else:
                    # Legacy register export
                    w = csv.DictWriter(f, fieldnames=[
                        'Register','Absolute Address','Offset','Size (bits)','Access','Field','Bit Range','Field Access','Reset Value','Description','Details'
                    ])
                    w.writeheader()
                    skip_placeholders = bool(opt['skip_placeholders'].get())
                    skipped_count = 0
                    for reg in self.registers:
                        name = (reg.get('name','') or '').strip()
                        if skip_placeholders and ((not name or name == 'Unnamed Register') and not reg.get('fields')):
                            skipped_count += 1
                            continue
                        if not reg['fields']:
                            details_txt = self._compose_details_legacy_inline(
                                reg['name'], reg['absolute_address'], f"0x{self.parse_number(reg['offset'], 0):X}",
                                reg['size'], str(reg.get('access','')).upper(), '', '', '', '', reg['description']
                            )
                            w.writerow({
                                'Register': reg['name'],
                                'Absolute Address': reg['absolute_address'],
                                'Offset': f"0x{self.parse_number(reg['offset'], 0):X}",
                                'Size (bits)': reg['size'],
                                'Access': str(reg.get('access','')).upper(),
                                'Description': reg['description'],
                                'Details': details_txt
                            })
                        for field in reg['fields']:
                            try:
                                bo = self.parse_number(field.get('bit_offset','0'), 0)
                                bw = self.parse_number(field.get('bit_width','1'), 1)
                                hi = bo + bw - 1
                                bit_range = f"[{hi}:{bo}]"
                            except Exception:
                                bit_range = f"[{field.get('bit_offset','0')}]"
                            details_txt = self._compose_details_legacy_inline(
                                reg['name'], reg['absolute_address'], f"0x{self.parse_number(reg['offset'], 0):X}",
                                reg['size'], str(reg.get('access','')).upper(), field.get('name',''), bit_range,
                                str(field.get('access','')).upper(), field.get('reset_value',''), field.get('description','')
                            )
                            w.writerow({
                                'Register': reg['name'],
                                'Absolute Address': reg['absolute_address'],
                                'Offset': f"0x{self.parse_number(reg['offset'], 0):X}",
                                'Size (bits)': reg['size'],
                                'Access': str(reg.get('access','')).upper(),
                                'Field': field.get('name',''),
                                'Bit Range': bit_range,
                                'Field Access': str(field.get('access','')).upper(),
                                'Reset Value': field.get('reset_value',''),
                                'Description': field.get('description',''),
                                'Details': details_txt
                            })
            msg = f'Saved CSV to {save_path}'
            try:
                if not has_snps and skip_placeholders and skipped_count:
                    msg += f" (skipped {skipped_count} unnamed/fieldless registers)"
            except Exception:
                pass
            self._status(msg)
            messagebox.showinfo('Success', msg)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save file: {e}')

    # ========= CSV Details Composers =========
    def _compose_details_snps_inline(self, *args, **kwargs) -> str:
        """Return multi-line Markdown-like details for SNPS rows.
        Supports both positional (legacy) and keyword arguments.
        Positional order: module, register, field, bitrange, addr, reset, access, desc, reg_bits, reg_bytes, end_hex
        Extra optional kwargs: alias, full, field_msb, field_lsb, field_width, field_mask, field_shift
        """
        # Allow legacy positional usage
        if args and not kwargs:
            (module, register, field, bitrange, addr, reset, access, desc, reg_bits, reg_bytes, end_hex) = (
                list(args) + [None]*11
            )[:11]
            kwargs = dict(module=module, register=register, field=field, bitrange=bitrange, addr=addr,
                          reset=reset, access=access, desc=desc, reg_bits=reg_bits, reg_bytes=reg_bytes, end_hex=end_hex)
        g = lambda k, d='': kwargs.get(k, d) or ''
        module = g('module'); register = g('register'); field = g('field'); bitrange = g('bitrange')
        addr = g('addr'); reset = g('reset'); access = g('access'); desc = g('desc')
        reg_bits = g('reg_bits'); reg_bytes = g('reg_bytes'); end_hex = g('end_hex')
        alias = g('alias'); full = g('full')
        fmsb = g('field_msb'); flsb = g('field_lsb'); fwidth = g('field_width')
        fmask = g('field_mask'); fshift = g('field_shift')
        lines = []
        title = register or field or 'Register'
        lines.append(f"# {title}")
        if module:
            lines.append(f"- Module: {module}")
        if addr:
            lines.append(f"- Address: {addr}")
        size_bits = f"{reg_bits} bits" if reg_bits else ""
        size_bytes = f"{reg_bytes} bytes" if reg_bytes else ""
        if size_bits or size_bytes:
            both = f"{size_bits} ({size_bytes})" if (size_bits and size_bytes) else (size_bits or size_bytes)
            lines.append(f"- Size: {both}")
        if end_hex:
            lines.append(f"- End: {end_hex}")
        if alias:
            lines.append(f"- Alias: {alias}")
        if full:
            lines.append(f"- Full: {full}")
        if field or bitrange or access or reset or fmask:
            lines.append("")
            lines.append("## Field")
            if field:
                lines.append(f"- Name: {field}")
            if bitrange:
                lines.append(f"- Bits: [{bitrange}]" if '[' not in bitrange else f"- Bits: {bitrange}")
            if fwidth or fmsb or flsb:
                parts = []
                if fwidth: parts.append(f"Width {fwidth}")
                if fmsb != '' and flsb != '': parts.append(f"MSB {fmsb}, LSB {flsb}")
                if parts:
                    lines.append("- " + ", ".join(parts))
            if access:
                lines.append(f"- Access: {access}")
            if reset:
                lines.append(f"- Reset: {reset}")
            if fmask:
                shift_part = f", shift {fshift}" if fshift != '' else ''
                lines.append(f"- Mask: {fmask}{shift_part}")
        if desc:
            lines.append("")
            lines.append("## Description")
            lines.append(str(desc))
        return "\n".join(lines)

    def _compose_details_legacy_inline(self, *args, **kwargs) -> str:
        """Return multi-line Markdown-like details for IP-XACT/legacy rows.
        Positional order: reg, abs_addr, offset, size_bits, access, field, bit_range, field_access, reset_value, description
        Extra kwargs supported: map_name, block_name
        """
        if args and not kwargs:
            (reg, abs_addr, offset, size_bits, access, field, bit_range, field_access, reset_value, description) = (
                list(args) + [None]*10
            )[:10]
            kwargs = dict(reg=reg, abs_addr=abs_addr, offset=offset, size_bits=size_bits, access=access,
                          field=field, bit_range=bit_range, field_access=field_access, reset_value=reset_value,
                          description=description)
        g = lambda k, d='': kwargs.get(k, d) or ''
        reg = g('reg'); abs_addr = g('abs_addr'); size_bits = g('size_bits'); access = g('access')
        field = g('field'); bit_range = g('bit_range'); field_access = g('field_access'); reset_value = g('reset_value')
        description = g('description'); map_name = g('map_name'); block_name = g('block_name')
        lines = []
        title = reg or 'Register'
        lines.append(f"# {title}")
        if map_name:
            lines.append(f"- Map: {map_name}")
        if block_name:
            lines.append(f"- Block: {block_name}")
        if abs_addr:
            lines.append(f"- Address: {abs_addr}")
        if size_bits:
            lines.append(f"- Size: {size_bits} bits")
        if access:
            lines.append(f"- Access: {access}")
        if field or bit_range or field_access or reset_value:
            lines.append("")
            lines.append("## Field")
            if field:
                lines.append(f"- Name: {field}")
            if bit_range:
                lines.append(f"- Bits: {bit_range}")
            if field_access:
                lines.append(f"- Field Access: {field_access}")
            if reset_value:
                lines.append(f"- Reset: {reset_value}")
        if description:
            lines.append("")
            lines.append("## Description")
            lines.append(str(description))
        return "\n".join(lines)

    def _compose_details_compact(self, title: str = '', address: str = '', size_bits: str = '', access: str = '',
                                 field: str = '', bit_range: str = '', field_access: str = '', reset_value: str = '',
                                 description: str = '', map_name: str = '', block_name: str = '') -> str:
        parts = []
        if title:
            parts.append(f"Name: {title}")
        if map_name:
            parts.append(f"Map: {map_name}")
        if block_name:
            parts.append(f"Block: {block_name}")
        if address:
            parts.append(f"Addr: {address}")
        if size_bits:
            parts.append(f"Size: {size_bits}b")
        if access:
            parts.append(f"Acc: {access}")
        if field:
            parts.append(f"Field: {field}")
        if bit_range:
            parts.append(f"Bits: {bit_range}")
        if field_access:
            parts.append(f"FAcc: {field_access}")
        if reset_value:
            parts.append(f"Reset: {reset_value}")
        if description:
            s = re.sub(r"\s+", ' ', str(description)).strip()
            if len(s) > 160:
                s = s[:157] + '...'
            parts.append(f"Desc: {s}")
        return ' | '.join(parts)

    def _build_pretty_node_text(self, elem: ET.Element) -> str:
        """Return a compact label for a node: tag with key attributes count."""
        # Show tag and up to 2 attributes
        attrs = []
        for i, (k, v) in enumerate(elem.attrib.items()):
            if i >= 2:
                attrs.append('…')
                break
            attrs.append(f"{k}='{v}'")
        attr_part = (" " + " ".join(attrs)) if attrs else ""
        text_part = ""
        if elem.text and elem.text.strip():
            snippet = elem.text.strip()
            if len(snippet) > 40:
                snippet = snippet[:37] + '…'
            text_part = f" = {snippet}"
        return f"<{elem.tag}{attr_part}>{text_part}"

    def _insert_xml_node(self, elem: ET.Element, parent_id):
        """Recursively insert children of an XML element into the tree."""
        # Add attributes as child nodes
        if elem.attrib:
            attrs_id = self.tree.insert(parent_id, 'end', text='@attributes', open=False)
            self._node_meta[attrs_id] = {
                'mode': 'xml', 'kind': 'attributes', 'parent': parent_id
            }
            for k, v in elem.attrib.items():
                cid = self.tree.insert(attrs_id, 'end', text=f"{k} = '{v}'")
                self._node_meta[cid] = {
                    'mode': 'xml', 'kind': 'attribute', 'name': k, 'value': v, 'parent': attrs_id
                }
        # Add text node if present
        if elem.text and elem.text.strip():
            txt = elem.text.strip()
            if len(txt) > 200:
                txt = txt[:197] + '…'
            tid = self.tree.insert(parent_id, 'end', text=f"#text = {txt}")
            self._node_meta[tid] = {
                'mode': 'xml', 'kind': 'text', 'text': elem.text.strip(), 'parent': parent_id
            }
        # Add children
        for child in list(elem):
            child_text = self._build_pretty_node_text(child)
            child_id = self.tree.insert(parent_id, 'end', text=child_text, open=False)
            self._node_meta[child_id] = {
                'mode': 'xml',
                'tag': child.tag,
                'attrib': dict(child.attrib),
                'text': (child.text or '').strip(),
                'element': child,
                'parent': parent_id,
            }
            self._insert_xml_node(child, child_id)

    def _open_loose_page_xml(self, content: str) -> bool:
        """Parse a vendor loose-XML style with tags Page/Subject/Byte/Bit lacking closing tags.
        We infer hierarchy:
          - Page contains Subject or Byte
          - Subject contains Byte
          - Byte contains Bit
          - Bit is a leaf
        """
        try:
            import re as _re
            # Remove comments
            txt = _re.sub(r'<!--.*?-->', '', content, flags=_re.S)
            # Find tags
            tag_re = _re.compile(r'<\s*(Page|Subject|Byte|Bit)\b([^>]*)>', _re.I)
            attr_re = _re.compile(r'(\w+)\s*=\s*"([^"]*)"')
            stack = []  # list of (kind, tree_id)
            root_id = None
            def parse_attrs(s: str) -> dict:
                return {m.group(1): m.group(2) for m in attr_re.finditer(s)}
            def node_label(kind: str, attrs: dict) -> str:
                nm = attrs.get('Name') or attrs.get('name') or ''
                extra = []
                for k in ('Position', 'Type', 'Size'):
                    v = attrs.get(k) or attrs.get(k.lower())
                    if v:
                        extra.append(f"{k}={v}")
                extra_txt = (" " + " ".join(extra)) if extra else ""
                return f"{kind} {nm}{extra_txt}".strip()
            for m in tag_re.finditer(txt):
                kind = m.group(1)
                attrs = parse_attrs(m.group(2) or '')
                label = node_label(kind, attrs)
                # Determine parent based on kind and stack
                parent_id = None
                # Collapse stack to valid parent
                def stack_top_kind():
                    return stack[-1][0] if stack else None
                if kind == 'Page':
                    # reset stack, start new root
                    stack.clear()
                    root_id = self.tree.insert('', 'end', text=label, open=True)
                    self._node_meta[root_id] = {'mode': 'loose', 'kind': 'Page', 'attrs': attrs}
                    stack.append(('Page', root_id))
                    continue
                # For Subject, parent can be Page
                if kind == 'Subject':
                    while stack and stack_top_kind() not in ('Page',):
                        stack.pop()
                    parent_id = stack[-1][1] if stack else ''
                    nid = self.tree.insert(parent_id, 'end', text=label, open=True)
                    self._node_meta[nid] = {'mode': 'loose', 'kind': 'Subject', 'attrs': attrs, 'parent': parent_id}
                    stack.append(('Subject', nid))
                    continue
                # For Byte, parent can be Subject or Page
                if kind == 'Byte':
                    while stack and stack_top_kind() not in ('Subject','Page'):
                        stack.pop()
                    parent_id = stack[-1][1] if stack else ''
                    nid = self.tree.insert(parent_id, 'end', text=label, open=False)
                    self._node_meta[nid] = {'mode': 'loose', 'kind': 'Byte', 'attrs': attrs, 'parent': parent_id}
                    stack.append(('Byte', nid))
                    continue
                # For Bit, parent must be Byte
                if kind == 'Bit':
                    while stack and stack_top_kind() not in ('Byte',):
                        stack.pop()
                    parent_id = stack[-1][1] if stack else ''
                    cid = self.tree.insert(parent_id, 'end', text=label, open=False)
                    self._node_meta[cid] = {'mode': 'loose', 'kind': 'Bit', 'attrs': attrs, 'parent': parent_id}
                    # Bit is leaf; do not push
                    continue
            return bool(root_id or self.tree.get_children(''))
        except Exception as e:
            self.debug_print(f"Loose XML parse error: {e}")
            return False

    def _on_tree_select(self, event=None):
        """When a tree node is selected, populate details panel with rich info."""
        try:
            if not hasattr(self, '_node_meta'):
                self._node_meta = {}
            sel = self.tree.selection()
            if not sel:
                # Clear details when nothing is selected
                self._set_details_content("")
                # Clear notes when nothing selected
                try:
                    self.note_text.delete(1.0, tk.END)
                except Exception:
                    pass
                return
            item = sel[0]
            # keep track of last selection
            self._last_selected_item = item
            meta = self._node_meta.get(item)
        except Exception as e:
            self._set_details_content(f"Selection error: {e}")
            return
        # Auto-load notes for the currently selected register (or its parent register)
        try:
            # Track last selected item for downstream helpers
            try:
                sel = self.tree.selection()
                if sel:
                    self._last_selected_item = sel[0]
            except Exception:
                pass
            reg = self._resolve_current_register()
            if reg:
                self._last_reg_info = reg
                self._load_note_into_widget(reg)
            else:
                # No register resolved; clear notes view
                self.note_text.delete(1.0, tk.END)
                try:
                    self._last_reg_info = None
                except Exception:
                    pass
                # Refresh preview to blank state
                try:
                    self._update_md_preview()
                except Exception:
                    pass
        except Exception:
            pass
        # Build path by walking parents
        path_labels = []
        cur = item
        while cur:
            path_labels.append(self.tree.item(cur, 'text'))
            cur = self.tree.parent(cur)
        path = ' / '.join(reversed(path_labels))
        lines = []
        if not meta:
            lines.append(f"Node: {self.tree.item(item, 'text')}")
            lines.append(f"Path: {path}")
        else:
            mode = meta.get('mode')
            lines.append(f"Mode: {mode}")
            lines.append(f"Path: {path}")
            if mode == 'xml':
                kind = meta.get('kind')
                if kind == 'attribute':
                    lines.append(f"Attribute: {meta.get('name')} = {meta.get('value')}")
                elif kind == 'attributes':
                    lines.append("Attributes group")
                elif kind == 'text':
                    lines.append("Text node:")
                    lines.append(meta.get('text',''))
                else:
                    tag = meta.get('tag')
                    attrib = meta.get('attrib', {})
                    text = meta.get('text', '')
                    lines.append(f"Tag: <{tag}>")
                    # XPath-like path
                    def build_xpath(elem):
                        try:
                            e = meta.get('element')
                            # Build simple absolute path with position index among same-tag siblings
                            parts = []
                            while e is not None:
                                parent = e.getparent() if hasattr(e, 'getparent') else None
                                if parent is None:
                                    # fallback using ElementTree default (no parent); skip index
                                    parts.append(e.tag)
                                    break
                                same = [c for c in list(parent) if c.tag == e.tag]
                                idx = same.index(e) + 1 if e in same else 1
                                parts.append(f"{e.tag}[{idx}]")
                                e = parent
                            return '/' + '/'.join(reversed(parts))
                        except Exception:
                            return f"//{tag}"
                    lines.append(f"XPath: {build_xpath(meta.get('element'))}")
                    if attrib:
                        lines.append("Attributes:")
                        for k,v in sorted(attrib.items()):
                            lines.append(f"  - {k}: {v}")
                    # Namespace info if any
                    try:
                        if isinstance(tag, str) and tag.startswith('{'):
                            ns_uri, _, local = tag[1:].partition('}')
                            lines.append(f"Namespace: {ns_uri}")
                            lines.append(f"Local tag: {local}")
                    except Exception:
                        pass
                    if text:
                        lines.append("Text:")
                        lines.append(self._maybe_collapse(text))
                    # Counts
                    try:
                        elem = meta.get('element')
                        if elem is not None:
                            lines.append(f"Children: {len(list(elem))}")
                            lines.append(f"Attributes count: {len(elem.attrib)}")
                            if getattr(elem, 'tail', None):
                                t = elem.tail.strip()
                                if t:
                                    lines.append("Tail:")
                                    lines.append(t)
                    except Exception:
                        pass
                    # Outer XML snippet (compact)
                    try:
                        elem = meta.get('element')
                        if elem is not None:
                            import xml.etree.ElementTree as _ET
                            snippet = _ET.tostring(elem, encoding='unicode')
                            lines.append("\nOuter XML:")
                            lines.append(self._maybe_collapse(snippet, raw=True))
                    except Exception:
                        pass
            elif mode == 'loose':
                kind = meta.get('kind')
                attrs = meta.get('attrs', {})
                lines.append(f"Node: {kind}")
                if attrs:
                    lines.append("Attributes:")
                    for k,v in attrs.items():
                        lines.append(f"  - {k}: {v}")
                # Derived info
                pos = attrs.get('Position') if attrs else None
                if pos and ':' in pos:
                    try:
                        msb, lsb = [int(x) for x in pos.replace('-',':').split(':')]
                        width = abs(msb - lsb) + 1
                        lines.append(f"Width: {width} bits (from {pos})")
                        # Mask
                        if width > 0 and lsb >= 0 and width <= 64:
                            mask = ((1 << width) - 1) << lsb
                            lines.append(f"Mask: 0x{mask:X} ({mask}) shift={lsb}")
                    except Exception:
                        pass
                # Any embedded text content collapsed if very long
                t = attrs.get('Description') if attrs else None
                if t:
                    lines.append('Description:')
                    lines.append(self._maybe_collapse(t))
            elif mode == 'snps':
                kind = meta.get('kind')
                lines.append(f"Node: {kind}")
                if kind == 'module':
                    module_name = meta.get('name','')
                    lines.append(f"Module: {module_name}")
                    # Count registers
                    try:
                        child_regs = self.tree.get_children(item)
                        lines.append(f"Registers: {len(child_regs)}")
                    except Exception:
                        pass
                elif kind == 'register':
                    module_name = self.tree.item(self.tree.parent(item), 'text').replace('Module ','')
                    lines.append(f"Module: {module_name}")
                    # Consistent labels for readability
                    lines.append(f"Name: {meta.get('name','')}")
                    addr = meta.get('address','')
                    try:
                        addr_int = int(addr, 16)
                        lines.append(f"Absolute Address: {addr} ({addr_int})")
                    except Exception:
                        lines.append(f"Absolute Address: {addr}")
                    # Computed width/size/end
                    rw = meta.get('reg_width_bits')
                    rs = meta.get('reg_size_bytes')
                    if rw is not None:
                        lines.append(f"Size: {rw} bits")
                    if rs is not None:
                        lines.append(f"Size (bytes): {rs}")
                    if meta.get('addr_end_int') is not None:
                        lines.append(f"End Address: {meta.get('addr_end_hex')} ({meta.get('addr_end_int')})")
                    # Fields as a bullet list with wrapped descriptions
                    child_fields = []
                    try:
                        child_fields = self.tree.get_children(item)
                    except Exception:
                        child_fields = []
                    lines.append("\nFields:")
                    for fid in child_fields:
                        fmeta = self._node_meta.get(fid, {})
                        if fmeta.get('kind') != 'field':
                            continue
                        fname = fmeta.get('field','') or fmeta.get('full','')
                        bits = fmeta.get('bitrange','')
                        facc = fmeta.get('access','')
                        frst = fmeta.get('reset','')
                        fdesc = fmeta.get('desc','')
                        bullet = f"- {fname} {('['+bits+']') if bits else ''} — Access {facc or '-'}"
                        if frst:
                            bullet += f", Reset {frst}"
                        lines.append(bullet)
                        if fdesc:
                            lines.append(fdesc)
                elif kind == 'field':
                    # Field details in a clean label:value format
                    lines.append(f"Module: {meta.get('module','')}")
                    lines.append(f"Register: {meta.get('register','')}")
                    lines.append(f"Name: {meta.get('field','')}")
                    br = meta.get('bitrange','')
                    if br:
                        lines.append(f"Bits: {br}")
                        try:
                            if ':' in br:
                                msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                                width = abs(msb - lsb) + 1
                            else:
                                msb = lsb = int(br)
                                width = 1
                            lines.append(f"Width: {width} (msb={msb}, lsb={lsb})")
                            if width > 0 and lsb >= 0 and width <= 64:
                                mask = ((1 << width) - 1) << lsb
                                lines.append(f"Mask: 0x{mask:X} ({mask}) shift={lsb}")
                        except Exception:
                            pass
                    addr = meta.get('address','')
                    if addr:
                        try:
                            addr_int = int(addr, 16)
                            lines.append(f"Absolute Address: {addr} ({addr_int})")
                        except Exception:
                            lines.append(f"Absolute Address: {addr}")
                    reset = meta.get('reset','')
                    if reset:
                        lines.append(f"Reset: {reset}")
                    access = meta.get('access','')
                    if access:
                        lines.append(f"Access: {access}")
                    desc = meta.get('desc','')
                    if desc:
                        lines.append("Description:")
                        lines.append(desc)
                    alias = meta.get('alias','')
                    if alias:
                        lines.append(f"Alias: {alias}")
                    full = meta.get('full','')
                    if full:
                        lines.append(f"Full: {full}")
        try:
            details = "\n".join(lines)
            self._set_details_content(details)
            self.details_text.see(tk.END)
        except Exception as e:
            self._set_details_content(f"Render error: {e}")

    # ========= Details Rich Text Rendering =========
    def _set_details_content(self, text: str):
        """Render details text with simple pseudo-markup support.
        Supports:
        - \ttwrap{...} as inline code (tag 'code')
        - \\newline tokens to paragraph breaks
        - Monospace sections heuristics (rows that look like tables)
        """
        self.details_text.configure(state='normal')
        self.details_text.delete(1.0, tk.END)
        if not text:
            self.details_text.configure(state='disabled')
            return
        # Normalize newlines: replace literal "\\newline" with blank line
        text = text.replace('\\newline', '\n\n')
        # Rewrite a wide 'Fields:' ASCII table into a friendlier bullet list with wrapped descriptions
        try:
            text = self._rewrite_fields_section(text)
        except Exception:
            pass
        # Break text into blocks to detect monospace tables (lines of '-' or '|' columns)
        blocks = text.split('\n')
        import re as _re
        monoline = _re.compile(r"^\s*-{3,}|^\s*\|.*\|\s*$")
        in_mono = False
        buf = []
        def flush_buf(tag=None):
            if not buf:
                return
            s = "\n".join(buf).rstrip() + "\n"
            # Try to render label:value lines nicely if not in monospace
            if not tag:
                # Render consecutive label:value lines as paragraphs with bold labels
                for line in s.split('\n'):
                    if not line:
                        self.details_text.insert(tk.END, "\n", ('p',))
                        continue
                    m = _re.match(r"^\s*([A-Za-z][A-Za-z /_-]{0,40}):\s*(.*)$", line)
                    if m and '|' not in line:
                        label = m.group(1)
                        value = m.group(2)
                        # Emphasize Name as a heading
                        if label.lower() == 'name':
                            self.details_text.insert(tk.END, label + ': ', ('h1',))
                        else:
                            self.details_text.insert(tk.END, label + ': ', ('label',))
                        self._insert_with_ttwrap((value or '') + "\n", tag)
                    else:
                        self._insert_with_ttwrap(line + "\n", tag)
            else:
                # Monospace block
                self._insert_with_ttwrap(s, tag)
            buf.clear()
        for line in blocks:
            if monoline.search(line):
                # Start or continue monospace block
                if not in_mono:
                    flush_buf()
                    in_mono = True
                buf.append(line)
            else:
                if in_mono and line.strip() == "":
                    # close mono block on blank line
                    flush_buf('mono')
                    in_mono = False
                buf.append(line)
        # Final flush
        flush_buf('mono' if in_mono else None)
        # Apply global highlight of current search query in details
        try:
            self._apply_details_highlight_safe()
        except Exception:
            pass
        self.details_text.configure(state='disabled')

    def _insert_with_ttwrap(self, s: str, tag: str = None):
        """Insert text s into details_text, converting \ttwrap{...} into tagged 'code'."""
        import re as _re
        # Accept one or two leading backslashes before ttwrap{...}
        pattern = _re.compile(r"\\{1,2}ttwrap\{(.*?)\}")
        last = 0
        for m in pattern.finditer(s):
            plain = s[last:m.start()]
            if plain:
                if tag:
                    self.details_text.insert(tk.END, plain, (tag,))
                else:
                    self.details_text.insert(tk.END, plain)
            code_text = m.group(1)
            # Ensure some backticks-like look via 'code' tag
            self.details_text.insert(tk.END, code_text, (tag, 'code') if tag else ('code',))
            last = m.end()
        tail = s[last:]
        if tail:
            if tag:
                self.details_text.insert(tk.END, tail, (tag,))
            else:
                self.details_text.insert(tk.END, tail)

    def _apply_details_highlight_safe(self):
        try:
            self._apply_details_highlight()
        except Exception:
            pass

    def _apply_details_highlight(self):
        """Highlight the current search query terms inside the details pane.
        Respects Case/Exact/Regex options and 'All terms' vs 'Any term'.
        """
        # Remove any existing highlight if widget not ready
        try:
            self.details_text.tag_remove('matchhl', '1.0', tk.END)
        except Exception:
            return
        try:
            raw_query = (self.search_var.get() or '').strip()
        except Exception:
            raw_query = ''
        if not raw_query:
            return
        try:
            case_sensitive = bool(self.case_var.get())
            exact = bool(self.exact_var.get())
            use_regex = bool(self.regex_var.get())
        except Exception:
            case_sensitive = False
            exact = False
            use_regex = False
        text = self.details_text.get('1.0', tk.END)
        flags = 0 if case_sensitive else re.IGNORECASE

        def add_span(start_idx, end_idx):
            try:
                self.details_text.tag_add('matchhl', start_idx, end_idx)
            except Exception:
                pass

        if use_regex:
            try:
                pattern = re.compile(raw_query, flags)
                for m in pattern.finditer(text):
                    s = f"1.0+{m.start()}c"
                    e = f"1.0+{m.end()}c"
                    add_span(s, e)
                return
            except re.error:
                return

        # Non-regex path
        tokens = [raw_query] if exact else [t for t in re.split(r"\s+", raw_query) if t]
        if not tokens:
            return
        hay = text if case_sensitive else text.lower()
        for tok in tokens:
            needle = tok if case_sensitive else tok.lower()
            start = 0
            while True:
                idx = hay.find(needle, start)
                if idx == -1:
                    break
                s = f"1.0+{idx}c"
                e = f"1.0+{idx+len(needle)}c"
                add_span(s, e)
                start = idx + max(1, len(needle))

    # ========= Details Zoom Controls =========
    def _adjust_details_zoom(self, delta: int):
        """Adjust details font size.
        delta > 0: bigger, delta < 0: smaller, delta == 0: reset.
        """
        try:
            import tkinter.font as tkfont
            if self._details_font is None:
                self._details_font = tkfont.nametofont(self.details_text.cget('font'))
            if delta == 0:
                new_size = self._details_base_size
            else:
                cur = self._details_font.cget('size') or self._details_base_size
                new_size = max(8, min(48, cur + delta))
            self._details_font.configure(size=new_size)
            # Update mono tag to follow roughly
            self.details_text.tag_configure('mono', font=('Courier New', new_size))
        except Exception:
            pass

    def _on_details_mousewheel(self, event):
        try:
            if event.delta > 0:
                self._adjust_details_zoom(+1)
            else:
                self._adjust_details_zoom(-1)
            return 'break'
        except Exception:
            return None

    # ========= Details Toolbar Actions =========
    def _copy_details_to_clipboard(self):
        try:
            txt = self.details_text.get('1.0', tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
        except Exception:
            pass

    def _save_details_markdown(self):
        try:
            from tkinter import filedialog as _fd
            path = _fd.asksaveasfilename(defaultextension='.md', filetypes=[('Markdown','*.md'), ('Text','*.txt')], title='Save Details as Markdown')
            if not path:
                return
            txt = self.details_text.get('1.0', tk.END)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(txt)
        except Exception:
            pass

    def _toggle_collapse(self):
        try:
            self.details_collapse_long = bool(self._collapse_var.get())
            # Re-generate details for current selection instead of reusing formatted text
            self._on_tree_select()
        except Exception:
            pass

    def _maybe_collapse(self, text: str, raw: bool = False, limit: int = 1200) -> str:
        """Return text truncated when collapse toggle is on; respects raw blocks like XML."""
        if not isinstance(text, str):
            return text
        if not self.details_collapse_long:
            return text
        if len(text) <= limit:
            return text
        suffix = "\n... (collapsed)"
        return text[:limit] + suffix
    
    def load_xml(self, file_path):
        self.debug_print(f"Loading file: {file_path}")
        try:
            # Track current source path and associated notes path
            self.current_regmap_path = file_path
            base = os.path.splitext(os.path.basename(file_path))[0]
            folder = os.path.dirname(file_path)
            self.notes_path = os.path.join(folder, f"{base}_reg_notes.md")
            # Initialize variables
            self.ns = {}
            self.used_prefixes = set()
            self.ns.update(self.common_namespaces)
            # Clear existing data
            self.tree.delete(*self.tree.get_children())
            self.registers = []
            self.details_text.delete(1.0, tk.END)
            self.used_prefixes = set()
            
            # First, read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.debug_print(f"Read {len(content)} bytes from file")
                
            # Check for HTML entities and unescape them
            if '&lt;' in content or '&gt;' in content or '&amp;' in content:
                content = html.unescape(content)
            
            # Fix common XML issues
            if '&' in content and '&amp;' not in content:
                content = content.replace('&', '&amp;')
                
            # Try to parse the content
            try:
                root = ET.fromstring(content)
                
                # Extract all namespaces from the document
                self.ns = {}
                self.used_prefixes = set()
                
                # Add common namespaces
                self.ns.update(self.common_namespaces)
                self.debug_print(f"Common namespaces: {self.common_namespaces}")
                self.debug_print(f"Root tag: {root.tag}")
                
                # Extract namespaces from the root element
                for attr, value in root.attrib.items():
                    if attr == 'xmlns':
                        self.ns[''] = value  # Default namespace
                        self.used_prefixes.add('')
                    elif attr.startswith('xmlns:'):
                        prefix = attr[6:]
                        self.ns[prefix] = value
                        self.used_prefixes.add(prefix)
                
                # Also try to get namespace from the root tag
                if '}' in root.tag:
                    ns = root.tag.split('}')[0].strip('{')
                    if ns and ns not in self.ns.values():
                        self.ns['default_ns'] = ns
                        self.used_prefixes.add('default_ns')
                
                # Try different XPath patterns to find memory maps
                memory_maps = []
                
                # Common XPath patterns for memory maps
                xpath_patterns = [
                    './/memoryMap',  # No namespace
                    './/ipxact:memoryMap',  # ipxact namespace
                    './/spirit:memoryMap',  # spirit namespace
                    './/*[local-name()="memoryMap"]',  # Any namespace
                    '//memoryMap',  # Anywhere in document
                    '//ipxact:memoryMap',
                    '//spirit:memoryMap',
                    '//*[local-name()="memoryMap"]',
                    # Add more patterns based on common variations
                    './/*[contains(local-name(), "MemoryMap")]',
                    './/*[contains(translate(local-name(), "MAP", "map"), "memorymap")]',
                    './/*[contains(translate(local-name(), "MEMORYMAP", "memorymap"), "memorymap")]'
                ]
                
                self.debug_print(f"Trying {len(xpath_patterns)} XPath patterns to find memory maps")
                
                for pattern in xpath_patterns:
                    try:
                        memory_maps = root.findall(pattern, self.ns)
                        if memory_maps:
                            break
                    except (KeyError, SyntaxError):
                        continue
                
                # If still no memory maps, try a very permissive search
                if not memory_maps:
                    for elem in root.iter():
                        if 'memoryMap' in elem.tag or 'MemoryMap' in elem.tag:
                            memory_maps = [elem]
                            break
                
                # If we still don't have memory maps, show the root children for debugging
                if not memory_maps:
                    error_msg = "Could not find memory maps. Root children:\n"
                    # Show first 10 children for debugging
                    children = list(root)[:10]
                    for i, child in enumerate(children):
                        error_msg += f"  {i}: {child.tag}\n"
                        # Show attributes of the child if any
                        if child.attrib:
                            error_msg += f"      Attributes: {child.attrib}\n"
                    self.debug_print(error_msg)
                    
                    # Also show all unique tag names in the document
                    all_tags = set()
                    for elem in root.iter():
                        all_tags.add(elem.tag)
                        if len(all_tags) > 50:  # Limit to first 50 unique tags
                            break
                    
                    self.debug_print("\nFirst 50 unique tags in document:")
                    for i, tag in enumerate(sorted(all_tags)):
                        self.debug_print(f"  {i}: {tag}")
                    
                    # Show namespace information
                    self.debug_print("\nDetected namespaces:")
                    for prefix, uri in self.ns.items():
                        self.debug_print(f"  {prefix}: {uri}")
                
                if not memory_maps:
                    # Fallback: try to parse vendor 'Addressmap' format (non-IP-XACT)
                    def _local(t: str) -> str:
                        return t.split('}', 1)[-1] if '}' in t else t
                    root_local = _local(root.tag)
                    if root_local.lower() == 'addressmap':
                        self.debug_print("No IP-XACT memoryMap found; attempting Addressmap fallback parse")
                        if self._try_load_addressmap(root):
                            # Successfully parsed Addressmap; stop normal IP-XACT flow
                            return
                    # Try direct memory map search as a fallback
                    memory_maps = root.findall('.//memoryMap')
                    if not memory_maps:
                        # Try one more time with a very permissive search
                        for elem in root.iter():
                            if 'memoryMap' in elem.tag:
                                memory_maps = [elem]
                                break
                                
                        if not memory_maps:
                            # Dump the first few lines for debugging
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    first_lines = [next(f) for _ in range(5)]
                                sample = ''.join(first_lines)
                                messagebox.showerror(
                                    "Error", 
                                    "No memory maps found in the IP-XACT file.\n\n"
                                    "First few lines of the file:\n" + sample
                                )
                            except:
                                messagebox.showerror("Error", "No memory maps found in the IP-XACT file")
                            return
                    
                # Process each memory map
                for mem_map in memory_maps:
                    try:
                        map_name = self.find_element(mem_map, 'name', 'Unnamed Memory Map')
                        self.debug_print(f"Found memory map: {map_name}")
                        
                        # Create the memory map node
                        map_node = self.tree.insert('', 'end', text=map_name, open=True, tags=('memory_map',))
                        if not map_node:
                            self.debug_print("Failed to create memory map node")
                            continue
                            
                        # Process address blocks
                        addr_blocks = []
                        for prefix in self.used_prefixes.union(self.ns.keys()):
                            try:
                                addr_blocks = mem_map.findall(f'.//{prefix}:addressBlock', self.ns) if prefix else mem_map.findall('.//addressBlock')
                                if addr_blocks:
                                    self.used_prefixes.add(prefix)
                                    self.debug_print(f"Found {len(addr_blocks)} address blocks with prefix: {prefix}")
                                    break
                            except (KeyError, SyntaxError) as e:
                                self.debug_print(f"Error searching for address blocks with prefix {prefix}: {e}")
                                continue
                        
                        # Process each address block
                        for block in addr_blocks:
                            try:
                                block_name = self.find_element(block, 'name', 'Unnamed Block')
                                block_offset = self.find_element(block, 'baseAddress', '0x0')
                                block_range = self.find_element(block, 'range', '0')
                                block_width = self.find_element(block, 'width', '32')
                                
                                self.debug_print(f"  Found address block: {block_name} at {block_offset}")
                                
                                # Parse the offset value
                                offset_value = self.parse_number(block_offset, 0)
                                
                                # Create the address block node
                                try:
                                    block_node = self.tree.insert(
                                        map_node, 'end', 
                                        text=block_name,
                                        values=(
                                            f"0x{offset_value:X}", 
                                            block_range, 
                                            block_width
                                        ),
                                        tags=('address_block',)
                                    )
                                    
                                    # Only process registers if node creation was successful
                                    if block_node:
                                        # Process registers within the address block
                                        registers = []
                                        for prefix in self.used_prefixes.union(self.ns.keys()):
                                            try:
                                                xpath = f'.//{prefix}:register' if prefix else './/register'
                                                registers = block.findall(xpath, self.ns)
                                                if registers:
                                                    self.used_prefixes.add(prefix)
                                                    self.debug_print(f"    Found {len(registers)} registers with prefix: {prefix}")
                                                    break
                                            except (KeyError, SyntaxError) as e:
                                                self.debug_print(f"    Error searching for registers with prefix {prefix}: {e}")
                                                continue
                                        
                                        # Process each register
                                        for reg in registers:
                                            try:
                                                self.process_register(reg, block_node, block_offset, block_name, map_name)
                                            except Exception as e:
                                                self.debug_print(f"      Error processing register: {e}")
                                                continue
                                        
                                except Exception as e:
                                    self.debug_print(f"      Error creating address block node: {e}")
                                    continue
                                    
                            except Exception as e:
                                self.debug_print(f"Error processing address block: {e}")
                                continue
                                
                    except Exception as e:
                        self.debug_print(f"Error processing memory map: {e}")
                        continue
                        
            except ET.ParseError as e:
                # Try to extract the first line for better error reporting
                first_line = content.split('\n', 1)[0] if '\n' in content else content
                if not first_line.strip():
                    raise ValueError("The file appears to be empty")
                if not first_line.lstrip().startswith('<'):
                    raise ValueError("File does not contain valid XML (doesn't start with '<')")
                raise
                
        except ET.ParseError as e:
            messagebox.showerror("XML Error", f"Failed to parse XML file: {str(e)}")
            return
        # except Exception as e:
        #     messagebox.showerror("Error", f"An error occurred: {str(e)}")
        #     return
        return
            
        # Reset namespaces after error handling
        self.ns = {}
        self.used_prefixes = set()
        self.ns.update(self.common_namespaces)
        self.debug_print("Reset namespaces")
        
        # Check if we have memory maps to process
        if not memory_maps:
            # Dump the first few lines for debugging
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_lines = [next(f) for _ in range(5)]
                sample = ''.join(first_lines)
                messagebox.showerror(
                    "Error", 
                    "No memory maps found in the IP-XACT file.\n\n"
                    "First few lines of the file:\n" + sample
                )
            except:
                messagebox.showerror("Error", "No memory maps found in the IP-XACT file")
            return
        
        # Process each memory map
        for mem_map in memory_maps:
            try:
                map_name = self.find_element(mem_map, 'name', 'Unnamed Memory Map')
                self.debug_print(f"Found memory map: {map_name}")
                
                # Create the memory map node
                map_node = self.tree.insert('', 'end', text=map_name, open=True, tags=('memory_map',))
                if not map_node:
                    self.debug_print("Failed to create memory map node")
                    continue
                
                # Process address blocks
                addr_blocks = []
                for prefix in self.used_prefixes.union(self.ns.keys()):
                    try:
                        addr_blocks = mem_map.findall(f'.//{prefix}:addressBlock', self.ns) if prefix else mem_map.findall('.//addressBlock')
                        if addr_blocks:
                            self.used_prefixes.add(prefix)
                            self.debug_print(f"Found {len(addr_blocks)} address blocks with prefix: {prefix}")
                            break
                    except (KeyError, SyntaxError) as e:
                        self.debug_print(f"Error searching for address blocks with prefix {prefix}: {e}")
                        continue
                
                # Process each address block
                for block in addr_blocks:
                    try:
                        block_name = self.find_element(block, 'name', 'Unnamed Block')
                        block_offset = self.find_element(block, 'baseAddress', '0x0')
                        block_range = self.find_element(block, 'range', '0')
                        block_width = self.find_element(block, 'width', '32')
                        
                        self.debug_print(f"  Found address block: {block_name} at {block_offset}")
                        
                        # Parse the offset value
                        offset_value = self.parse_number(block_offset, 0)
                        
                        # Create the address block node
                        try:
                            block_node = self.tree.insert(
                                map_node, 'end', 
                                text=block_name,
                                values=(
                                    f"0x{offset_value:X}", 
                                    block_range, 
                                    block_width
                                ),
                                tags=('address_block',)
                            )
                            
                            # Only process registers if node creation was successful
                            if block_node:
                                # Process registers within the address block
                                registers = []
                                for prefix in self.used_prefixes.union(self.ns.keys()):
                                    try:
                                        xpath = f'.//{prefix}:register' if prefix else './/register'
                                        registers = block.findall(xpath, self.ns)
                                        if registers:
                                            self.used_prefixes.add(prefix)
                                            self.debug_print(f"    Found {len(registers)} registers with prefix: {prefix}")
                                            break
                                    except (KeyError, SyntaxError) as e:
                                        self.debug_print(f"    Error searching for registers with prefix {prefix}: {e}")
                                        continue
                                
                                # Process each register
                                for reg in registers:
                                    try:
                                        self.process_register(reg, block_node, block_offset)
                                    except Exception as e:
                                        self.debug_print(f"      Error processing register: {e}")
                                        continue
                                    
                        except Exception as e:
                            self.debug_print(f"      Error creating address block node: {e}")
                            continue
                                
                    except Exception as e:
                        self.debug_print(f"Error processing address block: {e}")
                        continue
                                
            except Exception as e:
                self.debug_print(f"Error processing memory map: {e}")
                continue
                            
        # except ET.ParseError as e:
        #     messagebox.showerror("XML Error", f"Failed to parse XML file: {str(e)}")
        # except Exception as e:
        #     messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
    def process_register(self, reg_element, parent_node, block_offset, block_name=None, map_name=None):
        """Process a single register element and add it to the tree"""
        # Initialize register data with defaults
        register_data = {
            'name': 'Unnamed Register',
            'offset': '0x0',
            'size': '32',
            'access': 'read-write',
            'absolute_address': '0x0',
            'fields': [],
            'block': block_name or '',
            'map': map_name or ''
        }
        reg_node = None
        fields = []
        field_data = None
        
        try:
            # Extract register properties
            reg_name = self.find_element(reg_element, 'name', 'Unnamed Register')
            # Fallback to displayName when name is missing/empty/placeholder
            if not reg_name or reg_name.strip() == '' or reg_name == 'Unnamed Register':
                dn = self.find_element(reg_element, 'displayName', '').strip()
                if dn:
                    reg_name = dn
            reg_offset = self.find_element(reg_element, 'addressOffset', '0x0')
            reg_size = self.find_element(reg_element, 'size', '32')
            access_type = self.find_element(reg_element, 'access', 'read-write')
            description = self.find_element(reg_element, 'description', '')
            
            # Calculate absolute address
            block_addr = self.parse_number(block_offset, 0)
            reg_addr = self.parse_number(reg_offset, 0)
            abs_offset = f"0x{block_addr + reg_addr:X}"
            
            # Update register data
            register_data.update({
                'name': reg_name,
                'offset': reg_offset,
                'size': reg_size,
                'access': access_type,
                'absolute_address': abs_offset,
                'description': description,
                'block': block_name or '',
                'map': map_name or ''
            })
            
            # Add register to tree if parent is valid
            if parent_node:
                reg_node = self.tree.insert(
                    parent_node, 'end',
                    text=reg_name,
                    values=(f"0x{reg_addr:X}", reg_size, access_type),
                    tags=('register',)
                )
            
            # Find fields (namespace-agnostic, no XPath predicates)
            def _local(t: str) -> str:
                return t.split('}', 1)[-1] if '}' in t else t
            fields = [ch for ch in list(reg_element) if _local(ch.tag) == 'field']
            if not fields:
                # Fallback to any descendant fields
                fields = [el for el in reg_element.iter() if el is not reg_element and _local(el.tag) == 'field']
            
            for field in fields:
                try:
                    field_data = {
                        'name': self.find_element(field, 'name', 'Unnamed Field'),
                        'bit_offset': self.find_element(field, 'bitOffset', '0'),
                        'bit_width': self.find_element(field, 'bitWidth', '1'),
                        'access': self.find_element(field, 'access', access_type),
                        'reset_value': self.find_element(field, 'resetValue/value', '0x0'),
                        'description': self.find_element(field, 'description', '')
                    }
                    register_data['fields'].append(field_data)
                except Exception as e:
                    self.debug_print(f"      Error processing field data: {e}")
                    continue
            
            # Add register data to the registers list
            self.registers.append(register_data)
            
            # Process fields for the tree view if we have a valid node
            if reg_node and fields:
                for field in fields:
                    try:
                        self.process_field(field, reg_node)
                    except Exception as e:
                        self.debug_print(f"      Error adding field to tree: {e}")
            
            # Bind click event to show details
            self.tree.bind('<<TreeviewSelect>>', self.show_register_details)
            
        except Exception as e:
            self.debug_print(f"      Error processing register: {e}")
            raise
    
    def process_field(self, field_element, parent_node):
        """Process a single field element and add it to the tree"""
        try:
            self.debug_print(f"        Processing field element: {field_element}")
            
            field_name = self.find_element(field_element, 'name', 'Unnamed Field')
            self.debug_print(f"        Field name: {field_name}")
            
            bit_offset = self.find_element(field_element, 'bitOffset', '0')
            self.debug_print(f"        Bit offset: {bit_offset}")
            
            bit_width = self.find_element(field_element, 'bitWidth', '1')
            self.debug_print(f"        Bit width: {bit_width}")
            
            # Get access type and description
            access_type = self.find_element(field_element, 'access', 'read-write')
            description = self.find_element(field_element, 'description', '')
            
            # Get reset value if available (namespace-agnostic, no XPath predicates)
            def _local(t: str) -> str:
                return t.split('}', 1)[-1] if '}' in t else t
            reset_value = '0'
            try:
                val_text = None
                for el in field_element.iter():
                    if el is field_element:
                        continue
                    if _local(el.tag) == 'value' and el.text is not None:
                        val_text = el.text.strip()
                        break
                if val_text is not None:
                    rv = val_text.strip().strip("'").lower()
                    if rv.startswith('h'):
                        rv = rv[1:]
                    reset_value = rv if rv else '0'
            except Exception as e:
                self.debug_print(f"        Error getting reset value: {e}")
                reset_value = '0'
                
            self.debug_print(f"        Reset value: {reset_value}")
            
            # Ensure parent_node is valid
            if not parent_node:
                self.debug_print("        Error: Invalid parent node for field")
                return
                
            # Add to tree
            try:
                field_text = f"{field_name} [{int(bit_offset)+int(bit_width)-1}:{bit_offset}]"
                # Format the reset value for display
                try:
                    # If reset_value looks like hex (contains a-f or digits), parse as hex
                    reset_int = int(reset_value, 16)
                    reset_bin = f"{reset_int:0{int(bit_width)}b}"
                    reset_display = f"{bit_width}'b{reset_bin}"
                except Exception:
                    # Fallback to raw value (assumed already binary-digit string)
                    reset_display = f"{bit_width}'b{reset_value}" if reset_value else f"{bit_width}'b0"
                field_values = (reset_display, access_type, '')
                
                self.debug_print(f"        Adding field: {field_text} with values: {field_values}")
                
                field_id = self.tree.insert(
                    parent_node, 'end',
                    text=field_text,
                    values=field_values,
                    tags=('field',)
                )
                self.debug_print(f"        Added field with ID: {field_id}")
                
            except Exception as e:
                self.debug_print(f"        Failed to add field {field_name} to tree: {e}")
                import traceback
                self.debug_print("        " + "\n        ".join(traceback.format_exc().splitlines()))
            
        except AttributeError as e:
            print(f"Warning: Missing required field in field definition: {e}")
    
    def show_register_details(self, event=None):
        """Display detailed information about the selected register
        
        Args:
            event: Optional event parameter for Tkinter event binding
        """
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        if 'register' in item['tags']:
            reg_info = next((r for r in self.registers if r['name'] == item['text']), None)
            if reg_info:
                details = f"Name: {reg_info['name']}\n"
                details += f"Absolute Address: {reg_info['absolute_address']}\n"
                # Use parse_number to support 'h.. and 0x.. formats
                details += f"Offset: 0x{self.parse_number(reg_info['offset'], 0):X}\n"
                details += f"Size: {reg_info['size']} bits\n"
                details += f"Access: {reg_info['access'].upper()}\n\n"
                details += f"Description:\n{reg_info['description']}\n\n"
                
                # Include block-level description if present (Addressmap fallback)
                blk_desc = reg_info.get('block_description', '').strip()
                if blk_desc:
                    details += f"Block Notes:\n{blk_desc}\n\n"
                if reg_info['fields']:
                    details += "Fields:\n"
                    details += "-" * 80 + "\n"
                    details += "Name                 | Bits      | Access   | Reset    | Description\n"
                    details += "-" * 80 + "\n"
                    
                    for field in reg_info['fields']:
                        try:
                            bo = self.parse_number(field.get('bit_offset','0'), 0)
                            bw = self.parse_number(field.get('bit_width','1'), 1)
                            hi = bo + bw - 1
                            bits = f"[{hi}:{bo}]"
                        except Exception:
                            bits = f"[{field.get('bit_offset','0')}]"
                        details += f"{field['name']:<20} | {bits:<9} | {field['access'].upper():<8} | {field['reset_value']:<8} | {field['description']}\n"
                
                self.details_text.delete(1.0, tk.END)
                self.details_text.insert(tk.END, details)
                # Highlight current search terms inside details
                try:
                    self._apply_details_highlight()
                except Exception:
                    pass
                # Load associated note into the note editor
                try:
                    self._last_reg_info = reg_info
                    self._load_note_into_widget(reg_info)
                except Exception:
                    pass

    # ===== Advanced Search & Filter =====
    def perform_search(self):
        """Filter registers by query and scope, and rebuild the tree to show only matched branches."""
        raw_query = (self.search_var.get() or '').strip()
        case_sensitive = bool(self.case_var.get())
        exact = bool(self.exact_var.get())
        use_regex = bool(self.regex_var.get())
        query = raw_query if case_sensitive else raw_query.lower()
        scope = (self.search_scope.get() or 'any').lower()
        if not query:
            self.clear_search()
            return
        matched = []

        # Helpers
        def text_prepare(s: str) -> str:
            s = '' if s is None else str(s)
            return s if case_sensitive else s.lower()

        def text_match(hay: str, needle_raw: str) -> bool:
            h = text_prepare(hay)
            n = text_prepare(needle_raw)
            if use_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    return re.search(needle_raw, hay or '', flags) is not None
                except re.error:
                    return False
            if exact:
                return h == n
            return n in h

        # Numeric query parse with operators: =,==,!=,>,<,>=,<= and hex/dec
        def parse_numeric_query(qs: str):
            m = re.match(r"^(<=|>=|==|!=|=|<|>)?\s*(.+)$", qs.strip())
            if not m:
                return None, None
            op = m.group(1) or '=='
            val_s = m.group(2).strip().strip("'")
            try:
                if val_s.lower().startswith('h'):
                    val = int(val_s[1:], 16)
                elif val_s.lower().startswith('0x'):
                    val = int(val_s, 16)
                else:
                    val = int(val_s, 10)
                return op, val
            except Exception:
                return None, None

        def numeric_compare(value, op, qv) -> bool:
            try:
                v = int(value)
            except Exception:
                return False
            if op in ('==', '='):
                return v == qv
            if op == '!=':
                return v != qv
            if op == '>':
                return v > qv
            if op == '<':
                return v < qv
            if op == '>=':
                return v >= qv
            if op == '<=':
                return v <= qv
            return False

        def split_tokens_preserving_quotes(s: str):
            """Split a string into tokens by whitespace but preserve quoted phrases.
            Supports double-quotes "..." and single-quotes '...'. Surrounding quotes are stripped.
            Example: 'description:"link up" name:foo' -> ['description:"link up"', 'name:foo']
            We keep qualifiers attached to the quoted value by not splitting inside quotes.
            """
            tokens = []
            # Pattern matches either a qualifier:value where value may be quoted, or bare quoted/bare tokens
            # 1) qualifier with quoted value: key:"val with spaces" or key:'val with spaces'
            # 2) quoted token: "val with spaces" or 'val with spaces'
            # 3) bare token: \S+
            pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*):\s*(\"[^\"]*\"|'[^']*'|\S+)\b|\"([^\"]*)\"|'([^']*)'|(\S+)")
            for m in pattern.finditer(s):
                if m.group(1) is not None:
                    key = m.group(1)
                    val = m.group(2)
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    tokens.append(f"{key}:{val}")
                else:
                    val = m.group(3) or m.group(4) or m.group(5)
                    tokens.append(val)
            return tokens

        def reg_matches_leaf(reg, leaf_query: str) -> bool:
            # Evaluate a single leaf query against the chosen scope using provided options
            leaf_raw = leaf_query
            # Support exclusion with leading '!'
            negate = False
            if leaf_raw.startswith('!'):
                negate = True
                leaf_raw = leaf_raw[1:].strip()
            # Field-qualified prefixes override scope for this token
            eff_scope = None
            m = re.match(r"^(name|description|map|block|access|size|field|field_access|field_bits|field_width|field_offset|value|reset|address|offset)\s*:\s*(.*)$", leaf_raw, flags=re.IGNORECASE)
            if m:
                eff_scope = m.group(1).lower()
                leaf_raw = m.group(2).strip()
                # Allow negation inside the qualifier value too: e.g., name:!foo
                if leaf_raw.startswith('!'):
                    negate = not negate
                    leaf_raw = leaf_raw[1:].strip()
            local_query = leaf_raw if case_sensitive else leaf_raw.lower()
            # Text sources
            name = reg.get('name', '')
            desc = reg.get('description', '')
            blk = reg.get('block', '')
            mp = reg.get('map', '')
            fields = reg.get('fields', [])
            addr = reg.get('absolute_address', '')
            off = reg.get('offset', '')
            acc = str(reg.get('access', '')).lower()
            size_str = str(reg.get('size', '')).strip()

            # Numeric parsing for address/offset equality convenience
            q_int = None
            try:
                q_raw = leaf_raw.strip().strip("'")
                if q_raw.lower().startswith('h'):
                    q_int = int(q_raw[1:], 16)
                elif q_raw.lower().startswith('0x'):
                    q_int = int(q_raw, 16)
                else:
                    q_int = int(q_raw, 10)
            except Exception:
                q_int = None
            q_op, q_val = parse_numeric_query(leaf_raw)
            try:
                addr_int = self.parse_number(addr, None)
            except Exception:
                addr_int = None
            try:
                off_int = self.parse_number(off, None)
            except Exception:
                off_int = None

            # Matching by scope (use eff_scope if provided)
            sc = eff_scope or scope
            if sc == 'name':
                res = text_match(name, local_query)
                return (not res) if negate else res
            if sc == 'description':
                res = text_match(desc, local_query)
                return (not res) if negate else res
            if sc == 'map':
                res = text_match(mp, local_query)
                return (not res) if negate else res
            if sc == 'block':
                res = text_match(blk, local_query)
                return (not res) if negate else res
            if sc == 'access':
                res = text_match(acc, local_query)
                return (not res) if negate else res
            if sc == 'size':
                if text_match(size_str, local_query):
                    return True if not negate else False
                if q_op is not None and q_val is not None:
                    return numeric_compare(size_str, q_op, q_val)
                return False
            if sc == 'field':
                res = any(text_match(f.get('name','') + ' ' + f.get('description',''), local_query) for f in fields)
                return (not res) if negate else res
            if sc == 'field_access':
                res = any(text_match(str(f.get('access','')), local_query) for f in fields)
                return (not res) if negate else res
            if sc == 'field_bits':
                for f in fields:
                    try:
                        hi = int(f.get('bit_offset','0'))+int(f.get('bit_width','1'))-1
                        lo = int(f.get('bit_offset','0'))
                        bits = f"[{hi}:{lo}]"
                    except Exception:
                        bits = f"[{f.get('bit_offset','0')}:{f.get('bit_offset','0')}]"
                    if text_match(bits, local_query):
                        return False if negate else True
                return True if negate else False
            if sc == 'field_width':
                for f in fields:
                    bw = str(f.get('bit_width',''))
                    if text_match(bw, local_query):
                        return False if negate else True
                    if q_op is not None and q_val is not None and numeric_compare(bw, q_op, q_val):
                        return False if negate else True
                return True if negate else False
            if sc == 'field_offset':
                for f in fields:
                    bo = str(f.get('bit_offset',''))
                    if text_match(bo, local_query):
                        return False if negate else True
                    if q_op is not None and q_val is not None and numeric_compare(bo, q_op, q_val):
                        return False if negate else True
                return True if negate else False
            if sc in ('value','reset'):
                res = any(text_match(str(f.get('reset_value','')), local_query) for f in fields)
                return (not res) if negate else res
            if sc == 'address':
                if text_match(str(addr), local_query):
                    return False if negate else True
                if q_op is not None and q_val is not None and addr_int is not None:
                    return numeric_compare(addr_int, q_op, q_val)
                return (q_int is not None and addr_int is not None and q_int == addr_int)
            if sc == 'offset':
                if text_match(str(off), local_query):
                    return False if negate else True
                if q_op is not None and q_val is not None and off_int is not None:
                    return numeric_compare(off_int, q_op, q_val)
                return (q_int is not None and off_int is not None and q_int == off_int)
            # any
            base_match = (
                text_match(name, local_query) or text_match(desc, local_query) or text_match(blk, local_query) or text_match(mp, local_query)
                or text_match(acc, local_query) or text_match(size_str, local_query)
                or text_match(str(addr), local_query) or text_match(str(off), local_query)
            )
            if base_match:
                return False if negate else True
            for f in fields:
                if text_match(f.get('name','') + ' ' + f.get('description',''), local_query):
                    return False if negate else True
                if text_match(str(f.get('reset_value','')), local_query):
                    return False if negate else True
                if text_match(str(f.get('access','')), local_query):
                    return False if negate else True
                try:
                    hi = int(f.get('bit_offset','0'))+int(f.get('bit_width','1'))-1
                    lo = int(f.get('bit_offset','0'))
                    bits = f"[{hi}:{lo}]"
                except Exception:
                    bits = f"[{f.get('bit_offset','0')}:{f.get('bit_offset','0')}]"
                if text_match(bits, local_query) or text_match(str(f.get('bit_width','')), local_query) or text_match(str(f.get('bit_offset','')), local_query):
                    return False if negate else True
            return True if negate else False
            

        def reg_matches(reg) -> bool:
            # Support boolean combinations:
            # - OR groups with 'or' or '||'
            # - AND within each group with 'and' or '&&'
            # - Additionally, whitespace-separated tokens behave per toggle:
            #   All terms (AND) when self.and_terms_var is True; Any term (OR) when False
            expr = raw_query
            parts_or = re.split(r"\s*(?:\|\||\bor\b)\s*", expr, flags=re.IGNORECASE)
            for or_part in parts_or:
                and_chunks = re.split(r"\s*(?:\&\&|\band\b)\s*", or_part, flags=re.IGNORECASE)
                if not and_chunks:
                    continue
                chunk_results = []
                for ch in and_chunks:
                    ch = ch.strip()
                    if not ch:
                        chunk_results.append(True)
                        continue
                    if use_regex or exact:
                        chunk_results.append(reg_matches_leaf(reg, ch))
                    else:
                        tokens = [t for t in split_tokens_preserving_quotes(ch) if t]
                        if not tokens:
                            chunk_results.append(True)
                        else:
                            if bool(self.and_terms_var.get()):
                                chunk_results.append(all(reg_matches_leaf(reg, t) for t in tokens))
                            else:
                                chunk_results.append(any(reg_matches_leaf(reg, t) for t in tokens))
                # If all AND chunks are true, the OR group passes
                if all(chunk_results):
                    return True
            # No OR group matched
            return False

        # Optionally filter fields to only matching ones when scope is field/value/any
        # Preserve tree state
        state = self._capture_tree_state()
        for reg in self.registers:
            if reg_matches(reg):
                reg_copy = dict(reg)
                # Narrow fields for display when appropriate
                if scope in ('field', 'value', 'reset', 'field_access', 'field_bits', 'field_width', 'field_offset', 'any') and query:
                    nar = []
                    for f in reg.get('fields', []):
                        ftext = f.get('name','') + ' ' + f.get('description','')
                        if scope == 'field' and text_match(ftext, query):
                            nar.append(f)
                        elif scope in ('value','reset') and text_match(str(f.get('reset_value','')), query):
                            nar.append(f)
                        elif scope == 'field_access' and text_match(str(f.get('access','')), query):
                            nar.append(f)
                        elif scope == 'field_bits':
                            try:
                                hi = int(f.get('bit_offset','0'))+int(f.get('bit_width','1'))-1
                                lo = int(f.get('bit_offset','0'))
                                bits = f"[{hi}:{lo}]"
                            except Exception:
                                bits = f"[{f.get('bit_offset','0')}:{f.get('bit_offset','0')}]"
                            if text_match(bits, query):
                                nar.append(f)
                        elif scope == 'field_width' and text_match(str(f.get('bit_width','')), query):
                            nar.append(f)
                        elif scope == 'field_offset' and text_match(str(f.get('bit_offset','')), query):
                            nar.append(f)
                        elif scope == 'any' and (text_match(ftext, query) or text_match(str(f.get('reset_value','')), query) or text_match(str(f.get('access','')), query)):
                            nar.append(f)
                    # Keep at least some fields to avoid empty register children; if none, keep original
                    if nar:
                        reg_copy['fields'] = nar
                matched.append(reg_copy)

        # If zero matches, keep current tree and show status, do NOT clear it
        if not matched:
            try:
                self._status("No matches")
            except Exception:
                pass
            return

        # If we have an SNPS snapshot, keep the SNPS layout when showing matches
        if hasattr(self, '_snps_modules') and isinstance(self._snps_modules, dict) and self._snps_modules:
            filtered = {}
            for reg in (matched or []):
                try:
                    module_name = reg.get('block','') or 'ROOT'
                    reg_name = reg.get('name','')
                    # Pull original field list from SNPS snapshot if present, else synthesize from reg.fields
                    mod_regs = self._snps_modules.get(module_name, {}) if isinstance(self._snps_modules, dict) else {}
                    info = mod_regs.get(reg_name) if isinstance(mod_regs, dict) else None
                    if isinstance(info, dict) and 'fields' in info:
                        fields_list = info.get('fields', [])
                        address = info.get('address','')
                        reg_bits = info.get('reg_width_bits','')
                        reg_bytes = info.get('reg_size_bytes','')
                        end_hex = info.get('addr_end_hex','')
                    else:
                        fields_list = []
                        for f in reg.get('fields', []):
                            try:
                                hi = int(f.get('bit_offset','0')) + int(f.get('bit_width','1')) - 1
                                lo = int(f.get('bit_offset','0'))
                                br = f"{hi}:{lo}"
                            except Exception:
                                br = str(f.get('bit_offset','0'))
                            fields_list.append({
                                'field': f.get('name',''),
                                'bitrange': br,
                                'address': reg.get('absolute_address',''),
                                'reset': f.get('reset_value',''),
                                'access': f.get('access',''),
                                'desc': f.get('description',''),
                                'alias': '',
                                'full': ''
                            })
                        address = reg.get('absolute_address','')
                        reg_bits = reg.get('size','')
                        reg_bytes = ''
                        end_hex = ''
                    m = filtered.setdefault(module_name, {})
                    m[reg_name] = {
                        'address': address,
                        'reg_width_bits': reg_bits,
                        'reg_size_bytes': reg_bytes,
                        'addr_end_hex': end_hex,
                        'fields': fields_list
                    }
                except Exception:
                    continue
            self._rebuild_snps_tree(filtered)
            # Select first match for convenience
            self._status(f"Filtered (SNPS) modules={len(filtered)} regs={sum(len(x) for x in filtered.values())}")
            return

        # Otherwise, fallback to legacy/IP-XACT map/block rebuild
        self.matched_registers = matched
        self._rebuild_tree_from_registers(self.matched_registers)
        self._restore_tree_state(state)
        # Auto-open/select first matched register
        self._focus_first_match(self.matched_registers)

    # ===== Notes (Markdown) persistence =====
    def _note_key(self, reg: dict) -> str:
        """Build a stable key for notes. If block/module is missing (e.g., SNPS tree),
        infer the module name from the current selection's ancestor labeled 'Module <name>'."""
        map_name = (reg.get('map') or '').strip()
        block_name = self._normalize_module_name((reg.get('block') or '').strip())
        reg_name = (reg.get('name') or '').strip()
        if not block_name:
            # Try to infer module name from the last selected item ancestors
            try:
                item_id = getattr(self, '_last_selected_item', None)
                pid = item_id
                while pid:
                    txt = self.tree.item(pid, 'text')
                    if isinstance(txt, str) and txt.startswith('Module '):
                        block_name = self._normalize_module_name(txt.split(' ', 1)[1])
                        break
                    pid = self.tree.parent(pid)
            except Exception:
                pass
        return f"{(map_name or '(no map)')} / {(block_name or '(no block)')} / {reg_name}"

    def _ensure_notes_file(self, path: str | None = None):
        """Ensure the directory for the notes file exists; if a path is passed and file
        doesn't exist, create an empty file. Returns the file path used if created.
        """
        try:
            if not getattr(self, 'notes_dir', None):
                return None
            os.makedirs(self.notes_dir, exist_ok=True)
            if path:
                folder = os.path.dirname(path)
                os.makedirs(folder, exist_ok=True)
                if not os.path.exists(path):
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write("# Notes\n\n")
                return os.path.abspath(path)
            # Legacy fallback: ensure aggregate exists
            if not getattr(self, 'notes_path', None):
                self.notes_path = os.path.join(self.notes_dir, 'register_notes.md')
            if not os.path.exists(self.notes_path):
                with open(self.notes_path, 'w', encoding='utf-8') as f:
                    f.write("# Register Notes\n\n")
            return os.path.abspath(self.notes_path)
        except Exception:
            return None

    def _read_all_notes(self) -> dict:
        notes = {}
        if not self.notes_path or not os.path.exists(self.notes_path):
            return notes
        try:
            with open(self.notes_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            current_key = None
            buf = []
            for line in lines:
                if line.startswith('## '):
                    if current_key is not None:
                        notes[current_key] = ''.join(buf).rstrip()
                    current_key = line[3:].strip()
                    buf = []
                else:
                    if current_key is not None:
                        buf.append(line)
            if current_key is not None:
                notes[current_key] = ''.join(buf).rstrip()
        except Exception:
            pass
        return notes

    def _write_all_notes(self, notes: dict):
        if not self.notes_path:
            return
        try:
            with open(self.notes_path, 'w', encoding='utf-8') as f:
                f.write('# Register Notes\n\n')
                for key, body in sorted(notes.items()):
                    f.write(f"## {key}\n")
                    if body:
                        if not body.endswith('\n'):
                            body = body + '\n'
                        f.write(body)
                    f.write('\n')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to write notes: {e}')

    def _resolve_current_register(self) -> dict | None:
        try:
            sel = self.tree.selection()
            if not sel:
                # Fall back to last known register if available when nothing is selected
                if getattr(self, '_last_reg_info', None):
                    return self._last_reg_info
                return None
            item_id = sel[0]
            item = self.tree.item(item_id)
            # If a field is selected, walk up to parent
            if 'register' not in item.get('tags', ()):  # if a field or other node selected
                parent = self.tree.parent(item_id)
                if parent:
                    item_id = parent
                    item = self.tree.item(parent)
            text = item.get('text', '')
            # Normalize register name from different label styles
            name = text
            if text.startswith('Register '):
                # Expect forms like: "Register <name> @ <addr>"
                try:
                    rest = text.split(' ', 1)[1]
                    name = rest.split(' @ ', 1)[0]
                except Exception:
                    name = text
            # Prefer to match by both module/block and name when available
            sel_mod, _sel_reg = self._selected_module_and_register_names()
            sel_mod_norm = (sel_mod or '').strip()
            candidates = [r for r in self.registers if r.get('name','') == name]
            if sel_mod_norm and candidates:
                for r in candidates:
                    blk = (r.get('block','') or '').strip()
                    if blk == sel_mod_norm:
                        return r
            # Fallback: first by name only
            for r in candidates:
                return r
            # Fallback 1: use node meta (if present) to recover register name/module
            meta = self._node_meta.get(item_id) if hasattr(self, '_node_meta') else None
            if isinstance(meta, dict):
                mname = meta.get('name') or meta.get('register') or name
                # Try match by meta name too
                for r in self.registers:
                    if r.get('name','') == mname:
                        return r
            # Fallback 2: last resort synthesize minimal record
            return {'name': name, 'map': '', 'block': sel_mod_norm or '', 'fields': []}    
        except Exception:
            return None

    def _safe_name(self, s: str) -> str:
        return ''.join(ch if (ch.isalnum() or ch in ('-','_','.')) else '_' for ch in (s or ''))

    def _infer_module_from_selection(self) -> str:
        try:
            item_id = getattr(self, '_last_selected_item', None)
            pid = item_id
            while pid:
                txt = self.tree.item(pid, 'text')
                if isinstance(txt, str) and txt.startswith('Module '):
                    return txt.split(' ', 1)[1]
                pid = self.tree.parent(pid)
        except Exception:
            pass
        return ''

    def _per_reg_folder(self) -> str:
        base = self._notes_path_for(self.current_regmap_path)
        # turn file path .../<base>.notes.md into folder .../<base>/
        base_name = os.path.splitext(os.path.basename(base))[0]
        folder = os.path.join(self.notes_dir, base_name)
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass
        return folder

    def _note_file_for_register(self, reg: dict) -> str:
        # Folder per regmap
        folder = self._per_reg_folder()
        # Prefer names derived from the current selection when available
        sel_mod, sel_reg = self._selected_module_and_register_names()
        module = self._normalize_module_name((reg.get('block') or '').strip() or sel_mod or self._infer_module_from_selection() or 'module')
        # Use the register name from reg if valid; otherwise from selection
        rname = (reg.get('name') or '').strip() or sel_reg or 'register'
        # If for some reason module and register ended up identical while selection provides a different register name, prefer selection
        if module == rname and sel_reg and sel_reg != module:
            rname = sel_reg
        fname = f"{self._safe_name(module)}.{self._safe_name(rname)}.md"
        return os.path.join(folder, fname)

    def _selected_module_and_register_names(self) -> tuple[str, str]:
        """Return (module_name, register_name) from the current tree selection.
        Tries to parse labels like 'Module <M>' and 'Register <R> @ <addr>'.
        Returns ('','') when not available.
        """
        mod = ''
        regname = ''
        try:
            sel = self.tree.selection()
            if not sel:
                return mod, regname
            item_id = sel[0]
            # Walk up to find nearest 'Module <..>' parent
            pid = item_id
            while pid:
                txt = self.tree.item(pid, 'text')
                if isinstance(txt, str) and txt.startswith('Module '):
                    mod = txt.split(' ', 1)[1].strip()
                    break
                pid = self.tree.parent(pid)
            # If we didn't find a 'Module ' ancestor (e.g. filtered tree), try the immediate parent text as module/block
            if not mod:
                try:
                    parent = self.tree.parent(item_id)
                    if parent:
                        ptxt = self.tree.item(parent, 'text')
                        if isinstance(ptxt, str) and ptxt:
                            mod = ptxt.strip()
                except Exception:
                    pass
            # Resolve a register node to extract the register name
            reg_item_id = None
            item = self.tree.item(item_id)
            tags = item.get('tags', ()) if isinstance(item, dict) else ()
            if 'register' in tags:
                reg_item_id = item_id
            else:
                # Parent might be the register
                parent = self.tree.parent(item_id)
                if parent:
                    pitem = self.tree.item(parent)
                    if 'register' in (pitem.get('tags', ()) if isinstance(pitem, dict) else ()):  # type: ignore
                        reg_item_id = parent
                # Or a child under the selection might be a register
                if not reg_item_id:
                    for cid in self.tree.get_children(item_id):
                        citem = self.tree.item(cid)
                        if 'register' in (citem.get('tags', ()) if isinstance(citem, dict) else ()):  # type: ignore
                            reg_item_id = cid
                            break
            # Helper to parse a label like 'Register <name> @ <addr>'
            def _parse_reg_label(txt: str) -> str:
                if not isinstance(txt, str):
                    return ''
                if txt.startswith('Register '):
                    try:
                        rest = txt.split(' ', 1)[1]
                        return rest.split(' @ ', 1)[0].strip()
                    except Exception:
                        return txt
                return txt

            if reg_item_id:
                rtxt = self.tree.item(reg_item_id, 'text')
                regname = _parse_reg_label(rtxt)
            else:
                # No explicit register-tagged node found; try parsing current item text
                txt_here = self.tree.item(item_id, 'text')
                cand = _parse_reg_label(txt_here)
                if cand and cand != txt_here:
                    regname = cand
                # Otherwise, scan children for a parsable 'Register <..>' label (SNPS trees)
                if not regname:
                    for cid in self.tree.get_children(item_id):
                        ct = self.tree.item(cid, 'text')
                        cand = _parse_reg_label(ct)
                        if cand and (cand != ct or ct.startswith('Register ')):
                            regname = cand
                            break
        except Exception:
            pass
        return mod, regname

    def _normalize_module_name(self, name: str) -> str:
        """Strip common label prefix like 'Module ' from module names."""
        try:
            if isinstance(name, str) and name.startswith('Module '):
                return name.split(' ', 1)[1].strip()
        except Exception:
            pass
        return name

    def _read_note_for(self, reg: dict) -> str:
        path = self._note_file_for_register(reg)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return ''

    def _has_note_for(self, reg: dict) -> bool:
        """Return True if the note file for reg exists and is non-empty."""
        try:
            path = self._note_file_for_register(reg)
            return os.path.exists(path) and os.path.getsize(path) > 0
        except Exception:
            return False

    def _toggle_show_notes_only(self):
        """Toggle between showing only registers with notes and showing all."""
        try:
            if bool(self.show_notes_only_var.get()):
                self._filter_tree_to_noted_registers()
            else:
                self.clear_search()
        except Exception:
            try:
                # Fallback to a full rebuild if available
                self.clear_search()
            except Exception:
                pass

    def _write_note_for(self, reg: dict, body: str) -> str:
        """Write note body to its file robustly and return absolute path.
        Writes to a temp file and replaces the target to avoid partial writes.
        """
        path = os.path.abspath(self._note_file_for_register(reg))
        # Ensure parent exists / placeholder exists
        self._ensure_notes_file(path)
        folder = os.path.dirname(path)
        tmp_path = os.path.join(folder, '.__tmp_note__.md')
        try:
            os.makedirs(folder, exist_ok=True)
            data = body if body.endswith('\n') else body + '\n'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(data)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    pass
            try:
                # Atomic replace on Windows is available in Python 3.8+ via replace
                os.replace(tmp_path, path)
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            try:
                messagebox.showerror('Save Note', f'Failed to write note to:\n{path}\n\n{e}')
            except Exception:
                pass
        return path

    def _load_note_into_widget(self, reg: dict):
        body = self._read_note_for(reg)
        self.note_text.delete(1.0, tk.END)
        if body:
            self.note_text.insert(tk.END, body)
        # Refresh preview with loaded content
        try:
            self._update_md_preview()
        except Exception:
            pass

    def remove_current_note(self):
        """Delete the note file for the currently selected register, if present."""
        reg = self._resolve_current_register() or self._resolve_first_register_in_tree()
        if not reg:
            messagebox.showwarning('Remove Note', 'Select a register to remove its note.')
            return
        try:
            path = os.path.abspath(self._note_file_for_register(reg))
        except Exception as e:
            messagebox.showerror('Remove Note', f'Failed to resolve note path: {e}')
            return
        # Confirm
        try:
            if not os.path.exists(path):
                messagebox.showinfo('Remove Note', f'No note file exists for this register.\n{path}')
                # Still clear editor to reflect state
                self.note_text.delete(1.0, tk.END)
                try:
                    self._update_md_preview()
                except Exception:
                    pass
                return
        except Exception:
            pass
        if not messagebox.askyesno('Remove Note', f'Delete note file?\n\n{path}'):
            return
        # Delete
        try:
            os.remove(path)
        except Exception as e:
            messagebox.showerror('Remove Note', f'Failed to delete note:\n{path}\n\n{e}')
            return
        # Clear editor and preview
        self.note_text.delete(1.0, tk.END)
        try:
            self._update_md_preview()
        except Exception:
            pass
        # Update tree row tag: remove has_note
        try:
            sel = self.tree.selection()
            if sel:
                item_id = sel[0]
                # If selecting a field, move to its parent register node
                item = self.tree.item(item_id)
                if 'register' not in item.get('tags', ()):  # field or other
                    parent = self.tree.parent(item_id)
                    if parent:
                        item_id = parent
                        item = self.tree.item(item_id)
                tags = list(item.get('tags', ()))
                if 'has_note' in tags:
                    tags = [t for t in tags if t != 'has_note']
                    self.tree.item(item_id, tags=tuple(tags))
        except Exception:
            pass
        # If top toolbar has a notes-only toggle and it's active, refresh filter
        try:
            if getattr(self, 'show_notes_only_var', None) and bool(self.show_notes_only_var.get()):
                self._filter_tree_to_noted_registers()
        except Exception:
            pass
        self._status(f'Removed note: {path}')

    def save_current_note(self):
        reg = self._resolve_current_register()
        if not reg:
            # Fallback: pick the first register in the tree
            reg = self._resolve_first_register_in_tree()
        if not reg:
            messagebox.showwarning('No Register', 'Select a register to save a note for.')
            return
        # Normalize module/register names from current selection to ensure correct filename
        try:
            sel_mod, sel_reg = self._selected_module_and_register_names()
            if sel_reg:
                reg['name'] = sel_reg
            if sel_mod and not (reg.get('block') or '').strip():
                reg['block'] = sel_mod
        except Exception:
            pass
        key = self._note_key(reg)
        body = self.note_text.get(1.0, tk.END).rstrip()
        dest = self._write_note_for(reg, body)
        # Confirm existence and report absolute path
        dest_abs = os.path.abspath(dest)
        exists = os.path.exists(dest_abs)
        size = os.path.getsize(dest_abs) if exists else 0
        self._status(f"Saved note for {key} → {dest_abs}")
        try:
            print(f"[Notes] Save path: {dest_abs} | exists={exists} | size={size}")
        except Exception:
            pass
        if not exists:
            try:
                messagebox.showwarning('Save Note', f'Note path was computed but not found on disk yet:\n{dest_abs}')
            except Exception:
                pass
        try:
            self._update_md_preview()
        except Exception:
            pass

    def reload_current_note(self):
        reg = self._resolve_current_register()
        if not reg:
            reg = self._resolve_first_register_in_tree()
        if not reg:
            messagebox.showwarning('No Register', 'Select a register to reload a note for.')
            return
        self._load_note_into_widget(reg)
        self._status('Note reloaded')

    def _resolve_first_register_in_tree(self) -> dict | None:
        """Find the first register node in the tree and map it to a register record."""
        try:
            # Breadth-first over root children
            queue = list(self.tree.get_children(''))
            while queue:
                nid = queue.pop(0)
                item = self.tree.item(nid)
                tags = item.get('tags', ())
                if 'register' in tags:
                    text = item.get('text','')
                    name = text
                    if text.startswith('Register '):
                        try:
                            name = text.split(' ',1)[1].split(' @ ',1)[0]
                        except Exception:
                            name = text
                    for r in self.registers:
                        if r.get('name','') == name:
                            return r
                    return {'name': name, 'map': '', 'block': '', 'fields': []}
                queue.extend(self.tree.get_children(nid))
        except Exception:
            return None
        return None

    def open_notes_file(self):
        # Open the current register's note file; if none, open regmap folder
        reg = self._resolve_current_register() or self._resolve_first_register_in_tree()
        target = None
        if reg:
            target = self._note_file_for_register(reg)
            # Ensure parent folder exists; touch file if missing
            self._ensure_notes_file(target)
        else:
            target = self._per_reg_folder()
        # Show a clear message if missing
        try:
            if target and not os.path.exists(target):
                messagebox.showwarning('Open Notes', f'Target does not exist yet:\n{target}')
        except Exception:
            pass
        try:
            if os.path.isdir(target):
                if os.name == 'nt':
                    os.startfile(target)  # type: ignore[attr-defined]
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', target])
            else:
                if os.name == 'nt':
                    os.startfile(target)  # type: ignore[attr-defined]
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', target])
        except Exception:
            try:
                import webbrowser
                # Fallback to opening the containing folder or file URI
                if os.path.isfile(target):
                    webbrowser.open('file://' + target)
                else:
                    webbrowser.open('file://' + (target or ''))
            except Exception as e:
                messagebox.showerror('Error', f'Failed to open notes target: {e}')

    def _resolve_current_note_path(self) -> str | None:
        """Return absolute path to the current register's note file if determinable."""
        reg = self._resolve_current_register() or self._resolve_first_register_in_tree()
        if not reg:
            return None
        try:
            path = self._note_file_for_register(reg)
            return os.path.abspath(path)
        except Exception:
            return None

    def copy_current_note_path(self):
        path = self._resolve_current_note_path()
        if not path:
            messagebox.showwarning('Copy Path', 'No register selected; cannot determine note path.')
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            self._status(f"Copied path: {path}")
        except Exception as e:
            messagebox.showerror('Copy Path', f'Failed to copy path: {e}')

    def open_note_folder(self):
        path = self._resolve_current_note_path()
        if not path:
            messagebox.showwarning('Open Folder', 'No register selected; cannot determine note path.')
            return
        folder = os.path.dirname(path)
        try:
            os.makedirs(folder, exist_ok=True)
            if os.name == 'nt':
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                import subprocess
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            messagebox.showerror('Open Folder', f'Failed to open folder:\n{folder}\n{e}')

    # ===== Markdown editor helpers =====
    def _note_edit_sep(self):
        try:
            self.note_text.edit_separator()
        except Exception:
            pass

    def _get_sel(self):
        """Return (start, end, text). If no selection, use current word under cursor."""
        w = self.note_text
        try:
            start = w.index('sel.first')
            end = w.index('sel.last')
            return start, end, w.get(start, end)
        except Exception:
            # No selection: select current word
            try:
                pos = w.index(tk.INSERT)
                start = w.search(r'\m', pos, regexp=True, backwards=True) or pos
                end = w.search(r'\M', pos, regexp=True) or pos
                if start == end:
                    # fallback to line bounds
                    start = f"{pos.split('.')[0]}.0"
                    end = f"{pos.split('.')[0]}.end"
                return start, end, w.get(start, end)
            except Exception:
                return tk.INSERT, tk.INSERT, ''

    def _replace_range(self, start, end, new_text):
        w = self.note_text
        self._note_edit_sep()
        try:
            w.delete(start, end)
            w.insert(start, new_text)
        finally:
            try:
                w.see(start)
            except Exception:
                pass

    def _md_wrap_selection(self, left: str, right: str):
        start, end, txt = self._get_sel()
        self._replace_range(start, end, f"{left}{txt}{right}")

    def _md_insert_heading(self, level: int = 1):
        level = max(1, min(6, int(level or 1)))
        w = self.note_text
        line_start = w.index('insert linestart')
        line_end = w.index('insert lineend')
        content = w.get(line_start, line_end).lstrip('# ').rstrip()
        new_line = f"{'#'*level} {content}"
        self._replace_range(line_start, line_end, new_line)

    def _md_prefix_selection_lines(self, prefix: str):
        w = self.note_text
        try:
            start = w.index('sel.first')
            end = w.index('sel.last')
        except Exception:
            # No selection -> current line
            start = w.index('insert linestart')
            end = w.index('insert lineend')
        # Expand to full lines
        line_start = w.index(f"{start} linestart")
        line_end = w.index(f"{end} lineend")
        block = w.get(line_start, line_end)
        lines = block.splitlines()
        if not lines:
            lines = ['']
        new = '\n'.join((ln if ln.startswith(prefix) else prefix + ln) for ln in lines)
        self._replace_range(line_start, line_end, new)

    def _md_insert_code_block(self):
        w = self.note_text
        try:
            start = w.index('sel.first')
            end = w.index('sel.last')
            body = w.get(start, end)
        except Exception:
            start = end = w.index(tk.INSERT)
            body = ''
        fenced = f"```\n{body}\n```"
        self._replace_range(start, end, fenced)

    def _md_insert_link(self):
        url = simpledialog.askstring('Insert Link', 'Enter URL:')
        if not url:
            return
        start, end, txt = self._get_sel()
        label = txt.strip() or 'link-text'
        self._replace_range(start, end, f"[{label}]({url})")

    def _md_insert_image(self):
        # Prefer file picker, fallback to URL prompt
        path = filedialog.askopenfilename(title='Select image', filetypes=[('Images','*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.svg;*.webp'), ('All files','*.*')])
        if not path:
            path = simpledialog.askstring('Insert Image', 'Enter image URL or path:')
            if not path:
                return
        alt = simpledialog.askstring('Alt text', 'Enter alt text (optional):') or ''
        pos = self.note_text.index(tk.INSERT)
        self._replace_range(pos, pos, f"![{alt}]({path})")

    def _filter_tree_to_noted_registers(self):
        """Filter the tree to show only registers that have a non-empty markdown note file."""
        try:
            noted = []
            for reg in (self.registers or []):
                try:
                    path = self._note_file_for_register(reg)
                    if path and os.path.exists(path) and os.path.getsize(path) > 0:
                        noted.append(reg)
                except Exception:
                    continue
            if not noted:
                messagebox.showinfo('Notes Filter', 'No registers with notes were found for this regmap.')
                return
            # Rebuild tree with only noted registers
            self._rebuild_tree_from_registers(noted)
            try:
                self._status(f"Filtered to {len(noted)} register(s) with notes")
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror('Notes Filter', f'Failed to filter by notes: {e}')
            except Exception:
                pass

    def _update_md_preview(self):
        """Render the current note markdown into the Preview tab.
        Uses markdown -> HTML when possible, otherwise falls back to plain text.
        """
        try:
            text = self.note_text.get('1.0', tk.END)
        except Exception:
            text = ''
        text = text if isinstance(text, str) else str(text or '')
        # Only render when Preview tab is visible, but compute anyway to keep fresh
        html_content = None
        # Try python-markdown
        try:
            import markdown as _md
            html_content = _md.markdown(text, extensions=['extra', 'sane_lists'])
        except Exception:
            # Try markdown2
            try:
                import markdown2 as _md2
                html_content = _md2.markdown(text)
            except Exception:
                html_content = None
        if html_content is None:
            # Fallback: escape HTML, show as plain text in preview
            if self._preview_html_label is not None:
                # Render simple preformatted if html widget exists
                try:
                    esc = html.escape(text).replace('\n', '<br>')
                    self._preview_html_label.set_html(f"<div style='font-family: sans-serif; white-space: normal'>{esc}</div>")
                except Exception:
                    pass
            if self._preview_text is not None:
                try:
                    self._preview_text.configure(state='normal')
                    self._preview_text.delete('1.0', tk.END)
                    self._preview_text.insert(tk.END, text)
                    self._preview_text.configure(state='disabled')
                except Exception:
                    pass
            return
        # We have HTML content
        # Sanitize: remove style blocks and custom markers
        try:
            html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.IGNORECASE | re.DOTALL)
        except Exception:
            pass
        try:
            html_content = html_content.replace('[cite_start]', '')
        except Exception:
            pass
        if self._preview_html_label is not None:
            try:
                # Do not inject CSS; tkhtmlview may render <style> as text. Feed clean HTML only.
                self._preview_html_label.set_html(html_content)
            except Exception:
                pass
        if self._preview_text is not None:
            try:
                # Strip tags crudely if HTML renderer is not available
                plain = re.sub(r'<[^>]+>', '', html_content)
                plain = plain.replace('[cite_start]', '')
                self._preview_text.configure(state='normal')
                self._preview_text.delete('1.0', tk.END)
                self._preview_text.insert(tk.END, plain)
                self._preview_text.configure(state='disabled')
            except Exception:
                pass

    def clear_search(self):
        """Clear search filter and rebuild full tree from all registers."""
        self.matched_registers = None
        # If we have an SNPS modules model, rebuild that exact tree
        if hasattr(self, '_snps_modules') and isinstance(self._snps_modules, dict) and self._snps_modules:
            self._rebuild_snps_tree(self._snps_modules)
            return
        state = self._capture_tree_state()
        self._rebuild_tree_from_registers(self.registers)
        self._restore_tree_state(state)

    def _rebuild_tree_from_registers(self, registers):
        """Rebuild the tree to show only the branches contained in 'registers'."""
        # Clear current tree
        self.tree.delete(*self.tree.get_children())
        self._match_spans.clear()
        # Group by map -> block -> registers
        by_map = defaultdict(lambda: defaultdict(list))
        for reg in (registers or []):
            by_map[reg.get('map', '')][reg.get('block', '')].append(reg)
        
        for map_name, blocks in by_map.items():
            map_node = self.tree.insert('', 'end', text=map_name or '(no map)', open=True, tags=('memory_map',))
            for block_name, regs in blocks.items():
                block_node = self.tree.insert(
                    map_node, 'end', text=block_name or '(no block)',
                    values=('', '', ''), tags=('address_block',)
                )
                for reg in regs:
                    reg_offset_int = self.parse_number(reg.get('offset', '0'), 0)
                    _tags = ['register','match']
                    try:
                        if self._has_note_for(reg):
                            _tags.append('has_note')
                    except Exception:
                        pass
                    reg_node = self.tree.insert(
                        block_node, 'end', text=reg.get('name', ''),
                        values=(f"0x{reg_offset_int:X}", reg.get('size', ''), reg.get('access', '')), tags=tuple(_tags)
                    )
                    # Compute highlight spans within register text and selected value columns
                    try:
                        spans_name = self._compute_match_spans(reg.get('name',''))
                        spans_off = self._compute_match_spans(f"0x{reg_offset_int:X}")
                        spans_acc = self._compute_match_spans(str(reg.get('access','')))
                        colspans = {}
                        if spans_name:
                            colspans['#0'] = spans_name
                        if spans_off:
                            colspans['offset'] = spans_off
                        if spans_acc:
                            colspans['access'] = spans_acc
                        if colspans:
                            self._match_spans[reg_node] = colspans
                    except Exception:
                        pass
                    # Fields
                    for f in reg.get('fields', []):
                        try:
                            bits = f"[{int(f.get('bit_offset','0'))+int(f.get('bit_width','1'))-1}:{f.get('bit_offset','0')}]"
                        except Exception:
                            bits = f"[{f.get('bit_offset','0')}:{f.get('bit_offset','0')}]"
                        reset_val = f.get('reset_value', '')
                        # Attempt to present in binary width
                        try:
                            bw = int(f.get('bit_width','1'))
                            rv_int = int(str(reset_val), 16)
                            reset_disp = f"{bw}'b{rv_int:0{bw}b}"
                        except Exception:
                            reset_disp = str(reset_val)
                        field_item = self.tree.insert(
                            reg_node, 'end',
                            text=f"{f.get('name','')} {bits}",
                            values=(reset_disp, f.get('access',''), ''),
                            tags=('field','match')
                        )
                        try:
                            spans_name = self._compute_match_spans(f.get('name',''))
                            spans_off = self._compute_match_spans(reset_disp)
                            spans_acc = self._compute_match_spans(str(f.get('access','')))
                            colspans = {}
                            if spans_name:
                                colspans['#0'] = spans_name
                            if spans_off:
                                colspans['offset'] = spans_off
                            if spans_acc:
                                colspans['access'] = spans_acc
                            if colspans:
                                self._match_spans[field_item] = colspans
                        except Exception:
                            pass
        # Bind selection
        self.tree.bind('<<TreeviewSelect>>', self.show_register_details)
        # After rebuild, refresh overlay
        self._refresh_highlight_overlay()

    def _rebuild_snps_tree(self, modules: dict):
        """Rebuild SNPS Module→Register→Field tree from a saved modules snapshot.
        Structure: { module: { register: { 'address','reg_width_bits','reg_size_bytes','addr_end_hex','fields': [
            { 'field','bitrange','address','reset','access','desc','alias','full' }
        ] } } }
        """
        try:
            # Clear
            self.tree.delete(*self.tree.get_children())
            self._node_meta = {}
            for module, regs in (modules or {}).items():
                mid = self.tree.insert('', 'end', text=f"Module {module}", open=True)
                self._node_meta[mid] = {'mode': 'snps', 'kind': 'module', 'name': module}
                for reg, info in regs.items():
                    # info can be either a dict with 'fields' or a list of field dicts
                    if isinstance(info, dict) and 'fields' in info:
                        address = info.get('address','')
                        reg_width_bits = info.get('reg_width_bits','')
                        reg_size_bytes = info.get('reg_size_bytes','')
                        addr_end_hex = info.get('addr_end_hex','')
                        fields_list = info.get('fields', [])
                    else:
                        # Legacy shape from _populate_snps_tc_tree: info is a list of field dicts
                        fields_list = list(info) if isinstance(info, list) else []
                        # Derive address and register metrics
                        address = fields_list[0].get('address','') if fields_list else ''
                        # Compute width from bitranges
                        max_width = 0
                        max_msb = -1
                        for ent in fields_list:
                            br = ent.get('bitrange','')
                            try:
                                if br:
                                    if ':' in br or '-' in br:
                                        msb, lsb = [int(x) for x in br.replace('-',':').split(':')]
                                        w = abs(msb - lsb) + 1
                                        if w > max_width:
                                            max_width = w
                                        if msb > max_msb:
                                            max_msb = msb
                                    else:
                                        msb = lsb = int(br)
                                        if 1 > max_width:
                                            max_width = 1
                                        if msb > max_msb:
                                            max_msb = msb
                            except Exception:
                                pass
                        if max_msb >= 0 and (max_msb + 1) > max_width:
                            max_width = max_msb + 1
                        reg_width_bits = max_width
                        # size bytes heuristic
                        if not reg_width_bits:
                            reg_size_bytes = ''
                        else:
                            bits = int(reg_width_bits)
                            reg_size_bytes = 1 if bits <= 8 else 2 if bits <= 16 else 4 if bits <= 32 else 8 if bits <= 64 else (bits + 7)//8
                        # end address
                        try:
                            addr_int = int(address, 16)
                            addr_end_int = addr_int + max(1, int(reg_size_bytes) if reg_size_bytes else 1) - 1
                            addr_end_hex = f"0x{addr_end_int:08X}"
                        except Exception:
                            addr_end_hex = ''

                    _tags = ['register']
                    try:
                        if self._has_note_for({'name': reg, 'block': module, 'map': ''}):
                            _tags.append('has_note')
                    except Exception:
                        pass
                    rid = self.tree.insert(mid, 'end', text=f"Register {reg} @ {address}", open=False, tags=tuple(_tags))
                    self._node_meta[rid] = {
                        'mode': 'snps', 'kind': 'register', 'name': reg,
                        'address': address,
                        'reg_width_bits': reg_width_bits,
                        'reg_size_bytes': reg_size_bytes,
                        'addr_end_hex': addr_end_hex
                    }
                    for ent in fields_list:
                        label = ent.get('field') or ent.get('full')
                        txt = f"Field {label} [{ent.get('bitrange','')}] {ent.get('access','')} reset={ent.get('reset','')}"
                        fid = self.tree.insert(rid, 'end', text=txt, open=False)
                        meta = ent.copy(); meta.update({'mode':'snps','kind':'field','module':module,'register':reg})
                        self._node_meta[fid] = meta
            self._refresh_highlight_overlay()
        except Exception as e:
            self.debug_print(f"SNPS rebuild error: {e}")

    def _compute_match_spans(self, text):
        """Return list of (start,end) indices in 'text' matching current query settings."""
        raw_query = (self.search_var.get() or '').strip()
        if not raw_query:
            return []
        case_sensitive = bool(self.case_var.get())
        exact = bool(self.exact_var.get())
        use_regex = bool(self.regex_var.get())
        hay = text if case_sensitive else text.lower()
        needle = raw_query if case_sensitive else raw_query.lower()
        spans = []
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                for m in re.finditer(raw_query, text if case_sensitive else text, flags):
                    spans.append((m.start(), m.end()))
                return spans
            except re.error:
                return []
        if exact:
            if hay == needle:
                return [(0, len(text))]
            return []
        # substring occurrences
        start = 0
        while True:
            idx = hay.find(needle, start)
            if idx == -1:
                break
            spans.append((idx, idx+len(needle)))
            start = idx + (1 if len(needle)==0 else len(needle))
        return spans

    def _refresh_highlight_overlay(self, event=None):
        """Redraw highlight rectangles over matched substrings for visible items."""
        # Disabled overlay: no-op refresh to avoid covering Treeview text
        return

    def _focus_first_match(self, registers):
        """Auto-open parent branches and select the first matched register."""
        if not registers:
            return
        first = registers[0]
        map_name = first.get('map','') or '(no map)'
        block_name = first.get('block','') or '(no block)'
        reg_name = first.get('name','')
        # find nodes by text
        def find_child_by_text(parent, text):
            for c in self.tree.get_children(parent):
                if self.tree.item(c, 'text') == text:
                    return c
            return None
        map_node = find_child_by_text('', map_name)
        if not map_node:
            return
        try:
            self.tree.item(map_node, open=True)
        except Exception:
            pass
        block_node = find_child_by_text(map_node, block_name)
        if not block_node:
            return
        try:
            self.tree.item(block_node, open=True)
        except Exception:
            pass
        reg_node = find_child_by_text(block_node, reg_name)
        if reg_node:
            try:
                self.tree.selection_set(reg_node)
                self.tree.see(reg_node)
            except Exception:
                pass

    # ===== Query Builder Dialog =====
    def open_query_builder(self):
        """Open a simple dialog to compose boolean filters (AND/OR rows)."""
        qb = tk.Toplevel(self.root)
        qb.title('Query Builder')
        qb.transient(self.root)
        qb.grab_set()
        frm = ttk.Frame(qb, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        rows = []

        def add_row():
            row_frame = ttk.Frame(frm)
            row_frame.pack(fill=tk.X, pady=2)
            # Operator between rows
            op_var = tk.StringVar(value='AND' if rows else '')
            op_combo = ttk.Combobox(row_frame, textvariable=op_var, width=5, state='readonly', values=['AND','OR'])
            if rows:
                op_combo.pack(side=tk.LEFT, padx=(0,5))
            else:
                ttk.Label(row_frame, text='').pack(side=tk.LEFT, padx=(0,5))
            # Scope
            sc_var = tk.StringVar(value=self.search_scope.get())
            sc_combo = ttk.Combobox(row_frame, textvariable=sc_var, width=14, state='readonly', values=self.scope_combo['values'])
            sc_combo.pack(side=tk.LEFT, padx=5)
            # Query text
            q_var = tk.StringVar()
            q_entry = ttk.Entry(row_frame, textvariable=q_var, width=30)
            q_entry.pack(side=tk.LEFT, padx=5)
            # Remove button
            def remove():
                rows.remove((op_var, sc_var, q_var, row_frame))
                row_frame.destroy()
            ttk.Button(row_frame, text='Remove', command=remove).pack(side=tk.LEFT, padx=5)
            rows.append((op_var, sc_var, q_var, row_frame))

        def build_and_apply():
            if not rows:
                qb.destroy()
                return
            # Build expression; also set overall scope to 'any' for combined
            parts = []
            first = True
            for op_var, sc_var, q_var, _ in rows:
                token = q_var.get().strip()
                if not token:
                    continue
                # Temporarily switch scope and run per-scope search by prefixing with nothing; we will just set query box
                # We compose using the UI scope as independent groups user will execute in chosen scope
                # For simplicity, we set the main scope selector to the last selected scope; filtering logic evaluates scope globally.
                # Users can then adjust as needed.
                if not first:
                    parts.append(op_var.get().upper())
                parts.append(token)
                first = False
            if parts:
                expr = ' '.join(parts)
                self.search_var.set(expr)
                # Set scope to 'any' so terms are evaluated broadly, users can refine if needed
                try:
                    self.search_scope.set('any')
                    self.scope_combo.set('any')
                except Exception:
                    pass
                self.perform_search()
            qb.destroy()

        # Buttons
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(8,0))
        ttk.Button(btns, text='Add Row', command=add_row).pack(side=tk.LEFT)
        ttk.Button(btns, text='Build & Apply', command=build_and_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text='Close', command=qb.destroy).pack(side=tk.RIGHT)

        # Start with one row
        add_row()

    def _show_search_usage(self):
        """Show a quick reference for the search syntax and features."""
        tips = (
            "Search syntax (quick reference):\n"
            "\n"
            "- Whitespace terms (toggleable):\n"
            "  • Space-separated terms act as AND when 'All terms (AND)' is checked; as OR otherwise.\n"
            "  • Example: status ready  → finds items containing both terms.\n"
            "\n"
            "- Boolean operators (always available):\n"
            "  • Use AND / && and OR / || for explicit grouping.\n"
            "  • Example: status AND (ready OR error)\n"
            "\n"
            "- Field-qualified tokens (override dropdown scope per token):\n"
            "  • name:, description:, map:, block:, access:, size:, address:, offset:,\n"
            "    field:, field_access:, field_bits:, field_width:, field_offset:, value:, reset:.\n"
            "  • Examples: name:RXS_CFG_0   block:RX0   address:0x20000   field:ENABLE\n"
            "\n"
            "- Negation (!):\n"
            "  • Prefix any token with ! to exclude matches.\n"
            "  • Works before the qualifier or inside the value.\n"
            "  • Examples: !block:RX0   name:!RESERVED   description:!\"link down\"\n"
            "\n"
            "- Quoted phrases (multi-word tokens):\n"
            "  • Use double or single quotes to keep spaces: description:\"link up\"  name:'CFG 0'\n"
            "  • Works with qualifiers, negation, AND/OR.\n"
            "\n"
            "- Regex / Exact / Case options:\n"
            "  • Regex: treat each token as a Python regex (no whitespace splitting in a token).\n"
            "  • Exact: match whole field/token exactly.\n"
            "  • Case: enable case-sensitive matching.\n"
            "\n"
            "- Numeric comparisons (size, address, offset, field_width, field_offset):\n"
            "  • Use =, ==, !=, >, <, >=, <= with decimal, 0x..., or 'h... values.\n"
            "  • Examples: size:>=32   address:0x20000   offset:=='h10'   field_width:8\n"
            "\n"
            "Examples:\n"
            "  • any scope: RX0 RXS_CFG_0                      (both terms must match when AND is on)\n"
            "  • qualified: name:RXS_CFG_0 block:RX0          (unambiguous)\n"
            "  • exclude:   name:RXS_CFG_0 !block:RX0         (negation)\n"
            "  • phrases:   description:\"link up\"           (quoted phrase)\n"
            "  • boolean:   (name:RXS_CFG_0 OR name:RXS_CFG_1) AND block:RX0\n"
        )
        try:
            messagebox.showinfo("Search Usage", tips)
        except Exception:
            pass

    # ===== Tree state capture/restore =====
    def _capture_tree_state(self):
        """Capture open and selected paths by (map, block, register)."""
        def item_path(item_id):
            text = self.tree.item(item_id, 'text')
            parent = self.tree.parent(item_id)
            if not parent:
                return (text,)
            return (*item_path(parent), text)
        open_paths = set()
        for iid in self.tree.get_children(''):
            # DFS
            stack = [iid]
            while stack:
                cur = stack.pop()
                if self.tree.item(cur, 'open'):
                    open_paths.add(tuple(item_path(cur)))
                stack.extend(self.tree.get_children(cur))
        sel = self.tree.selection()
        selected_path = tuple(item_path(sel[0])) if sel else None
        return {'open': open_paths, 'selected': selected_path}

    def _restore_tree_state(self, state):
        if not state:
            return
        open_paths = state.get('open', set())
        selected_path = state.get('selected')

        def find_child_by_text(parent, text):
            for c in self.tree.get_children(parent):
                if self.tree.item(c, 'text') == text:
                    return c
            return None

        # Re-open nodes
        for path in open_paths:
            # Walk path
            parent = ''
            node = None
            for part in path:
                node = find_child_by_text(parent, part)
                if node is None:
                    break
                parent = node
            if node is not None:
                try:
                    self.tree.item(node, open=True)
                except Exception:
                    pass
        # Restore selection
        if selected_path:
            parent = ''
            node = None
            for part in selected_path:
                node = find_child_by_text(parent, part)
                if node is None:
                    break
                parent = node
            if node is not None:
                try:
                    self.tree.selection_set(node)
                    self.tree.see(node)
                except Exception:
                    pass

    # ===== Live search debounce =====
    def _on_search_key(self, event=None):
        # Reset status
        self.search_status.config(text="")
        if self._search_after_id:
            try:
                self.root.after_cancel(self._search_after_id)
            except Exception:
                pass
        # Validate regex early if enabled
        if self.regex_var.get():
            try:
                flags = 0 if self.case_var.get() else re.IGNORECASE
                re.compile(self.search_var.get() or '', flags)
            except re.error as e:
                self.search_status.config(text=f"Invalid regex: {e}")
                return
        # Debounce
        self._search_after_id = self.root.after(300, self.perform_search)

    # ===== Filter Save/Restore =====
    def _current_filter_state(self) -> dict:
        """Capture current search filter configuration into a dict."""
        try:
            state = {
                'query': self.search_var.get() or '',
                'scope': self.search_scope.get() or 'any',
                'case': bool(self.case_var.get()),
                'exact': bool(self.exact_var.get()),
                'regex': bool(self.regex_var.get()),
                'and_terms': bool(self.and_terms_var.get()),
            }
        except Exception:
            state = {
                'query': '', 'scope': 'any', 'case': False, 'exact': False, 'regex': False, 'and_terms': True
            }
        return state

    def _apply_filter_state(self, state: dict):
        """Apply a previously saved filter state and run the search."""
        if not isinstance(state, dict):
            return
        try:
            self.search_var.set(state.get('query', ''))
            sc = state.get('scope', 'any')
            self.search_scope.set(sc)
            try:
                self.scope_combo.set(sc)
            except Exception:
                pass
            self.case_var.set(bool(state.get('case', False)))
            self.exact_var.set(bool(state.get('exact', False)))
            self.regex_var.set(bool(state.get('regex', False)))
            self.and_terms_var.set(bool(state.get('and_terms', True)))
        except Exception:
            pass
        # Execute search with new settings
        try:
            self.perform_search()
        except Exception:
            pass

    def save_filter(self):
        """Save the current search filter settings to a JSON file."""
        state = self._current_filter_state()
        # Suggest a default filename based on current regmap
        base = 'filter.json'
        try:
            if getattr(self, 'current_regmap_path', None):
                stem = os.path.splitext(os.path.basename(self.current_regmap_path))[0]
                base = f"{stem}.filter.json"
        except Exception:
            pass
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON files','*.json'), ('All files','*.*')],
            initialfile=base,
            title='Save Filter As...'
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            self._status(f"Filter saved → {path}")
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save filter: {e}')

    def restore_filter(self):
        """Restore search filter settings from a JSON file and apply them."""
        path = filedialog.askopenfilename(
            filetypes=[('JSON files','*.json'), ('All files','*.*')],
            title='Open Filter File...'
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self._apply_filter_state(state)
            self._status(f"Filter restored from {path}")
        except Exception as e:
            messagebox.showerror('Error', f'Failed to restore filter: {e}')

    def save_matches_to_csv(self):
        """Save only the matched subset (if any) to CSV; otherwise all registers.
        Now includes a multi-line Details column and an optional DetailsCompact column.
        """
        subset = self.matched_registers if self.matched_registers is not None else self.registers
        if not subset:
            messagebox.showwarning("No Data", "No matching registers to save.")
            return
        # Options
        opt = { 'add_compact': tk.BooleanVar(value=True), 'skip_placeholders': tk.BooleanVar(value=True) }
        dlg = tk.Toplevel(self.root)
        dlg.title('Save Matches Options')
        dlg.transient(self.root)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Checkbutton(frm, text='Add Details (compact) column', variable=opt['add_compact']).pack(anchor='w')
        ttk.Checkbutton(frm, text="Skip unnamed registers with no fields", variable=opt['skip_placeholders']).pack(anchor='w')
        chosen = {'ok': False}
        def ok():
            chosen['ok'] = True
            dlg.destroy()
        def cancel():
            dlg.destroy()
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(8,0))
        ttk.Button(btns, text='OK', command=ok).pack(side=tk.LEFT)
        ttk.Button(btns, text='Cancel', command=cancel).pack(side=tk.RIGHT)
        self.root.wait_window(dlg)
        if not chosen['ok']:
            return
        add_compact = bool(opt['add_compact'].get())
        # Ask for path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save matched register map as..."
        )
        if not file_path:
            return
        try:
            skip_placeholders = bool(opt['skip_placeholders'].get())
            skipped_count = 0
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Register', 'Map', 'Block', 'Absolute Address', 'Offset', 'Size (bits)', 
                    'Access', 'Field', 'Bit Range', 'Field Access', 'Reset Value', 'Description', 'Details'
                ]
                if add_compact:
                    fieldnames.append('DetailsCompact')
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for reg in subset:
                    # Placeholder detection: unnamed (empty or 'Unnamed Register') and no fields
                    name = (reg.get('name','') or '').strip()
                    if skip_placeholders and ((not name or name == 'Unnamed Register') and not reg.get('fields')):
                        skipped_count += 1
                        continue
                    if not reg.get('fields'):
                        details_txt = self._compose_details_legacy_inline(
                            reg.get('name',''), reg.get('absolute_address',''), f"0x{self.parse_number(reg.get('offset','0'), 0):X}",
                            reg.get('size',''), str(reg.get('access','')).upper(), '', '', '', '', reg.get('description',''),
                            map_name=reg.get('map',''), block_name=reg.get('block','')
                        )
                        row = {
                            'Register': reg.get('name',''),
                            'Map': reg.get('map',''),
                            'Block': reg.get('block',''),
                            'Absolute Address': reg.get('absolute_address',''),
                            'Offset': f"0x{self.parse_number(reg.get('offset','0'), 0):X}",
                            'Size (bits)': reg.get('size',''),
                            'Access': str(reg.get('access','')).upper(),
                            'Description': reg.get('description',''),
                            'Details': details_txt,
                        }
                        if add_compact:
                            row['DetailsCompact'] = self._compose_details_compact(
                                title=reg.get('name',''), address=reg.get('absolute_address',''), size_bits=reg.get('size',''),
                                access=str(reg.get('access','')).upper(), description=reg.get('description',''),
                                map_name=reg.get('map',''), block_name=reg.get('block','')
                            )
                        writer.writerow(row)
                    for f in reg.get('fields', []):
                        try:
                            bit_range = f"[{int(f.get('bit_offset','0'))+int(f.get('bit_width','1'))-1}:{f.get('bit_offset','0')}]"
                        except Exception:
                            bit_range = f"[{f.get('bit_offset','0')}]"
                        details_txt = self._compose_details_legacy_inline(
                            reg.get('name',''), reg.get('absolute_address',''), f"0x{self.parse_number(reg.get('offset','0'), 0):X}",
                            reg.get('size',''), str(reg.get('access','')).upper(), f.get('name',''), bit_range,
                            str(f.get('access','')).upper(), f.get('reset_value',''), f.get('description',''),
                            map_name=reg.get('map',''), block_name=reg.get('block','')
                        )
                        row = {
                            'Register': reg.get('name',''),
                            'Map': reg.get('map',''),
                            'Block': reg.get('block',''),
                            'Absolute Address': reg.get('absolute_address',''),
                            'Offset': f"0x{self.parse_number(reg.get('offset','0'), 0):X}",
                            'Size (bits)': reg.get('size',''),
                            'Access': str(reg.get('access','')).upper(),
                            'Field': f.get('name',''),
                            'Bit Range': bit_range,
                            'Field Access': str(f.get('access','')).upper(),
                            'Reset Value': f.get('reset_value',''),
                            'Description': f.get('description',''),
                            'Details': details_txt
                        }
                        if add_compact:
                            row['DetailsCompact'] = self._compose_details_compact(
                                title=reg.get('name',''), address=reg.get('absolute_address',''), size_bits=reg.get('size',''),
                                access=str(reg.get('access','')).upper(), field=f.get('name',''), bit_range=bit_range,
                                field_access=str(f.get('access','')).upper(), reset_value=f.get('reset_value',''),
                                description=f.get('description',''), map_name=reg.get('map',''), block_name=reg.get('block','')
                            )
                        writer.writerow(row)
            msg = f"Saved to {file_path}"
            if skip_placeholders and skipped_count:
                msg += f" (skipped {skipped_count} unnamed/fieldless registers)"
            self._status(msg)
            messagebox.showinfo("Success", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def save_matches_to_snps_csv(self):
        """Save matches (or full set) using SNPS-enriched schema so reload keeps Module→Register→Field layout."""
        subset = self.matched_registers if self.matched_registers is not None else self.registers
        if not subset:
            messagebox.showwarning("No Data", "No matching registers to save.")
            return
        # Simple option dialog to allow skipping placeholders
        opt = { 'skip_placeholders': tk.BooleanVar(value=True) }
        dlg = tk.Toplevel(self.root)
        dlg.title('Save (SNPS) Options')
        dlg.transient(self.root)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Checkbutton(frm, text="Skip unnamed registers with no fields", variable=opt['skip_placeholders']).pack(anchor='w')
        chosen = {'ok': False}
        def ok():
            chosen['ok'] = True
            dlg.destroy()
        def cancel():
            dlg.destroy()
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(8,0))
        ttk.Button(btns, text='OK', command=ok).pack(side=tk.LEFT)
        ttk.Button(btns, text='Cancel', command=cancel).pack(side=tk.RIGHT)
        self.root.wait_window(dlg)
        if not chosen['ok']:
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save matched (SNPS format) as..."
        )
        if not file_path:
            return
        # Columns for SNPS enriched CSV
        fieldnames = [
            'Module','Register','Field','BitRange','Address','Reset','Access','Description','Alias','FullPath',
            'RegWidthBits','RegSizeBytes','AddrEndHex'
        ]
        try:
            skip_placeholders = bool(opt['skip_placeholders'].get())
            skipped_count = 0
            with open(file_path, 'w', newline='', encoding='utf-8') as out:
                w = csv.DictWriter(out, fieldnames=fieldnames, extrasaction='ignore')
                w.writeheader()
                # Group subset by Module/Reg so we can compute register-wide columns
                grouped = defaultdict(lambda: defaultdict(list))
                for reg in subset:
                    name = (reg.get('name','') or '').strip()
                    if skip_placeholders and ((not name or name == 'Unnamed Register') and not reg.get('fields')):
                        skipped_count += 1
                        continue
                    module = reg.get('block','') or 'ROOT'
                    rname = reg.get('name','')
                    grouped[module][rname].append(reg)
                for module, regs in grouped.items():
                    for rname, reg_list in regs.items():
                        # Merge fields from possibly multiple fragments (should be one)
                        fields = []
                        addr = ''
                        for r in reg_list:
                            addr = addr or r.get('absolute_address','')
                            for f in r.get('fields', []):
                                # Build BitRange from offset/width
                                try:
                                    bo = int(str(f.get('bit_offset','0')), 0)
                                except Exception:
                                    bo = 0
                                try:
                                    bw = int(str(f.get('bit_width','1')), 0)
                                except Exception:
                                    bw = 1
                                hi = bo + max(1, bw) - 1
                                br = f"{hi}:{bo}"
                                fields.append({
                                    'Field': f.get('name',''),
                                    'BitRange': br,
                                    'Reset': f.get('reset_value',''),
                                    'Access': f.get('access',''),
                                    'Description': f.get('description',''),
                                    'Alias': '',
                                    'FullPath': f"{module}.{rname}.{f.get('name','')}"
                                })
                        # Compute reg width and size bytes heuristically
                        max_width = 0
                        max_msb = -1
                        for f in fields:
                            s = f.get('BitRange','')
                            try:
                                if ':' in s:
                                    hi, lo = [int(x) for x in s.split(':',1)]
                                    wbits = max(1, hi-lo+1)
                                    max_width = max(max_width, wbits)
                                    max_msb = max(max_msb, hi)
                                elif s:
                                    idx = int(s, 0)
                                    max_width = max(max_width, 1)
                                    max_msb = max(max_msb, idx)
                            except Exception:
                                pass
                        if max_msb >= 0 and (max_msb + 1) > max_width:
                            max_width = max_msb + 1
                        if max_width <= 0:
                            try:
                                max_width = int(reg_list[0].get('size','') or 0)
                            except Exception:
                                max_width = 0
                        if max_width <= 0:
                            reg_bytes = ''
                        else:
                            reg_bytes = 1 if max_width <= 8 else 2 if max_width <= 16 else 4 if max_width <= 32 else 8 if max_width <= 64 else (max_width + 7)//8
                        # End address
                        try:
                            addr_int = int(str(addr), 16)
                            addr_end_int = addr_int + (int(reg_bytes) if reg_bytes else 1) - 1
                            addr_end_hex = f"0x{addr_end_int:08X}"
                        except Exception:
                            addr_end_hex = ''
                        # Write rows, one per field (register-level rows if no fields)
                        if not fields:
                            w.writerow({
                                'Module': module, 'Register': rname, 'Field': '', 'BitRange': '',
                                'Address': addr, 'Reset': '', 'Access': '', 'Description': '', 'Alias': '', 'FullPath': f"{module}.{rname}",
                                'RegWidthBits': str(max_width) if max_width else '', 'RegSizeBytes': reg_bytes, 'AddrEndHex': addr_end_hex
                            })
                        else:
                            for f in fields:
                                row = {
                                    'Module': module,
                                    'Register': rname,
                                    'Field': f.get('Field',''),
                                    'BitRange': f.get('BitRange',''),
                                    'Address': addr,
                                    'Reset': f.get('Reset',''),
                                    'Access': f.get('Access',''),
                                    'Description': f.get('Description',''),
                                    'Alias': f.get('Alias',''),
                                    'FullPath': f.get('FullPath',''),
                                    'RegWidthBits': str(max_width) if max_width else '',
                                    'RegSizeBytes': reg_bytes,
                                    'AddrEndHex': addr_end_hex,
                                }
                                w.writerow(row)
            msg = f"Saved (SNPS) CSV: {file_path}"
            if skip_placeholders and skipped_count:
                msg += f" (skipped {skipped_count} unnamed/fieldless registers)"
            self._status(msg)
            messagebox.showinfo("Success", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save SNPS CSV: {e}")
            
    # ===== Fast XML -> CSV pipeline (no tree rendering) =====
    def _status(self, text: str):
        try:
            self.search_status.config(text=text)
            # Also reflect in bottom status bar if present
            if hasattr(self, 'status_msg') and self.status_msg:
                self.status_msg.config(text=text)
            self.root.update_idletasks()
        except Exception:
            pass

    def _notes_path_for(self, path: str | None) -> str:
        """Return a per-regmap notes file path within notes_dir based on the file name.
        Examples:
          foo.xml -> foo.notes.md
          regs.csv -> regs.notes.md
        If path is None, fall back to 'register_notes.md'.
        """
        try:
            if not path:
                return os.path.join(self.notes_dir, 'register_notes.md')
            base = os.path.basename(path)
            name, _ext = os.path.splitext(base)
            # Sanitize to safe filename
            safe = ''.join(ch if (ch.isalnum() or ch in ('-','_','.')) else '_' for ch in name)
            return os.path.join(self.notes_dir, f"{safe}.notes.md")
        except Exception:
            return os.path.join(self.notes_dir, 'register_notes.md')

    def _set_current_path(self, path: str | None):
        """Update the current file path and show it on the status bar."""
        try:
            self.current_regmap_path = path
            # Update notes base folder to the folder containing the current regmap file
            try:
                if path:
                    folder = os.path.dirname(path)
                    if folder:
                        self.notes_dir = folder
                        os.makedirs(self.notes_dir, exist_ok=True)
            except Exception:
                pass
            # Update notes file to be unique per source regmap
            try:
                os.makedirs(self.notes_dir, exist_ok=True)
            except Exception:
                pass
            self.notes_path = self._notes_path_for(path)
            if not hasattr(self, 'status_path') or self.status_path is None:
                return
            disp = ''
            if path:
                # Normalize and shorten very long paths by keeping head and tail
                p = os.path.normpath(path)
                if len(p) > 120:
                    disp = p[:50] + ' … ' + p[-50:]
                else:
                    disp = p
            self.status_path.config(text=disp)
            self.root.update_idletasks()
        except Exception:
            pass

    def convert_xml_to_csv(self):
        """Convert an IP-XACT XML directly to CSV without displaying content. Shows progress in status bar."""
        xml_path = filedialog.askopenfilename(
            filetypes=[("IP-XACT files", "*.xml"), ("All files", "*.*")],
            title="Select IP-XACT XML to convert"
        )
        if not xml_path:
            return
        # Options dialog
        opts = { 'skip_fields': tk.BooleanVar(value=False), 'parallel': tk.BooleanVar(value=False), 'skip_placeholders': tk.BooleanVar(value=True) }
        dlg = tk.Toplevel(self.root)
        dlg.title('Conversion Options')
        dlg.transient(self.root)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Checkbutton(frm, text='Skip field-level rows (faster, smaller CSV)', variable=opts['skip_fields']).pack(anchor='w')
        ttk.Checkbutton(frm, text='Parallel by memory map (fallback path)', variable=opts['parallel']).pack(anchor='w')
        ttk.Checkbutton(frm, text='Skip unnamed registers with no fields', variable=opts['skip_placeholders']).pack(anchor='w')
        chosen = {'ok': False}
        def ok():
            chosen['ok'] = True
            dlg.destroy()
        def cancel():
            dlg.destroy()
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(8,0))
        ttk.Button(btns, text='OK', command=ok).pack(side=tk.LEFT)
        ttk.Button(btns, text='Cancel', command=cancel).pack(side=tk.RIGHT)
        self.root.wait_window(dlg)
        if not chosen['ok']:
            return

        csv_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save converted CSV as..."
        )
        if not csv_path:
            return
        try:
            skip_fields = bool(opts['skip_fields'].get())
            parallel = bool(opts['parallel'].get())
            skip_placeholders = bool(opts['skip_placeholders'].get())
            # Sniff XML root to see if it's an Addressmap (vendor) format
            try:
                with open(xml_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if '&lt;' in content or '&gt;' in content or '&amp;' in content:
                    content = html.unescape(content)
                if '&' in content and '&amp;' not in content:
                    content = content.replace('&', '&amp;')
                root = ET.fromstring(content)
                local_root = root.tag.split('}', 1)[-1] if '}' in root.tag else root.tag
            except Exception:
                local_root = ''
            if local_root.lower() == 'addressmap':
                self._status("Converting Addressmap XML...")
                # Addressmap converter currently ignores skip_placeholders; can be extended similarly if needed
                self._convert_addressmap_to_csv(xml_path, csv_path, skip_fields)
                self._status("Done")
                messagebox.showinfo("Success", f"Converted to CSV: {csv_path}")
                return
            # Prefer streaming writer; if parallel selected, use parallel fallback
            if parallel:
                self._status("Parallel conversion (pre-scan)...")
                self._parallel_convert_to_csv(xml_path, csv_path, skip_fields, skip_placeholders)
            else:
                self._stream_write_xml_to_csv(xml_path, csv_path, skip_fields, skip_placeholders)
            self._status("Done")
            messagebox.showinfo("Success", f"Converted to CSV: {csv_path}")
        except Exception as e:
            self._status("")
            messagebox.showerror("Error", f"Conversion failed: {str(e)}")

    def convert_dat_to_csv(self):
        """Convert a .dat register definition file to CSV using the observed format.
        Expected line format (tab-delimited preferred):
        REG_PREFIX.REG_NAME.FIELD_NAME \t HI:LO \t OFFSET \t REG_NAME \t RESET \t ACCESS \t DESCRIPTION...
        Example:
        SUP.IDCODE_LO.VAL\t15:0\t0x0000\tSUP.IDCODE_LO\t0x74CD\tR\tLow 16 Bits of IDCODE.
        """
        dat_path = filedialog.askopenfilename(
            filetypes=[("DAT files", "*.dat"), ("All files", "*.*")],
            title="Select .dat file to convert"
        )
        if not dat_path:
            return
        csv_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save converted CSV as..."
        )
        if not csv_path:
            return
        def parse_bit_range(br: str):
            s = (br or '').strip()
            s = s.strip('[]')
            if ':' in s:
                hi_s, lo_s = s.split(':', 1)
                try:
                    hi = int(hi_s, 0)
                except Exception:
                    hi = self.parse_number(hi_s, 0)
                try:
                    lo = int(lo_s, 0)
                except Exception:
                    lo = self.parse_number(lo_s, 0)
                width = max(1, (hi - lo + 1)) if hi >= lo else 1
                return (hi, lo, width)
            # single bit index
            try:
                idx = int(s, 0)
            except Exception:
                idx = self.parse_number(s, 0)
            return (idx, idx, 1)
        fieldnames = [
            'Register', 'Map', 'Block', 'Absolute Address', 'Offset', 'Size (bits)',
            'Access', 'Field', 'Bit Range', 'Field Access', 'Reset Value', 'Description', 'Details'
        ]
        try:
            with open(dat_path, 'r', encoding='utf-8') as f, open(csv_path, 'w', newline='', encoding='utf-8') as out:
                w = csv.DictWriter(out, fieldnames=fieldnames)
                w.writeheader()
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith('#') or line.startswith('//'):
                        continue
                    # Prefer tab-split; fallback to whitespace maxsplit=6 to keep description
                    parts = line.split('\t') if ('\t' in raw) else re.split(r"\s+", line, maxsplit=6)
                    if len(parts) < 6:
                        # Try harder if description missing
                        continue
                    # Map fields
                    full_name = parts[0].strip()
                    bit_range_txt = parts[1].strip()
                    offset_txt = parts[2].strip()
                    reg_name_txt = parts[3].strip()
                    reset_val = parts[4].strip()
                    access = parts[5].strip() if len(parts) >= 6 else ''
                    desc = parts[6].strip() if len(parts) >= 7 else ''
                    # Derive field and register names
                    if '.' in full_name:
                        # REG_PREFIX.REG_NAME.FIELD
                        fld_name = full_name.split('.')[-1]
                        reg_name = reg_name_txt or full_name.split('.')[-2]
                        block_name = '.'.join(full_name.split('.')[:-2]) if len(full_name.split('.')) > 2 else ''
                    else:
                        fld_name = full_name
                        reg_name = reg_name_txt or full_name
                        block_name = ''
                    # Compute widths and normalized addresses
                    hi, lo, width = parse_bit_range(bit_range_txt)
                    reg_off_int = self.parse_number(offset_txt.replace('_',''), 0)
                    abs_addr = f"0x{reg_off_int:X}"
                    w.writerow({
                        'Register': reg_name,
                        'Map': '',
                        'Block': block_name,
                        'Absolute Address': abs_addr,
                        'Offset': f"0x{reg_off_int:X}",
                        'Size (bits)': '',
                        'Access': access.upper(),
                        'Field': fld_name,
                        'Bit Range': f"[{hi}:{lo}]",
                        'Field Access': access.upper(),
                        'Reset Value': reset_val,
                        'Description': desc,
                    })
            messagebox.showinfo('Success', f'Converted DAT to CSV: {csv_path}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to convert DAT: {e}')

    def convert_regdump_to_csv(self):
        """Convert a regdump CSV with header like: fields,pids,values,addrs
        into the standardized register CSV format used by this tool.
        """
        in_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Select regdump CSV (fields,pids,values,addrs)"
        )
        if not in_path:
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save converted CSV as..."
        )
        if not out_path:
            return
        fieldnames = [
            'Register', 'Map', 'Block', 'Absolute Address', 'Offset', 'Size (bits)',
            'Access', 'Field', 'Bit Range', 'Field Access', 'Reset Value', 'Description', 'Details'
        ]
        try:
            with open(in_path, 'r', encoding='utf-8') as f_in, open(out_path, 'w', newline='', encoding='utf-8') as f_out:
                reader = csv.reader(f_in)
                writer = csv.DictWriter(f_out, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                header = next(reader, None)
                if header is None:
                    raise ValueError("Empty input file")
                # Normalize header
                hdr_lower = [h.strip().lower() for h in header]
                try:
                    idx_fields = hdr_lower.index('fields')
                except ValueError:
                    # Some dumps may use 'field' singular
                    idx_fields = hdr_lower.index('field') if 'field' in hdr_lower else 0
                idx_pids = hdr_lower.index('pids') if 'pids' in hdr_lower else None
                idx_values = hdr_lower.index('values') if 'values' in hdr_lower else (hdr_lower.index('value') if 'value' in hdr_lower else None)
                idx_addrs = hdr_lower.index('addrs') if 'addrs' in hdr_lower else (hdr_lower.index('addr') if 'addr' in hdr_lower else None)
                for row in reader:
                    if not row or all(not str(c).strip() for c in row):
                        continue
                    # Safe get helpers
                    def _get(idx, default=''):
                        try:
                            return row[idx]
                        except Exception:
                            return default
                    path = _get(idx_fields, '').strip()
                    value_txt = _get(idx_values, '').strip()
                    addr_txt = _get(idx_addrs, '').strip()
                    # Parse path: Block.Register[.Field]
                    block = ''
                    reg_name = ''
                    field_name = ''
                    parts = [p for p in path.split('.') if p]
                    if len(parts) >= 3:
                        block = parts[0]
                        reg_name = parts[1]
                        field_name = '.'.join(parts[2:])  # keep any extra nesting
                    elif len(parts) == 2:
                        block, reg_name = parts
                    elif len(parts) == 1:
                        reg_name = parts[0]
                    # Address formatting
                    try:
                        addr_int = int(addr_txt, 0)
                    except Exception:
                        addr_int = self.parse_number(addr_txt.replace('_',''), 0)
                    abs_addr = f"0x{addr_int:X}"
                    # Compose multi-line details for this row
                    details_txt = self._compose_details_legacy_inline(
                        reg_name, abs_addr, abs_addr, '', '', field_name, '', '', value_txt, '',
                        map_name='', block_name=block
                    )
                    # Write standardized row; we don't have bit ranges or access in regdump snapshot
                    writer.writerow({
                        'Register': reg_name,
                        'Map': '',
                        'Block': block,
                        'Absolute Address': abs_addr,
                        'Offset': abs_addr,
                        'Size (bits)': '',
                        'Access': '',
                        'Field': field_name,
                        'Bit Range': '',
                        'Field Access': '',
                        'Reset Value': value_txt,  # use snapshot value as reset/value placeholder
                        'Description': '',
                        'Details': details_txt,
                    })
            messagebox.showinfo('Success', f'Converted regdump to CSV: {out_path}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to convert regdump CSV: {e}')

    def _fast_parse_registers(self, file_path: str):
        """Parse XML into register dicts using streaming iterparse for low memory.
        Falls back to non-streaming parsing if the XML has issues.
        """
        def _local(t: str) -> str:
            return t.split('}', 1)[-1] if '}' in t else t

        registers = []
        self._status("Scanning XML (streaming)...")
        try:
            context = ET.iterparse(file_path, events=("start", "end"))
            # Track simple state
            map_name = ''
            block_name = ''
            base_addr = '0x0'
            current_elem_stack = []

            for event, elem in context:
                tag = _local(elem.tag)
                if event == 'start':
                    current_elem_stack.append(tag)
                    # reset contexts on entry
                    if tag == 'memoryMap':
                        map_name = ''
                    elif tag == 'addressBlock':
                        block_name = ''
                        base_addr = '0x0'
                elif event == 'end':
                    # Parent tag name (if any)
                    parent_tag = current_elem_stack[-2] if len(current_elem_stack) >= 2 else None

                    # Capture names/attrs for map and block when their name child closes
                    if tag == 'name' and parent_tag == 'memoryMap' and elem.text:
                        map_name = elem.text.strip()
                    elif tag == 'name' and parent_tag == 'addressBlock' and elem.text:
                        block_name = elem.text.strip()
                    elif tag == 'baseAddress' and parent_tag == 'addressBlock' and elem.text:
                        base_addr = elem.text.strip()

                    # When a register closes, process it fully and clear from memory
                    if tag == 'register':
                        rname = 'Unnamed Register'
                        roffset = '0x0'
                        rsize = '32'
                        racc = 'read-write'
                        rdesc = ''
                        # Scan direct children for properties
                        for ch in list(elem):
                            ct = _local(ch.tag)
                            if ch.text is None:
                                continue
                            txt = ch.text.strip()
                            if ct == 'name':
                                rname = txt
                            elif ct == 'addressOffset':
                                roffset = txt
                            elif ct == 'size':
                                rsize = txt
                            elif ct == 'access':
                                racc = txt
                            elif ct == 'description':
                                rdesc = txt
                        # Build reg record
                        block_addr_int = self.parse_number(base_addr, 0)
                        reg_addr_int = self.parse_number(roffset, 0)
                        abs_addr = f"0x{block_addr_int + reg_addr_int:X}"
                        reg_data = {
                            'name': rname,
                            'offset': roffset,
                            'size': rsize,
                            'access': racc,
                            'absolute_address': abs_addr,
                            'description': rdesc,
                            'fields': [],
                            'block': block_name,
                            'map': map_name
                        }
                        # Fields under this register (descendants)
                        for field in elem.iter():
                            if field is elem:
                                continue
                            if _local(field.tag) != 'field':
                                continue
                            fname = ''
                            fbo = '0'
                            fbw = '1'
                            facc = racc
                            fdesc = ''
                            freset = ''
                            for c2 in list(field):
                                ct = _local(c2.tag)
                                if c2.text is None:
                                    continue
                                t2 = c2.text.strip()
                                if ct == 'name':
                                    fname = t2
                                elif ct == 'bitOffset':
                                    fbo = t2
                                elif ct == 'bitWidth':
                                    fbw = t2
                                elif ct == 'access':
                                    facc = t2
                                elif ct == 'description':
                                    fdesc = t2
                            # first descendant 'value'
                            for d in field.iter():
                                if d is field:
                                    continue
                                if _local(d.tag) == 'value' and d.text:
                                    rv = d.text.strip().strip("'")
                                    if rv.lower().startswith('h'):
                                        rv = rv[1:]
                                    freset = rv
                                    break
                            reg_data['fields'].append({
                                'name': fname or 'Unnamed Field',
                                'bit_offset': fbo,
                                'bit_width': fbw,
                                'access': facc,
                                'reset_value': freset or '0',
                                'description': fdesc
                            })
                        registers.append(reg_data)
                        # Clear processed element to free memory
                        elem.clear()
                    # Pop the current tag after processing end
                    if current_elem_stack:
                        current_elem_stack.pop()
            return registers
        except ET.ParseError:
            # Fallback to prior non-streaming method if parsing fails (e.g., invalid entities)
            self._status("Streaming failed, falling back to buffered parse...")
            # Reuse previous buffered logic
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if '&lt;' in content or '&gt;' in content or '&amp;' in content:
                content = html.unescape(content)
            if '&' in content and '&amp;' not in content:
                content = content.replace('&', '&amp;')
            root = ET.fromstring(content)
            # Simple non-streaming fallback: reuse a subset of earlier logic
            def _fallback_find(parent, tag_name, default=''):
                for ch in list(parent):
                    if _local(ch.tag) == tag_name and ch.text:
                        return ch.text.strip()
                for el in parent.iter():
                    if el is parent:
                        continue
                    if _local(el.tag) == tag_name and el.text:
                        return el.text.strip()
                return default
            registers = []
            for mem_map in root.iter():
                if _local(mem_map.tag) != 'memoryMap':
                    continue
                map_name = _fallback_find(mem_map, 'name', '')
                for block in mem_map.iter():
                    if _local(block.tag) != 'addressBlock':
                        continue
                    block_name = _fallback_find(block, 'name', '')
                    base_addr = _fallback_find(block, 'baseAddress', '0x0')
                    for reg in block.iter():
                        if _local(reg.tag) != 'register':
                            continue
                        rname = _fallback_find(reg, 'name', 'Unnamed Register')
                        roffset = _fallback_find(reg, 'addressOffset', '0x0')
                        rsize = _fallback_find(reg, 'size', '32')
                        racc = _fallback_find(reg, 'access', 'read-write')
                        rdesc = _fallback_find(reg, 'description', '')
                        block_addr_int = self.parse_number(base_addr, 0)
                        reg_addr_int = self.parse_number(roffset, 0)
                        abs_addr = f"0x{block_addr_int + reg_addr_int:X}"
                        reg_data = {
                            'name': rname,
                            'offset': roffset,
                            'size': rsize,
                            'access': racc,
                            'absolute_address': abs_addr,
                            'description': rdesc,
                            'fields': [],
                            'block': block_name,
                            'map': map_name
                        }
                        for field in reg.iter():
                            if _local(field.tag) != 'field':
                                continue
                            fname = _fallback_find(field, 'name', 'Unnamed Field')
                            fbo = _fallback_find(field, 'bitOffset', '0')
                            fbw = _fallback_find(field, 'bitWidth', '1')
                            facc = _fallback_find(field, 'access', racc)
                            fdesc = _fallback_find(field, 'description', '')
                            # Find value
                            freset = '0'
                            for d in field.iter():
                                if _local(d.tag) == 'value' and d.text:
                                    rv = d.text.strip().strip("'")
                                    if rv.lower().startswith('h'):
                                        rv = rv[1:]
                                    freset = rv
                                    break
                            reg_data['fields'].append({
                                'name': fname,
                                'bit_offset': fbo,
                                'bit_width': fbw,
                                'access': facc,
                                'reset_value': freset,
                                'description': fdesc
                            })
                        registers.append(reg_data)
            return registers
            
    def _stream_write_xml_to_csv(self, file_path: str, csv_path: str, skip_fields: bool, skip_placeholders: bool):
        """Stream-parse and write directly to CSV without holding registers in memory."""
        def _local(t: str) -> str:
            return t.split('}', 1)[-1] if '}' in t else t
        fieldnames = [
            'Register', 'Map', 'Block', 'Absolute Address', 'Offset', 'Size (bits)', 
            'Access', 'Field', 'Bit Range', 'Field Access', 'Reset Value', 'Description', 'Details'
        ]
        written = 0
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            self._status("Streaming parse & write...")
            context = ET.iterparse(file_path, events=("start","end"))
            map_name = ''
            block_name = ''
            base_addr = '0x0'
            current_elem_stack = []
            for event, elem in context:
                tag = _local(elem.tag)
                if event == 'start':
                    current_elem_stack.append(tag)
                    if tag == 'memoryMap':
                        map_name = ''
                    elif tag == 'addressBlock':
                        block_name = ''
                        base_addr = '0x0'
                elif event == 'end':
                    parent_tag = current_elem_stack[-2] if len(current_elem_stack) >= 2 else None
                    if tag == 'name' and parent_tag == 'memoryMap' and elem.text:
                        map_name = elem.text.strip()
                    elif tag == 'name' and parent_tag == 'addressBlock' and elem.text:
                        block_name = elem.text.strip()
                    elif tag == 'baseAddress' and parent_tag == 'addressBlock' and elem.text:
                        base_addr = elem.text.strip()
                    elif tag == 'register':
                        rname = 'Unnamed Register'
                        roffset = '0x0'
                        rsize = '32'
                        racc = 'read-write'
                        rdesc = ''
                        for ch in list(elem):
                            ct = _local(ch.tag)
                            if ch.text is None:
                                continue
                            txt = ch.text.strip()
                            if ct == 'name':
                                rname = txt
                            elif ct == 'addressOffset':
                                roffset = txt
                            elif ct == 'size':
                                rsize = txt
                            elif ct == 'access':
                                racc = txt
                            elif ct == 'description':
                                rdesc = txt
                        block_addr_int = self.parse_number(base_addr, 0)
                        reg_addr_int = self.parse_number(roffset, 0)
                        abs_addr = f"0x{block_addr_int + reg_addr_int:X}"
                        wrote_reg = False
                        # Detect if this register actually has any <field> descendants
                        any_field_detected = False
                        for field in elem.iter():
                            if field is elem:
                                continue
                            if _local(field.tag) == 'field':
                                any_field_detected = True
                                break
                        # Skip placeholder if requested
                        if skip_placeholders and ((not rname or rname == 'Unnamed Register') and not any_field_detected):
                            elem.clear()
                            if current_elem_stack:
                                current_elem_stack.pop()
                            continue
                        if skip_fields:
                            details_txt = self._compose_details_legacy_inline(
                                rname, abs_addr, f"0x{reg_addr_int:X}", rsize, str(racc).upper(), '', '', '', '', rdesc
                            )
                            writer.writerow({
                                'Register': rname,
                                'Map': map_name,
                                'Block': block_name,
                                'Absolute Address': abs_addr,
                                'Offset': f"0x{reg_addr_int:X}",
                                'Size (bits)': rsize,
                                'Access': str(racc).upper(),
                                'Description': rdesc,
                                'Details': details_txt
                            })
                            wrote_reg = True
                            written += 1
                        if not skip_fields:
                            any_field = False
                            for field in elem.iter():
                                if field is elem or _local(field.tag) != 'field':
                                    continue
                                any_field = True
                                fname = ''
                                fbo = '0'
                                fbw = '1'
                                facc = racc
                                fdesc = ''
                                freset = ''
                                for c2 in list(field):
                                    ct = _local(c2.tag)
                                    if c2.text is None:
                                        continue
                                    t2 = c2.text.strip()
                                    if ct == 'name':
                                        fname = t2
                                    elif ct == 'bitOffset':
                                        fbo = t2
                                    elif ct == 'bitWidth':
                                        fbw = t2
                                    elif ct == 'access':
                                        facc = t2
                                    elif ct == 'description':
                                        fdesc = t2
                                for d in field.iter():
                                    if d is field:
                                        continue
                                    if _local(d.tag) == 'value' and d.text:
                                        rv = d.text.strip().strip("'")
                                        if rv.lower().startswith('h'):
                                            rv = rv[1:]
                                        freset = rv
                                        break
                                try:
                                    bit_range = f"[{int(fbo)+int(fbw)-1}:{fbo}]"
                                except Exception:
                                    bit_range = f"[{fbo}]"
                                details_txt = self._compose_details_legacy_inline(
                                    rname, abs_addr, f"0x{reg_addr_int:X}", rsize, str(racc).upper(),
                                    fname or 'Unnamed Field', bit_range, str(facc).upper(), freset or '0', fdesc
                                )
                                writer.writerow({
                                    'Register': rname,
                                    'Map': map_name,
                                    'Block': block_name,
                                    'Absolute Address': abs_addr,
                                    'Offset': f"0x{reg_addr_int:X}",
                                    'Size (bits)': rsize,
                                    'Access': str(racc).upper(),
                                    'Field': fname or 'Unnamed Field',
                                    'Bit Range': bit_range,
                                    'Field Access': str(facc).upper(),
                                    'Reset Value': freset or '0',
                                    'Description': fdesc,
                                    'Details': details_txt
                                })
                                written += 1
                            if not any_field and not wrote_reg:
                                writer.writerow({
                                    'Register': rname,
                                    'Map': map_name,
                                    'Block': block_name,
                                    'Absolute Address': abs_addr,
                                    'Offset': f"0x{reg_addr_int:X}",
                                    'Size (bits)': rsize,
                                    'Access': str(racc).upper(),
                                    'Description': rdesc
                                })
                                written += 1
                        elem.clear()
                    if current_elem_stack:
                        current_elem_stack.pop()
                    if written and written % 500 == 0:
                        self._status(f"Written {written} rows...")

    def _parallel_convert_to_csv(self, file_path: str, csv_path: str, skip_fields: bool, skip_placeholders: bool):
        """Parallel conversion by memory map: pre-parse and process maps in threads, then merge files."""
        import tempfile, os
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def _local(t: str) -> str:
            return t.split('}', 1)[-1] if '}' in t else t
        self._status("Scanning memory maps for parallel conversion...")
        # Buffered parse to locate memory maps
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if '&lt;' in content or '&gt;' in content or '&amp;' in content:
            content = html.unescape(content)
        if '&' in content and '&amp;' not in content:
            content = content.replace('&', '&amp;')
        root = ET.fromstring(content)
        maps = [el for el in root.iter() if _local(el.tag) == 'memoryMap']
        fieldnames = [
            'Register', 'Map', 'Block', 'Absolute Address', 'Offset', 'Size (bits)', 
            'Access', 'Field', 'Bit Range', 'Field Access', 'Reset Value', 'Description', 'Details'
        ]
        def process_map(mem_map):
            tf = tempfile.NamedTemporaryFile('w', delete=False, newline='', encoding='utf-8')
            w = csv.DictWriter(tf, fieldnames=fieldnames)
            w.writeheader()
            map_name = ''
            for ch in list(mem_map):
                if _local(ch.tag) == 'name' and ch.text:
                    map_name = ch.text.strip()
                    break
            for block in mem_map.iter():
                if _local(block.tag) != 'addressBlock':
                    continue
                block_name = ''
                base_addr = '0x0'
                for e in list(block):
                    t = _local(e.tag)
                    if t == 'name' and e.text:
                        block_name = e.text.strip()
                    elif t == 'baseAddress' and e.text:
                        base_addr = e.text.strip()
                for reg in block.iter():
                    if _local(reg.tag) != 'register':
                        continue
                    rname = 'Unnamed Register'
                    roffset = '0x0'
                    rsize = '32'
                    racc = 'read-write'
                    rdesc = ''
                    for c in list(reg):
                        tt = _local(c.tag)
                        if c.text is None:
                            continue
                        tx = c.text.strip()
                        if tt == 'name': rname = tx
                        elif tt == 'addressOffset': roffset = tx
                        elif tt == 'size': rsize = tx
                        elif tt == 'access': racc = tx
                        elif tt == 'description': rdesc = tx
                    block_addr_int = self.parse_number(base_addr, 0)
                    reg_addr_int = self.parse_number(roffset, 0)
                    abs_addr = f"0x{block_addr_int + reg_addr_int:X}"
                    wrote_reg = False
                    # Scan for any field
                    any_field_detected = False
                    for field in reg.iter():
                        if _local(field.tag) == 'field':
                            any_field_detected = True
                            break
                    if skip_placeholders and ((not rname or rname == 'Unnamed Register') and not any_field_detected):
                        continue
                    if skip_fields:
                        details_txt = self._compose_details_legacy_inline(
                            rname, abs_addr, f"0x{reg_addr_int:X}", rsize, str(racc).upper(), '', '', '', '', rdesc
                        )
                        w.writerow({
                            'Register': rname, 'Map': map_name, 'Block': block_name,
                            'Absolute Address': abs_addr, 'Offset': f"0x{reg_addr_int:X}",
                            'Size (bits)': rsize, 'Access': str(racc).upper(), 'Description': rdesc,
                            'Details': details_txt
                        })
                        wrote_reg = True
                    if not skip_fields:
                        any_field = False
                        for field in reg.iter():
                            if _local(field.tag) != 'field':
                                continue
                            any_field = True
                            fname = ''
                            fbo = '0'
                            fbw = '1'
                            facc = racc
                            fdesc = ''
                            freset = ''
                            for c2 in list(field):
                                tt = _local(c2.tag)
                                if c2.text is None:
                                    continue
                                tx2 = c2.text.strip()
                                if tt == 'name': fname = tx2
                                elif tt == 'bitOffset': fbo = tx2
                                elif tt == 'bitWidth': fbw = tx2
                                elif tt == 'access': facc = tx2
                                elif tt == 'description': fdesc = tx2
                            for d in field.iter():
                                if _local(d.tag) == 'value' and d.text:
                                    rv = d.text.strip().strip("'")
                                    if rv.lower().startswith('h'):
                                        rv = rv[1:]
                                    freset = rv
                                    break
                            try:
                                bit_range = f"[{int(fbo)+int(fbw)-1}:{fbo}]"
                            except Exception:
                                bit_range = f"[{fbo}]"
                            details_txt = self._compose_details_legacy_inline(
                                rname, abs_addr, f"0x{reg_addr_int:X}", rsize, str(racc).upper(),
                                fname or 'Unnamed Field', bit_range, str(facc).upper(), freset or '0', fdesc
                            )
                            w.writerow({
                                'Register': rname, 'Map': map_name, 'Block': block_name,
                                'Absolute Address': abs_addr, 'Offset': f"0x{reg_addr_int:X}",
                                'Size (bits)': rsize, 'Access': str(racc).upper(),
                                'Field': fname or 'Unnamed Field', 'Bit Range': bit_range,
                                'Field Access': str(facc).upper(), 'Reset Value': freset or '0',
                                'Description': fdesc, 'Details': details_txt
                            })
                        if not any_field and not wrote_reg:
                            details_txt = self._compose_details_legacy_inline(
                                rname, abs_addr, f"0x{reg_addr_int:X}", rsize, str(racc).upper(), '', '', '', '', rdesc
                            )
                            w.writerow({
                                'Register': rname, 'Map': map_name, 'Block': block_name,
                                'Absolute Address': abs_addr, 'Offset': f"0x{reg_addr_int:X}",
                                'Size (bits)': rsize, 'Access': str(racc).upper(), 'Description': rdesc,
                                'Details': details_txt
                            })
            tf.close()
            return tf.name
        tmp_paths = []
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor() as ex:
            futures = [ex.submit(process_map, m) for m in maps]
            for fut in as_completed(futures):
                tmp_paths.append(fut.result())
        with open(csv_path, 'w', newline='', encoding='utf-8') as out:
            wout = csv.DictWriter(out, fieldnames=fieldnames)
            wout.writeheader()
            for p in tmp_paths:
                with open(p, 'r', encoding='utf-8') as inp:
                    first = True
                    for line in inp:
                        if first:
                            first = False
                            continue
                        out.write(line)
                try:
                    os.remove(p)
                except Exception:
                    pass

    def load_regmap_csv(self):
        """Load a previously saved regmap CSV and rebuild the tree view from it."""
        try:
            csv_path = filedialog.askopenfilename(
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Open Regmap CSV"
            )
            if not csv_path:
                return
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = [h.strip() for h in (reader.fieldnames or [])]
                # Detect SNPS enriched schema
                is_snps = {'Module','Register','Field','BitRange','Address'}.issubset(set(fieldnames))
                # Clear tree and meta
                try:
                    self.tree.delete(*self.tree.get_children())
                except Exception:
                    pass
                self._node_meta = {}
                self.registers = []

                if is_snps:
                    # Build Module -> Register -> Field tree using enriched metadata
                    modules = {}
                    rows = list(reader)
                    for row in rows:
                        mod = (row.get('Module') or '').strip() or 'ROOT'
                        reg = (row.get('Register') or '').strip()
                        fld = (row.get('Field') or '').strip()
                        br = (row.get('BitRange') or row.get('Bit Range') or '').strip().strip('[]')
                        addr = (row.get('Address') or '').strip()
                        reset = (row.get('Reset') or row.get('Reset Value') or '').strip()
                        access = (row.get('Access') or row.get('Field Access') or '').strip()
                        desc = (row.get('Description') or '').strip()
                        alias = (row.get('Alias') or '').strip()
                        full = (row.get('FullPath') or row.get('Full') or '').strip()
                        # Register-level computed columns (if any)
                        reg_bits = row.get('RegWidthBits', '').strip()
                        reg_bytes = row.get('RegSizeBytes', '').strip()
                        addr_end_hex = row.get('AddrEndHex', '').strip()
                        # Group
                        m = modules.setdefault(mod, {})
                        r = m.setdefault(reg, {
                            'address': addr,
                            'reg_width_bits': reg_bits,
                            'reg_size_bytes': reg_bytes,
                            'addr_end_hex': addr_end_hex,
                            'fields': []
                        })
                        r['fields'].append({
                            'field': fld,
                            'bitrange': br,
                            'address': addr,
                            'reset': reset,
                            'access': access,
                            'desc': desc,
                            'alias': alias,
                            'full': full,
                        })
                    # Populate tree
                    for module, regs in modules.items():
                        mid = self.tree.insert('', 'end', text=f"Module {module}", open=True)
                        self._node_meta[mid] = {'mode': 'snps', 'kind': 'module', 'name': module}
                        for reg, info in regs.items():
                            _tags = ['register']
                            try:
                                if self._has_note_for({'name': reg, 'block': module, 'map': ''}):
                                    _tags.append('has_note')
                            except Exception:
                                pass
                            rid = self.tree.insert(mid, 'end', text=f"Register {reg} @ {info.get('address','')}", open=False, tags=tuple(_tags))
                            self._node_meta[rid] = {
                                'mode': 'snps', 'kind': 'register', 'name': reg,
                                'address': info.get('address',''),
                                'reg_width_bits': info.get('reg_width_bits',''),
                                'reg_size_bytes': info.get('reg_size_bytes',''),
                                'addr_end_hex': info.get('addr_end_hex','')
                            }
                            for ent in info['fields']:
                                label = ent['field'] or ent['full']
                                txt = f"Field {label} [{ent['bitrange']}] {ent['access']} reset={ent['reset']}"
                                fid = self.tree.insert(rid, 'end', text=txt, open=False)
                                meta = ent.copy(); meta.update({'mode':'snps','kind':'field','module':module,'register':reg})
                                self._node_meta[fid] = meta
                    # Also synthesize self.registers to support the legacy search pipeline
                    synthesized = []
                    def _parse_bitrange_to_bw(br: str):
                        s = (br or '').strip().strip('[]')
                        if not s:
                            return ('0','1')
                        if ':' in s:
                            try:
                                hi, lo = [int(x) for x in s.split(':',1)]
                                return (str(lo), str(max(1, hi-lo+1)))
                            except Exception:
                                return ('0','1')
                        try:
                            idx = int(s, 0)
                        except Exception:
                            idx = 0
                        return (str(idx), '1')
                    for module, regs in modules.items():
                        for reg, info in regs.items():
                            reg_rec = {
                                'name': reg,
                                'absolute_address': info.get('address',''),
                                'offset': info.get('address',''),
                                'size': info.get('reg_width_bits',''),
                                'access': '',
                                'description': '',
                                'map': '',
                                'block': module,
                                'fields': []
                            }
                            for ent in info['fields']:
                                bo, bw = _parse_bitrange_to_bw(ent.get('bitrange',''))
                                reg_rec['fields'].append({
                                    'name': ent.get('field',''),
                                    'bit_offset': bo,
                                    'bit_width': bw,
                                    'access': ent.get('access',''),
                                    'reset_value': ent.get('reset',''),
                                    'description': ent.get('desc','')
                                })
                            synthesized.append(reg_rec)
                    self.registers = synthesized
                    self.matched_registers = None
                    # Save SNPS modules for restoring tree after searches
                    self._snps_modules = modules
                    self._set_details_content(f"Loaded SNPS CSV: modules={len(modules)} registers={len(self.registers)}")
                
                
                else:
                    # Legacy/standard CSV path. Parse rows then rebuild SNPS-style tree so layout matches Module→Register→Field
                    regs_map = {}
                    f.seek(0); reader = csv.DictReader(f)
                    for row in reader:
                        reg_name = row.get('Register', '').strip()
                        if not reg_name:
                            continue
                        key = reg_name
                        if key not in regs_map:
                            regs_map[key] = {
                                'name': reg_name,
                                'absolute_address': row.get('Absolute Address', ''),
                                'offset': row.get('Offset', ''),
                                'size': row.get('Size (bits)', ''),
                                'access': row.get('Access', ''),
                                'description': row.get('Description', ''),
                                'fields': []
                            }
                        fname = row.get('Field', '').strip()
                        if fname:
                            bit_range = row.get('Bit Range', '').strip().strip('[]')
                            bo, bw = '0', '1'
                            if ':' in bit_range:
                                try:
                                    hi, lo = [int(x) for x in bit_range.split(':')]
                                    bo = str(lo)
                                    bw = str(hi - lo + 1)
                                except Exception:
                                    pass
                            regs_map[key]['fields'].append({
                                'name': fname,
                                'bit_offset': bo,
                                'bit_width': bw,
                                'access': row.get('Field Access', row.get('Access', '')),
                                'reset_value': row.get('Reset Value', '0'),
                                'description': row.get('Description', '')
                            })
                    # Build modules snapshot treating Block as Module
                    modules = {}
                    for reg in regs_map.values():
                        module = (reg.get('block','') or 'ROOT')
                        rname = reg.get('name','')
                        m = modules.setdefault(module, {})
                        # Compute reg width from fields when size missing
                        max_width = 0
                        max_msb = -1
                        fields_list = []
                        for f in reg.get('fields', []):
                            try:
                                bo = int(str(f.get('bit_offset','0')), 0)
                            except Exception:
                                bo = 0
                            try:
                                bw = int(str(f.get('bit_width','1')), 0)
                            except Exception:
                                bw = 1
                            hi = bo + max(1, bw) - 1
                            max_msb = max(max_msb, hi)
                            max_width = max(max_width, max(1, bw))
                            br = f"{hi}:{bo}"
                            fields_list.append({
                                'field': f.get('name',''),
                                'bitrange': br,
                                'address': reg.get('absolute_address',''),
                                'reset': f.get('reset_value',''),
                                'access': f.get('access',''),
                                'desc': f.get('description',''),
                                'alias': '',
                                'full': ''
                            })
                        if max_msb >= 0 and (max_msb + 1) > max_width:
                            max_width = max_msb + 1
                        reg_bits = reg.get('size','') or (str(max_width) if max_width else '')
                        if reg_bits:
                            try:
                                bits = int(reg_bits)
                                reg_bytes = 1 if bits <= 8 else 2 if bits <= 16 else 4 if bits <= 32 else 8 if bits <= 64 else (bits + 7)//8
                            except Exception:
                                reg_bytes = ''
                        else:
                            reg_bytes = ''
                        # Compute end address
                        try:
                            addr_int = int(str(reg.get('absolute_address','')), 16)
                            addr_end_int = addr_int + (int(reg_bytes) if reg_bytes else 1) - 1
                            addr_end_hex = f"0x{addr_end_int:08X}"
                        except Exception:
                            addr_end_hex = ''
                        m[rname] = {
                            'address': reg.get('absolute_address',''),
                            'reg_width_bits': reg_bits,
                            'reg_size_bytes': reg_bytes,
                            'addr_end_hex': addr_end_hex,
                            'fields': fields_list
                        }
                    # Save and render SNPS-style tree
                    self._snps_modules = modules
                    self._rebuild_snps_tree(modules)
                    # Also keep a synthesized registers list for search pipeline
                    self.registers = list(regs_map.values())
                    self.matched_registers = None
                self._set_current_path(csv_path)
                self._status("Loaded CSV")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
    def _try_load_addressmap(self, root) -> bool:
        """Attempt to parse vendor Addressmap format.
        Expected shape:
        <Addressmap>
          <BlockTag Name="foo" Offset="0x..." ...>
            <Register Name="..." Offset="0x..." Size="32" Access="rw" Description="...">
              <Field Name="..." BitOffset=".." BitWidth=".." Access=".." ResetValue=".." Description=".."/>
            </Register>
          </BlockTag>
        </Addressmap>
        We don't depend on exact tag names; we inspect attributes instead.
        """
        def _attr(elem, key, default=''):
            return (elem.attrib.get(key) or default)

        # Clear current view
        try:
            self.tree.delete(*self.tree.get_children())
        except Exception:
            pass
        self.registers = []

        # Treat the top-level tag name as the map name
        map_name = 'Addressmap'
        try:
            map_node = self.tree.insert('', 'end', text=map_name, open=True, tags=('memory_map',))
        except Exception:
            map_node = ''

        # Determine blocks: prefer explicit <Group> nodes; otherwise use direct children
        groups = list(root.findall('.//Group'))
        block_elems = groups if groups else list(root)
        # Each block element is treated as an address block
        for block in block_elems:
            block_tag = block.tag
            block_name = _attr(block, 'Name', block_tag)
            block_offset = _attr(block, 'Offset', '0x0')
            # Normalize base address (strip underscores like 0x10_0000)
            block_offset_norm = block_offset.replace('_', '')
            block_offset_val = self.parse_number(block_offset_norm, 0)
            block_desc_text = (block.text or '').strip()
            try:
                block_node = self.tree.insert(
                    map_node, 'end', text=block_name,
                    values=(f"0x{block_offset_val:X}", '', ''), tags=('address_block',)
                )
            except Exception:
                block_node = map_node

            # Registers: search within this block for elements with Name and (Offset or AddressOffset)
            regs_in_block = list(block.findall('.//Register')) if block.find('.//Register') is not None else list(block)
            for reg in regs_in_block:
                if not isinstance(reg.tag, str):
                    continue
                if 'Name' not in reg.attrib and 'name' not in reg.attrib:
                    # skip non-register elements in the general list case
                    if reg.tag.lower() != 'register':
                        continue
                reg_name = _attr(reg, 'Name', _attr(reg, 'name', 'Unnamed Register'))
                reg_off = _attr(reg, 'Offset', _attr(reg, 'AddressOffset', '0x0')).replace('_', '')
                # Some formats use SizeInBits for registers
                reg_size = _attr(reg, 'Size', _attr(reg, 'SizeInBits', '32'))
                reg_access = _attr(reg, 'Access', 'read-write')
                # Use inner text as description if provided
                reg_desc_text = (reg.text or '').strip()
                reg_desc = _attr(reg, 'Description', reg_desc_text)

                reg_offset_val = self.parse_number(reg_off, 0)
                abs_addr = f"0x{(block_offset_val + reg_offset_val):X}"
                reg_rec = {
                    'name': reg_name,
                    'offset': reg_off or '0x0',
                    'size': reg_size,
                    'access': reg_access,
                    'absolute_address': abs_addr,
                    'description': reg_desc,
                    'fields': [],
                    'block': block_name,
                    'map': map_name,
                    'block_description': block_desc_text,
                }
                try:
                    reg_node = self.tree.insert(
                        block_node, 'end', text=reg_name,
                        values=(f"0x{reg_offset_val:X}", reg_size, reg_access), tags=('register',)
                    )
                except Exception:
                    reg_node = block_node

                # Fields under register
                for fld in list(reg):
                    if not isinstance(fld.tag, str):
                        continue
                    fname = _attr(fld, 'Name', _attr(fld, 'name', ''))
                    if not fname:
                        continue
                    # Some formats use Position/Size for fields
                    fbo = _attr(fld, 'BitOffset', _attr(fld, 'bitOffset', _attr(fld, 'Position', '0')))
                    fbw = _attr(fld, 'BitWidth', _attr(fld, 'bitWidth', _attr(fld, 'Size', '1')))
                    facc = _attr(fld, 'Access', _attr(fld, 'access', reg_access))
                    # Prefer attribute description; fallback to inner text lines
                    fdesc_text = (fld.text or '').strip()
                    fdesc = _attr(fld, 'Description', _attr(fld, 'description', fdesc_text))
                    frst = _attr(fld, 'ResetValue', _attr(fld, 'resetValue', _attr(fld, 'value', '0')))
                    # Normalize hex like 0x1_2 to 0x12 if present
                    frst = frst.replace('_', '')
                    reg_rec['fields'].append({
                        'name': fname,
                        'bit_offset': fbo,
                        'bit_width': fbw,
                        'access': facc,
                        'reset_value': frst,
                        'description': fdesc,
                    })
                    # Add to tree
                    try:
                        hi = int(fbo) + int(fbw) - 1
                        bits = f"[{hi}:{fbo}]"
                    except Exception:
                        bits = f"[{fbo}]"
                    self.tree.insert(
                        reg_node, 'end',
                        text=f"{fname} {bits}",
                        values=(frst, facc, ''), tags=('field',)
                    )

                self.registers.append(reg_rec)

        # Bind selection and finish
        try:
            self.tree.bind('<<TreeviewSelect>>', self.show_register_details)
        except Exception:
            pass
        # Ensure status and selection
        self._status(f"Loaded Addressmap with {len(self.registers)} registers")
        try:
            self._focus_first_match(self.registers)
        except Exception:
            pass
        return True

if __name__ == "__main__":
    root = tk.Tk()
    app = XMLViewer(root)
    root.mainloop()
