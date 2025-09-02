"""
Image Browser Application with Excel-like File List

A tkinter-based image browser that displays images in a grid layout and files in an Excel-like table.

Changelog:
### [2025-01-19] added up/down keys to nevigate through the file list table and load the new file 
- add button to rename all files based on the field values

### [2025-01-17]Changed
- Added auto column width adjustment for file list table
- Set default sort order to sort by date modified (newest first)

## [2025-01-14] - Image Browser Update
### Added
- Added "Move Files" functionality to move selected files to another folder
  - Support for moving multiple files at once using table's multiplerowlist
  - File overwrite confirmation for each file
  - Automatic UI update after moving files
  - Success message showing number of files moved
- Added "Delete Files" button to toolbar for multi-file deletion
  - Support for deleting multiple selected files at once
  - Single confirmation dialog showing number of files to delete
  - Individual error handling for each file
  - Success message showing number of files deleted

### Fixed
- Fixed issue with filtered table where row selection would load incorrect images
- Added 'File Path' column to maintain accurate image-to-row mapping during filtering
- Fixed image clearing when moving files that are displayed in grid cells
- Improved delete functionality to handle multiple files and provide better feedback

### Changed
- Modified [update_file_dataframe](cci:1://file:///f:/taurus-sdk-python/scripts/scratchpad/image_browser%20-%20multi-cells2.py:188:4-221:38) to include full file path in DataFrame
- Updated [on_table_select](cci:1://file:///f:/taurus-sdk-python/scripts/scratchpad/image_browser%20-%20multi-cells2.py:228:4-259:33) to use filtered DataFrame view for correct row selection
- Enhanced table selection logic to handle filtered and sorted views properly
- Updated Delete key binding to use new multi-file delete functionality

### Technical Details
- Added 'File Path' column to store absolute paths for direct file access
- Now using `table.model.df` to access the currently displayed (filtered) data
- Improved error handling and debugging information in table selection
- Added proper image cleanup in grid cells when moving or deleting files
- Enhanced error handling to provide specific feedback for each file operation

- 2025-01-13:
  - Added filename field columns (split by underscore)
  - Improved browse folder behavior with proper frame cleanup
  - Added dynamic column creation based on filename fields
  - Fixed filter functionality to work with all columns
  - Added horizontal scrollbar for wide tables
  - Added debug logging for directory changes
  - Set default directory to validation_Rx_results
  - Improved toolbar organization with better controls

- 2024-01-13:
  - Fixed layout switching to maintain panel visibility
  - Added proper frame hierarchy with minimum sizes
  - Improved panel size preservation during layout switches
  - Fixed cell frame visibility and image scaling
  - Added dynamic cell size adjustment based on image dimensions
  - Added white background for image cells
  - Improved selection highlighting with thicker borders

- 2024-01-12:
  - Initial implementation
  - Basic grid layout with adjustable size
  - File browser with sorting capabilities
  - Image display with aspect ratio preservation
  - Drag and drop support
  - Layout switching between vertical and horizontal
  - Copy/paste support
  - File operations (delete, rename)
  - Image information display

Features:
- Grid-based image layout with adjustable size (up to 10x10)
- File browser with:
  - Sorting by name, date, size, and filename fields
  - Dynamic columns based on filename structure
  - Filter functionality across all fields
  - Horizontal scrolling for many fields
- Image preview in grid cells
- Vertical and horizontal layout options
- Directory selection
- File filtering
- Keyboard shortcuts (Delete, Ctrl+C)
"""

import os
import sys
import json
# Add custom pandastable path to sys.path BEFORE importing pandastable
# custom_pandastable_path = r"C:\Users\juesh\OneDrive\Documents\windsurf\pandastable\pandastable"
# # custom_pandastable_path = r"C:\Users\JueShi\OneDrive - Astera Labs, Inc\Documents\windsurf\pandastable\pandastable"
# if os.path.exists(custom_pandastable_path):
#     # Insert at the beginning of sys.path to prioritize this version
#     sys.path.insert(0, custom_pandastable_path)
#     print(f"Using custom pandastable from: {custom_pandastable_path}")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
try:
    # For screen capture on Windows
    from PIL import ImageGrab  # type: ignore
except Exception:
    ImageGrab = None  # type: ignore
import pandas as pd
import subprocess
import io
from typing import Optional
import time
import re
import hashlib
import tempfile
# Load environment variables from .env if available (non-fatal if python-dotenv missing)
try:
    from dotenv import load_dotenv  # type: ignore
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _env_path = os.path.join(_project_root, '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        # Fallback to default search in parent directories
        load_dotenv()
except Exception:
    # Proceed without .env if package not installed; runtime will prompt for API key when needed
    pass
# Support running the example directly from the repo by adding project root to sys.path if needed
try:
    from pandastable import Table, TableModel
except ModuleNotFoundError:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        from pandastable import Table, TableModel
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "Could not import 'pandastable'. Install it (pip install pandastable) "
            "or run this script from within the repository so that the local package is on sys.path."
        ) from e
from datetime import datetime
import shutil
import traceback
import logging


# Configure logging with both file and console output
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'mermaid_debug.log')

# File handler for debug logs
file_handler = logging.FileHandler(log_file, mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)

# Console handler for warnings and above
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(log_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers = []  # Remove any existing handlers
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Module-specific logger for Mermaid
mermaid_logger = logging.getLogger('mermaid')
mermaid_logger.setLevel(logging.DEBUG)

# Log startup information
logging.info("=== Starting Image Browser with Mermaid Debugging ===")
logging.info(f"Logging to: {log_file}")
logging.info(f"Python: {sys.version}")
logging.info(f"Working directory: {os.getcwd()}")

# Log environment variables that might affect Mermaid
for var in ['PATH', 'APPDATA', 'NVM_HOME', 'NVM_SYMLINK']:
    if var in os.environ:
        logging.debug(f"Env {var}: {os.environ[var]}")

# Configure Mermaid CLI discovery logging
logging.info("Configuring Mermaid CLI discovery...")

# Add a custom exception hook
def custom_exception_handler(exctype, value, traceback_obj):
    logging.error("Uncaught exception", exc_info=(exctype, value, traceback_obj))
    sys.__excepthook__(exctype, value, traceback_obj)

sys.excepthook = custom_exception_handler

class ImageBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Image Browser")
        self.state('zoomed')
        
        # Initialize variables
        self.current_image = None
        self.image_label = None
        self.grid_rows = 1
        self.grid_cols = 1
        self.cell_width = 200
        self.cell_height = 200
        self.is_horizontal = False  # Start with vertical layout
        self.filter_text = tk.StringVar()
        self.filter_text.trace_add("write", self.filter_images)
        self.selected_cell = None  # Initialize selected_cell
        self.grid_cells = []  # Initialize grid_cells list
        
        # Variables for image zooming and panning
        self.zoom_level = 1.0  # Default zoom level (1.0 = 100%)
        self.original_image = None  # Store the original PIL Image object
        self.current_image_path = None  # Path to the currently displayed image
        
        # Variables for panning
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.crop_x = 0  # Current crop position (for panning)
        self.crop_y = 0
        
        # Variables for annotations
        self.annotations = {}  # Dictionary to store annotations by image path
        self.current_annotation = None  # Current annotation being drawn
        self.annotation_type = "text"  # Default annotation type: text, arrow, rectangle, circle
        self.annotation_color = "red"  # Default annotation color
        self.annotation_mode = False  # Whether annotation mode is active
        self.annotation_start_x = 0  # Starting x position for shape annotations
        self.annotation_start_y = 0  # Starting y position for shape annotations
        
        # Variables for annotation selection and movement
        self.selected_annotation = None  # Currently selected annotation
        self.selection_mode = False  # Whether in selection mode
        self.is_moving_annotation = False  # Whether currently moving an annotation
        self.move_start_x = 0  # Starting x position for annotation movement
        self.move_start_y = 0  # Starting y position for annotation movement
        
        # Add include_subfolders variable
        self.include_subfolders = tk.BooleanVar(value=False)

        # Markdown preview/chat state
        self.md_current_path = os.path.join(os.getcwd(), "image_explanation_from_gemini.md")
        self.translate_to_chinese = False  # Track translation state
        # Mermaid cache directory for rendered diagrams
        try:
            self._mermaid_cache_dir = os.path.join(os.path.abspath(os.getcwd()), ".mermaid_cache")
            os.makedirs(self._mermaid_cache_dir, exist_ok=True)
        except Exception:
            self._mermaid_cache_dir = None
        # Discover Mermaid CLI command
        try:
            self._mmdc_cmd = self._discover_mmdc()
        except Exception:
            self._mmdc_cmd = None
        
        # Initialize recent folders list (max 10)
        self.recent_folders = []
        self.max_recent_folders = 10
        
        # Try to load recent folders from file
        self.load_recent_folders()
        
        # Set default directory to Pictures folder
        pictures_dir = r"C:\Users\juesh\OneDrive\Pictures"
        if os.path.exists(pictures_dir):
            self.current_directory = pictures_dir
        else:
            self.current_directory = os.path.dirname(os.path.abspath(__file__))
            
        # Get initial list of image files
        self.update_image_files()
        
        # Calculate max fields for the current directory
        self.max_fields = self.get_max_fields()
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create and pack the toolbar
        self.toolbar = ttk.Frame(self.main_container)
        self.toolbar.pack(fill="x", padx=5, pady=5)
        self.setup_toolbar()
        
        # Create and pack the panels
        self.setup_panels()
        
        # Create the file browser and grid
        self.setup_file_browser()
        self.create_grid()
        
        # Bind keyboard shortcuts
        self.bind('<Delete>', self.delete_selected)
        self.bind('<Control-c>', self._copy_button_click)
        # PDF page navigation
        try:
            self.bind(']', self.next_pdf_page)
            self.bind('[', self.prev_pdf_page)
        except Exception:
            pass

    def format_size(self, size):
        # Convert size to human readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_date(self, timestamp):
        # Convert timestamp to readable format
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")

    def setup_panels(self):
        """Setup the main panels with proper orientation"""
        # Create main paned window with proper orientation
        orient = tk.HORIZONTAL if self.is_horizontal else tk.VERTICAL
        self.paned = ttk.PanedWindow(self.main_container, orient=orient)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Create file browser frame
        self.file_frame = ttk.Frame(self.paned)
        self.paned.add(self.file_frame, weight=1)
        try:
            # Ensure file pane can't collapse to zero
            self.paned.paneconfigure(self.file_frame, minsize=200)
        except Exception:
            pass

        # Create grid container frame
        self.grid_container = ttk.Frame(self.paned)
        self.paned.add(self.grid_container, weight=2)
        try:
            # Ensure grid pane can't collapse to zero
            self.paned.paneconfigure(self.grid_container, minsize=200)
        except Exception:
            pass

        # Create a notebook with two tabs: Images and Markdown Preview/Chat
        self.notebook = ttk.Notebook(self.grid_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Images tab
        self.images_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.images_tab, text="Images")

        # Grid frame inside Images tab
        self.grid_frame = ttk.Frame(self.images_tab)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Recreate PDF navigation widgets so they belong to the new images_tab
        try:
            # Destroy old nav frame if it exists (from previous layout)
            if hasattr(self, 'pdf_nav_frame') and self.pdf_nav_frame.winfo_exists():
                try:
                    self.pdf_nav_frame.destroy()
                except Exception:
                    pass
            self.pdf_nav_initialized = False
            self._ensure_pdf_nav_widgets()
            # After creating widgets, refresh state for current selection
            try:
                if getattr(self, 'selected_cell', None):
                    r, c = self.selected_cell
                    frame, label = self.grid_cells[r][c]
                    self._update_pdf_controls(label)
                else:
                    self._hide_pdf_controls()
            except Exception:
                self._hide_pdf_controls()
        except Exception:
            pass

        # Markdown Preview/Chat tab
        self.md_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.md_tab, text="Markdown Preview / Chat")
        self.setup_markdown_tab()

        # Set minimum sizes to prevent collapse
        if self.is_horizontal:
            self.file_frame.configure(width=400)
            self.grid_container.configure(width=800)
        else:
            self.file_frame.configure(height=300)
            self.grid_container.configure(height=500)

        # Force geometry update
        self.update_idletasks()
        
        # Set initial sash position
        if self.is_horizontal:
            self.paned.sashpos(0, 400)  # 400 pixels from left
        else:
            self.paned.sashpos(0, 300)  # 300 pixels from top

        # Defer another sash adjustment to ensure visibility after layout settles
        try:
            self.after(100, self._set_initial_sash)
        except Exception:
            pass

    def _set_initial_sash(self):
        """Adjust sash after widgets are realized so both panes are visible."""
        try:
            self.update_idletasks()
            if self.is_horizontal:
                total = self.paned.winfo_width()
                pos = max(200, min(total - 200, int(total * 0.3)))
                self.paned.sashpos(0, pos)
            else:
                total = self.paned.winfo_height()
                pos = max(150, min(total - 150, int(total * 0.35)))
                self.paned.sashpos(0, pos)
        except Exception:
            pass

    def setup_markdown_tab(self):
        """Initialize widgets for the Markdown preview and chat UI."""
        # Top: preview
        preview_frame = ttk.Frame(self.md_tab)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))
        # Keep a reference so we can rebuild the preview widget when needed
        self._md_preview_frame = preview_frame

        # Try HTML markdown preview if tkhtmlview is available; fallback to text
        self.md_use_html = False
        self._md_html_widget = None
        try:
            from tkhtmlview import HTMLScrolledText  # type: ignore
            self._md_html_widget = HTMLScrolledText(preview_frame, html="", width=80)
            self._md_html_widget.pack(fill=tk.BOTH, expand=True)
            self.md_use_html = True
        except Exception:
            # Fallback: raw ScrolledText
            self.md_preview = ScrolledText(preview_frame, wrap=tk.WORD, height=10)
            self.md_preview.pack(fill=tk.BOTH, expand=True)
            self.md_preview.configure(state=tk.DISABLED)

        # Bottom: chat input and controls
        controls = ttk.Frame(self.md_tab)
        controls.pack(fill=tk.X, padx=8, pady=(4, 8))
        self.md_controls_frame = controls

        ttk.Label(controls, text="Chat with Gemini:").pack(side=tk.LEFT)

        # Language selector for chat outputs
        self.chat_lang_var = tk.StringVar(value="English")
        self.chat_lang_combo = ttk.Combobox(
            controls,
            textvariable=self.chat_lang_var,
            width=18,
            state="readonly",
            values=(
                "English",
                "Chinese (Simplified)",
                "Chinese (Traditional)",
                "Japanese",
                "Korean",
                "Spanish",
            ),
        )
        self.chat_lang_combo.pack(side=tk.LEFT, padx=(6, 6))

        self.chat_var = tk.StringVar()
        self.chat_entry = ttk.Entry(controls, textvariable=self.chat_var)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.chat_entry.bind('<Return>', lambda e: self.send_md_chat())

        send_btn = ttk.Button(controls, text="Send", command=self.send_md_chat)
        send_btn.pack(side=tk.LEFT, padx=(0, 6))

        save_btn = ttk.Button(controls, text="Save As .md", command=self.save_markdown_as_new)
        save_btn.pack(side=tk.LEFT, padx=(0, 6))

        clear_btn = ttk.Button(controls, text="Clear", command=self.clear_markdown_content)
        clear_btn.pack(side=tk.LEFT)

        # Copy actions
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        copy_btn = ttk.Button(controls, text="Copy", command=lambda: self.copy_markdown(selection=True))
        copy_btn.pack(side=tk.LEFT)
        copy_all_btn = ttk.Button(controls, text="Copy All", command=lambda: self.copy_markdown(selection=False))
        copy_all_btn.pack(side=tk.LEFT, padx=(6, 0))

        # View mode toggle (enable selectable text preview)
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.md_view_as_text = tk.BooleanVar(value=False)
        view_toggle = ttk.Checkbutton(
            controls,
            text="View as Text",
            variable=self.md_view_as_text,
            command=self.update_markdown_preview,
        )
        view_toggle.pack(side=tk.LEFT)

        # Edit mode toggle and Save button
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.md_edit_mode = tk.BooleanVar(value=False)
        edit_toggle = ttk.Checkbutton(
            controls,
            text="Edit",
            variable=self.md_edit_mode,
            command=self.toggle_md_edit_mode,
        )
        edit_toggle.pack(side=tk.LEFT)

        save_btn_current = ttk.Button(controls, text="Save", command=self.save_markdown_current)
        save_btn_current.pack(side=tk.LEFT, padx=(6, 0))
        
        # Add translation toggle button
        ttk.Separator(controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.translate_btn = ttk.Button(
            controls, 
            text="Translate to Chinese", 
            command=self.toggle_translation
        )
        self.translate_btn.pack(side=tk.LEFT)

        # Bind Ctrl+S globally
        try:
            self.bind('<Control-s>', lambda e: (self.save_markdown_current(), 'break'))
        except Exception:
            pass

        # Load any existing content
        self.update_markdown_preview()

        # Suggestions area (follow-up questions)
        self._md_suggest_frame = ttk.Frame(self.md_tab)
        self._md_suggest_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.render_suggested_questions([])

    def toggle_translation(self):
        """Toggle between English and Chinese translation of markdown content."""
        self.translate_to_chinese = not self.translate_to_chinese
        self.translate_btn.config(
            text="Translate to English" if self.translate_to_chinese 
            else "Translate to Chinese"
        )
        self.update_markdown_preview()
    
    def translate_text(self, text):
        """Translate text between English and Chinese using Google Translate API.
        Preserves Mermaid code blocks during translation.
        
        Args:
            text: The text to translate
            
        Returns:
            str: Translated text with Mermaid blocks preserved, or original text if translation fails
        """
        if not text.strip():
            return text
            
        try:
            import json
            import urllib.parse
            import re
            import requests
            
            # Extract Mermaid code blocks and replace them with placeholders
            mermaid_blocks = []
            def save_mermaid(match):
                block = match.group(0)
                mermaid_blocks.append(block)
                return f'{{{{mermaid_block_{len(mermaid_blocks)-1}}}}}'  # Use double braces for safety
                
            # More flexible pattern to match mermaid code blocks, even with translated text
            mermaid_pattern = r'```\s*(?:mermaid|mermaid\s+[^\n]*|.*?mermaid.*?)\s*\n([\s\S]*?)\n\s*```'
            
            # Replace Mermaid blocks with placeholders
            text_with_placeholders = re.sub(mermaid_pattern, save_mermaid, text, flags=re.IGNORECASE)
            
            # Split text into chunks to handle API limits, being careful with placeholders
            chunk_size = 2000  # Reduced to account for placeholders
            chunks = []
            current_chunk = ""
            
            # Split text into chunks, ensuring we don't split in the middle of a placeholder
            for part in text_with_placeholders.split('\n'):
                # Check if adding this part would exceed chunk size and we're not in the middle of a placeholder
                if (len(current_chunk) + len(part) + 1 > chunk_size and 
                    current_chunk and 
                    not any(f'{{mermaid_block_{i}}}' in current_chunk for i in range(len(mermaid_blocks)))):
                    chunks.append(current_chunk)
                    current_chunk = part
                else:
                    if current_chunk:
                        current_chunk += '\n' + part
                    else:
                        current_chunk = part
            
            if current_chunk:
                chunks.append(current_chunk)
            
            translated_chunks = []
            
            # Translate each chunk
            for chunk in chunks:
                # Skip empty chunks
                if not chunk.strip():
                    translated_chunks.append("")
                    continue
                
                # Skip chunks that only contain placeholders
                if re.match(r'^\s*(?:{{mermaid_block_\d+}}\s*)+$', chunk):
                    translated_chunks.append(chunk)
                    continue
                    
                # Prepare the request
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    'client': 'gtx',
                    'sl': 'en' if self.translate_to_chinese else 'zh-CN',
                    'tl': 'zh-CN' if self.translate_to_chinese else 'en',
                    'dt': 't',
                    'q': chunk
                }
                
                # Make the request
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                if result and isinstance(result, list) and len(result) > 0:
                    # Extract translated text from the response
                    translated_text = ' '.join([item[0] for item in result[0] if item[0]])
                    translated_chunks.append(translated_text)
                else:
                    translated_chunks.append(chunk)  # Fallback to original if parsing fails
            
            # Combine translated chunks
            translated_text = '\n'.join(translated_chunks)
            
            # Restore Mermaid blocks using a more robust replacement
            for i, block in enumerate(mermaid_blocks):
                # Try both uppercase and lowercase variants for backward compatibility
                for variant in [f'{{{{mermaid_block_{i}}}}}', f'{{{{MERMAID_BLOCK_{i}}}}}']:
                    if variant in translated_text:
                        translated_text = translated_text.replace(variant, block, 1)  # Replace one at a time
            
            return translated_text
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            error_msg = f"Error parsing translation response: {str(e)}"
        except Exception as e:
            error_msg = str(e)
            
        logging.error(f"Translation error: {error_msg}")
        return f"[Translation Error: {error_msg}]\n\n{text}"

    def update_markdown_preview(self):
        """Load current markdown file and render preview.
        If Edit mode is on, force text view and keep the text widget editable without overwriting user edits.
        """
        text = ""
        try:
            if self.md_current_path and os.path.isfile(self.md_current_path):
                with open(self.md_current_path, 'r', encoding='utf-8') as f:
                    text = f.read()
        except Exception as e:
            logging.warning(f"Failed to load markdown preview: {e}")

        # Respect 'View as Text' and Edit mode
        editing = bool(getattr(self, 'md_edit_mode', None)) and self.md_edit_mode.get()
        
        # Apply translation if enabled (only when not in edit mode)
        if not editing and text and self.translate_to_chinese:
            text = self.translate_text(text)
        # Detect if backing file path changed since last render; if so, we must refresh even in edit mode
        try:
            path_changed = getattr(self, '_md_last_rendered_path', None) != self.md_current_path
        except Exception:
            path_changed = True
        # Force raw text when editing
        use_html = self.md_use_html and not (hasattr(self, 'md_view_as_text') and self.md_view_as_text.get()) and not editing
        if use_html:
            # Recreate the HTML widget each time to avoid residual/concatenated content
            try:
                from tkhtmlview import HTMLScrolledText  # type: ignore
            except Exception:
                # Fallback to raw text if tkhtmlview unavailable at runtime
                self.md_use_html = False
                self._md_html_widget = None
                # Clear container completely and render raw text
                try:
                    for child in self._md_preview_frame.winfo_children():
                        child.destroy()
                except Exception:
                    pass
                self.md_preview = ScrolledText(self._md_preview_frame, wrap=tk.WORD, height=10)
                self.md_preview.pack(fill=tk.BOTH, expand=True)
                self.md_preview.configure(state=tk.NORMAL)
                self.md_preview.delete('1.0', tk.END)
                self.md_preview.insert(tk.END, text)
                self.md_preview.configure(state=tk.DISABLED)
                # Bind copy keys and context menu
                try:
                    self._bind_md_copy_handlers(self.md_preview)
                except Exception:
                    pass
                return

            # Destroy all previous children in the preview frame to guarantee a clean slate
            try:
                for child in self._md_preview_frame.winfo_children():
                    child.destroy()
            except Exception:
                pass
            # Clear stale reference to text widget to avoid calling methods on destroyed Tk widget
            try:
                self.md_preview = None
            except Exception:
                pass

            # Build fresh widget
            self._md_html_widget = HTMLScrolledText(self._md_preview_frame, html="", width=80)
            self._md_html_widget.pack(fill=tk.BOTH, expand=True)

            # Compute HTML
            try:
                import markdown as _md  # type: ignore
                # Preprocess Mermaid code fences into image links if possible
                logging.debug(f"Original markdown content (first 200 chars):\n{text[:200]}...")
                text_pre = self._preprocess_mermaid_markdown(text)
                logging.debug(f"Markdown after mermaid preprocessing (first 300 chars):\n{text_pre[:300]}...")
                html = _md.markdown(text_pre, extensions=['fenced_code', 'tables'])
                logging.debug(f"Generated HTML (first 500 chars):\n{html[:500]}...")
            except Exception:
                safe = (text or "").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html = f"<pre>{safe}</pre>"

            # Set HTML
            try:
                if hasattr(self._md_html_widget, 'set_html'):
                    self._md_html_widget.set_html(html)
                else:
                    self._md_html_widget.set_text(html)
            except Exception as e:
                logging.warning(f"Failed to render HTML preview: {e}")
            # Bind copy handlers on HTML widget
            try:
                # Provide the same copy/context behavior
                self._md_html_widget.bind('<Control-c>', lambda e: (self.copy_markdown(selection=True), 'break'))
                self._md_html_widget.bind('<Button-3>', self._md_show_context_menu)
            except Exception:
                pass
            # Record last rendered path
            try:
                self._md_last_rendered_path = self.md_current_path
            except Exception:
                pass
            return

        # Non-HTML preview: build/update a ScrolledText
        try:
            # If editing, avoid overwriting any in-flight user edits
            editing = bool(getattr(self, 'md_edit_mode', None)) and self.md_edit_mode.get()
            if editing and not path_changed and hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                try:
                    self.md_preview.configure(state=tk.NORMAL)
                except Exception:
                    pass
                # Do not overwrite content while editing
            else:
                for child in self._md_preview_frame.winfo_children():
                    child.destroy()
                self.md_preview = ScrolledText(self._md_preview_frame, wrap=tk.WORD, height=10)
                self.md_preview.pack(fill=tk.BOTH, expand=True)
                self.md_preview.configure(state=tk.NORMAL)
                self.md_preview.delete('1.0', tk.END)
                self.md_preview.insert(tk.END, text)
                # Disable when not editing for read-only view
                if not editing:
                    self.md_preview.configure(state=tk.DISABLED)
            # Bind copy keys and context menu
            try:
                self._bind_md_copy_handlers(self.md_preview)
            except Exception:
                pass
            # Record last rendered path
            try:
                self._md_last_rendered_path = self.md_current_path
            except Exception:
                pass
        except Exception as e:
            logging.warning(f"Failed to render text preview: {e}")
        
        # --- Copy helpers for Markdown preview ---
    def _bind_md_copy_handlers(self, widget):
        """Bind Ctrl+C and right-click menu for the markdown preview widget."""
        try:
            widget.bind('<Control-c>', lambda e: (self.copy_markdown(selection=True), 'break'))
            widget.bind('<Button-3>', self._md_show_context_menu)
        except Exception:
            pass

    def _md_show_context_menu(self, event):
        try:
            if not hasattr(self, '_md_context_menu'):
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label="Copy", command=lambda: self.copy_markdown(selection=True))
                menu.add_command(label="Copy All", command=lambda: self.copy_markdown(selection=False))
                self._md_context_menu = menu
            self._md_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._md_context_menu.grab_release()
            except Exception:
                pass

    def copy_markdown(self, selection: bool = True):
        """Copy selection (if any) or entire markdown content to clipboard.
        Works for both text and HTML preview modes by reading from the backing file when needed.
        """
        try:
            text = None
            # Try selection from text widget if present
            if selection and hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                try:
                    state = str(self.md_preview['state'])
                    if state == tk.DISABLED:
                        self.md_preview.configure(state=tk.NORMAL)
                    if self.md_preview.tag_ranges(tk.SEL):
                        text = self.md_preview.get(tk.SEL_FIRST, tk.SEL_LAST)
                    if state == tk.DISABLED:
                        self.md_preview.configure(state=tk.DISABLED)
                except Exception:
                    text = None
            # Fallback to entire file content
            if not text:
                if self.md_current_path and os.path.isfile(self.md_current_path):
                    with open(self.md_current_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                else:
                    text = ""
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # ensure clipboard is set
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy: {e}")

    def _get_markdown_preview_text(self) -> Optional[str]:
        """Return current markdown text from the preview widget if present; otherwise None.
        This reads from the text widget regardless of edit mode by temporarily enabling it if disabled.
        """
        try:
            if hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                # Ensure the underlying Tk widget still exists
                try:
                    if not int(self.md_preview.winfo_exists()):
                        return None
                except Exception:
                    return None
                prev_state = None
                try:
                    prev_state = str(self.md_preview['state'])
                    if prev_state == tk.DISABLED:
                        self.md_preview.configure(state=tk.NORMAL)
                except Exception:
                    pass
                try:
                    text = self.md_preview.get('1.0', 'end-1c')
                except Exception:
                    return None
                if prev_state == tk.DISABLED:
                    try:
                        self.md_preview.configure(state=tk.DISABLED)
                    except Exception:
                        pass
                return text
        except Exception:
            pass
        return None

    def _autosave_markdown_if_dirty(self):
        """If a markdown file is open and the preview content differs from disk, save it silently."""
        try:
            md_path = getattr(self, 'md_current_path', None)
            if not md_path:
                return
            preview_text = self._get_markdown_preview_text()
            if preview_text is None:
                return
            disk_text = ""
            if os.path.isfile(md_path):
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        disk_text = f.read()
                except Exception:
                    disk_text = ""
            if preview_text != disk_text:
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(preview_text)
                logging.info(f"Autosaved markdown to {md_path}")
        except Exception as e:
            logging.warning("Autosave markdown failed", exc_info=e)

    # --- Mermaid rendering helpers ---
    def _preprocess_mermaid_markdown(self, text: str) -> str:
        """Find ```mermaid fenced blocks and replace them with image links.
        Uses mermaid-cli (mmdc) to render PNGs into a cache dir. Falls back to raw blocks if unavailable.
        Also handles Mermaid blocks that were replaced with placeholders during translation.
        Returns: Processed text with mermaid code blocks replaced by image tags.
        """
        logger = logging.getLogger('mermaid')
        if not text:
            logger.debug("No text provided to _preprocess_mermaid_markdown")
            return text
            
        # Check for Mermaid blocks or placeholders
        text_lower = text.lower()
        has_mermaid = ("```mermaid" in text_lower) or ("``` mermaid" in text_lower) or \
                     ("```mermaid" in text_lower.replace(" ", "")) or ("mermaid" in text_lower and "```" in text_lower) or \
                     "{{mermaid_block_" in text_lower or "{mermaid_block_" in text_lower
        
        logger.debug(f"Mermaid blocks or placeholders found in text: {has_mermaid}")
        
        if not has_mermaid:
            return text

        logger.info("Mermaid code blocks or placeholders detected, initializing Mermaid processor...")
        
        # Check if mmdc is available
        mmdc_available = self._is_mermaid_cli_available()
        logger.info(f"Mermaid CLI (mmdc) available: {mmdc_available}")
        
        if not mmdc_available:
            logger.warning("Mermaid CLI not available, falling back to raw code blocks")
            return text

        # First, handle any placeholder blocks from translation
        placeholder_pattern = re.compile(r'(?:\{\{mermaid_block_(\d+)\}\}|\{mermaid_block_(\d+)\})', re.IGNORECASE)
        placeholder_matches = list(placeholder_pattern.finditer(text))
        
        # If we have placeholders, restore the original Mermaid blocks
        if placeholder_matches:
            logger.info(f"Found {len(placeholder_matches)} Mermaid placeholders to process")
            # First, collect all Mermaid blocks in the text
            mermaid_blocks = []
            # Find all Mermaid code blocks in the text
            mermaid_block_pattern = re.compile(r'```\s*(?:mermaid|mermaid\s+[^\n]*|.*?mermaid.*?)\s*\n([\s\S]*?)\n\s*```', re.IGNORECASE)
            
            # Store the original blocks
            def collect_blocks(match):
                block = match.group(0)
                mermaid_blocks.append(block)
                return block
                
            # Replace blocks with placeholders to avoid double-processing
            temp_text = mermaid_block_pattern.sub(collect_blocks, text)
            
            # If we found Mermaid blocks, replace placeholders with the original blocks
            if mermaid_blocks:
                logger.info(f"Found {len(mermaid_blocks)} Mermaid blocks to restore")
                # Replace placeholders with original Mermaid blocks
                def restore_placeholder(match):
                    try:
                        block_id = int(match.group(1) or match.group(2))
                        if 0 <= block_id < len(mermaid_blocks):
                            return mermaid_blocks[block_id]
                    except (ValueError, IndexError):
                        pass
                    return match.group(0)
                
                text = placeholder_pattern.sub(restore_placeholder, text)
            else:
                logger.warning("No Mermaid blocks found to restore")

        # Now process standard Mermaid blocks
        def process_mermaid_blocks(text):
            # More flexible pattern to match mermaid code blocks
            pattern = re.compile(r'```\s*(?:mermaid|mermaid\s+[^\n]*|.*?mermaid.*?)\s*\n([\s\S]*?)\n\s*```', re.IGNORECASE)
            matches = list(pattern.finditer(text))
            logger.info(f"Found {len(matches)} Mermaid code blocks to process")

            def repl(match):
                code = match.group(1).strip()
                logger.debug(f"Processing Mermaid block: {code[:100]}...")
                
                # Clean up the code - remove any remaining language specifiers
                if code.lower().startswith('mermaid'):
                    code = code.split('\n', 1)[1] if '\n' in code else ''
                
                if not code.strip():
                    return match.group(0)  # Return original if no code
                    
                try:
                    logger.debug("Rendering Mermaid diagram...")
                    start_time = time.time()
                    img_path = self._render_mermaid_to_png(code)
                    render_time = time.time() - start_time
                    
                    if not img_path or not os.path.exists(img_path):
                        logger.error(f"Mermaid render failed: No output file at {img_path}")
                        return match.group(0)
                        
                    # Verify the image was created and has content
                    img_size = os.path.getsize(img_path)
                    logger.info(f"Mermaid render successful: {img_path} ({img_size} bytes, {render_time:.2f}s)")
                    
                    # Use absolute path with forward slashes for HTML
                    src = os.path.abspath(img_path).replace('\\', '/')
                    img_tag = f'<div class="mermaid-diagram"><img src="{src}" alt="Mermaid Diagram" style="max-width: 100%;"></div>'
                    return img_tag
                    
                except Exception as e:
                    logger.error(f"Mermaid render failed: {str(e)}", exc_info=True)
                    error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
                    return f'<div class="mermaid-error">Error rendering Mermaid diagram: {error_msg}</div>\n```mermaid\n{code}\n```'
            
            return pattern.sub(repl, text)
        
        # Process the text to handle Mermaid blocks
        return process_mermaid_blocks(text)

    def _is_mermaid_cli_available(self) -> bool:
        """Return True if Mermaid CLI is available (either on PATH or discovered)."""
        try:
            if getattr(self, "_mmdc_cmd", None):
                return True
            self._mmdc_cmd = self._discover_mmdc()
            return self._mmdc_cmd is not None
        except Exception:
            return False

    def _discover_mmdc(self) -> Optional[str]:
        """Try to find the Mermaid CLI executable.
        
        Returns:
            str: Full path to mmdc executable, or 'mmdc' if found in PATH, or None if not found.
        """
        logger = logging.getLogger('mermaid.discover')
        candidates = []
        
        # 1) Check if mmdc is in PATH
        candidates.append('mmdc')
        
        # 2) Check common npm global install locations
        appdata = os.environ.get('APPDATA', '')
        localappdata = os.environ.get('LOCALAPPDATA', '')
        program_files = os.environ.get('ProgramFiles', '')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', '')
        
        # Common npm global install locations
        npm_paths = [
            os.path.join(appdata, 'npm'),
            os.path.join(localappdata, 'npm'),
            os.path.join(program_files, 'nodejs'),
            os.path.join(program_files_x86, 'nodejs'),
            os.path.join(program_files, 'nodejs/node_modules/npm/bin'),
            os.path.join(program_files_x86, 'nodejs/node_modules/npm/bin'),
            'C:\\Program Files\\nodejs',
            'C:\\Program Files (x86)\\nodejs',
            'C:\\Users\\' + os.environ.get('USERNAME', '') + '\\AppData\\Roaming\\npm',
            'C:\\Users\\' + os.environ.get('USERNAME', '') + '\\AppData\\Local\\npm',
            'C:\\Program Files\\nodejs\\node_modules\\@mermaid-js\\mermaid-cli'
        ]
        
        # Add all possible mmdc paths from npm locations
        for base_path in set(npm_paths):
            if not base_path or not os.path.exists(base_path):
                continue
                
            # Check for mmdc with different extensions and in different subdirectories
            for subdir in ['', 'node_modules/.bin', 'node_modules/@mermaid-js/mermaid-cli']:
                full_path = os.path.join(base_path, subdir) if subdir else base_path
                if not os.path.exists(full_path):
                    continue
                    
                for ext in ['', '.cmd', '.ps1', '.bat']:
                    mmdc_path = os.path.join(full_path, f'mmdc{ext}')
                    if mmdc_path not in candidates:
                        candidates.append(mmdc_path)
        
        # Also check if we can find it via npm
        try:
            npm_prefix = subprocess.run(
                ['npm', 'config', 'get', 'prefix'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                timeout=5
            )
            if npm_prefix.returncode == 0:
                npm_prefix_path = npm_prefix.stdout.strip()
                if os.path.exists(npm_prefix_path):
                    candidates.extend([
                        os.path.join(npm_prefix_path, 'mmdc'),
                        os.path.join(npm_prefix_path, 'mmdc.cmd'),
                        os.path.join(npm_prefix_path, 'node_modules', '.bin', 'mmdc'),
                        os.path.join(npm_prefix_path, 'node_modules', '.bin', 'mmdc.cmd')
                    ])
        except Exception as e:
            logger.debug(f"Error getting npm prefix: {e}")
        
        logger.debug(f"Looking for mmdc in: {candidates}")
        
        # Try each candidate
        for cmd in candidates:
            try:
                # Skip non-existent paths (except for 'mmdc' which we'll try to find in PATH)
                if cmd != 'mmdc' and not os.path.exists(cmd):
                    continue
                    
                # Try to get version
                logger.debug(f"Testing mmdc candidate: {cmd}")
                proc = subprocess.run(
                    [cmd, '--version'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False,
                    timeout=5
                )
                
                if proc.returncode == 0 and proc.stdout.strip():
                    version = proc.stdout.strip()
                    logger.info(f"Found mmdc v{version} at: {cmd}")
                    return cmd
                else:
                    logger.debug(f"mmdc check failed for {cmd}: {proc.stderr or proc.stdout}")
                    
            except Exception as e:
                logger.debug(f"Error checking mmdc at {cmd}: {e}")
                continue
        
        # Last resort: Try to install it
        logger.info("Mermaid CLI not found, attempting to install...")
        try:
            install_cmd = ['npm', 'install', '-g', '@mermaid-js/mermaid-cli']
            logger.debug(f"Running: {' '.join(install_cmd)}")
            proc = subprocess.run(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                timeout=300  # 5 minutes should be enough for installation
            )
            
            if proc.returncode == 0:
                logger.info("Successfully installed Mermaid CLI")
                # Try to find it again after installation
                return self._discover_mmdc()
            else:
                logger.warning(f"Failed to install Mermaid CLI: {proc.stderr or proc.stdout}")
        except Exception as e:
            logger.warning(f"Error installing Mermaid CLI: {e}")
        
        logger.warning("Could not find or install mmdc in any of the expected locations")
        return None

    def _render_mermaid_to_png(self, code: str) -> str:
        """Render mermaid code to a PNG in the cache directory and return the absolute path.
        Caches by SHA1 of the code content.
        """
        logger = logging.getLogger('mermaid.render')
        
        if not self._mermaid_cache_dir:
            error_msg = "No Mermaid cache directory configured"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Compute a stable filename
        sha = hashlib.sha1(code.encode('utf-8')).hexdigest()
        out_png = os.path.abspath(os.path.join(self._mermaid_cache_dir, f"{sha}.png"))
        
        # Check cache first
        if os.path.isfile(out_png) and os.path.getsize(out_png) > 0:
            logger.debug(f"Using cached render: {out_png}")
            return out_png

        # Ensure cache directory exists
        try:
            os.makedirs(self._mermaid_cache_dir, exist_ok=True)
            logger.debug(f"Cache directory: {os.path.abspath(self._mermaid_cache_dir)}")
        except Exception as e:
            error_msg = f"Failed to create cache directory: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Write code to a temp .mmd file in cache dir
        in_mmd = os.path.join(self._mermaid_cache_dir, f"{sha}.mmd")
        logger.debug(f"Writing Mermaid code to temp file: {in_mmd}")
        
        try:
            with open(in_mmd, 'w', encoding='utf-8') as f:
                f.write(code)
            logger.debug(f"Wrote {len(code)} bytes to {in_mmd}")
        except Exception as e:
            error_msg = f"Failed to write Mermaid code to {in_mmd}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

        # Get the Mermaid CLI command
        mmdc_cmd = self._mmdc_cmd or "mmdc"
        
        # Create puppeteer config file
        puppeteer_config_path = os.path.join(self._mermaid_cache_dir, "puppeteer-config.json")
        try:
            with open(puppeteer_config_path, 'w') as f:
                f.write('{"args": ["--no-sandbox", "--disable-setuid-sandbox"]}')
        except Exception as e:
            error_msg = f"Failed to write puppeteer config to {puppeteer_config_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
            
        # Build the command with additional debugging options
        cmd = [
            mmdc_cmd,
            "-i", in_mmd,
            "-o", out_png,
            "--width", "1200",
            "--height", "800",
            "-b", "transparent",
            "-s", "1.5",
            "-t", "default",  # Use default theme for better compatibility
            "--puppeteerConfigFile", puppeteer_config_path,
            "--pdfFit"  # Ensure the diagram fits the specified dimensions
        ]
        
        # Execute the command with better error handling
        start_time = time.time()
        try:
            logger.debug("Starting Mermaid CLI process...")
            logger.debug(f"Input file exists: {os.path.exists(in_mmd)}")
            logger.debug(f"Output directory exists: {os.path.exists(os.path.dirname(out_png))}")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(out_png), exist_ok=True)
            
            # Add common Node.js paths if they exist
            common_paths = [
                os.path.join(os.environ.get('APPDATA', ''), 'npm'),
                os.path.join(os.environ.get('ProgramFiles', ''), 'nodejs'),
                os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'nodejs')
            ]
            
            # Set up environment with basic path
            env = os.environ.copy()
            if 'PATH' not in env:
                env['PATH'] = os.defpath
            
            # Add paths to environment
            extra_paths = [p for p in common_paths if p and os.path.exists(p)]
            if extra_paths:
                env['PATH'] = os.pathsep.join(extra_paths) + os.pathsep + env['PATH']
                logger.debug(f"Updated PATH: {env['PATH']}")
            
            # Run the command with a timeout
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                shell=False
            )
            
            try:
                # Set a timeout of 60 seconds
                stdout, stderr = proc.communicate(timeout=60)
                returncode = proc.returncode
                
                # Log the output
                if stdout and stdout.strip():
                    logger.debug(f"Mermaid CLI stdout: {stdout}")
                if stderr and stderr.strip():
                    logger.warning(f"Mermaid CLI stderr: {stderr}")
                
                # Check if the output file was created
                if not os.path.exists(out_png):
                    error_msg = f"Mermaid CLI did not create output file: {out_png}"
                    if stderr:
                        error_msg += f"\nError: {stderr}"
                    if stdout:
                        error_msg += f"\nOutput: {stdout}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                    
                if os.path.getsize(out_png) == 0:
                    error_msg = f"Mermaid CLI created empty output file: {out_png}"
                    if stderr:
                        error_msg += f"\nError: {stderr}"
                    logger.error(error_msg)
                    os.remove(out_png)  # Clean up empty file
                    raise RuntimeError(error_msg)
                
                logger.info(f"Successfully rendered Mermaid diagram to {out_png} ({(time.time() - start_time):.2f}s)")
                return out_png
                
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                error_msg = "Mermaid CLI timed out after 60 seconds"
                if stderr:
                    error_msg += f"\nLast error: {stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            error_msg = f"Failed to render Mermaid diagram: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Provide more helpful error messages for common issues
            if "ENOENT" in str(e) or "No such file or directory" in str(e):
                error_msg += "\n\nThis might be because Mermaid CLI is not properly installed or not in your system PATH."
                error_msg += "\nTry running: npm install -g @mermaid-js/mermaid-cli"
            
            # Clean up any partial output files
            try:
                if os.path.exists(out_png) and os.path.getsize(out_png) == 0:
                    os.remove(out_png)
            except Exception as cleanup_error:
                logger.warning(f"Error cleaning up partial output file: {cleanup_error}")
            
            raise RuntimeError(error_msg) from e

    def _switch_markdown_for_selection(self, file_path: str, switch_tab: bool = False):
        """Point md_current_path to the sidecar markdown for the selected file.
        If the sidecar doesn't exist, still set the intended path and refresh preview to blank.
        """
        try:
            if not file_path:
                return
            stem, _ = os.path.splitext(file_path)
            md_path = stem + ".md"
            self.md_current_path = md_path
            # Refresh preview (will be blank if file doesn't exist)
            self.update_markdown_preview()
            if switch_tab:
                self.activate_markdown_tab()
        except Exception as e:
            logging.debug(f"Failed to switch markdown for {file_path}: {e}")

    def toggle_md_edit_mode(self):
        """Toggle edit mode for the Markdown tab. Forces Text view when enabled."""
        try:
            if self.md_edit_mode.get():
                # Force text view when editing
                if hasattr(self, 'md_view_as_text'):
                    self.md_view_as_text.set(True)
                # Rebuild preview as editable text
                self.update_markdown_preview()
                try:
                    if hasattr(self, 'md_preview'):
                        self.md_preview.focus_set()
                except Exception:
                    pass
            else:
                # Leaving edit mode: refresh preview honoring the view toggle
                self.update_markdown_preview()
        except Exception as e:
            logging.error("Failed to toggle edit mode", exc_info=e)

    def save_markdown_current(self):
        """Save current Markdown text widget content into md_current_path."""
        try:
            # Only meaningful if we have a text widget
            content_read = False
            if hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                # Ensure widget exists
                try:
                    if not int(self.md_preview.winfo_exists()):
                        raise RuntimeError("Markdown text widget no longer exists")
                except Exception:
                    # Fall through to backing file read
                    pass
                # Ensure we can read the content
                prev_state = None
                try:
                    prev_state = str(self.md_preview['state'])
                    if prev_state == tk.DISABLED:
                        self.md_preview.configure(state=tk.NORMAL)
                except Exception:
                    pass
                try:
                    content = self.md_preview.get('1.0', 'end-1c')
                    content_read = True
                except Exception:
                    content_read = False
                # Restore state if needed
                if prev_state == tk.DISABLED:
                    try:
                        self.md_preview.configure(state=tk.DISABLED)
                    except Exception:
                        pass
            if not content_read:
                # Fallback: read from backing file to avoid data loss
                content = ""
                if self.md_current_path and os.path.isfile(self.md_current_path):
                    with open(self.md_current_path, 'r', encoding='utf-8') as f:
                        content = f.read()

            if not self.md_current_path:
                # If no current path, prompt for one
                path = filedialog.asksaveasfilename(
                    title="Save Markdown",
                    defaultextension=".md",
                    initialfile="conversation.md",
                    filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All Files", "*.*")]
                )
                if not path:
                    return
                self.md_current_path = path

            # Write out
            with open(self.md_current_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # If not editing, refresh preview to show read-only state
            if not (hasattr(self, 'md_edit_mode') and self.md_edit_mode.get()):
                self.update_markdown_preview()

            # Optional: lightweight confirmation in log
            logging.info(f"Markdown saved to {self.md_current_path}")
        except Exception as e:
            logging.error("Failed to save markdown", exc_info=e)
            messagebox.showerror("Save Error", f"Failed to save: {e}")

    def activate_markdown_tab(self):
        """Switch to the Markdown tab."""
        try:
            self.notebook.select(self.md_tab)
        except Exception:
            pass

    def _ensure_gemini_model(self):
        """Helper to return a configured Gemini model or raise."""
        import google.generativeai as genai  # type: ignore
        api_key = (
            getattr(self, 'gemini_api_key', None)
            or os.environ.get('GOOGLE_API_KEY')
            or os.environ.get('GEMINI_API_KEY')
        )
        if not api_key:
            api_key = simpledialog.askstring(
                "Google Gemini API Key",
                "Enter your GOOGLE_API_KEY or GEMINI_API_KEY (not stored persistently):",
                show='*',
                parent=self
            )
            if not api_key:
                raise RuntimeError("Gemini API key not provided")
            self.gemini_api_key = api_key
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")

    def send_md_chat(self):
        """Send a follow-up prompt to Gemini and append response to the markdown file."""
        user_msg = (self.chat_var.get() or '').strip()
        if not user_msg:
            return
        try:
            # Read existing markdown as lightweight context
            context_text = ''
            try:
                if self.md_current_path and os.path.isfile(self.md_current_path):
                    with open(self.md_current_path, 'r', encoding='utf-8') as f:
                        context_text = f.read()[-6000:]  # limit context size
            except Exception:
                pass

            # Call Gemini
            try:
                model = self._ensure_gemini_model()
            except Exception as e:
                messagebox.showerror("Gemini", str(e))
                return

            # Build language instruction
            lang_label = getattr(self, 'chat_lang_var', None).get() if hasattr(self, 'chat_lang_var') else 'English'
            lang_map = {
                'English': 'Answer in English and format with Markdown.',
                'Chinese (Simplified)': 'Answer in Chinese (Simplified) and format with Markdown.',
                'Chinese (Traditional)': 'Answer in Chinese (Traditional) and format with Markdown.',
                'Japanese': 'Answer in Japanese and format with Markdown.',
                'Korean': 'Answer in Korean and format with Markdown.',
                'Spanish': 'Answer in Spanish and format with Markdown.',
            }
            lang_instruction = lang_map.get(lang_label, 'Answer in English and format with Markdown.')

            resp = model.generate_content([
                    "You are continuing a markdown-based analysis conversation.",
                    lang_instruction,
                    "Context (may be truncated):\n" + context_text,
                    "User question:\n" + user_msg,
                ])
            answer = (getattr(resp, 'text', '') or '').strip()

            # Fetch reference links and format them
            reference_links = []
            try:
                reference_links = self.fetch_reference_links(context_text + "\n\n" + answer)
            except Exception as e:
                logging.warning(f"Failed to fetch reference links: {e}")
            
            # Format reference links in markdown
            references_md = ""
            if reference_links:
                references_md = "\n\n**参考资料:**\n"
                for i, (title, url) in enumerate(reference_links, 1):
                    if title:
                        references_md += f"{i}. [{title}]({url})\n"
                    else:
                        references_md += f"{i}. {url}\n"
            
            # Fetch follow-up questions and format them
            followups_md = ""
            try:
                followups = self.fetch_followups(context_text + "\n\n" + answer)
                self.render_suggested_questions(followups)  # Still show in UI
                
                if followups:
                    followups_md = "\n\n**后续问题:**\n"
                    for i, question in enumerate(followups, 1):
                        followups_md += f"{i}. {question}\n"
            except Exception as e:
                logging.warning(f"Failed to generate follow-up questions: {e}")
                self.render_suggested_questions([])
            
            # Combine everything into the markdown block
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            block = f"\n\n---\n## Follow-up ({ts})\n**User:**\n\n{user_msg}\n\n**Assistant:**\n\n{answer}{references_md}{followups_md}\n"
            
            # Write to file
            with open(self.md_current_path, 'a', encoding='utf-8') as f:
                f.write(block)

            # Refresh UI
            self.chat_var.set("")
            self.update_markdown_preview()
            self.activate_markdown_tab()
        except Exception as e:
            logging.error("send_md_chat failed", exc_info=e)
            messagebox.showerror("Error", f"Failed to send chat: {e}")


    def save_markdown_as_new(self):
        """Save current preview content to a new markdown file and clear the preview."""
        try:
            # Default to current image name for better association, fallback to current md name
            suggested_name = "conversation.md"
            try:
                if getattr(self, 'current_image_path', None):
                    base = os.path.splitext(os.path.basename(self.current_image_path))[0]
                    suggested_name = f"{base}.md"
                elif getattr(self, 'md_current_path', None):
                    suggested_name = os.path.basename(self.md_current_path)
            except Exception:
                pass

            # Determine current text to save
            text_to_save = ""
            try:
                if hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                    state = None
                    try:
                        state = str(self.md_preview['state'])
                        if state == tk.DISABLED:
                            self.md_preview.configure(state=tk.NORMAL)
                    except Exception:
                        pass
                    text_to_save = self.md_preview.get('1.0', 'end-1c')
                    if state == tk.DISABLED:
                        try:
                            self.md_preview.configure(state=tk.DISABLED)
                        except Exception:
                            pass
                elif self.md_current_path and os.path.isfile(self.md_current_path):
                    with open(self.md_current_path, 'r', encoding='utf-8') as f:
                        text_to_save = f.read()
            except Exception:
                pass

            # Ask a new path
            path = filedialog.asksaveasfilename(
                title="Save Markdown As",
                defaultextension=".md",
                initialfile=suggested_name,
                filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All Files", "*.*")]
            )
            if not path:
                return

            # Save file and adopt as current
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text_to_save or "")
            self.md_current_path = path

            # Clear preview area for a clean slate
            try:
                if hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                    self.md_preview.configure(state=tk.NORMAL)
                    self.md_preview.delete('1.0', tk.END)
                    self.md_preview.configure(state=tk.DISABLED)
            except Exception:
                pass

            # Confirmation
            try:
                messagebox.showinfo("Saved", f"Markdown saved to:\n{path}")
            except Exception:
                pass
        except Exception as e:
            logging.error("Failed to save markdown as new", exc_info=e)
            messagebox.showerror("Error", f"Failed to save: {e}")

    def get_selected_file_paths(self):
        """Return absolute file paths for currently selected rows in the table."""
        paths = []
        try:
            if not hasattr(self, 'table') or self.table is None:
                return paths
            view_df = getattr(self.table.model, 'df', None)
            if view_df is None or view_df.empty:
                return paths

            rows = []
            # Prefer multi-select list if available
            if hasattr(self.table, 'multiplerowlist') and self.table.multiplerowlist:
                rows = [r for r in self.table.multiplerowlist if isinstance(r, int) and 0 <= r < len(view_df)]
            else:
                r = self.table.getSelectedRow()
                if isinstance(r, int) and 0 <= r < len(view_df):
                    rows = [r]

            for r in rows:
                try:
                    fp = str(view_df.iloc[r]['File_Path'])
                    if fp:
                        paths.append(fp)
                except Exception:
                    continue
        except Exception as e:
            logging.error("get_selected_file_paths failed: %s", e)
        return paths

    def clear_markdown_content(self):
        """Clear the Markdown preview area (HTML or text)."""
        try:
            if getattr(self, 'md_use_html', False) and getattr(self, '_md_html_widget', None):
                # For HTML widget, reset content
                try:
                    if hasattr(self._md_html_widget, 'set_html'):
                        self._md_html_widget.set_html("")
                    else:
                        self._md_html_widget.set_text("")
                except Exception:
                    # Recreate a blank widget if needed
                    try:
                        for child in self._md_preview_frame.winfo_children():
                            child.destroy()
                    except Exception:
                        pass
                    from tkinter.scrolledtext import ScrolledText as _ST
                    self.md_use_html = False
                    self._md_html_widget = None
                    self.md_preview = _ST(self._md_preview_frame, wrap=tk.WORD, height=10)
                    self.md_preview.pack(fill=tk.BOTH, expand=True)
                    self.md_preview.configure(state=tk.DISABLED)
            else:
                # Text mode
                if hasattr(self, 'md_preview') and isinstance(self.md_preview, ScrolledText):
                    self.md_preview.configure(state=tk.NORMAL)
                    self.md_preview.delete('1.0', tk.END)
                    self.md_preview.configure(state=tk.DISABLED)
        except Exception as e:
            logging.warning(f"Failed to clear markdown content: {e}")

    def delete_selected_files(self):
        """Delete selected files from disk and refresh the file list."""
        try:
            paths = self.get_selected_file_paths()
            if not paths:
                messagebox.showinfo("Delete Files", "No files selected.")
                return
            if not messagebox.askyesno("Delete Files", f"Delete {len(paths)} file(s)? This cannot be undone."):
                return

            successes = 0
            errors = []
            for p in paths:
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                        successes += 1
                except Exception as e:
                    errors.append((p, str(e)))

            # Refresh UI after operations
            self.refresh_file_list()

            msg = f"Deleted {successes} file(s)."
            if errors:
                msg += f"\n{len(errors)} failed."
            messagebox.showinfo("Delete Files", msg)
        except Exception as e:
            logging.error("delete_selected_files failed", exc_info=e)
            messagebox.showerror("Delete Files", f"Error: {e}")

    def move_selected_files(self):
        """Move selected files to a destination folder with overwrite confirmation."""
        try:
            paths = self.get_selected_file_paths()
            if not paths:
                messagebox.showinfo("Move Files", "No files selected.")
                return

            dest_dir = filedialog.askdirectory(
                title="Select Destination Folder",
                initialdir=os.path.dirname(self.current_directory) if self.current_directory else os.getcwd()
            )
            if not dest_dir:
                return

            moved = 0
            errors = []
            for src in paths:
                try:
                    if not os.path.isfile(src):
                        continue
                    fname = os.path.basename(src)
                    dst = os.path.join(dest_dir, fname)
                    if os.path.exists(dst):
                        overwrite = messagebox.askyesno("Overwrite?", f"{fname} exists. Overwrite?")
                        if not overwrite:
                            continue
                        try:
                            os.remove(dst)
                        except Exception:
                            pass
                    shutil.move(src, dst)
                    moved += 1
                except Exception as e:
                    errors.append((src, str(e)))

            # Refresh UI and update current directory if we actually moved files
            self.refresh_file_list()

            msg = f"Moved {moved} file(s) to:\n{dest_dir}"
            if errors:
                msg += f"\n{len(errors)} failed."
            messagebox.showinfo("Move Files", msg)
        except Exception as e:
            logging.error("move_selected_files failed", exc_info=e)
            messagebox.showerror("Move Files", f"Error: {e}")

    def browse_folder(self):
        """Open a directory chooser dialog and update the file list"""
        print("\n=== Browse folder called ===")  # Debug print
        directory = filedialog.askdirectory(
            title="Select Directory",
            initialdir=self.current_directory or os.path.dirname(os.path.abspath(__file__))
        )
        if directory:
            print(f"Selected directory: {directory}")  # Debug print
            self.current_directory = directory
            
            # Add to recent folders
            self.add_recent_folder(directory)
            
            # Update image files list
            self.update_image_files()
            
            # Update max fields
            old_max = self.max_fields
            self.max_fields = self.get_max_fields()
            print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
            
            # Update file browser
            self.setup_file_browser()
            
            # Update grid
            if hasattr(self, 'create_grid'):
                print("Updating grid")  # Debug print
                self.create_grid()

    def update_image_files(self):
        """Update the list of files in the current directory (optionally including subfolders)."""
        print("\n=== Updating files list ===")  # Debug print
        
        # Clear existing list
        self.image_files = []
        
        # Normalize directory path
        normalized_directory = os.path.normpath(self.current_directory)
        
        try:
            # Check if we should include subfolders
            if self.include_subfolders.get():
                # Recursively walk through all subdirectories
                for root, _, files in os.walk(normalized_directory):
                    for file in files:
                        full_path = os.path.normpath(os.path.join(root, file))
                        if os.path.isfile(full_path):
                            self.image_files.append(full_path)
            else:
                # Get files only from current directory
                files = os.listdir(normalized_directory)
                self.image_files = [os.path.normpath(os.path.join(normalized_directory, f)) 
                                  for f in files 
                                  if os.path.isfile(os.path.join(normalized_directory, f))]
            
            print(f"Found {len(self.image_files)} files")  # Debug print
        except Exception as e:
            print(f"Error updating image files: {e}")
            messagebox.showerror("Error", f"Failed to update image files: {e}")
            self.image_files = []

    def get_max_fields(self):
        """Get the maximum number of underscore-separated fields in filenames"""
        max_fields = 0
        for file_path in self.image_files:
            # Get just the filename without the path
            filename = os.path.basename(file_path)
            
            # Remove extension and split by underscore
            name_without_ext = os.path.splitext(filename)[0]
            fields = name_without_ext.split('_')
            max_fields = max(max_fields, len(fields))
        print(f"Max fields found: {max_fields}")  # Debug print
        return max_fields

    def setup_file_browser(self):
        """Setup the file browser panel with pandastable."""
        print("\n=== Setting up file browser ===")
        try:
            prev_selection_paths = []
            try:
                if hasattr(self, 'table') and getattr(self.table, 'model', None):
                    view_df_prev = self.table.model.df
                    if isinstance(view_df_prev, pd.DataFrame) and not view_df_prev.empty:
                        # Save selected paths to restore later
                        if hasattr(self.table, 'multiplerowlist') and self.table.multiplerowlist:
                            rows = [r for r in self.table.multiplerowlist if isinstance(r, int) and 0 <= r < len(view_df_prev)]
                        else:
                            r = self.table.getSelectedRow()
                            rows = [r] if isinstance(r, int) and 0 <= r < len(view_df_prev) else []
                        for r in rows:
                            try:
                                prev_selection_paths.append(str(view_df_prev.iloc[r]['File_Path']))
                            except Exception:
                                pass
            except Exception:
                pass

            # Decide whether to reuse or rebuild the DataFrame
            need_rebuild = True
            if isinstance(getattr(self, 'df', None), pd.DataFrame) and 'File_Path' in getattr(self.df, 'columns', []):
                try:
                    df_paths = set(map(str, self.df['File_Path'].tolist()))
                    img_paths = set(map(str, getattr(self, 'image_files', []) or []))
                    # Reuse only if paths match; otherwise, folder/content changed -> rebuild
                    need_rebuild = (df_paths != img_paths)
                    if not need_rebuild and self.df.empty and img_paths:
                        need_rebuild = True
                except Exception:
                    need_rebuild = True
            if not need_rebuild:
                print("Reusing existing DataFrame for table")
            else:
                # Build DataFrame from current files
                records = []
                for fp in getattr(self, 'image_files', []) or []:
                    try:
                        name = os.path.basename(fp)
                        size = os.path.getsize(fp)
                        mtime = os.path.getmtime(fp)
                        records.append({
                            'Name': name,
                            'Size': self.format_size(size),
                            'Date_Modified': self.format_date(mtime),
                            'File_Path': fp,
                        })
                    except Exception:
                        continue

                self.df = pd.DataFrame(records)
            # If somehow df is empty but we have files, rebuild
            if (not isinstance(self.df, pd.DataFrame)) or (self.df.empty and getattr(self, 'image_files', [])):
                records = []
                for fp in getattr(self, 'image_files', []) or []:
                    try:
                        name = os.path.basename(fp)
                        size = os.path.getsize(fp)
                        mtime = os.path.getmtime(fp)
                        records.append({
                            'Name': name,
                            'Size': self.format_size(size),
                            'Date_Modified': self.format_date(mtime),
                            'File_Path': fp,
                        })
                    except Exception:
                        continue
                self.df = pd.DataFrame(records)
            # Add Field_ columns based on max_fields
            if not self.df.empty:
                for i in range(1, int(self.max_fields) + 1):
                    col = f"Field_{i}"
                    if col not in self.df.columns:
                        self.df[col] = ''
                # Populate Field_ values from filename parts
                try:
                    for idx in self.df.index:
                        base = os.path.splitext(self.df.at[idx, 'Name'])[0]
                        parts = base.split('_')
                        for i, part in enumerate(parts, start=1):
                            col = f"Field_{i}"
                            if col in self.df.columns:
                                self.df.at[idx, col] = part
                except Exception:
                    pass

            # Keep a copy for filtering
            self._base_df = self.df.copy() if isinstance(getattr(self, 'df', None), pd.DataFrame) else pd.DataFrame()
            print(f"Table rows prepared: {len(self.df) if isinstance(self.df, pd.DataFrame) else 0}")

            # Rebuild filter toolbar (ensure it persists across layout toggles)
            try:
                if hasattr(self, 'file_toolbar') and self.file_toolbar.winfo_exists():
                    try:
                        self.file_toolbar.destroy()
                    except Exception:
                        pass
                self.file_toolbar = ttk.Frame(self.file_frame)
                self.file_toolbar.pack(fill=tk.X, padx=6, pady=(6, 0))
                ttk.Label(self.file_toolbar, text="Filter:").pack(side=tk.LEFT)
                # Preserve existing text value
                current_query = ''
                try:
                    current_query = (self.filter_text.get() or '')
                except Exception:
                    current_query = ''
                self.filter_entry = ttk.Entry(self.file_toolbar, textvariable=self.filter_text, width=30)
                self.filter_entry.pack(side=tk.LEFT, padx=(6, 0))
                # A clear button
                ttk.Button(self.file_toolbar, text="Clear", command=lambda: self.filter_text.set('')).pack(side=tk.LEFT, padx=6)
                # If there was a query, reapply it (trace will trigger filter)
                if current_query:
                    try:
                        # Force re-set to trigger trace
                        self.filter_text.set(current_query)
                    except Exception:
                        pass
            except Exception:
                pass

            # Recreate container frame under the current file_frame (avoid reusing old parent)
            try:
                if hasattr(self, 'table_frame') and self.table_frame.winfo_exists():
                    try:
                        self.table_frame.destroy()
                    except Exception:
                        pass
                self.table_frame = ttk.Frame(self.file_frame)
                self.table_frame.pack(fill=tk.BOTH, expand=True)
            except Exception:
                self.table_frame = ttk.Frame(self.file_frame)
                self.table_frame.pack(fill=tk.BOTH, expand=True)

            # Create table
            self.table = Table(self.table_frame, dataframe=self.df, showtoolbar=False, showstatusbar=False)
            self.table.show()
            try:
                self.table.multipleselection = True
            except Exception:
                pass

            # Redraw
            self.table.redraw()

            # Bind table selection events to update image grid
            try:
                # Mouse selection
                self.table.bind('<ButtonRelease-1>', self.on_table_select)
                # Keyboard navigation
                self.table.bind('<KeyRelease-Up>', self.on_table_select)
                self.table.bind('<KeyRelease-Down>', self.on_table_select)
                self.table.bind('<KeyRelease-Home>', self.on_table_select)
                self.table.bind('<KeyRelease-End>', self.on_table_select)
                self.table.bind('<KeyRelease-Prior>', self.on_table_select)  # PageUp
                self.table.bind('<KeyRelease-Next>', self.on_table_select)   # PageDown
            except Exception:
                pass

            # Try to restore selection by File_Path
            try:
                if prev_selection_paths and isinstance(self.table.model.df, pd.DataFrame):
                    df_now = self.table.model.df
                    restore_rows = [df_now.index.get_loc(idx) if isinstance(idx, (int,)) else None for idx in []]  # placeholder
                    rows_to_select = []
                    for i in range(len(df_now)):
                        try:
                            if str(df_now.iloc[i]['File_Path']) in prev_selection_paths:
                                rows_to_select.append(i)
                        except Exception:
                            continue
                    if rows_to_select:
                        try:
                            self.table.multiplerowlist = rows_to_select
                        except Exception:
                            # Fallback: select first
                            self.table.setSelectedRow(rows_to_select[0])
            except Exception:
                pass
            print(f"Table rows shown: {len(self.table.model.df) if getattr(self.table, 'model', None) else 0}")
        except Exception as e:
            print(f"Error in setup_file_browser: {e}")
            traceback.print_exc()

    def filter_images(self, *args):
        """Filter the table view by substring across all columns using self.filter_text."""
        try:
            if not isinstance(getattr(self, '_base_df', None), pd.DataFrame) or self._base_df.empty:
                return
            query = ''
            try:
                query = (self.filter_text.get() or '').strip()
            except Exception:
                query = ''
            if not query:
                self.df = self._base_df.copy()
            else:
                q = query.lower()
                mask = self._base_df.apply(lambda col: col.astype(str).str.lower().str.contains(q, na=False))
                rows = mask.any(axis=1)
                self.df = self._base_df[rows].copy()
            if hasattr(self, 'table') and getattr(self.table, 'model', None):
                self.table.model.df = self.df
                self.table.redraw()
        except Exception as e:
            print(f"Error in filter_images: {e}")
            traceback.print_exc()

    def create_grid(self):
        """Create the image grid"""
        print("\n=== Creating grid ===")  # Debug print
        
        # Clear existing grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        
        # Initialize grid cells list
        self.grid_cells = []
        
        # Force update to get current dimensions
        self.update_idletasks()
        grid_width = self.grid_frame.winfo_width()
        grid_height = self.grid_frame.winfo_height()
        
        # Calculate cell dimensions based on available space
        cell_width = max(200, (grid_width - (self.grid_cols * 4)) // self.grid_cols)  # Account for padding
        cell_height = max(200, (grid_height - (self.grid_rows * 4)) // self.grid_rows)
        
        print(f"Grid dimensions: {grid_width}x{grid_height}, Cell size: {cell_width}x{cell_height}")  # Debug print
        
        # Create new grid cells
        for i in range(self.grid_rows):
            row_cells = []
            for j in range(self.grid_cols):
                # Create frame for cell
                cell_frame = ttk.Frame(self.grid_frame, borderwidth=1, relief="solid", width=cell_width, height=cell_height)
                cell_frame.grid(row=i, column=j, sticky="nsew", padx=2, pady=2)
                cell_frame.grid_propagate(False)
                
                # Create label for image
                cell = ttk.Label(cell_frame, background="white")
                cell.place(relx=0.5, rely=0.5, anchor="center")
                
                # Bind click events
                cell_frame.bind("<Button-1>", lambda e, r=i, c=j: self.select_cell(r, c))
                cell.bind("<Button-1>", lambda e, r=i, c=j: self.select_cell(r, c))
                # Right-click context menu to open externally
                cell_frame.bind("<Button-3>", lambda e, r=i, c=j: self._show_cell_context_menu(e, r, c))
                cell.bind("<Button-3>", lambda e, r=i, c=j: self._show_cell_context_menu(e, r, c))
                # Double-click to open with system default
                cell_frame.bind("<Double-Button-1>", lambda e, r=i, c=j: (self._reset_or_open(e, r, c)))
                cell.bind("<Double-Button-1>", lambda e, r=i, c=j: (self._reset_or_open(e, r, c)))
                # Mouse wheel zoom bindings (Windows/macOS/Linux)
                cell.bind("<MouseWheel>", lambda e, r=i, c=j: self._on_mouse_wheel_zoom(e, r, c))
                cell_frame.bind("<MouseWheel>", lambda e, r=i, c=j: self._on_mouse_wheel_zoom(e, r, c))
                cell.bind("<Button-4>", lambda e, r=i, c=j: self._on_mouse_wheel_zoom(e, r, c, linux_dir=1))
                cell.bind("<Button-5>", lambda e, r=i, c=j: self._on_mouse_wheel_zoom(e, r, c, linux_dir=-1))
                cell_frame.bind("<Button-4>", lambda e, r=i, c=j: self._on_mouse_wheel_zoom(e, r, c, linux_dir=1))
                cell_frame.bind("<Button-5>", lambda e, r=i, c=j: self._on_mouse_wheel_zoom(e, r, c, linux_dir=-1))
                # Pan (drag) when zoomed in
                cell.bind("<ButtonPress-1>", lambda e, r=i, c=j: self._on_pan_start(e, r, c))
                cell.bind("<B1-Motion>", lambda e, r=i, c=j: self._on_pan_move(e, r, c))
                cell_frame.bind("<ButtonPress-1>", lambda e, r=i, c=j: self._on_pan_start(e, r, c))
                cell_frame.bind("<B1-Motion>", lambda e, r=i, c=j: self._on_pan_move(e, r, c))
                
                row_cells.append((cell_frame, cell))
            self.grid_cells.append(row_cells)
        
        # Configure grid weights
        for i in range(self.grid_rows):
            self.grid_frame.grid_rowconfigure(i, weight=1)
        for j in range(self.grid_cols):
            self.grid_frame.grid_columnconfigure(j, weight=1)
            
        print(f"Created grid with {self.grid_rows}x{self.grid_cols} cells")  # Debug print

    def on_table_select(self, event=None):
        """Handle selection change in the file table and load the image into the grid.
        Uses the currently displayed DataFrame view (self.table.model.df) and 'File_Path'.
        """
        try:
            if not hasattr(self, 'table') or not getattr(self.table, 'model', None):
                return
            view_df = self.table.model.df
            if not isinstance(view_df, pd.DataFrame) or view_df.empty:
                return

            # Determine selected row from table (prefer multiplerowlist; use first selection)
            sel_rows = []
            try:
                if hasattr(self.table, 'multiplerowlist') and self.table.multiplerowlist:
                    sel_rows = [r for r in self.table.multiplerowlist if isinstance(r, int) and 0 <= r < len(view_df)]
                else:
                    r = self.table.getSelectedRow()
                    if isinstance(r, int) and 0 <= r < len(view_df):
                        sel_rows = [r]
            except Exception:
                pass
            if not sel_rows:
                return

            row = sel_rows[0]
            try:
                fp = str(view_df.iloc[row]['File_Path'])
            except Exception:
                fp = None
            if not fp or not os.path.isfile(fp):
                return

            # If Markdown file, preview it in Markdown tab
            try:
                ext = os.path.splitext(fp)[1].lower()
            except Exception:
                ext = ''
            if ext in ('.md', '.markdown'):
                try:
                    self.md_current_path = fp
                    self.update_markdown_preview()
                    self.activate_markdown_tab()
                except Exception:
                    pass
                return

            # Otherwise, ensure images tab is visible and load image
            try:
                if hasattr(self, 'notebook') and hasattr(self, 'images_tab'):
                    self.notebook.select(self.images_tab)
            except Exception:
                pass

            # Load into currently selected grid cell, or default to (0,0)
            target = getattr(self, 'selected_cell', None)
            if not target:
                target = (0, 0)
            # Before displaying, try to load associated Markdown sidecar for preview
            try:
                self._load_associated_markdown(fp, switch_tab=False)
            except Exception:
                pass
            self._display_image_in_cell(target[0], target[1], fp)
        except Exception as e:
            print(f"Error in on_table_select: {e}")
            traceback.print_exc()

    def _display_image_in_cell(self, row: int, col: int, file_path: str):
        """Open image at file_path, fit it to the target cell, and display it.
        Also sets label.image_path so select_cell() and other features work.
        """
        try:
            if not hasattr(self, 'grid_cells') or not self.grid_cells:
                return
            # Clamp row/col to grid bounds
            row = max(0, min(row, self.grid_rows - 1))
            col = max(0, min(col, self.grid_cols - 1))

            frame, label = self.grid_cells[row][col]
            # Compute fit to cell size (account for padding/border)
            frame.update_idletasks()
            avail_w = max(10, frame.winfo_width() - 8)
            avail_h = max(10, frame.winfo_height() - 8)
            if avail_w <= 0 or avail_h <= 0:
                # Fallback reasonable size
                avail_w, avail_h = 300, 300

            # If the file is a common non-image type, try to render a preview snapshot
            base = os.path.basename(file_path)
            ext = os.path.splitext(base)[1].lower()
            base_img = None
            try:
                if ext == '.pdf':
                    # Track current page per cell/label
                    current_page = getattr(label, 'pdf_page', 0)
                    base_img = self._render_pdf_preview(file_path, max(avail_w, 1200), max(avail_h, 900), page=current_page)
                    # Cache page info on the label for navigation
                    try:
                        label._pdf_page_count = self._get_pdf_page_count(file_path)
                    except Exception:
                        label._pdf_page_count = None
                elif ext == '.svg':
                    base_img = self._render_svg_preview(file_path, max(avail_w, 1200), max(avail_h, 900))
                elif ext in ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.mpg', '.mpeg', '.m4v'):
                    base_img = self._render_video_preview(file_path, target_w=max(avail_w, 800))
                elif ext in ('.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'):
                    base_img = self._render_audio_preview(file_path, width=max(avail_w, 800), height=max(avail_h, 400))
                elif ext in ('.csv', '.tsv'):
                    sep = '\t' if ext == '.tsv' else ','
                    try:
                        preview_df = pd.read_csv(file_path, sep=sep, nrows=50)
                        text = preview_df.to_string(max_rows=50, max_cols=12, show_dimensions=False)
                    except Exception as _e:
                        # Fallback to raw text read
                        text = self._safe_read_text(file_path, max_bytes=65536)
                    base_img = self._render_text_snapshot(text, max(avail_w, 800), max(avail_h, 600), title=base)
                elif ext in ('.txt', '.log', '.json', '.yaml', '.yml', '.ini', '.cfg', '.py', '.md'):
                    text = self._safe_read_text(file_path, max_bytes=65536)
                    base_img = self._render_text_snapshot(text, max(avail_w, 800), max(avail_h, 600), title=base)
                elif ext in ('.xlsx', '.xls'):
                    try:
                        preview_df = pd.read_excel(file_path, sheet_name=0, nrows=30)
                        text = preview_df.to_string(max_rows=30, max_cols=12, show_dimensions=False)
                        base_img = self._render_text_snapshot(text, max(avail_w, 800), max(avail_h, 600), title=base)
                    except Exception as _e:
                        # Likely missing engine (openpyxl). Show a hint.
                        hint = f"Unable to preview Excel. Install 'openpyxl' to enable.\n\nFile: {base}"
                        base_img = self._render_text_snapshot(hint, max(avail_w, 800), max(avail_h, 600), title=base)
            except Exception:
                base_img = None

            if base_img is None:
                # Try to open the file as an image; if it fails, create a placeholder preview
                try:
                    base_img = Image.open(file_path)
                except Exception:
                    # Generate a simple placeholder image with file name and extension
                    from PIL import ImageDraw, ImageFont
                    base_img = Image.new('RGB', (max(10, avail_w), max(10, avail_h)), color='white')
                    draw = ImageDraw.Draw(base_img)
                    title = (base[:40] + '...') if len(base) > 43 else base
                    subtitle = f"{ext or 'file'} preview"
                    try:
                        font_title = ImageFont.load_default()
                        font_sub = ImageFont.load_default()
                        t_w, t_h = draw.textsize(title, font=font_title)
                        s_w, s_h = draw.textsize(subtitle, font=font_sub)
                    except Exception:
                        t_w = s_w = 0
                        t_h = s_h = 0
                        font_title = ImageFont.load_default()
                        font_sub = ImageFont.load_default()
                    t_x = max(4, (base_img.width - t_w) // 2)
                    t_y = max(4, (base_img.height - t_h) // 2 - 10)
                    s_x = max(4, (base_img.width - s_w) // 2)
                    s_y = min(base_img.height - s_h - 4, t_y + t_h + 8)
                    try:
                        draw.rectangle([(0, 0), (base_img.width - 1, base_img.height - 1)], outline='#cccccc')
                    except Exception:
                        pass
                    draw.text((t_x, t_y), title, fill='black', font=font_title)
                    draw.text((s_x, s_y), subtitle, fill='gray', font=font_sub)

            # Compute initial zoom to fit and initial view center
            img_w, img_h = base_img.size
            zoom_fit = min(avail_w / max(1, img_w), avail_h / max(1, img_h))
            zoom_fit = max(0.01, zoom_fit)
            # Initialize view center to image center
            view_cx = img_w // 2
            view_cy = img_h // 2
            # Render to display
            disp_img = self._render_cell_view(base_img, avail_w, avail_h, zoom_fit, zoom_fit, view_cx, view_cy)
            photo = ImageTk.PhotoImage(disp_img)
            label.configure(image=photo)
            label.image = photo  # keep reference
            label.image_path = file_path  # custom attribute used by select_cell()
            # Store base image and zoom for mouse zooming
            label.base_image = base_img
            # Keep file-type specific state on label
            if ext == '.pdf':
                try:
                    if not hasattr(label, 'pdf_page'):
                        label.pdf_page = 0
                except Exception:
                    pass
            label.zoom = zoom_fit
            label.fit_zoom = zoom_fit
            label.zoom_min = 0.05
            label.zoom_max = 10.0
            label.view_cx = view_cx
            label.view_cy = view_cy
            # Pan state
            label._pan_start = None

            # Update current selection and state
            self.select_cell(row, col)
        except Exception as e:
            print(f"Error displaying image in cell: {e}")
            traceback.print_exc()

    # ---- Lightweight renderers for non-image previews ----
    def _ensure_pdf_nav_widgets(self):
        """Create PDF nav controls once. Initially hidden (not packed)."""
        if getattr(self, 'pdf_nav_initialized', False):
            return
        self.pdf_nav_frame = ttk.Frame(self.images_tab)
        self.btn_pdf_prev = ttk.Button(self.pdf_nav_frame, text="◀ Prev", command=self.prev_pdf_page)
        self.lbl_pdf_page = ttk.Label(self.pdf_nav_frame, text="Page -/-")
        self.btn_pdf_next = ttk.Button(self.pdf_nav_frame, text="Next ▶", command=self.next_pdf_page)
        self.btn_pdf_prev.pack(side=tk.LEFT)
        self.lbl_pdf_page.pack(side=tk.LEFT, padx=8)
        self.btn_pdf_next.pack(side=tk.LEFT)
        self.pdf_nav_initialized = True

    def _hide_pdf_controls(self):
        try:
            if hasattr(self, 'pdf_nav_frame') and self.pdf_nav_frame.winfo_ismapped():
                self.pdf_nav_frame.pack_forget()
        except Exception:
            pass

    def _update_pdf_controls(self, label):
        """Show/update pdf nav for the current label if it's a PDF; otherwise hide."""
        try:
            self._ensure_pdf_nav_widgets()
            img_path = getattr(label, 'image_path', None)
            if not img_path or os.path.splitext(img_path)[1].lower() != '.pdf':
                self._hide_pdf_controls()
                return
            total = getattr(label, '_pdf_page_count', None)
            page = getattr(label, 'pdf_page', 0)
            text = f"Page {page + 1}/{total if total is not None else '?'}"
            try:
                self.lbl_pdf_page.configure(text=text)
            except Exception:
                pass
            # Enable/disable buttons
            try:
                can_prev = page > 0
                can_next = (total is None) or (page < max(0, total - 1))
                self.btn_pdf_prev.configure(state=(tk.NORMAL if can_prev else tk.DISABLED))
                self.btn_pdf_next.configure(state=(tk.NORMAL if can_next else tk.DISABLED))
            except Exception:
                pass
            # Show controls above the grid_frame
            try:
                if not self.pdf_nav_frame.winfo_ismapped():
                    self.pdf_nav_frame.pack(in_=self.images_tab, side=tk.TOP, fill=tk.X, padx=10, pady=(6, 0), before=self.grid_frame)
                else:
                    # Ensure it's positioned before the grid_frame
                    self.pdf_nav_frame.pack_forget()
                    self.pdf_nav_frame.pack(in_=self.images_tab, side=tk.TOP, fill=tk.X, padx=10, pady=(6, 0), before=self.grid_frame)
            except Exception:
                pass
        except Exception:
            pass
    def _safe_read_text(self, path: str, max_bytes: int = 65536) -> str:
        try:
            with open(path, 'rb') as f:
                data = f.read(max_bytes)
            return data.decode('utf-8', errors='replace')
        except Exception:
            return "(unable to read file)"

    def _render_text_snapshot(self, text: str, width: int, height: int, title: str = ""):
        from PIL import ImageDraw, ImageFont
        img = Image.new('RGB', (max(10, width), max(10, height)), color='white')
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        line_height = max(12, font.getbbox('Ag')[3] - font.getbbox('Ag')[1]) if hasattr(font, 'getbbox') else 14
        padding = 8
        x = padding
        y = padding
        # title
        if title:
            draw.text((x, y), title, fill='black', font=font)
            y += line_height + 4
            draw.line([(padding, y), (img.width - padding, y)], fill='#dddddd')
            y += 6
        # wrap text based on approximate char width
        try:
            avg_char_w = draw.textlength('M', font=font)
            if not avg_char_w:
                avg_char_w = 7
        except Exception:
            avg_char_w = 7
        max_chars = max(10, int((img.width - 2 * padding) / max(1, avg_char_w)))
        import textwrap
        lines = []
        for paragraph in text.splitlines()[:2000]:
            wrapped = textwrap.wrap(paragraph, width=max_chars, drop_whitespace=False)
            if not wrapped:
                lines.append('')
            else:
                lines.extend(wrapped)
            if len(lines) > 2000:
                break
        # draw lines until we run out of space
        for ln in lines:
            if y + line_height > img.height - padding:
                break
            draw.text((x, y), ln, fill='black', font=font)
            y += line_height
        # border
        try:
            draw.rectangle([(0, 0), (img.width - 1, img.height - 1)], outline='#cccccc')
        except Exception:
            pass
        return img

    # ---- Renderers for additional formats (optional deps) ----
    def _render_pdf_preview(self, path: str, max_w: int, max_h: int, page: int = 0):
        try:
            import fitz  # PyMuPDF
        except Exception:
            hint = "PDF preview requires 'PyMuPDF' (pip install pymupdf)."
            return self._render_text_snapshot(hint, max_w, max_h, title=os.path.basename(path))
        try:
            doc = fitz.open(path)
            if doc.page_count == 0:
                return self._render_text_snapshot("Empty PDF.", max_w, max_h, title=os.path.basename(path))
            # Clamp page index
            p = max(0, min(page, doc.page_count - 1))
            page_obj = doc.load_page(p)
            zoom = 2.0  # 144 dpi approx
            mat = fitz.Matrix(zoom, zoom)
            pix = page_obj.get_pixmap(matrix=mat)
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if mode == "RGBA":
                img = img.convert('RGB')
            # scale down to max_w/h while preserving aspect
            scale = min(max_w / max(1, img.width), max_h / max(1, img.height), 1.0)
            if scale < 1.0:
                try:
                    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
                except Exception:
                    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
            return img
        except Exception as e:
            return self._render_text_snapshot(f"Failed to render PDF: {e}", max_w, max_h, title=os.path.basename(path))

    def _get_pdf_page_count(self, path: str) -> int | None:
        try:
            import fitz  # PyMuPDF
        except Exception:
            return None
        try:
            with fitz.open(path) as doc:
                return int(doc.page_count)
        except Exception:
            return None

    def next_pdf_page(self, event=None):
        """Go to next page of the PDF in the currently selected cell (if any)."""
        try:
            if not getattr(self, 'selected_cell', None):
                return
            r, c = self.selected_cell
            frame, label = self.grid_cells[r][c]
            if not hasattr(label, 'image_path') or not label.image_path:
                return
            _, ext = os.path.splitext(label.image_path)
            if ext.lower() != '.pdf':
                return
            total = getattr(label, '_pdf_page_count', None)
            page = getattr(label, 'pdf_page', 0) + 1
            if total is not None:
                page = min(page, max(0, total - 1))
            label.pdf_page = page
            # Re-render base image for this page and refresh display
            frame.update_idletasks()
            avail_w = max(10, frame.winfo_width() - 8)
            avail_h = max(10, frame.winfo_height() - 8)
            base_img = self._render_pdf_preview(label.image_path, max(avail_w, 1200), max(avail_h, 900), page=page)
            label.base_image = base_img
            # Reset fit zoom and center
            img_w, img_h = base_img.size
            zoom_fit = min(avail_w / max(1, img_w), avail_h / max(1, img_h))
            label.fit_zoom = zoom_fit
            label.zoom = zoom_fit
            label.view_cx = img_w // 2
            label.view_cy = img_h // 2
            self._update_cell_zoom_display(r, c)
            # Update controls text and button states
            try:
                self._update_pdf_controls(label)
            except Exception:
                pass
        except Exception:
            pass

    def prev_pdf_page(self, event=None):
        """Go to previous page of the PDF in the currently selected cell (if any)."""
        try:
            if not getattr(self, 'selected_cell', None):
                return
            r, c = self.selected_cell
            frame, label = self.grid_cells[r][c]
            if not hasattr(label, 'image_path') or not label.image_path:
                return
            _, ext = os.path.splitext(label.image_path)
            if ext.lower() != '.pdf':
                return
            page = max(0, getattr(label, 'pdf_page', 0) - 1)
            label.pdf_page = page
            # Re-render base image for this page and refresh display
            frame.update_idletasks()
            avail_w = max(10, frame.winfo_width() - 8)
            avail_h = max(10, frame.winfo_height() - 8)
            base_img = self._render_pdf_preview(label.image_path, max(avail_w, 1200), max(avail_h, 900), page=page)
            label.base_image = base_img
            # Reset fit zoom and center
            img_w, img_h = base_img.size
            zoom_fit = min(avail_w / max(1, img_w), avail_h / max(1, img_h))
            label.fit_zoom = zoom_fit
            label.zoom = zoom_fit
            label.view_cx = img_w // 2
            label.view_cy = img_h // 2
            self._update_cell_zoom_display(r, c)
            # Update controls text and button states
            try:
                self._update_pdf_controls(label)
            except Exception:
                pass
        except Exception:
            pass

    def _render_svg_preview(self, path: str, max_w: int, max_h: int):
        try:
            import cairosvg
        except Exception:
            hint = "SVG preview requires 'cairosvg' (pip install cairosvg)."
            return self._render_text_snapshot(hint, max_w, max_h, title=os.path.basename(path))
        try:
            png_bytes = cairosvg.svg2png(url=path, output_width=max_w, output_height=max_h, scale=1)
            bio = io.BytesIO(png_bytes)
            img = Image.open(bio).convert('RGB')
            return img
        except Exception as e:
            return self._render_text_snapshot(f"Failed to render SVG: {e}", max_w, max_h, title=os.path.basename(path))

    def _render_video_preview(self, path: str, target_w: int = 800):
        try:
            import cv2
        except Exception:
            hint = "Video preview requires 'opencv-python' (pip install opencv-python)."
            return self._render_text_snapshot(hint, target_w, int(target_w*0.56), title=os.path.basename(path))
        try:
            cap = cv2.VideoCapture(path)
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                return self._render_text_snapshot("Unable to decode first frame.", target_w, int(target_w*0.56), title=os.path.basename(path))
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape
            img = Image.fromarray(frame)
            # scale to target width
            scale = min(target_w / max(1, w), 1.0)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            try:
                img = img.resize((new_w, new_h), Image.LANCZOS)
            except Exception:
                img = img.resize((new_w, new_h))
            return img
        except Exception as e:
            return self._render_text_snapshot(f"Failed to render video: {e}", target_w, int(target_w*0.56), title=os.path.basename(path))

    def _render_audio_preview(self, path: str, width: int = 800, height: int = 400):
        try:
            import librosa
            import numpy as np
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except Exception:
            hint = "Audio preview requires 'librosa' and 'matplotlib' (pip install librosa matplotlib)."
            return self._render_text_snapshot(hint, width, height, title=os.path.basename(path))
        try:
            y, sr = librosa.load(path, mono=True, duration=30.0)
            if y is None or len(y) == 0:
                return self._render_text_snapshot("Unable to load audio.", width, height, title=os.path.basename(path))
            fig = plt.figure(figsize=(width/100, height/100), dpi=100)
            ax = fig.add_subplot(111)
            ax.plot(y, linewidth=0.5)
            ax.set_title(os.path.basename(path))
            ax.set_xlabel('Samples')
            ax.set_ylabel('Amplitude')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            img = Image.open(buf).convert('RGB')
            return img
        except Exception as e:
            return self._render_text_snapshot(f"Failed to render audio: {e}", width, height, title=os.path.basename(path))

    def _render_cell_view(self, base_img, avail_w, avail_h, zoom, fit_zoom, view_cx, view_cy):
        """Render the cell image. If zoom<=fit_zoom, scale whole image to fit; otherwise crop around (view_cx,view_cy)
        to viewport size (avail_w/zoom, avail_h/zoom) and resize to (avail_w,avail_h)."""
        try:
            img_w, img_h = base_img.size
            if zoom <= fit_zoom + 1e-6:
                # full-image fit
                scale = min(avail_w / max(1, img_w), avail_h / max(1, img_h))
                new_w = max(1, int(img_w * scale))
                new_h = max(1, int(img_h * scale))
                try:
                    disp_img = base_img.resize((new_w, new_h), Image.LANCZOS)
                except Exception:
                    disp_img = base_img.resize((new_w, new_h))
                return disp_img
            # zoomed beyond fit -> crop viewport
            vw = max(1, int(avail_w / max(zoom, 1e-6)))
            vh = max(1, int(avail_h / max(zoom, 1e-6)))
            # Clamp center and compute box
            half_vw = vw // 2
            half_vh = vh // 2
            cx = max(half_vw, min(img_w - half_vw, int(view_cx)))
            cy = max(half_vh, min(img_h - half_vh, int(view_cy)))
            left = max(0, cx - half_vw)
            upper = max(0, cy - half_vh)
            right = min(img_w, left + vw)
            lower = min(img_h, upper + vh)
            try:
                cropped = base_img.crop((left, upper, right, lower))
            except Exception:
                cropped = base_img
            try:
                disp_img = cropped.resize((avail_w, avail_h), Image.LANCZOS)
            except Exception:
                disp_img = cropped.resize((avail_w, avail_h))
            return disp_img
        except Exception:
            return base_img

    # ---- Zoom handlers ----
    def _on_mouse_wheel_zoom(self, event, row: int, col: int, linux_dir: int | None = None):
        try:
            if not hasattr(self, 'grid_cells') or not self.grid_cells:
                return
            frame, label = self.grid_cells[row][col]
            if not hasattr(label, 'base_image'):
                return
            # Determine direction: positive for zoom in, negative for zoom out
            delta = 0
            if linux_dir is not None:
                delta = linux_dir  # +1 for Button-4, -1 for Button-5
            else:
                # Windows/mac: event.delta is multiple of 120 typically
                delta = 1 if event.delta > 0 else -1
            # Adjust zoom factor
            factor = 1.1 if delta > 0 else 0.9
            new_zoom = max(getattr(label, 'zoom_min', 0.05), min(getattr(label, 'zoom_max', 10.0), label.zoom * factor))
            if abs(new_zoom - label.zoom) < 1e-3:
                return
            label.zoom = new_zoom
            self._update_cell_zoom_display(row, col)
        except Exception:
            pass

    def _update_cell_zoom_display(self, row: int, col: int):
        try:
            frame, label = self.grid_cells[row][col]
            if not hasattr(label, 'base_image'):
                return
            base_img = label.base_image
            frame.update_idletasks()
            avail_w = max(10, frame.winfo_width() - 8)
            avail_h = max(10, frame.winfo_height() - 8)
            disp_img = self._render_cell_view(base_img, avail_w, avail_h, label.zoom, getattr(label, 'fit_zoom', label.zoom), getattr(label, 'view_cx', base_img.size[0]//2), getattr(label, 'view_cy', base_img.size[1]//2))
            photo = ImageTk.PhotoImage(disp_img)
            label.configure(image=photo)
            label.image = photo
        except Exception:
            pass

    def _on_pan_start(self, event, row: int, col: int):
        try:
            frame, label = self.grid_cells[row][col]
            if not hasattr(label, 'base_image') or label.zoom <= getattr(label, 'fit_zoom', label.zoom):
                label._pan_start = None
                return
            label._pan_start = (event.x_root, event.y_root, label.view_cx, label.view_cy)
        except Exception:
            pass

    def _on_pan_move(self, event, row: int, col: int):
        try:
            frame, label = self.grid_cells[row][col]
            if not getattr(label, '_pan_start', None):
                return
            if label.zoom <= getattr(label, 'fit_zoom', label.zoom):
                return
            sx, sy, start_cx, start_cy = label._pan_start
            dx = event.x_root - sx
            dy = event.y_root - sy
            # Convert screen delta to image-space delta (approx: 1 px move equals 1/zoom in image space)
            label.view_cx = start_cx - int(dx / max(label.zoom, 1e-6))
            label.view_cy = start_cy - int(dy / max(label.zoom, 1e-6))
            # Clamp
            img_w, img_h = label.base_image.size
            vw = max(1, int((frame.winfo_width() - 8) / max(label.zoom, 1e-6)))
            vh = max(1, int((frame.winfo_height() - 8) / max(label.zoom, 1e-6)))
            half_vw, half_vh = vw // 2, vh // 2
            label.view_cx = max(half_vw, min(img_w - half_vw, label.view_cx))
            label.view_cy = max(half_vh, min(img_h - half_vh, label.view_cy))
            self._update_cell_zoom_display(row, col)
        except Exception:
            pass

    def _reset_or_open(self, event, row: int, col: int):
        """Shift+Double-Click resets zoom/pan; otherwise open externally."""
        try:
            if (event.state & 0x0001):  # Shift pressed
                self._reset_cell_zoom(row, col)
            else:
                self._open_cell_file(row, col)
        except Exception:
            self._open_cell_file(row, col)

    def _reset_cell_zoom(self, row: int, col: int):
        try:
            frame, label = self.grid_cells[row][col]
            if not hasattr(label, 'base_image'):
                return
            label.zoom = getattr(label, 'fit_zoom', label.zoom)
            img_w, img_h = label.base_image.size
            label.view_cx = img_w // 2
            label.view_cy = img_h // 2
            self._update_cell_zoom_display(row, col)
        except Exception:
            pass

    def _load_associated_markdown(self, image_path: str, switch_tab: bool = False):
        """If a sidecar markdown file exists for the given image, load it into the preview.
        Looks for files with the same basename and .md or .markdown extensions in the same directory.
        If switch_tab is True, also activates the Markdown tab.
        """
        try:
            if not image_path:
                return
            stem, _ = os.path.splitext(image_path)
            candidates = [stem + ".md", stem + ".markdown"]
            md_path = next((p for p in candidates if os.path.isfile(p)), None)
            if not md_path:
                return
            self.md_current_path = md_path
            self.update_markdown_preview()
            if switch_tab:
                self.activate_markdown_tab()
        except Exception as e:
            logging.debug(f"No associated markdown loaded for {image_path}: {e}")

    def open_with_system_default(self, path: str | None = None):
        """Open the given path (or current selection) with the OS default application."""
        try:
            target = path
            if not target:
                # Prefer the currently selected/displayed file
                target = getattr(self, 'current_image_path', None)
            if not target or not os.path.exists(target):
                # Fallback: try current table selection
                try:
                    if hasattr(self, 'table') and getattr(self.table, 'model', None):
                        view_df = self.table.model.df
                        r = self.table.getSelectedRow()
                        if isinstance(r, int) and 0 <= r < len(view_df):
                            candidate = str(view_df.iloc[r].get('File_Path', ''))
                            if candidate and os.path.exists(candidate):
                                target = candidate
                except Exception:
                    pass
            if not target or not os.path.exists(target):
                messagebox.showinfo("Open", "No file selected to open.")
                return

            if sys.platform.startswith('win'):
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', target])
            else:
                subprocess.Popen(['xdg-open', target])
        except Exception as e:
            messagebox.showerror("Open Externally", f"Failed to open file:\n{e}")

    def _open_cell_file(self, row: int, col: int):
        """Open the file associated with the specified grid cell via system default app."""
        try:
            if not hasattr(self, 'grid_cells') or not self.grid_cells:
                return
            frame, label = self.grid_cells[row][col]
            fp = getattr(label, 'image_path', None)
            if fp and os.path.exists(fp):
                self.open_with_system_default(fp)
        except Exception:
            pass

    def _show_cell_context_menu(self, event, row: int, col: int):
        """Show a context menu for a grid cell with an option to open externally."""
        try:
            if not hasattr(self, '_cell_context_menu'):
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label="Open with Default App", command=lambda: self._open_cell_file(row, col))
                menu.add_command(label="Reset Zoom", command=lambda: self._reset_cell_zoom(row, col))
                self._cell_context_menu = menu
            # Rebuild command to capture current row/col
            try:
                self._cell_context_menu.entryconfig(0, command=lambda: self._open_cell_file(row, col))
                self._cell_context_menu.entryconfig(1, command=lambda: self._reset_cell_zoom(row, col))
            except Exception:
                pass
            self._cell_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._cell_context_menu.grab_release()
            except Exception:
                pass

    def setup_toolbar(self):
        # Grid size controls
        ttk.Label(self.toolbar, text="Grid Size:").pack(side="left", padx=5)

        # Spinbox for rows
        self.rows_var = tk.StringVar(value=str(self.grid_rows))
        rows_spinbox = ttk.Spinbox(self.toolbar, from_=1, to=10, width=3,
                                 textvariable=self.rows_var)
        rows_spinbox.pack(side="left")

        ttk.Label(self.toolbar, text="x").pack(side="left", padx=2)

        # Spinbox for columns
        self.cols_var = tk.StringVar(value=str(self.grid_cols))
        cols_spinbox = ttk.Spinbox(self.toolbar, from_=1, to=10, width=3,
                                 textvariable=self.cols_var)
        cols_spinbox.pack(side="left")

        # Update grid button
        update_btn = ttk.Button(self.toolbar, text="Update Grid",
                              command=self.update_grid_size)
        update_btn.pack(side="left", padx=5)

        # Add toggle layout button
        self.toggle_btn = ttk.Button(
            self.toolbar, 
            text="Switch to Vertical Layout",
            command=self.toggle_layout
        )
        self.toggle_btn.pack(side="left", padx=5)

        # Add browse folder button
        ttk.Button(self.toolbar, text="Browse Folder", 
                  command=self.browse_folder).pack(side="left", padx=5)
                  
        # Add load subfolders button
        ttk.Button(self.toolbar, text="Load Subfolders",
                  command=self.load_subfolders).pack(side="left", padx=5)
                  
        # Add recent folders dropdown
        recent_folders_frame = ttk.Frame(self.toolbar)
        recent_folders_frame.pack(side="left", padx=5)
        
        ttk.Label(recent_folders_frame, text="Recent:").pack(side="left")
        
        # Create StringVar for the dropdown
        self.recent_folders_var = tk.StringVar()
        
        # Create the dropdown menu
        self.recent_folders_dropdown = ttk.Combobox(recent_folders_frame, 
                                                 textvariable=self.recent_folders_var,
                                                 width=30)
        self.recent_folders_dropdown.pack(side="left", padx=2)
        
        # Update the dropdown with recent folders
        self.update_recent_folders_dropdown()
        
        # Bind selection event
        self.recent_folders_dropdown.bind("<<ComboboxSelected>>", self.on_recent_folder_selected)
                  
        # Add move files button
        ttk.Button(self.toolbar, text="Move Files", 
                  command=self.move_selected_files).pack(side="left", padx=5)
                  
        # Add delete files button
        ttk.Button(self.toolbar, text="Delete Files", 
                  command=self.delete_selected_files).pack(side="left", padx=5)

        # Add rename all files button
        ttk.Button(self.toolbar, text="Rename All Files",
                   command=self.rename_all_files).pack(side="left", padx=5)
                   
        # Add rename selected file button
        ttk.Button(self.toolbar, text="Rename Selected",
                   command=self.rename_selected_file).pack(side="left", padx=5)
                   
        # Add search and replace button
        ttk.Button(self.toolbar, text="Search & Replace",
                   command=self.search_replace_filenames).pack(side="left", padx=5)
                   
        # Add annotate button
        ttk.Button(self.toolbar, text="Annotate Image",
                   command=self.toggle_annotation_mode).pack(side="left", padx=5)
                   
        # Add rotate image dropdown menu
        rotate_frame = ttk.Frame(self.toolbar)
        rotate_frame.pack(side="left", padx=5)
        
        ttk.Label(rotate_frame, text="Rotate:").pack(side="left")
        
        # Create rotation options
        self.rotation_options = [
            "90° Clockwise", 
            "180°", 
            "90° Counter-Clockwise",
            "Flip Horizontal",
            "Flip Vertical"
        ]
        
        # Create StringVar for the dropdown
        self.rotation_var = tk.StringVar()
        
        # Create the dropdown menu
        self.rotation_dropdown = ttk.Combobox(rotate_frame, 
                                           textvariable=self.rotation_var,
                                           values=self.rotation_options,
                                           width=15)
        self.rotation_dropdown.pack(side="left", padx=2)
        
        # Bind selection event
        self.rotation_dropdown.bind("<<ComboboxSelected>>", self.on_rotation_selected)

        # Add refresh button
        ttk.Button(self.toolbar, text="Refresh", command=self.refresh_file_list).pack(side="left", padx=5)               

        # Add OCR button
        ttk.Button(self.toolbar, text="OCR to Clipboard",
                  command=self.ocr_current_image).pack(side="left", padx=5)

        # Bind keyboard shortcut for OCR
        self.bind('<Control-Shift-O>', lambda e: self.ocr_current_image())

        # Add Gemini image explanation button
        ttk.Button(self.toolbar, text="Explain (Gemini)",
                   command=self.explain_image_with_gemini).pack(side="left", padx=5)

        # Bind keyboard shortcut for Gemini explanation
        self.bind('<Control-Shift-G>', lambda e: self.explain_image_with_gemini())

        # Add Open Externally button
        ttk.Button(self.toolbar, text="Open Externally",
                   command=lambda: self.open_with_system_default()).pack(side="left", padx=5)

    def ocr_current_image(self):
        """Run OCR on the currently selected image and copy text to clipboard."""
        try:
            # Ensure an image is currently selected/displayed
            image_path = getattr(self, 'current_image_path', None)
            if not image_path or not os.path.exists(image_path):
                messagebox.showinfo("No Image", "Please load an image into a grid cell first.")
                return

            # Import pytesseract lazily
            try:
                import pytesseract
            except ImportError as ie:
                messagebox.showerror(
                    "pytesseract not installed",
                    f"Python: {sys.executable}\nError: {ie}\n"
                    "Please install pytesseract (pip install pytesseract).\n"
                    "Also install Tesseract OCR engine from https://github.com/tesseract-ocr/tesseract"
                )
                return

            # Ensure tesseract is available; try common paths or ask user
            def _ensure_tesseract_cmd() -> bool:
                try:
                    from subprocess import DEVNULL, check_call
                    cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract')
                    check_call([cmd, '--version'], stdout=DEVNULL, stderr=DEVNULL)
                    return True
                except Exception:
                    default_paths = [
                        getattr(self, 'tesseract_cmd_path', None),
                        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
                    ]
                    for exe_path in default_paths:
                        if exe_path and os.path.isfile(exe_path):
                            try:
                                pytesseract.pytesseract.tesseract_cmd = exe_path
                                from subprocess import DEVNULL, check_call
                                check_call([exe_path, '--version'], stdout=DEVNULL, stderr=DEVNULL)
                                self.tesseract_cmd_path = exe_path
                                return True
                            except Exception:
                                continue
                    exe_path = filedialog.askopenfilename(
                        title="Locate tesseract.exe",
                        filetypes=[["Executable", "tesseract.exe"], ["All files", "*"]]
                    )
                    if not exe_path:
                        return False
                    try:
                        pytesseract.pytesseract.tesseract_cmd = exe_path
                        from subprocess import DEVNULL, check_call
                        check_call([exe_path, '--version'], stdout=DEVNULL, stderr=DEVNULL)
                        self.tesseract_cmd_path = exe_path
                        return True
                    except Exception:
                        messagebox.showerror("Tesseract Error", "Selected tesseract.exe is not valid.")
                        return False

            if not _ensure_tesseract_cmd():
                messagebox.showerror(
                    "Tesseract not found",
                    "Tesseract OCR not found. Please install it and/or provide the path to tesseract.exe."
                )
                return

            # Open and preprocess image, or fallback to capturing the Images tab if not an image
            gray = None
            try:
                # Quick extension check to skip obvious non-images
                _ext = os.path.splitext(image_path)[1].lower()
                if _ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.gif', '.webp'):
                    img = Image.open(image_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    gray = img.convert('L')
                else:
                    raise ValueError("Selected file is not an image; will try screen capture of the preview area.")
            except Exception:
                # Fallback: capture the currently visible image widget/canvas region
                try:
                    # Prefer an inner Canvas if present for tighter crop
                    widget = self._find_first_canvas(self.grid_frame) or self.grid_frame
                    cap_img = self._capture_widget_region(widget)
                    if cap_img.mode != 'RGB':
                        cap_img = cap_img.convert('RGB')
                    gray = cap_img.convert('L')
                except Exception as e2:
                    messagebox.showerror("Image Error", f"Failed to open or capture image for OCR: {e2}")
                    return

            # OCR
            try:
                text = pytesseract.image_to_string(gray)
            except Exception as e:
                messagebox.showerror("OCR Error", f"Failed to run OCR: {e}")
                return

            # Clipboard
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
            except Exception as e:
                messagebox.showerror("Clipboard Error", f"Failed to copy text to clipboard: {e}")
                return

            # Feedback
            snippet = (text.strip()[:200] + ('…' if len(text.strip()) > 200 else '')) if text else '(no text)'
            messagebox.showinfo("OCR Complete", f"Extracted text copied to clipboard.\n\nPreview:\n{snippet}")

        except Exception as e:
            logging.error("Unexpected error in ocr_current_image", exc_info=e)
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def explain_image_with_gemini(self):
        """Ask what to send to Gemini (selected file, current Images tab, or area capture),
        send it, and append the response to a markdown file. Also copies the response to clipboard.
        Requires the 'google-generativeai' package and a GOOGLE_API_KEY.
        """
        try:
            # Ask user for source
            choice = simpledialog.askstring(
                "Explain (Gemini)",
                "Choose source to send:\n1) Selected file\n2) Current Images tab\n3) Area of screen\n\nEnter 1/2/3:",
                parent=self
            )
            if not choice:
                return
            choice = choice.strip()

            # Determine image and a representative path (for saving/embedding)
            img = None
            image_path_for_md = None
            current_path = getattr(self, 'current_image_path', None)
            used_file_direct = False

            if choice == '1':
                # Use currently selected file (always associate with its sidecar md)
                if not current_path or not os.path.exists(current_path):
                    messagebox.showinfo("No Image", "Please load an image into a grid cell first.")
                    return
                image_path_for_md = current_path
                try:
                    img = Image.open(current_path)
                    used_file_direct = True
                except Exception:
                    used_file_direct = False

            elif choice == '2':
                # Current Images tab; prefer actual file; if not image, capture widget
                if current_path and os.path.exists(current_path):
                    image_path_for_md = current_path
                    try:
                        img = Image.open(current_path)
                        used_file_direct = True
                    except Exception:
                        used_file_direct = False
                else:
                    used_file_direct = False

            elif choice == '3':
                # Interactive area selection; prefer appending to the selected file's sidecar markdown
                if current_path and os.path.exists(current_path):
                    image_path_for_md = current_path
                if ImageGrab is None:
                    messagebox.showerror("Screen Capture", "PIL.ImageGrab is unavailable on this system.")
                    return
                try:
                    img = self._capture_screen_area()
                except Exception as e:
                    messagebox.showerror("Capture Error", f"Failed to capture area: {e}")
                    return
                if img is None:
                    return
            else:
                messagebox.showinfo("Explain (Gemini)", "Invalid choice. Please enter 1, 2, or 3.")
                return

            # If option 1/2 failed to open image directly, capture widget area but keep association
            if choice in ('1', '2') and not used_file_direct:
                if ImageGrab is None:
                    messagebox.showerror("Screen Capture", "PIL.ImageGrab is unavailable on this system.")
                    return
                try:
                    # Bring Images tab to front and refresh painting
                    try:
                        self.notebook.select(self.images_tab)
                    except Exception:
                        pass
                    self.lift()
                    # Close any lingering Toplevels from the prompt
                    try:
                        for child in self.winfo_children():
                            if isinstance(child, tk.Toplevel):
                                try:
                                    child.destroy()
                                except Exception:
                                    pass
                        try:
                            root = self.nametowidget('.')
                            for child in root.winfo_children():
                                if isinstance(child, tk.Toplevel):
                                    try:
                                        child.destroy()
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    except Exception:
                        pass
                    # Small delay to ensure prompt fully disappears
                    self.update_idletasks()
                    self.update()
                    time.sleep(0.5)
                    self.update_idletasks()
                    self.update()
                    # Prefer inner canvas inside grid_frame if present
                    target = getattr(self, 'grid_frame', None) or self.images_tab
                    canvas = self._find_first_canvas(target)
                    if canvas is not None:
                        target = canvas
                    img = self._capture_widget_region(target)
                except Exception as e:
                    messagebox.showerror("Capture Error", f"Failed to capture Images tab: {e}")
                    return

            # Lazy import google-generativeai
            try:
                import google.generativeai as genai
            except ImportError as ie:
                messagebox.showerror(
                    "Package not installed",
                    f"Python: {sys.executable}\nError: {ie}\n"
                    "Please install the Google Generative AI SDK:\n"
                    "pip install google-generativeai"
                )
                return

            # Get API key
            api_key = (
                getattr(self, 'gemini_api_key', None)
                or os.environ.get('GOOGLE_API_KEY')
                or os.environ.get('GEMINI_API_KEY')
            )
            if not api_key:
                api_key = simpledialog.askstring(
                    "Google Gemini API Key",
                    "Enter your GOOGLE_API_KEY or GEMINI_API_KEY (not stored persistently):",
                    show='*',
                    parent=self
                )
                if not api_key:
                    messagebox.showwarning("API Key Required", "Gemini API key is required to proceed.")
                    return
                self.gemini_api_key = api_key

            # Configure model
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                messagebox.showerror("Gemini Error", f"Failed to configure Gemini client: {e}")
                return

            # Build prompt (Chinese response)
            prompt = (
                "你是一位资深的视觉分析专家。请清晰地解释这张图片的内容。"
                "说明它展示了什么、有哪些重要元素/对象/文本或图表，并给出洞见。"
                "如果是图表/示意图，请描述坐标轴、单位、趋势、异常与结论。"
                "请严格使用中文（简体），并用 Markdown 组织结构（包含标题、小节与要点列表），"
                "最后给出一个简短的小结。"
            )

            # Generate
            try:
                response = model.generate_content([prompt, img])
                explanation = (getattr(response, 'text', '') or '').strip()
            except Exception as e:
                messagebox.showerror("Gemini Error", f"Failed to get response from Gemini: {e}")
                return
            if not explanation:
                messagebox.showinfo("No Response", "Gemini returned no text for this image.")
                return

            # Decide where to save markdown and image (if capture)
            from datetime import datetime as _dt
            timestamp = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
            # Save captured image if we didn't use the file directly (widget/area capture)
            if not used_file_direct:
                # Prefer saving alongside the selected file if we have one; else use current directory
                save_dir = os.path.dirname(image_path_for_md) if image_path_for_md else getattr(self, 'current_directory', os.getcwd())
                fname = _dt.now().strftime('capture_%Y%m%d_%H%M%S.png')
                embed_path = os.path.join(save_dir, fname)
                try:
                    img_rgb = img.convert('RGB') if img.mode != 'RGB' else img
                    img_rgb.save(embed_path)
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save captured image: {e}")
                    return
                file_label = os.path.basename(embed_path)
                path_label = embed_path
            else:
                # Using the selected file directly as the embedded image
                embed_path = image_path_for_md
                file_label = os.path.basename(image_path_for_md)
                path_label = image_path_for_md

            # Resolve markdown path: if we have a selected file association, write to its sidecar; otherwise default file
            if image_path_for_md:
                img_dir = os.path.dirname(image_path_for_md)
                base = os.path.splitext(os.path.basename(image_path_for_md))[0]
                md_path = os.path.join(img_dir, f"{base}.md")
            else:
                save_dir = getattr(self, 'current_directory', os.getcwd())
                md_path = os.path.join(save_dir, 'image_explanation_from_gemini.md')

            self.md_current_path = md_path
            header_needed = not os.path.isfile(md_path) or os.path.getsize(md_path) == 0
            section = (
                ("# Image Explanation (Gemini)\n" if header_needed else "") +
                ("\n" if header_needed else "") +
                f"---\n**File:** {file_label}\n\n**Path:** {path_label}\n\n**Generated:** {timestamp}\n\n" +
                f"![{file_label}]({path_label})\n\n" +
                f"{explanation}\n"
            )

            # Write markdown
            try:
                with open(md_path, 'a', encoding='utf-8') as f:
                    f.write(section)
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to write markdown file: {e}")
                return

            # Clipboard
            try:
                self.clipboard_clear()
                self.clipboard_append(explanation)
                self.update()
            except Exception as e:
                logging.warning("Clipboard copy failed: %s", e)

            logging.info("Gemini explanation appended to %s", md_path)
            self.update_markdown_preview()
            self.activate_markdown_tab()

            # Suggestions and references
            try:
                suggestions = self.fetch_followups(explanation)
            except Exception:
                suggestions = []
            try:
                references = self.fetch_reference_links(explanation)
            except Exception:
                references = []
            try:
                extra_parts = []
                if suggestions:
                    extra_parts.append("\n\n### 建议的后续问题")
                    for q in suggestions:
                        extra_parts.append(f"- {q}")
                if references:
                    extra_parts.append("\n\n### 参考链接")
                    for title, url in references:
                        if title:
                            extra_parts.append(f"- [{title}]({url})")
                        else:
                            extra_parts.append(f"- {url}")
                if extra_parts:
                    with open(self.md_current_path, 'a', encoding='utf-8') as f:
                        f.write("\n".join(extra_parts) + "\n")
                    self.update_markdown_preview()
            except Exception as e:
                logging.warning("Failed to append suggestions/references: %s", e)

            self.render_suggested_questions(suggestions or [])
        except Exception as e:
            logging.error("Unexpected error in explain_image_with_gemini", exc_info=e)
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def _capture_widget_region(self, widget) -> Image.Image:
        """Capture a screenshot of the given widget's visible region and return a PIL Image."""
        self.update_idletasks()
        x = widget.winfo_rootx()
        y = widget.winfo_rooty()
        w = widget.winfo_width()
        h = widget.winfo_height()
        if ImageGrab is None:
            raise RuntimeError("ImageGrab unavailable")
        bbox = (x, y, x + max(1, w), y + max(1, h))
        return ImageGrab.grab(bbox)

    def _find_first_canvas(self, widget) -> Optional[tk.Canvas]:
        """Depth-first search for the first tk.Canvas descendant of the given widget."""
        try:
            # Direct match
            if isinstance(widget, tk.Canvas):
                return widget
            # Search children
            for child in widget.winfo_children():
                if isinstance(child, tk.Canvas):
                    return child
                found = self._find_first_canvas(child)
                if found is not None:
                    return found
        except Exception:
            pass
        return None

    def _capture_screen_area(self) -> Optional[Image.Image]:
        """Let user draw a rectangle on screen and capture that region. Returns PIL Image or None."""
        if ImageGrab is None:
            raise RuntimeError("ImageGrab unavailable")
        sel = {'x0': 0, 'y0': 0, 'x1': 0, 'y1': 0}

        top = tk.Toplevel(self)
        top.attributes('-fullscreen', True)
        try:
            top.attributes('-alpha', 0.2)
        except Exception:
            pass
        top.attributes('-topmost', True)
        top.configure(bg='black')
        canvas = tk.Canvas(top, cursor='cross', bg='gray90', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        rect_id = {'id': None}

        def on_down(e):
            sel['x0'], sel['y0'] = e.x_root, e.y_root
            sel['x1'], sel['y1'] = e.x_root, e.y_root
            if rect_id['id'] is not None:
                canvas.delete(rect_id['id'])
            rect_id['id'] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline='red', width=2)

        def on_move(e):
            sel['x1'], sel['y1'] = e.x_root, e.y_root
            if rect_id['id'] is not None:
                canvas.coords(rect_id['id'], sel['x0'] - top.winfo_rootx(), sel['y0'] - top.winfo_rooty(), e.x, e.y)

        def on_up(e):
            sel['x1'], sel['y1'] = e.x_root, e.y_root
            top.destroy()

        canvas.bind('<ButtonPress-1>', on_down)
        canvas.bind('<B1-Motion>', on_move)
        canvas.bind('<ButtonRelease-1>', on_up)
        # Cancel with Esc
        top.bind('<Escape>', lambda e: (top.destroy()))

        # Block until selection done
        self.wait_window(top)

        x0, y0, x1, y1 = sel['x0'], sel['y0'], sel['x1'], sel['y1']
        if (x0, y0) == (x1, y1):
            return None
        # Normalize bbox
        left, right = sorted([x0, x1])
        topy, bottom = sorted([y0, y1])
        bbox = (left, topy, right, bottom)
        return ImageGrab.grab(bbox)

    def fetch_reference_links(self, context_text):
        """Ask Gemini for 3-7 reference links as JSON. Returns list of (title, url)."""
        try:
            model = self._ensure_gemini_model()
        except Exception as e:
            logging.warning("fetch_reference_links: model unavailable: %s", e)
            return []

        prompt = (
            "基于以下内容，给出3到7条可供参考的链接（权威来源优先）。"
            "输出要求：严格为JSON数组字符串。每个元素为对象，包含 'title' 和 'url' 两个字段；"
            "如果无法提供title，可以仅输出url字符串。不得输出额外文字。\n\n"
            f"内容：\n{context_text}"
        )
        try:
            resp = model.generate_content([prompt])
            text = (getattr(resp, 'text', '') or '').strip()
        except Exception as e:
            logging.warning("fetch_reference_links: generation failed: %s", e)
            return []

        # Try to parse different JSON shapes
        def _extract_json(s):
            try:
                return json.loads(s)
            except Exception:
                try:
                    i = s.find('[')
                    j = s.rfind(']')
                    if i != -1 and j != -1 and j > i:
                        return json.loads(s[i:j+1])
                except Exception:
                    pass
            return []

        data = _extract_json(text)
        out = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    title = str(item.get('title') or '').strip()
                    url = str(item.get('url') or '').strip()
                    if url:
                        out.append((title, url))
                elif isinstance(item, str):
                    url = item.strip()
                    if url:
                        out.append(("", url))
                if len(out) >= 7:
                    break
        return out

    def fetch_followups(self, context_text):
        """Ask Gemini for 3-5 concise follow-up questions (Chinese), returned as a JSON array."""
        try:
            model = self._ensure_gemini_model()
        except Exception as e:
            logging.warning("fetch_followups: model unavailable: %s", e)
            return []

        prompt = (
            "请基于以下内容，给出3到5个简短的后续追问（用于更深入分析或澄清）。"
            "要求：严格输出JSON数组字符串，每个元素是中文问题字符串，不要添加任何多余文字。\n\n"
            f"内容：\n{context_text}"
        )
        try:
            resp = model.generate_content([prompt])
            text = (getattr(resp, 'text', '') or '').strip()
        except Exception as e:
            logging.warning("fetch_followups: generation failed: %s", e)
            return []

        # Parse as JSON array; try robust extraction
        def _parse_json_array(s):
            try:
                return json.loads(s)
            except Exception:
                try:
                    start = s.find('[')
                    end = s.rfind(']')
                    if start != -1 and end != -1 and end > start:
                        return json.loads(s[start:end+1])
                except Exception:
                    pass
            return []

        arr = _parse_json_array(text)
        # Normalize and limit 3-5
        out = []
        for q in arr:
            if isinstance(q, str):
                q = q.strip()
                if q:
                    out.append(q)
            if len(out) >= 5:
                break
        return out[:5]

    def render_suggested_questions(self, questions):
        """Render follow-up questions as buttons under the preview controls."""
        frame = getattr(self, '_md_suggest_frame', None)
        if frame is None:
            return
        # Clear existing
        for child in frame.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
        if not questions:
            return
        # Title
        ttk.Label(frame, text="建议的后续问题：").pack(anchor='w')
        # Buttons
        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X)
        for q in questions:
            ttk.Button(btns, text=q, command=lambda t=q: self.ask_follow_up(t)).pack(side=tk.LEFT, padx=4, pady=2)

    def ask_follow_up(self, question_text: str):
        """Populate the chat entry with the question and send it."""
        try:
            self.chat_var.set(question_text)
            self.send_md_chat()
        except Exception as e:
            logging.warning("ask_follow_up failed: %s", e)

    def reconstruct_filename(self, row):
        """Reconstruct filename from columns starting with 'Field_'.
        Keeps the original file extension from `row['Name']`.
        """
        try:
            import pandas as _pd  # local import to avoid top-level dependency if unused
            f_columns = [col for col in row.index if str(col).startswith('Field_')]
            # Extract non-empty values in order
            parts = [str(row[col]) for col in f_columns if _pd.notna(row[col]) and str(row[col]).strip()]
            current_name = str(row['Name'])
            _base, ext = os.path.splitext(current_name)
            new_filename = ('_'.join(parts)).replace('\n', '') + ext
            return new_filename
        except Exception:
            # Fallback to original name if anything goes wrong
            try:
                return str(row['Name'])
            except Exception:
                return ""

    def rename_csv_file(self, old_filepath, new_filename):
        """Rename a file on disk and return the new absolute path.
        Preserves directory of `old_filepath`. On failure, returns `old_filepath`.
        Also renames paired sidecar markdown if it exists and shares the same stem.
        """
        try:
            directory = os.path.dirname(old_filepath)
            old_filename = os.path.basename(old_filepath)
            new_filepath = os.path.join(directory, new_filename)

            # If destination exists, confirm overwrite
            if os.path.exists(new_filepath):
                if not messagebox.askyesno(
                    "Overwrite File",
                    f"{new_filename} already exists. Overwrite?"
                ):
                    return old_filepath
                try:
                    os.remove(new_filepath)
                except Exception:
                    pass

            # Move/rename image
            os.rename(old_filepath, new_filepath)

            # Try renaming paired markdown if present: <old_stem>.md -> <new_stem>.md
            try:
                old_stem, _old_ext = os.path.splitext(old_filename)
                new_stem, _new_ext = os.path.splitext(new_filename)
                old_md = os.path.join(directory, f"{old_stem}.md")
                new_md = os.path.join(directory, f"{new_stem}.md")
                if os.path.isfile(old_md):
                    # Apply same overwrite policy for markdown
                    if os.path.exists(new_md):
                        try:
                            os.remove(new_md)
                        except Exception:
                            pass
                    os.rename(old_md, new_md)
                # Update current markdown pointer if it was pointing to the old md
                try:
                    if getattr(self, 'md_current_path', None) == old_md:
                        self.md_current_path = new_md
                        if hasattr(self, 'update_markdown_preview'):
                            self.update_markdown_preview()
                except Exception:
                    pass
            except Exception:
                # Non-fatal if sidecar rename fails
                pass

            return new_filepath
        except Exception as e:
            logging.warning("Error renaming file: %s", e)
            return old_filepath

    def rename_all_files(self):
        """Rename all files where constructed name differs from current name"""
        try:
            renamed_count = 0
            # ... (rest of the code remains the same)
            for idx, row in self.df.iterrows():
                current_name = row['Name']
                new_name = self.reconstruct_filename(row)
                
                if new_name != current_name:
                    old_path = row['File_Path']
                    new_path = self.rename_csv_file(old_path, new_name)
                    
                    # Update the DataFrame
                    self.df.at[idx, 'Name'] = new_name
                    self.df.at[idx, 'File_Path'] = new_path
                    
                    # Update Field_ columns if they exist
                    name_without_ext = os.path.splitext(new_name)[0]
                    fields = name_without_ext.split('_')
                    for i, field in enumerate(fields):
                        field_name = f"Field_{i+1}"
                        if field_name in self.df.columns:
                            self.df.at[idx, field_name] = field
                    
                    renamed_count += 1
        
            if renamed_count > 0:
                # Update the table display
                self.table.model.df = self.df
                self.table.redraw()
                messagebox.showinfo("Files Renamed", 
                                 f"Renamed {renamed_count} files based on field values")
            else:
                messagebox.showinfo("No Changes", 
                                 "All filenames already match their field values")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename files: {str(e)}")

    def search_replace_filenames(self):
        """Search and replace strings in selected filenames"""
        try:
            # Get selected rows
            selected_rows = self.table.multiplerowlist
            if not selected_rows:
                messagebox.showinfo("No Selection", "Please select at least one file to rename")
                return
                
            # Get search and replace strings
            search_dialog = tk.Toplevel(self)
            search_dialog.title("Search and Replace in Filenames")
            search_dialog.geometry("400x180")
            search_dialog.resizable(False, False)
            search_dialog.transient(self)  # Set to be on top of the main window
            search_dialog.grab_set()  # Modal dialog
            
            # Center the dialog
            search_dialog.update_idletasks()
            width = search_dialog.winfo_width()
            height = search_dialog.winfo_height()
            x = (search_dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (search_dialog.winfo_screenheight() // 2) - (height // 2)
            search_dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create frame for content
            content_frame = ttk.Frame(search_dialog, padding="10")
            content_frame.pack(fill="both", expand=True)
            
            # Search string
            ttk.Label(content_frame, text="Search for:").grid(row=0, column=0, sticky="w", pady=(0, 5))
            search_var = tk.StringVar()
            search_entry = ttk.Entry(content_frame, width=30, textvariable=search_var)
            search_entry.grid(row=0, column=1, sticky="ew", pady=(0, 5), padx=(5, 0))
            search_entry.focus_set()
            
            # Replace string
            ttk.Label(content_frame, text="Replace with:").grid(row=1, column=0, sticky="w", pady=(0, 5))
            replace_var = tk.StringVar()
            replace_entry = ttk.Entry(content_frame, width=30, textvariable=replace_var)
            replace_entry.grid(row=1, column=1, sticky="ew", pady=(0, 5), padx=(5, 0))
            
            # Case sensitive option
            case_sensitive_var = tk.BooleanVar(value=False)
            case_check = ttk.Checkbutton(content_frame, text="Case sensitive", variable=case_sensitive_var)
            case_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 10))
            
            # Preview only option
            preview_var = tk.BooleanVar(value=True)
            preview_check = ttk.Checkbutton(content_frame, text="Preview changes before applying", variable=preview_var)
            preview_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))
            
            # Buttons frame
            buttons_frame = ttk.Frame(content_frame)
            buttons_frame.grid(row=4, column=0, columnspan=2, sticky="e")
            
            # Cancel button
            ttk.Button(buttons_frame, text="Cancel", command=search_dialog.destroy).pack(side="right", padx=(5, 0))
            
            # OK button
            def on_ok():
                search_str = search_var.get()
                replace_str = replace_var.get()
                case_sensitive = case_sensitive_var.get()
                preview_only = preview_var.get()
                
                if not search_str:
                    messagebox.showwarning("Missing Input", "Please enter a search string")
                    return
                    
                search_dialog.destroy()
                
                # Process the search and replace
                self._process_search_replace(search_str, replace_str, case_sensitive, preview_only, selected_rows)
                
            ttk.Button(buttons_frame, text="OK", command=on_ok).pack(side="right", padx=(5, 0))
            
            # Make dialog modal
            search_dialog.wait_window()
            
        except Exception as e:
            print(f"Error in search_replace_filenames: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def _process_search_replace(self, search_str, replace_str, case_sensitive, preview_only, selected_rows):
        """Process the search and replace operation on selected filenames"""
        try:
            # Get the currently displayed DataFrame
            displayed_df = self.table.model.df
            
            # Create a list to store preview information
            preview_data = []
            
            # Process each selected row
            for row in selected_rows:
                if row >= len(displayed_df):
                    continue
                    
                current_name = displayed_df.iloc[row]['Name']
                file_path = displayed_df.iloc[row]['File_Path']
                
                # Get file name and extension separately
                file_name, file_ext = os.path.splitext(current_name)
                
                # Perform the search and replace on the filename (not the extension)
                if case_sensitive:
                    new_name = file_name.replace(search_str, replace_str)
                else:
                    # Case-insensitive replace (using regex)
                    import re
                    pattern = re.compile(re.escape(search_str), re.IGNORECASE)
                    new_name = pattern.sub(replace_str, file_name)
                
                # Add extension back
                new_name = new_name + file_ext
                
                # If the name changed, add to preview
                if new_name != current_name:
                    preview_data.append((row, current_name, new_name, file_path))
            
            # If no changes found
            if not preview_data:
                messagebox.showinfo("No Changes", "No filenames matched the search criteria")
                return
                
            # If preview is requested, show preview dialog
            if preview_only:
                self._show_rename_preview(preview_data)
            else:
                # Apply changes directly
                self._apply_filename_changes(preview_data)
                
        except Exception as e:
            print(f"Error in _process_search_replace: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def _show_rename_preview(self, preview_data):
        """Show preview of filename changes before applying"""
        try:
            # Create preview dialog
            preview_dialog = tk.Toplevel(self)
            preview_dialog.title("Rename Preview")
            preview_dialog.geometry("600x400")
            preview_dialog.transient(self)  # Set to be on top of the main window
            preview_dialog.grab_set()  # Modal dialog
            
            # Center the dialog
            preview_dialog.update_idletasks()
            width = preview_dialog.winfo_width()
            height = preview_dialog.winfo_height()
            x = (preview_dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (preview_dialog.winfo_screenheight() // 2) - (height // 2)
            preview_dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create frame for content
            content_frame = ttk.Frame(preview_dialog, padding="10")
            content_frame.pack(fill="both", expand=True)
            
            # Add label
            ttk.Label(content_frame, text=f"The following {len(preview_data)} file(s) will be renamed:").pack(anchor="w", pady=(0, 10))
            
            # Create treeview for preview
            columns = ("current", "new")
            tree = ttk.Treeview(content_frame, columns=columns, show="headings")
            tree.heading("current", text="Current Name")
            tree.heading("new", text="New Name")
            tree.column("current", width=250)
            tree.column("new", width=250)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack treeview and scrollbar
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Add data to treeview
            for row, current_name, new_name, _ in preview_data:
                tree.insert("", "end", values=(current_name, new_name))
            
            # Buttons frame
            buttons_frame = ttk.Frame(preview_dialog)
            buttons_frame.pack(fill="x", pady=10, padx=10)
            
            # Cancel button
            ttk.Button(buttons_frame, text="Cancel", command=preview_dialog.destroy).pack(side="right", padx=(5, 0))
            
            # Apply button
            def on_apply():
                preview_dialog.destroy()
                self._apply_filename_changes(preview_data)
                
            ttk.Button(buttons_frame, text="Apply Changes", command=on_apply).pack(side="right", padx=(5, 0))
            
            # Make dialog modal
            preview_dialog.wait_window()
            
        except Exception as e:
            print(f"Error in _show_rename_preview: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def _apply_filename_changes(self, preview_data):
        """Apply the filename changes"""
        try:
            success_count = 0
            error_count = 0
            
            for row, current_name, new_name, file_path in preview_data:
                try:
                    # Get the directory path
                    dir_path = os.path.dirname(file_path)
                    new_path = os.path.join(dir_path, new_name)
                    
                    # Rename the file
                    os.rename(file_path, new_path)
                    
                    # Update the DataFrame
                    # Find the row in the original DataFrame
                    orig_idx = self.df[self.df['File_Path'] == file_path].index
                    if len(orig_idx) > 0:
                        # Update the DataFrame
                        self.df.loc[orig_idx[0], 'Name'] = new_name
                        self.df.loc[orig_idx[0], 'File_Path'] = new_path
                        
                        # Update Field_ columns if they exist
                        name_without_ext = os.path.splitext(new_name)[0]
                        fields = name_without_ext.split('_')
                        for i, field in enumerate(fields):
                            field_name = f"Field_{i+1}"
                            if field_name in self.df.columns:
                                self.df.loc[orig_idx[0], field_name] = field
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"Error renaming {current_name} to {new_name}: {e}")
                    error_count += 1
            
            # Refresh the file list
            self.refresh_file_list()
            
            # Show result message
            if error_count == 0:
                messagebox.showinfo("Rename Complete", f"Successfully renamed {success_count} file(s)")
            else:
                messagebox.showwarning("Rename Partial", 
                                     f"Renamed {success_count} file(s), but {error_count} file(s) could not be renamed. See console for details.")
                
        except Exception as e:
            print(f"Error in _apply_filename_changes: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def toggle_annotation_mode(self):
        """Toggle annotation mode on/off and show annotation toolbar"""
        if self.selected_cell is None or self.original_image is None:
            messagebox.showinfo("No Image Selected", "Please select an image to annotate first")
            return
            
        self.annotation_mode = not self.annotation_mode
        
        # If turning on annotation mode, show annotation toolbar
        if self.annotation_mode:
            self.show_annotation_toolbar()
            # Update bindings for all cells when entering annotation mode
            self.update_all_cell_bindings()
        else:
            # Hide annotation toolbar if it exists
            if hasattr(self, 'annotation_toolbar'):
                self.annotation_toolbar.destroy()
                delattr(self, 'annotation_toolbar')
                
            # Restore bindings for all cells when exiting annotation mode
            self.restore_all_cell_bindings()
    
    def show_annotation_toolbar(self):
        """Show the annotation toolbar with annotation options"""
        # Create annotation toolbar if it doesn't exist
        if hasattr(self, 'annotation_toolbar'):
            self.annotation_toolbar.destroy()
            
        # Create a new toolbar for annotation options and place it below the main toolbar
        # Make it visually distinct with a border
        self.annotation_toolbar = ttk.LabelFrame(self.main_container, text="Annotation Tools")
        self.annotation_toolbar.pack(fill="x", padx=5, pady=5, after=self.toolbar)
        
        # Add annotation type selector
        ttk.Label(self.annotation_toolbar, text="Type:").pack(side="left", padx=(0, 5))
        
        # Create annotation type combobox
        self.annotation_type_var = tk.StringVar(value=self.annotation_type)
        type_combo = ttk.Combobox(self.annotation_toolbar, textvariable=self.annotation_type_var, 
                                 values=["text", "arrow", "rectangle", "circle"], width=10)
        type_combo.pack(side="left", padx=5)
        type_combo.bind("<<ComboboxSelected>>", self.on_annotation_type_change)
        
        # Add color selector
        ttk.Label(self.annotation_toolbar, text="Color:").pack(side="left", padx=(10, 5))
        
        # Create color combobox
        self.annotation_color_var = tk.StringVar(value=self.annotation_color)
        color_combo = ttk.Combobox(self.annotation_toolbar, textvariable=self.annotation_color_var,
                                  values=["red", "blue", "green", "yellow", "black", "white"], width=10)
        color_combo.pack(side="left", padx=5)
        color_combo.bind("<<ComboboxSelected>>", self.on_annotation_color_change)
        
        # Add text entry for text annotations
        ttk.Label(self.annotation_toolbar, text="Text:").pack(side="left", padx=(10, 5))
        self.annotation_text_var = tk.StringVar()
        text_entry = ttk.Entry(self.annotation_toolbar, textvariable=self.annotation_text_var, width=20)
        text_entry.pack(side="left", padx=5)
        
        # Add selection mode toggle button
        self.selection_mode_var = tk.BooleanVar(value=self.selection_mode)
        selection_check = ttk.Checkbutton(self.annotation_toolbar, text="Selection Mode",
                                        variable=self.selection_mode_var,
                                        command=self.toggle_selection_mode)
        selection_check.pack(side="left", padx=(10, 5))
        
        # Add delete selected annotation button
        ttk.Button(self.annotation_toolbar, text="Delete Selected", 
                  command=self.delete_selected_annotation).pack(side="left", padx=5)
        
        # Add clear annotations button
        ttk.Button(self.annotation_toolbar, text="Clear All", 
                  command=self.clear_annotations).pack(side="right", padx=5)
        
        # Add save annotations button
        ttk.Button(self.annotation_toolbar, text="Save Annotations", 
                  command=self.save_annotations).pack(side="right", padx=5)
        
        # Add save annotated image button
        ttk.Button(self.annotation_toolbar, text="Save Image", 
                  command=self.save_annotated_image).pack(side="right", padx=5)
        
        # Update the image display to show any existing annotations
        self.show_annotations()
        
        # Update event bindings for the selected cell
        self.update_annotation_bindings()
    
    def on_annotation_type_change(self, event):
        """Handle change of annotation type"""
        self.annotation_type = self.annotation_type_var.get()
    
    def on_annotation_color_change(self, event):
        """Handle change of annotation color"""
        self.annotation_color = self.annotation_color_var.get()
    
    def toggle_selection_mode(self):
        """Toggle between selection mode and creation mode"""
        self.selection_mode = self.selection_mode_var.get()
        self.selected_annotation = None  # Clear any selected annotation
        self.update_annotation_bindings()
        self.show_annotations()  # Refresh to show/hide selection highlights
        
    def delete_selected_annotation(self):
        """Delete the currently selected annotation"""
        if self.selected_annotation is None or self.current_image_path is None:
            messagebox.showinfo("No Selection", "Please select an annotation to delete first")
            return
            
        if self.current_image_path in self.annotations:
            # Find and remove the selected annotation
            try:
                self.annotations[self.current_image_path].remove(self.selected_annotation)
                self.selected_annotation = None
                self.show_annotations()
                messagebox.showinfo("Annotation Deleted", "The selected annotation has been deleted")
            except ValueError:
                # This shouldn't happen, but just in case
                messagebox.showinfo("Error", "Could not find the selected annotation")
    
    def update_annotation_bindings(self):
        """Update mouse event bindings for annotation"""
        if self.selected_cell is None:
            return
            
        row, col = self.selected_cell
        frame, label = self.grid_cells[row][col]
        
        # Remove existing bindings
        label.unbind('<ButtonPress-1>')
        label.unbind('<B1-Motion>')
        label.unbind('<ButtonRelease-1>')
        label.unbind('<Control-ButtonPress-1>')
        label.unbind('<Control-B1-Motion>')
        
        if self.annotation_mode:
            if self.selection_mode:
                # Add selection and movement bindings
                label.bind('<ButtonPress-1>', self.start_annotation_selection)
                label.bind('<B1-Motion>', self.move_selected_annotation)
                label.bind('<ButtonRelease-1>', self.finish_annotation_movement)
            else:
                # Add annotation creation bindings
                label.bind('<ButtonPress-1>', self.start_annotation)
                label.bind('<B1-Motion>', self.update_annotation)
                label.bind('<ButtonRelease-1>', self.finish_annotation)
        else:
            # Add back cell selection binding
            label.bind('<ButtonPress-1>', lambda e, r=row, c=col: self.select_cell(r, c))
            
            # Add back panning bindings (with Control key)
            label.bind('<Control-ButtonPress-1>', self.start_pan)
            label.bind('<Control-B1-Motion>', self.pan_image)
            label.bind('<ButtonRelease-1>', self.stop_pan)
            
            # Add back zoom binding
            label.bind('<MouseWheel>', self.on_mouse_wheel)
            
    def restore_all_cell_bindings(self):
        """Restore event bindings for all cells in the grid"""
        print("Restoring bindings for all cells")  # Debug print
        
        # Loop through all cells in the grid
        for i in range(self.grid_rows):
            for j in range(self.grid_cols):
                # Get the frame and label for this cell
                frame, label = self.grid_cells[i][j]
                
                # Remove any existing bindings
                label.unbind('<ButtonPress-1>')
                label.unbind('<B1-Motion>')
                label.unbind('<ButtonRelease-1>')
                label.unbind('<Control-ButtonPress-1>')
                label.unbind('<Control-B1-Motion>')
                
                # Restore cell selection binding
                frame.bind('<Button-1>', lambda e, r=i, c=j: self.select_cell(r, c))
                label.bind('<Button-1>', lambda e, r=i, c=j: self.select_cell(r, c))
                
                # Restore panning bindings (with Control key)
                label.bind('<Control-ButtonPress-1>', self.start_pan)
                label.bind('<Control-B1-Motion>', self.pan_image)
                label.bind('<ButtonRelease-1>', self.stop_pan)
                
                # Restore zoom binding
                label.bind('<MouseWheel>', self.on_mouse_wheel)
                
    def update_all_cell_bindings(self):
        """Update event bindings for all cells in the grid for annotation mode"""
        print("Updating bindings for all cells for annotation mode")  # Debug print
        
        # Loop through all cells in the grid
        for i in range(self.grid_rows):
            for j in range(self.grid_cols):
                # Get the frame and label for this cell
                frame, label = self.grid_cells[i][j]
                
                # Remove any existing bindings
                label.unbind('<ButtonPress-1>')
                label.unbind('<B1-Motion>')
                label.unbind('<ButtonRelease-1>')
                label.unbind('<Control-ButtonPress-1>')
                label.unbind('<Control-B1-Motion>')
                
                # First add cell selection binding to the frame and label
                frame.bind('<Button-1>', lambda e, r=i, c=j: self.select_cell(r, c))
                
                # Then add annotation bindings to the label
                if self.selection_mode:
                    # Add selection and movement bindings
                    label.bind('<ButtonPress-1>', self.start_annotation_selection)
                    label.bind('<B1-Motion>', self.move_selected_annotation)
                    label.bind('<ButtonRelease-1>', self.finish_annotation_movement)
                else:
                    # Add annotation creation bindings
                    label.bind('<ButtonPress-1>', self.start_annotation)
                    label.bind('<B1-Motion>', self.update_annotation)
                    label.bind('<ButtonRelease-1>', self.finish_annotation)
                
                # Keep zoom binding
                label.bind('<MouseWheel>', self.on_mouse_wheel)
            
    def start_annotation_selection(self, event):
        """Start selecting an annotation"""
        if not self.annotation_mode or not self.selection_mode or self.current_image_path is None:
            return
            
        # Store click position
        self.move_start_x = event.x
        self.move_start_y = event.y
        
        # Find if we clicked on an annotation
        if self.current_image_path in self.annotations:
            # Check each annotation to see if it was clicked
            for annotation in self.annotations[self.current_image_path]:
                if self._is_point_in_annotation(event.x, event.y, annotation):
                    self.selected_annotation = annotation
                    self.is_moving_annotation = True
                    break
            else:  # No annotation found
                self.selected_annotation = None
                
            # Redraw to show selection highlight
            self.show_annotations()
            
    def move_selected_annotation(self, event):
        """Move the selected annotation"""
        if not self.annotation_mode or not self.selection_mode or not self.is_moving_annotation:
            return
            
        if self.selected_annotation is None:
            return
            
        # Calculate movement delta
        dx = event.x - self.move_start_x
        dy = event.y - self.move_start_y
        
        # Update annotation position based on type
        if self.selected_annotation["type"] == "text":
            self.selected_annotation["x"] += dx
            self.selected_annotation["y"] += dy
        elif self.selected_annotation["type"] in ["arrow", "rectangle", "circle"]:
            self.selected_annotation["start_x"] += dx
            self.selected_annotation["start_y"] += dy
            self.selected_annotation["end_x"] += dx
            self.selected_annotation["end_y"] += dy
            
        # Update start position for next movement
        self.move_start_x = event.x
        self.move_start_y = event.y
        
        # Redraw annotations
        self.show_annotations()
        
    def finish_annotation_movement(self, event):
        """Finish moving the selected annotation"""
        self.is_moving_annotation = False
        
    def _is_point_in_annotation(self, x, y, annotation):
        """Check if a point (x,y) is within an annotation"""
        # Different hit testing based on annotation type
        if annotation["type"] == "text":
            # For text, use a small rectangle around the text position
            text_x, text_y = annotation["x"], annotation["y"]
            # Approximate text size - could be improved with actual text measurements
            text_width = len(annotation["text"]) * 8  # Rough estimate of text width
            text_height = 20  # Rough estimate of text height
            
            return (text_x <= x <= text_x + text_width and 
                    text_y <= y <= text_y + text_height)
                    
        elif annotation["type"] == "arrow":
            # For arrows, check if point is close to the line
            return self._point_line_distance(x, y, 
                                            annotation["start_x"], annotation["start_y"],
                                            annotation["end_x"], annotation["end_y"]) < 10
                                            
        elif annotation["type"] == "rectangle":
            # For rectangles, check if point is inside or close to edges
            x1, y1 = min(annotation["start_x"], annotation["end_x"]), min(annotation["start_y"], annotation["end_y"])
            x2, y2 = max(annotation["start_x"], annotation["end_x"]), max(annotation["start_y"], annotation["end_y"])
            
            # Check if point is inside rectangle with some margin
            margin = 5
            return (x1 - margin <= x <= x2 + margin and 
                    y1 - margin <= y <= y2 + margin)
                    
        elif annotation["type"] == "circle":
            # For circles, check if point is inside or close to the edge
            center_x = (annotation["start_x"] + annotation["end_x"]) / 2
            center_y = (annotation["start_y"] + annotation["end_y"]) / 2
            radius_x = abs(annotation["end_x"] - annotation["start_x"]) / 2
            radius_y = abs(annotation["end_y"] - annotation["start_y"]) / 2
            
            # Normalize to unit circle
            dx = (x - center_x) / radius_x if radius_x > 0 else 0
            dy = (y - center_y) / radius_y if radius_y > 0 else 0
            distance = (dx * dx + dy * dy) ** 0.5
            
            return distance <= 1.1  # Allow some margin for selection
            
        return False
        
    def _point_line_distance(self, x, y, x1, y1, x2, y2):
        """Calculate the distance from point (x,y) to line segment (x1,y1)-(x2,y2)"""
        import math
        
        # Line length
        line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_length == 0:  # Line is actually a point
            return math.sqrt((x - x1)**2 + (y - y1)**2)
            
        # Calculate the perpendicular distance
        t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / (line_length * line_length)
        
        if t < 0:
            # Point is beyond the 'start' of the line segment
            return math.sqrt((x - x1)**2 + (y - y1)**2)
        elif t > 1:
            # Point is beyond the 'end' of the line segment
            return math.sqrt((x - x2)**2 + (y - y2)**2)
        else:
            # Projection falls on the line segment
            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)
            return math.sqrt((x - proj_x)**2 + (y - proj_y)**2)
    
    def start_annotation(self, event):
        """Start creating an annotation"""
        if not self.annotation_mode or self.original_image is None:
            return
            
        # Store starting position
        self.annotation_start_x = event.x
        self.annotation_start_y = event.y
        
        # Create a new annotation based on type
        if self.annotation_type == "text":
            # For text, we'll add it on click release
            pass
        elif self.annotation_type in ["arrow", "rectangle", "circle"]:
            # Create a temporary annotation
            self.current_annotation = {
                "type": self.annotation_type,
                "color": self.annotation_color,
                "start_x": event.x,
                "start_y": event.y,
                "end_x": event.x,
                "end_y": event.y
            }
    
    def update_annotation(self, event):
        """Update annotation while dragging"""
        if not self.annotation_mode or self.current_annotation is None:
            return
            
        # Update end position
        self.current_annotation["end_x"] = event.x
        self.current_annotation["end_y"] = event.y
        
        # Redraw with the temporary annotation
        self.show_annotations(include_current=True)
    
    def finish_annotation(self, event):
        """Finish creating an annotation"""
        if not self.annotation_mode or self.original_image is None:
            return
            
        # Get the image path to store annotation with
        image_path = self.current_image_path
        if image_path is None:
            return
            
        # Initialize annotations list for this image if it doesn't exist
        if image_path not in self.annotations:
            self.annotations[image_path] = []
            
        # Handle different annotation types
        if self.annotation_type == "text":
            # For text annotations, add at the clicked position
            text = self.annotation_text_var.get()
            if text.strip():
                self.annotations[image_path].append({
                    "type": "text",
                    "text": text,
                    "x": event.x,
                    "y": event.y,
                    "color": self.annotation_color
                })
        elif self.annotation_type in ["arrow", "rectangle", "circle"] and self.current_annotation is not None:
            # Finalize the shape annotation
            self.annotations[image_path].append(self.current_annotation)
            self.current_annotation = None
            
        # Redraw annotations
        self.show_annotations()
    
    def show_annotations(self, include_current=False):
        """Display all annotations on the current image"""
        if self.selected_cell is None or self.original_image is None:
            return
            
        # Get the selected cell
        row, col = self.selected_cell
        frame, label = self.grid_cells[row][col]
        
        # Get cell dimensions
        cell_width = frame.winfo_width() - 8
        cell_height = frame.winfo_height() - 8
        
        # Create a copy of the displayed image to draw on
        # We need to recreate this from the original image to avoid annotation buildup
        img_width, img_height = self.original_image.size
        aspect_ratio = img_width / img_height
        
        # Calculate dimensions preserving aspect ratio
        if aspect_ratio > 1:
            new_width = cell_width
            new_height = int(cell_width / aspect_ratio)
            if new_height > cell_height:
                new_height = cell_height
                new_width = int(cell_height * aspect_ratio)
        else:
            new_height = cell_height
            new_width = int(cell_height * aspect_ratio)
            if new_width > cell_width:
                new_width = cell_width
                new_height = int(cell_width / aspect_ratio)
        
        # Center the image
        x = (cell_width - new_width) // 2
        y = (cell_height - new_height) // 2
        
        # Create white background
        bg = Image.new('RGBA', (cell_width, cell_height), (255, 255, 255, 255))
        
        # Resize image
        resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Paste onto white background
        bg.paste(resized_image, (x, y))
        
        # Convert to a format we can draw on
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(bg)
        
        # Draw existing annotations for this image
        if self.current_image_path in self.annotations:
            for annotation in self.annotations[self.current_image_path]:
                # Determine if this annotation is selected
                is_selected = (self.selected_annotation == annotation)
                
                # Set line width based on selection state
                line_width = 4 if is_selected else 2
                
                # Set color - use original color or highlight color if selected
                color = annotation["color"]
                
                if annotation["type"] == "text":
                    # Draw text annotation
                    try:
                        font = ImageFont.truetype("arial.ttf", 16)
                    except IOError:
                        font = ImageFont.load_default()
                    
                    # Draw text
                    draw.text((annotation["x"], annotation["y"]), annotation["text"], 
                             fill=color, font=font)
                    
                    # Draw selection box around text if selected
                    if is_selected:
                        text_width = len(annotation["text"]) * 8  # Rough estimate
                        text_height = 20  # Rough estimate
                        draw.rectangle([
                            (annotation["x"]-2, annotation["y"]-2),
                            (annotation["x"]+text_width+2, annotation["y"]+text_height+2)
                        ], outline="blue", width=2)
                        
                elif annotation["type"] == "arrow":
                    # Draw arrow annotation
                    draw.line([(annotation["start_x"], annotation["start_y"]), 
                              (annotation["end_x"], annotation["end_y"])], 
                             fill=color, width=line_width)
                    # Draw arrowhead
                    self._draw_arrowhead(draw, annotation["start_x"], annotation["start_y"],
                                       annotation["end_x"], annotation["end_y"], color)
                    
                    # Draw selection indicators at endpoints if selected
                    if is_selected:
                        # Draw blue dots at start and end points
                        r = 5  # Radius of selection indicator
                        draw.ellipse([(annotation["start_x"]-r, annotation["start_y"]-r),
                                     (annotation["start_x"]+r, annotation["start_y"]+r)],
                                    fill="blue")
                        draw.ellipse([(annotation["end_x"]-r, annotation["end_y"]-r),
                                     (annotation["end_x"]+r, annotation["end_y"]+r)],
                                    fill="blue")
                        
                elif annotation["type"] == "rectangle":
                    # Draw rectangle annotation - ensure coordinates are properly ordered
                    x1, y1 = min(annotation["start_x"], annotation["end_x"]), min(annotation["start_y"], annotation["end_y"])
                    x2, y2 = max(annotation["start_x"], annotation["end_x"]), max(annotation["start_y"], annotation["end_y"])
                    
                    # Draw rectangle
                    draw.rectangle([(x1, y1), (x2, y2)],
                                 outline=color, width=line_width)
                    
                    # Draw selection indicators at corners if selected
                    if is_selected:
                        r = 5  # Radius of selection indicator
                        # Draw blue dots at corners
                        for corner_x, corner_y in [
                            (annotation["start_x"], annotation["start_y"]),
                            (annotation["end_x"], annotation["start_y"]),
                            (annotation["start_x"], annotation["end_y"]),
                            (annotation["end_x"], annotation["end_y"])
                        ]:
                            draw.ellipse([(corner_x-r, corner_y-r),
                                         (corner_x+r, corner_y+r)],
                                        fill="blue")
                        
                elif annotation["type"] == "circle":
                    # Draw circle annotation (ellipse in PIL) - ensure coordinates are properly ordered
                    x1, y1 = min(annotation["start_x"], annotation["end_x"]), min(annotation["start_y"], annotation["end_y"])
                    x2, y2 = max(annotation["start_x"], annotation["end_x"]), max(annotation["start_y"], annotation["end_y"])
                    
                    # Draw ellipse
                    draw.ellipse([(x1, y1), (x2, y2)],
                               outline=color, width=line_width)
                    
                    # Draw selection indicators if selected
                    if is_selected:
                        r = 5  # Radius of selection indicator
                        # Draw blue dots at key points
                        center_x = (annotation["start_x"] + annotation["end_x"]) / 2
                        center_y = (annotation["start_y"] + annotation["end_y"]) / 2
                        
                        for point_x, point_y in [
                            (annotation["start_x"], annotation["start_y"]),
                            (annotation["end_x"], annotation["end_y"]),
                            (center_x, center_y)
                        ]:
                            draw.ellipse([(point_x-r, point_y-r),
                                         (point_x+r, point_y+r)],
                                        fill="blue")
        
        # Draw current annotation being created
        if include_current and self.current_annotation is not None:
            if self.current_annotation["type"] == "arrow":
                # Draw arrow
                draw.line([(self.current_annotation["start_x"], self.current_annotation["start_y"]),
                           (self.current_annotation["end_x"], self.current_annotation["end_y"])],
                          fill=self.current_annotation["color"], width=2)
                # Draw arrowhead
                self._draw_arrowhead(draw, self.current_annotation["start_x"], self.current_annotation["start_y"],
                                    self.current_annotation["end_x"], self.current_annotation["end_y"], 
                                    self.current_annotation["color"])
                    
            elif self.current_annotation["type"] == "rectangle":
                # Draw rectangle - ensure coordinates are properly ordered
                x1, y1 = self.current_annotation["start_x"], self.current_annotation["start_y"]
                x2, y2 = self.current_annotation["end_x"], self.current_annotation["end_y"]
                # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                draw.rectangle([(x1, y1), (x2, y2)],
                              outline=self.current_annotation["color"], width=2)
                
            elif self.current_annotation["type"] == "circle":
                # Draw circle annotation (ellipse in PIL) - ensure coordinates are properly ordered
                x1, y1 = self.current_annotation["start_x"], self.current_annotation["start_y"]
                x2, y2 = self.current_annotation["end_x"], self.current_annotation["end_y"]
                # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                draw.ellipse([(x1, y1), (x2, y2)],
                           outline=self.current_annotation["color"], width=2)
        
        # Convert to PhotoImage and display
        photo = ImageTk.PhotoImage(bg)
        label.configure(image=photo)
        label.image = photo  # Keep reference!
    
    def _draw_arrowhead(self, draw, x1, y1, x2, y2, color, arrow_size=10):
        """Draw an arrowhead at the end of a line"""
        import math
        
        # Calculate angle of the line
        angle = math.atan2(y2 - y1, x2 - x1)
        
        # Calculate arrowhead points
        x3 = x2 - arrow_size * math.cos(angle - math.pi/6)
        y3 = y2 - arrow_size * math.sin(angle - math.pi/6)
        x4 = x2 - arrow_size * math.cos(angle + math.pi/6)
        y4 = y2 - arrow_size * math.sin(angle + math.pi/6)
        
        # Draw arrowhead
        draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)
    
    def clear_annotations(self):
        """Clear all annotations for the current image"""
        if self.current_image_path is not None and self.current_image_path in self.annotations:
            self.annotations[self.current_image_path] = []
            self.show_annotations()
            messagebox.showinfo("Annotations Cleared", "All annotations for this image have been cleared")
    
    def save_annotations(self):
        """Save annotations to a file"""
        if not self.annotations:
            messagebox.showinfo("No Annotations", "There are no annotations to save")
            return
            
        try:
            # Ask for a file to save to
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Save Annotations"
            )
            
            if not file_path:
                return
                
            # Convert annotations to a serializable format
            import json
            
            # Save annotations to file
            with open(file_path, 'w') as f:
                json.dump(self.annotations, f, indent=2)
                
            messagebox.showinfo("Annotations Saved", f"Annotations saved to {file_path}")
            
        except Exception as e:
            print(f"Error saving annotations: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")
    
    def save_annotated_image(self):
        """Save the current image with annotations as a new file"""
        if self.selected_cell is None or self.original_image is None or self.current_image_path is None:
            messagebox.showinfo("No Image Selected", "Please select an image to save first")
            return
            
        # Get the current image path and create a new filename with "_annotated" suffix
        file_path = self.current_image_path
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name)
        new_file_name = f"{base_name}_annotated{ext}"
        new_file_path = os.path.join(file_dir, new_file_name)
        
        try:
            # Create a copy of the original image
            img_copy = self.original_image.copy()
            
            # Draw all annotations on the copy
            self.draw_annotations_on_image(img_copy)
            
            # Save the annotated image
            img_copy.save(new_file_path)
            
            messagebox.showinfo("Image Saved", f"Annotated image saved as:\n{new_file_name}")
            
            # Refresh the file list to show the new file
            self.refresh_file_list()
            
        except Exception as e:
            print(f"Error saving annotated image: {e}")
            messagebox.showerror("Error", f"Failed to save annotated image: {str(e)}")
            
    def on_rotation_selected(self, event=None):
        """Handle selection of a rotation option from the dropdown"""
        try:
            # Get the selected rotation option
            rotation_choice = self.rotation_var.get()
            
            # Clear the selection in the dropdown
            self.rotation_dropdown.set('')
            
            # Apply the rotation
            self.apply_rotation(rotation_choice)
            
        except Exception as e:
            print(f"Error handling rotation selection: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to apply rotation: {str(e)}")
    
    def apply_rotation(self, rotation_choice):
        """Apply the selected rotation to the current image"""
        if self.selected_cell is None or self.original_image is None or self.current_image_path is None:
            messagebox.showinfo("No Image Selected", "Please select an image to rotate first")
            return
            
        try:
            # Determine rotation angle in degrees or flip operation
            if rotation_choice == "90° Clockwise":
                angle = -90  # PIL rotates counter-clockwise, so negative for clockwise
                rotated_image = self.original_image.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            elif rotation_choice == "180°":
                angle = 180
                rotated_image = self.original_image.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            elif rotation_choice == "90° Counter-Clockwise":
                angle = 90
                rotated_image = self.original_image.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            elif rotation_choice == "Flip Horizontal":
                rotated_image = self.original_image.transpose(Image.FLIP_LEFT_RIGHT)
            elif rotation_choice == "Flip Vertical":
                rotated_image = self.original_image.transpose(Image.FLIP_TOP_BOTTOM)
            else:
                messagebox.showinfo("Invalid Selection", "Please select a valid rotation option")
                return
                
            # Update the original image reference
            self.original_image = rotated_image
            
            # Reset zoom and pan
            self.zoom_level = 1.0
            self.crop_x = 0
            self.crop_y = 0
            
            # Display the rotated image
            self.apply_zoom()
            
            # Ask if user wants to save the rotated image
            if messagebox.askyesno("Save Rotated Image", "Do you want to save the rotated image?\n\nNote: This will overwrite the original file."):
                try:
                    # Save the rotated image
                    self.original_image.save(self.current_image_path)
                    messagebox.showinfo("Image Saved", "Rotated image saved successfully")
                except Exception as e:
                    print(f"Error saving rotated image: {e}")
                    messagebox.showerror("Error", f"Failed to save rotated image: {str(e)}")
            
        except Exception as e:
            print(f"Error rotating image: {e}")
            messagebox.showerror("Error", f"Failed to rotate image: {str(e)}")
            
    def rotate_image(self):
        """Legacy method for backward compatibility"""
        # Show a dialog to select rotation option
        rotation_options = ["90° Clockwise", "180°", "90° Counter-Clockwise", "Flip Horizontal", "Flip Vertical"]
        rotation_choice = simpledialog.askstring(
            "Rotate Image",
            "Select rotation option:",
            initialvalue=rotation_options[0],
            parent=self.master
        )
        
        if rotation_choice is not None:
            self.apply_rotation(rotation_choice)
    
    def save_annotated_image(self):
        """Save the current image with annotations as a new file"""
        if self.selected_cell is None or self.original_image is None or self.current_image_path is None:
            messagebox.showinfo("No Image Selected", "Please select an image to save first")
            return
            
        try:
            # Get the original image filename and path
            original_filename = os.path.basename(self.current_image_path)
            original_dir = os.path.dirname(self.current_image_path)
            
            # Create a new filename with "_annotated" appended
            filename_without_ext, file_extension = os.path.splitext(original_filename)
            new_filename = f"{filename_without_ext}_annotated{file_extension}"
            
            default_save_path = os.path.join(original_dir, new_filename)
            
            # Ask for a file to save to
            file_path = filedialog.asksaveasfilename(
                initialfile=new_filename,
                defaultextension=file_extension,
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")],
                title="Save Annotated Image"
            )
            
            if not file_path:
                return
                
            # Create a copy of the original image
            image = Image.open(self.current_image_path)
            
            # Convert to a format we can draw on
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(image)
            
            # Calculate scaling factors between displayed image and original image
            # Get the selected cell dimensions
            row, col = self.selected_cell
            frame, label = self.grid_cells[row][col]
            
            # Get cell dimensions
            cell_width = frame.winfo_width() - 8  # Account for padding
            cell_height = frame.winfo_height() - 8
            
            # Get original image dimensions
            orig_width, orig_height = self.original_image.size
            
            # Calculate the dimensions of the displayed image (preserving aspect ratio)
            aspect_ratio = orig_width / orig_height
            
            if aspect_ratio > 1:
                # Image is wider than tall
                display_width = cell_width
                display_height = int(cell_width / aspect_ratio)
                if display_height > cell_height:
                    display_height = cell_height
                    display_width = int(cell_height * aspect_ratio)
            else:
                # Image is taller than wide
                display_height = cell_height
                display_width = int(cell_height * aspect_ratio)
                if display_width > cell_width:
                    display_width = cell_width
                    display_height = int(display_width / aspect_ratio)
            
            # Calculate the position offset (where the image is positioned in the cell)
            x_offset = (cell_width - display_width) // 2
            y_offset = (cell_height - display_height) // 2
            
            # Calculate scaling factors
            x_scale = orig_width / display_width
            y_scale = orig_height / display_height
            
            print(f"Scaling factors: x_scale={x_scale}, y_scale={y_scale}")
            print(f"Offsets: x_offset={x_offset}, y_offset={y_offset}")
            
            # Draw all annotations on the image with scaled coordinates
            if self.current_image_path in self.annotations:
                for annotation in self.annotations[self.current_image_path]:
                    color = annotation["color"]
                    
                    if annotation["type"] == "text":
                        # Scale text annotation coordinates
                        x = int((annotation["x"] - x_offset) * x_scale)
                        y = int((annotation["y"] - y_offset) * y_scale)
                        
                        # Ensure coordinates are within image bounds
                        x = max(0, min(x, orig_width - 1))
                        y = max(0, min(y, orig_height - 1))
                        
                        # Draw text annotation with scaled coordinates
                        try:
                            # Scale font size based on image size
                            font_size = max(16, int(16 * min(x_scale, y_scale)))
                            font = ImageFont.truetype("arial.ttf", font_size)
                        except IOError:
                            font = ImageFont.load_default()
                        
                        draw.text((x, y), annotation["text"], fill=color, font=font)
                                
                    elif annotation["type"] == "arrow":
                        # Scale arrow coordinates
                        start_x = int((annotation["start_x"] - x_offset) * x_scale)
                        start_y = int((annotation["start_y"] - y_offset) * y_scale)
                        end_x = int((annotation["end_x"] - x_offset) * x_scale)
                        end_y = int((annotation["end_y"] - y_offset) * y_scale)
                        
                        # Ensure coordinates are within image bounds
                        start_x = max(0, min(start_x, orig_width - 1))
                        start_y = max(0, min(start_y, orig_height - 1))
                        end_x = max(0, min(end_x, orig_width - 1))
                        end_y = max(0, min(end_y, orig_height - 1))
                        
                        # Calculate line width based on image size
                        line_width = max(2, int(2 * min(x_scale, y_scale)))
                        
                        # Draw arrow with scaled coordinates
                        draw.line([(start_x, start_y), (end_x, end_y)], fill=color, width=line_width)
                        
                        # Draw arrowhead with scaled coordinates
                        arrow_size = max(10, int(10 * min(x_scale, y_scale)))
                        self._draw_arrowhead(draw, start_x, start_y, end_x, end_y, color, arrow_size)
                                
                    elif annotation["type"] == "rectangle":
                        # Scale rectangle coordinates
                        x1 = int((annotation["start_x"] - x_offset) * x_scale)
                        y1 = int((annotation["start_y"] - y_offset) * y_scale)
                        x2 = int((annotation["end_x"] - x_offset) * x_scale)
                        y2 = int((annotation["end_y"] - y_offset) * y_scale)
                        
                        # Ensure coordinates are within image bounds
                        x1 = max(0, min(x1, orig_width - 1))
                        y1 = max(0, min(y1, orig_height - 1))
                        x2 = max(0, min(x2, orig_width - 1))
                        y2 = max(0, min(y2, orig_height - 1))
                        
                        # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                        x1, x2 = min(x1, x2), max(x1, x2)
                        y1, y2 = min(y1, y2), max(y1, y2)
                        
                        # Calculate line width based on image size
                        line_width = max(2, int(2 * min(x_scale, y_scale)))
                        
                        # Draw rectangle with scaled coordinates
                        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=line_width)
                                
                    elif annotation["type"] == "circle":
                        # Scale circle coordinates
                        x1 = int((annotation["start_x"] - x_offset) * x_scale)
                        y1 = int((annotation["start_y"] - y_offset) * y_scale)
                        x2 = int((annotation["end_x"] - x_offset) * x_scale)
                        y2 = int((annotation["end_y"] - y_offset) * y_scale)
                        
                        # Ensure coordinates are within image bounds
                        x1 = max(0, min(x1, orig_width - 1))
                        y1 = max(0, min(y1, orig_height - 1))
                        x2 = max(0, min(x2, orig_width - 1))
                        y2 = max(0, min(y2, orig_height - 1))
                        
                        # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                        x1, x2 = min(x1, x2), max(x1, x2)
                        y1, y2 = min(y1, y2), max(y1, y2)
                        
                        # Calculate line width based on image size
                        line_width = max(2, int(2 * min(x_scale, y_scale)))
                        
                        # Draw ellipse with scaled coordinates
                        draw.ellipse([(x1, y1), (x2, y2)], outline=color, width=line_width)
            
            # Save the image
            image.save(file_path)
            
            messagebox.showinfo("Image Saved", f"Annotated image saved to {file_path}")
            
        except Exception as e:
            print(f"Error saving annotated image: {e}")
            messagebox.showerror("Error", f"Failed to save annotated image: {str(e)}")
    
    def select_cell(self, row, col):
        """Select a grid cell and make its image the selected image for further actions"""
        try:
            # Autosave current markdown before switching selection
            try:
                self._autosave_markdown_if_dirty()
            except Exception:
                pass
            # Update the selected cell
            self.selected_cell = (row, col)
            print(f"Selected cell: [{row}, {col}]")  # Debug print
            
            # Highlight the selected cell by changing its border
            for i in range(len(self.grid_cells)):
                for j in range(len(self.grid_cells[i])):
                    frame, _ = self.grid_cells[i][j]
                    if i == row and j == col:
                        frame.configure(borderwidth=3, relief="solid")
                    else:
                        frame.configure(borderwidth=1, relief="solid")
            
            # Check if the cell has an image
            frame, label = self.grid_cells[row][col]
            if hasattr(label, 'image') and label.image is not None:
                # Get the image path from the label's image
                if hasattr(label, 'image_path') and label.image_path is not None:
                    # Set this image as the selected image for further actions
                    self.current_image_path = label.image_path
                    # If we have a pre-rendered base_image (e.g., PDF/SVG/video/audio/text previews), reuse it
                    if hasattr(label, 'base_image') and label.base_image is not None:
                        try:
                            self.original_image = label.base_image
                            # Also update self.current_image to maintain consistency
                            self.current_image = self.current_image_path
                            print(f"Selected image (preview): {self.current_image_path}")  # Debug print
                            
                            # Switch associated markdown to sidecar (blank if unavailable)
                            try:
                                self._switch_markdown_for_selection(self.current_image_path)
                            except Exception:
                                pass
                            
                            # Reset zoom and pan for the newly selected image
                            self.zoom_level = 1.0
                            self.crop_x = 0
                            self.crop_y = 0
                            
                            # If annotation mode is active, show annotations for this image
                            if self.annotation_mode:
                                self.show_annotations()
                            # Update pdf controls visibility/state
                            try:
                                self._update_pdf_controls(label)
                            except Exception:
                                pass
                            
                            # Return True to indicate successful selection with image
                            return True
                        except Exception as e:
                            print(f"Error assigning preview image in select_cell: {e}")
                            self.current_image_path = None
                            self.original_image = None
                            self.current_image = None
                    # Fallback: attempt to open from disk (for native image formats)
                    try:
                        self.original_image = Image.open(self.current_image_path)
                        # Also update self.current_image to maintain consistency
                        self.current_image = self.current_image_path
                        print(f"Selected image: {self.current_image_path}")  # Debug print
                        
                        # Switch associated markdown to sidecar (blank if unavailable)
                        try:
                            self._switch_markdown_for_selection(self.current_image_path)
                        except Exception:
                            pass
                        
                        # Reset zoom and pan for the newly selected image
                        self.zoom_level = 1.0
                        self.crop_x = 0
                        self.crop_y = 0
                        
                        # If annotation mode is active, show annotations for this image
                        if self.annotation_mode:
                            self.show_annotations()
                        # Non-PDF image -> hide pdf controls
                        try:
                            self._hide_pdf_controls()
                        except Exception:
                            pass
                        
                        # Return True to indicate successful selection with image
                        return True
                    except Exception as e:
                        print(f"Error loading image in select_cell: {e}")
                        # Clear the image reference if it can't be loaded
                        self.current_image_path = None
                        self.original_image = None
                        self.current_image = None
            
            # Return False to indicate successful selection but no image
            try:
                self._hide_pdf_controls()
            except Exception:
                pass
            return False
            
        except Exception as e:
            print(f"Error selecting cell: {e}")  # Debug print
            traceback.print_exc()
            return False
    
    def rename_selected_file(self):
        """Rename selected file to a custom name specified in an input dialog"""
        # Get selected rows from the table's multiplerowlist
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select a file to rename")
            return
            
        # If multiple rows are selected, use only the first one
        if len(selected_rows) > 1:
            messagebox.showinfo("Info", "Only the first selected file will be renamed")
            
        row_idx = selected_rows[0]
        if row_idx >= len(self.df):
            messagebox.showerror("Error", "Invalid selection")
            return
            
        # Get current file information
        current_name = self.df.iloc[row_idx]['Name']
        file_path = self.df.iloc[row_idx]['File_Path']
        _, file_extension = os.path.splitext(current_name)
        
        # Show input dialog for new name
        new_name = simpledialog.askstring(
            "Rename File", 
            "Enter new filename (without extension):",
            initialvalue=os.path.splitext(current_name)[0]
        )
        
        # If user canceled or entered empty name, abort
        if not new_name:
            return
            
        try:
            # Add the original extension to the new name
            new_filename = new_name + file_extension
            
            # Rename the file
            new_path = self.rename_csv_file(file_path, new_filename)
            
            # Update the DataFrame
            self.df.at[row_idx, 'Name'] = new_filename
            self.df.at[row_idx, 'File_Path'] = new_path
            
            # Update Field_ columns based on the new filename
            name_without_ext = os.path.splitext(new_filename)[0]
            fields = name_without_ext.split('_')
            
            # Update Field_ columns
            for i, field in enumerate(fields):
                field_col = f'Field_{i+1}'
                if field_col in self.df.columns:
                    self.df.at[row_idx, field_col] = field
            
            # Update the table display
            self.table.model.df = self.df
            self.table.redraw()
            
            # Refresh the file list to ensure UI consistency
            self.refresh_file_list()
            
            messagebox.showinfo("File Renamed", f"File renamed to: {new_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename file: {str(e)}")

    def move_selected_files(self):
        """Move selected files to another folder"""
        # Get selected rows from the table's multiplerowlist
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select files to move")
            return

        # Ask for destination directory
        dest_dir = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=os.path.dirname(self.current_directory)
        )
        
        if not dest_dir:
            return

        try:
            moved_files = []  # list of filenames moved (for DataFrame removal)
            moved_paths = []  # list of full source paths moved (for self.image_files update)
            for row in selected_rows:
                if row < len(self.df):
                    filename = self.df.iloc[row]['Name']
                    # Use the File_Path column directly instead of constructing the path
                    filepath = self.df.iloc[row]['File_Path']

                    try:
                        # Delete the file
                        os.remove(filepath)
                        moved_files.append(filename)
                        
                        # Clear image display if it was one of the deleted images
                        if self.current_image == filepath and self.selected_cell is not None:
                            self.current_image = None
                            row, col = self.selected_cell
                            _, label = self.grid_cells[row][col]
                            if label:
                                label.configure(image='')
                                label.image = None
                                
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete file {filename}:\n{str(e)}")

            # Update the DataFrame and table
            if moved_files:
                self.df = self.df[~self.df['Name'].isin(moved_files)]
                self.table.model.df = self.df
                self.table.redraw()
                
                # Update image files list
                self.image_files = [f for f in self.image_files if f not in moved_files]
                
                messagebox.showinfo("Success", f"Deleted {len(moved_files)} files")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error during deletion:\n{str(e)}")

    def delete_selected(self, event=None):
        """Handle Delete key press - now calls delete_selected_files"""
        self.delete_selected_files()

    def load_subfolders(self):
        """Load all image files from current directory and all subdirectories"""
        try:
            print("\n=== Loading files from subfolders ===")  # Debug print
            
            # Set include_subfolders to True
            self.include_subfolders.set(True)
            
            # Use standard directory selection
            directory = filedialog.askdirectory(
                initialdir=self.current_directory
            )
            
            # Validate the selected directory
            if directory:
                # Update current directory
                self.current_directory = directory
                
                # Add to recent folders
                self.add_recent_folder(directory)
                
                # Update file list
                self.update_image_files()
                
                # Update max fields
                old_max = self.max_fields
                self.max_fields = self.get_max_fields()
                print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
                
                # Update file browser - use setup_file_browser instead of just update_file_dataframe
                self.setup_file_browser()
                
                # Update grid
                if hasattr(self, 'create_grid'):
                    print("Updating grid")  # Debug print
                    self.create_grid()
                
                # Show summary of files found
                messagebox.showinfo("Subfolder Search", 
                    f"Found {len(self.image_files)} image files in {directory} and its subdirectories")
            
        except Exception as e:
            print(f"Error in load_subfolders: {e}")
            messagebox.showerror("Error", "Failed to load subfolders")

    def refresh_file_list(self):
        """Refresh the file list and update the UI"""
        print(f"\n=== Refreshing file list for directory: {self.current_directory} ===")  # Debug print
        
        # Update image files
        self.update_image_files()
        
        # Update max fields
        old_max = self.max_fields
        self.max_fields = self.get_max_fields()
        print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
        
        # Update file browser
        self.setup_file_browser()
        
        # Update grid
        if hasattr(self, 'create_grid'):
            print("Updating grid")  # Debug print
            self.create_grid()

    def update_file_list(self):
        """Update a simple list of files in the current directory (unused helper)."""
        print("\n=== Updating file list ===")  # Debug print
        try:
            files = os.listdir(self.current_directory)
            self.csv_files = [f for f in files if os.path.isfile(os.path.join(self.current_directory, f))]
            print(f"Found {len(self.csv_files)} files")  # Debug print
        except Exception as e:
            self.csv_files = []
            print(f"Error updating file list: {e}")
    def update_grid_size(self):
        try:
            new_rows = max(1, min(10, int(self.rows_var.get())))
            new_cols = max(1, min(10, int(self.cols_var.get())))

            # Save current grid state
            old_grid_state = {}
            for i in range(self.grid_rows):
                for j in range(self.grid_cols):
                    frame, label = self.grid_cells[i][j]
                    if hasattr(label, 'image') and label.image is not None:
                        old_grid_state[(i, j)] = label.image

            # Update grid dimensions
            self.grid_rows = new_rows
            self.grid_cols = new_cols

            # Recreate grid while preserving images
            self.create_grid()
            
            # Restore images
            for (i, j), image in old_grid_state.items():
                frame, label = self.grid_cells[i][j]
                label.configure(image=image)
                label.image = image

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for grid size")

    def toggle_layout(self):
        """Toggle between horizontal and vertical layouts"""
        # Store current states
        current_selection = None
        if hasattr(self, 'selected_cell'):
            current_selection = self.selected_cell
        
        # Toggle orientation
        self.is_horizontal = not self.is_horizontal
        
        # Update button text
        self.toggle_btn.configure(
            text="Switch to Vertical Layout" if self.is_horizontal else "Switch to Horizontal Layout"
        )

        # Remove old paned window and its children
        if hasattr(self, 'paned'):
            self.paned.pack_forget()
            
        # Create new layout
        self.setup_panels()
        
        # Restore file browser
        self.setup_file_browser()
        
        # Restore grid
        self.create_grid()
        
        # Restore states
        if current_selection:
            self.select_cell(*current_selection)
            
        # Force geometry update
        self.update_idletasks()
        
        # Set final sash position
        if self.is_horizontal:
            self.paned.sashpos(0, 400)
        else:
            self.paned.sashpos(0, 300)

    def _copy_button_click(self, event=None):  
        print("\n=== Copy button clicked! ===")  
        print(f"Current image path: {getattr(self, 'current_image', None)}")  
        self.copy_image()

    def _copy_shortcut(self, event):
        print("\n=== Ctrl+C pressed! ===")  
        print(f"Current image path: {getattr(self, 'current_image', None)}")  
        self.copy_image()

    def copy_image(self):
        print("\n=== Starting copy_image ===")  
        if not self.current_image or not os.path.exists(self.current_image):
            print(f"No image selected or file doesn't exist: {self.current_image}")  
            return

        print(f"Current image path: {self.current_image}")  

        try:
            # Save to temporary PNG file
            temp_dir = os.environ.get('TEMP', os.getcwd())
            temp_path = os.path.join(temp_dir, 'temp_clipboard_image.png')
            print(f"Temp file path: {temp_path}")  

            # Copy the file directly
            import shutil
            shutil.copy2(self.current_image, temp_path)
            print("File copied to temp location")  

            # Use PowerShell to copy to clipboard
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $img = [System.Drawing.Image]::FromFile('{temp_path}')
            [System.Windows.Forms.Clipboard]::SetImage($img)
            $img.Dispose()
            '''

            print("Executing PowerShell script...")  

            # Execute PowerShell with proper encoding and window style
            import subprocess
            result = subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_script],
                capture_output=True,
                text=True,
                check=True
            )

            print("PowerShell execution completed")  
            print("PowerShell output:", result.stdout)  
            if result.stderr:
                print("PowerShell error:", result.stderr)  

            # Clean up
            try:
                os.remove(temp_path)
                print("Temp file cleaned up")  
            except Exception as e:
                print(f"Cleanup error: {e}")  
                pass

            print("Image copied successfully")  
            messagebox.showinfo("Success", "Image copied to clipboard")

        except subprocess.CalledProcessError as e:
            print(f"PowerShell error: {e.stderr}")  
            messagebox.showerror("Error", f"Failed to copy image to clipboard:\n{e.stderr}")
        except Exception as e:
            print(f"Python error: {str(e)}")  
            messagebox.showerror("Error", f"Failed to copy image:\n{str(e)}")
        finally:
            print("=== Finished copy_image ===\n")  

    def load_recent_folders(self):
        """Load recent folders from file"""
        try:
            # Define the path for the recent folders file
            recent_folders_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recent_folders.txt')
            
            # Check if the file exists
            if os.path.exists(recent_folders_file):
                with open(recent_folders_file, 'r') as f:
                    # Read each line as a folder path
                    self.recent_folders = [line.strip() for line in f.readlines() if line.strip()]
                    # Keep only valid directories
                    self.recent_folders = [folder for folder in self.recent_folders if os.path.isdir(folder)]
                    # Limit to max_recent_folders
                    self.recent_folders = self.recent_folders[:self.max_recent_folders]
                    
                print(f"Loaded {len(self.recent_folders)} recent folders")
            else:
                print("No recent folders file found")
                
        except Exception as e:
            print(f"Error loading recent folders: {e}")
            self.recent_folders = []
    
    def save_recent_folders(self):
        """Save recent folders to file"""
        try:
            # Define the path for the recent folders file
            recent_folders_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recent_folders.txt')
            
            # Write the folders to the file
            with open(recent_folders_file, 'w') as f:
                for folder in self.recent_folders:
                    f.write(f"{folder}\n")
                    
            print(f"Saved {len(self.recent_folders)} recent folders")
                
        except Exception as e:
            print(f"Error saving recent folders: {e}")
    
    def add_recent_folder(self, folder):
        """Add a folder to the recent folders list"""
        if not folder or not os.path.isdir(folder):
            return
            
        # Remove the folder if it already exists in the list
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
            
        # Add the folder to the beginning of the list
        self.recent_folders.insert(0, folder)
        
        # Limit to max_recent_folders
        if len(self.recent_folders) > self.max_recent_folders:
            self.recent_folders = self.recent_folders[:self.max_recent_folders]
            
        # Save the updated list
        self.save_recent_folders()
        
        # Update the recent folders dropdown if it exists
        if hasattr(self, 'recent_folders_var'):
            self.update_recent_folders_dropdown()
            
    def update_recent_folders_dropdown(self):
        """Update the recent folders dropdown with the current list of folders"""
        if not hasattr(self, 'recent_folders_dropdown'):
            return
            
        # Format folder paths for display (show only last part of path)
        display_values = []
        for folder in self.recent_folders:
            # Get folder name for display
            folder_name = os.path.basename(folder)
            # If folder name is empty (e.g., for root directories), use the full path
            if not folder_name:
                folder_name = folder
            # Format as "folder_name (full_path)"
            display_values.append(f"{folder_name} ({folder})")
            
        # Update the dropdown values
        self.recent_folders_dropdown['values'] = display_values
        
    def on_recent_folder_selected(self, event=None):
        """Handle selection of a folder from the recent folders dropdown"""
        try:
            # Autosave current markdown before changing folder
            try:
                self._autosave_markdown_if_dirty()
            except Exception:
                pass
            # Get the selected index
            selected_index = self.recent_folders_dropdown.current()
            
            if selected_index >= 0 and selected_index < len(self.recent_folders):
                # Get the selected folder
                selected_folder = self.recent_folders[selected_index]
                
                # Check if the folder exists
                if os.path.isdir(selected_folder):
                    print(f"Loading recent folder: {selected_folder}")
                    
                    # Update current directory
                    self.current_directory = selected_folder
                    
                    # Update image files list
                    self.update_image_files()
                    
                    # Update max fields
                    old_max = self.max_fields
                    self.max_fields = self.get_max_fields()
                    print(f"Max fields changed from {old_max} to {self.max_fields}")
                    
                    # Update file browser
                    self.setup_file_browser()
                    
                    # Update grid
                    if hasattr(self, 'create_grid'):
                        print("Updating grid")
                        self.create_grid()
                else:
                    # Folder doesn't exist, remove it from the list
                    print(f"Recent folder no longer exists: {selected_folder}")
                    self.recent_folders.pop(selected_index)
                    self.save_recent_folders()
                    self.update_recent_folders_dropdown()
                    messagebox.showwarning("Folder Not Found", f"The folder no longer exists:\n{selected_folder}")
            
            # Clear the selection in the dropdown
            self.recent_folders_dropdown.set('')
            
        except Exception as e:
            print(f"Error selecting recent folder: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load selected folder: {str(e)}")
            # Clear the selection in the dropdown
            self.recent_folders_dropdown.set('')
    
    def __del__(self):
        """Clean up resources when the application is closed"""
        logging.info("ImageBrowser application terminated")

if __name__ == "__main__":
    try:
        app = ImageBrowser()
        logging.info("ImageBrowser application started")
        
        # Add a proper shutdown mechanism
        def on_closing():
            logging.info("Application is closing")
            try:
                # Autosave markdown on close
                try:
                    app._autosave_markdown_if_dirty()
                except Exception:
                    pass
                # Destroy all widgets
                for widget in app.winfo_children():
                    widget.destroy()
                app.destroy()
            except Exception as e:
                logging.error(f"Error during application shutdown: {e}")
            
        app.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Run the main event loop
        app.mainloop()
    except Exception as e:
        logging.critical(f"Critical error in ImageBrowser: {e}")
        logging.critical(traceback.format_exc())
        messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{e}")
    finally:
        logging.info("ImageBrowser application terminated")