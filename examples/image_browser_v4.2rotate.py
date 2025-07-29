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
# Add custom pandastable path to sys.path BEFORE importing pandastable
# custom_pandastable_path = r"C:\Users\juesh\OneDrive\Documents\windsurf\pandastable\pandastable"
custom_pandastable_path = r"C:\Users\JueShi\OneDrive - Astera Labs, Inc\Documents\windsurf\pandastable\pandastable"
if os.path.exists(custom_pandastable_path):
    # Insert at the beginning of sys.path to prioritize this version
    sys.path.insert(0, custom_pandastable_path)
    print(f"Using custom pandastable from: {custom_pandastable_path}")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import pandas as pd
from pandastable import Table, TableModel
from datetime import datetime
import shutil
import traceback
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_browser.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

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
        
        # Set default directory to Pictures folder
        pictures_dir = r"C:\Users\juesh\OneDrive\Documents\windsurf\stock_data"
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

        # Create grid container frame
        self.grid_container = ttk.Frame(self.paned)
        self.paned.add(self.grid_container, weight=2)

        # Create grid frame
        self.grid_frame = ttk.Frame(self.grid_container)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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

    def setup_file_browser(self):
        """Setup the file browser panel with pandastable"""
        print("\n=== Setting up file browser ===")  # Debug print
        
        # Create frame for pandastable
        if hasattr(self, 'pt_frame'):
            self.pt_frame.destroy()
        self.pt_frame = ttk.Frame(self.file_frame)
        self.pt_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add filter frame
        filter_frame = ttk.Frame(self.pt_frame)
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        # Add filter label and entry
        ttk.Label(filter_frame, text="Filter Files:").pack(side="left", padx=(0,5))
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_text)
        filter_entry.pack(side="left", fill="x", expand=True)
        
        # Create right-click context menu for filtering instructions
        filter_menu = tk.Menu(filter_entry, tearoff=0)
        filter_menu.add_command(label="Filtering Instructions", state='disabled', font=('Arial', 10, 'bold'))
        filter_menu.add_separator()
        filter_menu.add_command(label="Basic Search: Enter any text to match", state='disabled')
        filter_menu.add_command(label="Multiple Terms: Use space ' 'to combine", state='disabled')
        filter_menu.add_command(label="Exclude Terms: Use '!' prefix", state='disabled')
        filter_menu.add_separator()
        filter_menu.add_command(label="Examples:", state='disabled', font=('Arial', 10, 'bold'))
        filter_menu.add_command(label="'png': Show files with 'png'", state='disabled')
        filter_menu.add_command(label="'2024 report': Files with both terms", state='disabled')
        filter_menu.add_command(label="'!temp': Exclude files with 'temp'", state='disabled')
        filter_menu.add_command(label="'png !old': PNG files, not old", state='disabled')
        
        def show_filter_menu(event):
            filter_menu.tk_popup(event.x_root, event.y_root)
        
        filter_entry.bind('<Button-3>', show_filter_menu)  # Right-click
        
        # Create DataFrame for files
        self.update_file_dataframe()
        
        # Create a separate frame for the table to avoid geometry manager conflicts
        table_frame = ttk.Frame(self.pt_frame)
        table_frame.pack(fill="both", expand=True)
        
        # Create pandastable
        self.table = Table(table_frame, dataframe=self.df,
                          showtoolbar=True, showstatusbar=True)
        self.table.show()
        
        # Configure table options
        self.table.autoResizeColumns()
        self.table.columnwidths['Name'] = 30
        self.table.columnwidths['File_Path'] = 30
        self.table.columnwidths['Date_Modified'] = 30
        self.table.columnwidths['Size_(KB)'] = 30
        for col in self.df.columns:
            if col not in ['Name', 'File_Path', 'Date_Modified', 'Size_(KB)']:
                max_width = max(len(str(x)) for x in self.df[col].head(20))
                self.table.columnwidths[col] = max(min(max_width * 10, 200), 50) # fit to number of letter *10 if it's in between 50 and 250

        self.table.redraw()
        
        # Bind double click for editing and single click for selection
        self.table.bind('<Double-1>', self.on_table_double_click)
        self.table.bind('<ButtonRelease-1>', self.on_table_select)
        
        # Enable editing and bind to key events
        self.table.editable = True
        self.table.bind('<Key>', self.on_key_press)  # Bind to key press
        self.table.bind('<Return>', self.on_return_press)  # Bind to return key
        self.table.bind('<FocusOut>', self.on_focus_out)  # Bind to focus loss
        # Bind arrow keys specifically to handle navigation
        self.table.bind('<Up>', self.on_key_press)
        self.table.bind('<Down>', self.on_key_press)

    def on_key_press(self, event):
        """Handle key press events"""
        try:
            if event.keysym in ('Up', 'Down'):
                # Handle arrow key navigation
                current_row = self.table.getSelectedRow()
                num_rows = len(self.table.model.df)
                
                if event.keysym == 'Up' and current_row > 0:
                    new_row = current_row - 1
                elif event.keysym == 'Down' and current_row < num_rows - 1:
                    new_row = current_row + 1
                else:
                    return
                
                # Select the new row and ensure it's visible
                self.table.setSelectedRow(new_row)
                self.table.redraw()  # Ensure table updates
                
                # Load the corresponding image
                self.load_selected_image()
                
            elif event.char and event.char.isprintable():            
                row = self.table.getSelectedRow()
                col = self.table.getSelectedColumn()
                if row is not None and col is not None:
                    # Let the default handler process the key first
                    self.table.handle_key_press(event)
                    # Then check for changes
                    self.check_for_changes(row, col)
        except Exception as e:
            print(f"Error handling key press: {e}")
            traceback.print_exc()

    def on_return_press(self, event):
        """Handle return key press"""
        try:
            row = self.table.getSelectedRow()
            col = self.table.getSelectedColumn()
            if row is not None and col is not None:
                self.check_for_changes(row, col)
        except Exception as e:
            print(f"Error handling return press: {e}")
            traceback.print_exc()

    def on_focus_out(self, event):
        """Handle focus out events"""
        try:
            row = self.table.getSelectedRow()
            col = self.table.getSelectedColumn()
            if row is not None and col is not None:
                self.check_for_changes(row, col)
        except Exception as e:
            print(f"Error handling focus out: {e}")
            traceback.print_exc()

    def check_for_changes(self, row, col):
        """Check for changes in the cell and handle file renaming"""
        try:
            # Get both the displayed and original DataFrames
            displayed_df = self.table.model.df
            if row < len(displayed_df):
                # If filter is active, temporarily disable and re-enable it
                filter_text = self.filter_text.get()
                if filter_text:
                    self.filter_text.set('')
                    self.filter_text.set(filter_text)

                displayed_df = self.table.model.df
                # Get current filename and path from displayed DataFrame
                file_path = str(displayed_df.iloc[row]['File_Path'])
                current_name = displayed_df.iloc[row]['Name']
                
                # Reconstruct filename from Field_ columns
                new_filename = self.reconstruct_filename(displayed_df.iloc[row])
                
                # If filename is different, rename the file
                if new_filename != current_name:
                    print(f"Renaming file from {current_name} to {new_filename}")  # Debug print
                    new_filepath = self.rename_csv_file(file_path, new_filename)
                    
                    # Update the displayed DataFrame
                    displayed_df.loc[row, 'Name'] = new_filename
                    displayed_df.loc[row, 'File_Path'] = new_filepath
                    
                    # Find and update the corresponding row in the original DataFrame
                    orig_idx = self.df[self.df['File_Path'] == file_path].index
                    if len(orig_idx) > 0:
                        # Update all Field_ columns in the original DataFrame
                        for col in self.df.columns:
                            if col.startswith('Field_'):
                                self.df.loc[orig_idx[0], col] = displayed_df.iloc[row][col]
                        # Update Name and File_Path
                        self.df.loc[orig_idx[0], 'Name'] = new_filename
                        self.df.loc[orig_idx[0], 'File_Path'] = new_filepath
                    
                    # If filtering is active, reapply the filter
                    if hasattr(self, 'filter_text') and self.filter_text.get():
                        self.filter_files()
                    else:
                        # Just update the model's DataFrame
                        self.table.model.df = displayed_df
                    
                    # Show confirmation
                    messagebox.showinfo("File Renamed", 
                                    f"File has been renamed from:\n{current_name}\nto:\n{new_filename}")
                    
                    # Refresh the table
                    self.table.redraw()
        except Exception as e:
            print(f"Error checking for changes: {e}")
            traceback.print_exc()                    

    def update_file_dataframe(self):
        """Update the pandas DataFrame with file information"""
        print("\n=== Updating file DataFrame ===")  # Debug print
        
        data = []
        for file_path in self.image_files:
            # Get the filename from the full path
            filename = os.path.basename(file_path)
            
            try:
                file_stat = os.stat(file_path)
                
                # Get basic file info
                file_info = {
                    'Name': filename,
                    'File_Path': file_path,  # Store full path for direct access
                    'Date_Modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'Size_(KB)': round(file_stat.st_size / 1024, 2)
                }
                
                # Add fields from filename
                name_without_ext = os.path.splitext(filename)[0]
                fields = name_without_ext.split('_')
                for i in range(self.max_fields):
                    field_name = f'Field_{i+1}'
                    file_info[field_name] = fields[i] if i < len(fields) else ''
                
                data.append(file_info)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        # Create DataFrame with a reset index
        self.df = pd.DataFrame(data)
        if not self.df.empty:
            # Ensure consistent column order
            columns = ['Name', 'File_Path', 'Date_Modified', 'Size_(KB)']
            columns.extend([f'Field_{i+1}' for i in range(self.max_fields)])
            self.df = self.df[columns]
            self.df.sort_values(by='Date_Modified', ascending=False, inplace=True)            

    def reconstruct_filename(self, row):
        """Reconstruct filename from columns starting with 'Field_'"""
        # Find columns starting with 'Field_'
        f_columns = [col for col in row.index if col.startswith('Field_')]
        
        # Sort the columns to maintain order, in case the user changed the column order in the table
        # f_columns.sort(key=lambda x: int(x.split('_')[1]))
        
        # Extract values from these columns, skipping None/empty values
        filename_parts = [str(row[col]) for col in f_columns if pd.notna(row[col]) and str(row[col]).strip()]
        
        # Join with underscore and preserve the original file extension
        current_name = row['Name']
        _, file_extension = os.path.splitext(current_name)
        
        # Create new filename with original extension
        new_filename = '_'.join(filename_parts).replace('\n', '') + file_extension
        
        return new_filename

    def rename_csv_file(self, old_filepath, new_filename):
        """Rename CSV file on disk"""
        try:
            directory = os.path.dirname(old_filepath)
            new_filepath = os.path.join(directory, new_filename)
            
            # Rename the file
            os.rename(old_filepath, new_filepath)
            return new_filepath
        except Exception as e:
            print(f"Error renaming file: {e}")
            return old_filepath
        
    def on_table_double_click(self, event):
        """Handle double click for cell editing"""
        if self.table.get_row_clicked(event) is not None:
            self.table.handle_double_click(event)

    def on_table_select(self, event):
        """Handle table row selection"""
        try:
            # Get the clicked row
            row = self.table.get_row_clicked(event)
            print(f"Clicked row: {row}")  # Debug print
            
            if row is not None:
                # Get the actual data from the filtered/sorted view
                displayed_df = self.table.model.df
                if row < len(displayed_df):
                    # Get filename and path directly from the displayed DataFrame
                    filename = str(displayed_df.iloc[row]['Name'])
                    file_path = str(displayed_df.iloc[row]['File_Path'])
                    print(f"Selected row {row}, filename: {filename}")  # Debug print
                    
                    # If no cell is selected, select the first empty cell
                    if self.selected_cell is None:
                        print("No cell selected, finding empty cell")  # Debug print
                        self.find_and_select_empty_cell()
                    
                    if self.selected_cell is not None:
                        print(f"Displaying image in cell {self.selected_cell}")  # Debug print
                        # Show image in selected cell using the full path
                        self.display_image(file_path, update_current=True)
                    else:
                        print("No cell selected after find_and_select_empty_cell")  # Debug print
                        messagebox.showinfo("Info", "No empty cells available")
        except Exception as e:
            print(f"Error in table selection: {e}")
            import traceback
            traceback.print_exc()

    def load_selected_image(self):
        """Load the selected image into the selected grid cell"""
        try:
            # Get the current selection from the table
            row = self.table.getSelectedRow()
            print(f"Selected row: {row}")  # Debug print
            
            if row is None:
                messagebox.showinfo("Info", "Please select a row in the table first")
                return
                
            if row < len(self.df):
                # Get filename from selected row
                filename = str(self.df.iloc[row]['Name'])
                print(f"Loading image: {filename}")  # Debug print
                
                # If no cell is selected, select the first empty cell
                if self.selected_cell is None:
                    print("No cell selected, finding empty cell")  # Debug print
                    self.find_and_select_empty_cell()
                
                if self.selected_cell is not None:
                    print(f"Displaying image in cell {self.selected_cell}")  # Debug print
                    # Show image in selected cell
                    self.display_image(filename)
                else:
                    print("No cell selected after find_and_select_empty_cell")  # Debug print
                    messagebox.showinfo("Info", "Please select a grid cell first")
        except Exception as e:
            print(f"Error loading selected image: {e}")
            import traceback
            traceback.print_exc()

    def find_and_select_empty_cell(self):
        """Find the first empty cell in the grid and select it"""
        print("\n=== Finding empty cell ===")  # Debug print
        for i in range(self.grid_rows):
            for j in range(self.grid_cols):
                frame, label = self.grid_cells[i][j]
                if not hasattr(label, 'image') or label.image is None:
                    print(f"Found empty cell at [{i}, {j}]")  # Debug print
                    self.select_cell(i, j)
                    return
        
        # If no empty cell found, select first cell
        print("No empty cell found, selecting first cell")  # Debug print
        self.select_cell(0, 0)

    def display_image(self, filename, update_current=True):
        """Display the selected image in the selected grid cell
        
        Args:
            filename: The filename or full path of the image to display
            update_current: Whether to update the current_image_path and other references
                           Set to False when displaying an image but not selecting it
        """
        print(f"\n=== Displaying image: {filename} ===")  # Debug print
        
        if self.selected_cell is None:
            messagebox.showinfo("Info", "Please select a grid cell first")
            return
            
        try:
            # Check if filename is actually a full path
            if os.path.isabs(filename) and os.path.exists(filename):
                image_path = filename
                print(f"Loading image from direct path: {image_path}")  # Debug print
                image = Image.open(image_path)
            else:
                # Find the file path from the DataFrame
                file_row = self.table.model.df[self.table.model.df['Name'] == filename]
                if not file_row.empty:
                    # Use the stored File_Path instead of joining with current_directory
                    image_path = file_row.iloc[0]['File_Path']
                    print(f"Loading image from: {image_path}")  # Debug print
                    image = Image.open(image_path)
                else:
                    # Fallback to the old method if not found in DataFrame
                    image_path = os.path.join(self.current_directory, filename)
                    print(f"Fallback loading image from: {image_path}")  # Debug print
                    image = Image.open(image_path)
            
            # Store the original image and reset zoom level if update_current is True
            if update_current:
                self.original_image = image
                self.current_image_path = image_path
                self.zoom_level = 1.0  # Reset zoom level when loading a new image
                print(f"Updated current image to: {image_path}")  # Debug print
            
            # Get the selected cell
            row, col = self.selected_cell
            frame, label = self.grid_cells[row][col]
            
            # Get cell dimensions
            frame.update()  # Ensure we have current size
            cell_width = frame.winfo_width() - 8  # Account for padding
            cell_height = frame.winfo_height() - 8
            print(f"Cell dimensions: {cell_width}x{cell_height}")  # Debug print
            
            # Calculate new dimensions preserving aspect ratio
            img_width, img_height = image.size
            aspect_ratio = img_width / img_height
            
            if aspect_ratio > 1:
                # Image is wider than tall
                new_width = cell_width
                new_height = int(cell_width / aspect_ratio)
                if new_height > cell_height:
                    new_height = cell_height
                    new_width = int(cell_height * aspect_ratio)
            else:
                # Image is taller than wide
                new_height = cell_height
                new_width = int(cell_height * aspect_ratio)
                if new_width > cell_width:
                    new_width = cell_width
                    new_height = int(cell_width / aspect_ratio)
            
            print(f"New image dimensions: {new_width}x{new_height}")  # Debug print
            
            # Center the image
            x = (cell_width - new_width) // 2
            y = (cell_height - new_height) // 2
            
            # Create white background
            bg = Image.new('RGBA', (cell_width, cell_height), (255, 255, 255, 255))
            
            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Paste onto white background
            bg.paste(resized_image, (x, y))
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(bg)
            label.configure(image=photo)
            label.image = photo  # Keep reference!
            label.image_path = image_path  # Store image path in the label for cell selection
            
            # Store current image path
            self.current_image = image_path
            
            # Bind mouse events for zooming and panning
            label.bind('<MouseWheel>', self.on_mouse_wheel)
            # Use Control+Click for panning instead of just click to avoid conflict with cell selection
            label.bind('<Control-ButtonPress-1>', self.start_pan)
            label.bind('<Control-B1-Motion>', self.pan_image)
            label.bind('<ButtonRelease-1>', self.stop_pan)
            print("Image displayed successfully")  # Debug print
            
        except Exception as e:
            print(f"Error displaying image: {e}")  # Debug print
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming images"""
        if self.original_image is None or self.selected_cell is None:
            return
            
        # Get cursor position relative to the label
        cursor_x = event.x
        cursor_y = event.y
        
        # Store previous zoom level for calculating zoom center
        prev_zoom = self.zoom_level
            
        # Determine zoom direction based on wheel movement
        # For Windows, event.delta is positive when scrolling up and negative when scrolling down
        zoom_factor = 1.1  # 10% zoom change per scroll
        
        if event.delta > 0:
            # Zoom in
            self.zoom_level *= zoom_factor
        else:
            # Zoom out
            self.zoom_level /= zoom_factor
            
        # Limit zoom level to reasonable bounds
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))  # Between 10% and 500%
        
        print(f"Zoom level: {self.zoom_level:.2f}x at cursor position ({cursor_x}, {cursor_y})")  # Debug print
        
        # Apply zoom and redisplay the image with cursor position as center
        self.apply_zoom(cursor_x, cursor_y, prev_zoom)
    
    def apply_zoom(self, cursor_x=None, cursor_y=None, prev_zoom=None):
        """Apply the current zoom level to the image and display it
        
        Args:
            cursor_x: X position of cursor for centered zoom (optional)
            cursor_y: Y position of cursor for centered zoom (optional)
            prev_zoom: Previous zoom level before this zoom operation (optional)
        """
        if self.original_image is None or self.selected_cell is None:
            return
            
        try:
            # Get the selected cell
            row, col = self.selected_cell
            frame, label = self.grid_cells[row][col]
            
            # Get cell dimensions
            frame.update()  # Ensure we have current size
            cell_width = frame.winfo_width() - 8  # Account for padding
            cell_height = frame.winfo_height() - 8
            
            # Get original image dimensions
            img_width, img_height = self.original_image.size
            aspect_ratio = img_width / img_height
            
            # Calculate base size (100% zoom) preserving aspect ratio
            if aspect_ratio > 1:
                # Image is wider than tall
                base_width = cell_width
                base_height = int(cell_width / aspect_ratio)
                if base_height > cell_height:
                    base_height = cell_height
                    base_width = int(cell_height * aspect_ratio)
            else:
                # Image is taller than wide
                base_height = cell_height
                base_width = int(cell_height * aspect_ratio)
                if base_width > cell_width:
                    base_width = cell_width
                    base_height = int(cell_width / aspect_ratio)
            
            # Apply zoom factor to the base size
            new_width = int(base_width * self.zoom_level)
            new_height = int(base_height * self.zoom_level)
            
            print(f"Zoomed dimensions: {new_width}x{new_height}")  # Debug print
            
            # Resize image with zoom factor
            resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create white background
            bg = Image.new('RGBA', (cell_width, cell_height), (255, 255, 255, 255))
            
            # Calculate position to center the zoomed image
            x = max(0, (cell_width - new_width) // 2)
            y = max(0, (cell_height - new_height) // 2)
            
            # If image is larger than cell, use cursor position as center for zooming
            if new_width > cell_width or new_height > cell_height:
                # Default to center if cursor position not provided
                if cursor_x is None or cursor_y is None or prev_zoom is None:
                    # Use center of image as default
                    crop_x = max(0, (new_width - cell_width) // 2)
                    crop_y = max(0, (new_height - cell_height) // 2)
                else:
                    # Calculate the relative position of cursor within the cell
                    rel_x = cursor_x / cell_width
                    rel_y = cursor_y / cell_height
                    
                    # Calculate the point in the image that should stay under cursor
                    # This is the key to cursor-centered zooming
                    zoom_ratio = self.zoom_level / prev_zoom
                    
                    # Calculate crop position to keep cursor point fixed
                    crop_x = int(rel_x * base_width * prev_zoom * zoom_ratio - cursor_x)
                    crop_y = int(rel_y * base_height * prev_zoom * zoom_ratio - cursor_y)
                    
                    # Ensure crop region stays within bounds
                    crop_x = max(0, min(crop_x, new_width - cell_width))
                    crop_y = max(0, min(crop_y, new_height - cell_height))
                
                crop_width = min(new_width, cell_width)
                crop_height = min(new_height, cell_height)
                
                # Crop the zoomed image to fit the cell
                resized_image = resized_image.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
                x = 0
                y = 0
            
            # Paste onto white background
            bg.paste(resized_image, (x, y))
            
            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(bg)
            label.configure(image=photo)
            label.image = photo  # Keep reference!
            
        except Exception as e:
            print(f"Error applying zoom: {e}")
            messagebox.showerror("Error", f"Failed to apply zoom: {str(e)}")
    
    def start_pan(self, event):
        """Start panning the image"""
        if self.original_image is None or self.selected_cell is None:
            return
            
        # Only enable panning when zoomed in
        if self.zoom_level <= 1.0:
            return
        
        # Check if Control key is pressed (for the new Control+Click binding)
        if not event.state & 0x0004:  # 0x0004 is the state mask for Control key
            print("Panning requires Control key to be pressed")  # Debug print
            return
            
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        print(f"Starting pan at ({event.x}, {event.y})")  # Debug print
    
    def pan_image(self, event):
        """Pan the image as mouse moves"""
        if not self.is_panning or self.original_image is None or self.selected_cell is None:
            return
            
        # Calculate the distance moved
        dx = self.pan_start_x - event.x
        dy = self.pan_start_y - event.y
        
        # Update pan start position for next movement
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        # Update crop position based on movement
        row, col = self.selected_cell
        frame, label = self.grid_cells[row][col]
        
        # Get cell dimensions
        cell_width = frame.winfo_width() - 8
        cell_height = frame.winfo_height() - 8
        
        # Get image dimensions at current zoom
        img_width, img_height = self.original_image.size
        aspect_ratio = img_width / img_height
        
        # Calculate base size (100% zoom)
        if aspect_ratio > 1:
            base_width = cell_width
            base_height = int(cell_width / aspect_ratio)
            if base_height > cell_height:
                base_height = cell_height
                base_width = int(cell_height * aspect_ratio)
        else:
            base_height = cell_height
            base_width = int(cell_height * aspect_ratio)
            if base_width > cell_width:
                base_width = cell_width
                base_height = int(cell_width / aspect_ratio)
        
        # Calculate zoomed size
        zoomed_width = int(base_width * self.zoom_level)
        zoomed_height = int(base_height * self.zoom_level)
        
        # Update crop position
        self.crop_x += dx
        self.crop_y += dy
        
        # Ensure crop position stays within bounds
        self.crop_x = max(0, min(self.crop_x, zoomed_width - cell_width))
        self.crop_y = max(0, min(self.crop_y, zoomed_height - cell_height))
        
        # Apply the pan
        self.apply_pan()
        
    def stop_pan(self, event):
        """Stop panning the image"""
        self.is_panning = False
        print("Panning stopped")  # Debug print
    
    def apply_pan(self):
        """Apply the current pan position to the image"""
        if self.original_image is None or self.selected_cell is None:
            return
            
        try:
            # Get the selected cell
            row, col = self.selected_cell
            frame, label = self.grid_cells[row][col]
            
            # Get cell dimensions
            frame.update()  # Ensure we have current size
            cell_width = frame.winfo_width() - 8  # Account for padding
            cell_height = frame.winfo_height() - 8
            
            # Get original image dimensions
            img_width, img_height = self.original_image.size
            aspect_ratio = img_width / img_height
            
            # Calculate base size (100% zoom) preserving aspect ratio
            if aspect_ratio > 1:
                # Image is wider than tall
                base_width = cell_width
                base_height = int(cell_width / aspect_ratio)
                if base_height > cell_height:
                    base_height = cell_height
                    base_width = int(cell_height * aspect_ratio)
            else:
                # Image is taller than wide
                base_height = cell_height
                base_width = int(cell_height * aspect_ratio)
                if base_width > cell_width:
                    base_width = cell_width
                    base_height = int(cell_width / aspect_ratio)
            
            # Apply zoom factor to the base size
            new_width = int(base_width * self.zoom_level)
            new_height = int(base_height * self.zoom_level)
            
            # Resize image with zoom factor
            resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create white background
            bg = Image.new('RGBA', (cell_width, cell_height), (255, 255, 255, 255))
            
            # Crop the zoomed image based on pan position
            crop_width = min(new_width, cell_width)
            crop_height = min(new_height, cell_height)
            
            # Ensure crop region stays within bounds
            crop_x = max(0, min(self.crop_x, new_width - crop_width))
            crop_y = max(0, min(self.crop_y, new_height - crop_height))
            
            # Crop the zoomed image to fit the cell
            resized_image = resized_image.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
            
            # Paste onto white background
            bg.paste(resized_image, (0, 0))
            
            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(bg)
            label.configure(image=photo)
            label.image = photo  # Keep reference!
            
        except Exception as e:
            print(f"Error applying pan: {e}")
            messagebox.showerror("Error", f"Failed to apply pan: {str(e)}")
    
    def select_cell(self, row, col):
        """Select a cell in the grid"""
        print(f"\n=== Selecting cell [{row}, {col}] ===")  # Debug print
        
        # Clear previous selection
        if hasattr(self, 'selected_cell'):
            if self.selected_cell is not None:
                old_row, old_col = self.selected_cell
                old_frame, _ = self.grid_cells[old_row][old_col]
                old_frame.configure(borderwidth=1, relief="solid")
        
        # Update selection
        self.selected_cell = (row, col)
        frame, _ = self.grid_cells[row][col]
        frame.configure(borderwidth=4, relief="solid")
        print(f"Selected cell at [{row}, {col}]")  # Debug print

    def filter_images(self, *args):
        """Filter images based on the filter text"""
        if hasattr(self, 'table'):
            try:
                # Get filter text and remove any quotes
                filter_text = self.filter_text.get().lower().strip('"\'')
                print(f"\n=== Filtering images with: '{filter_text}' ===")  # Debug print
                
                if filter_text:
                    # Split filter text by spaces
                    filter_terms = [term.strip() for term in filter_text.split()]
                    print(f"Searching for terms: {filter_terms}")  # Debug print
                    
                    # Start with all rows
                    mask = pd.Series([True] * len(self.df), index=self.df.index)
                    
                    # Apply each filter term with AND logic
                    for term in filter_terms:
                        term = term.strip()
                        if term:  # Skip empty terms
                            if term.startswith('!'):  # Exclusion term
                                exclude_term = term[1:].strip()  # Remove ! and whitespace
                                if exclude_term:  # Only if there's something to exclude
                                    term_mask = ~self.df['Name'].str.contains(exclude_term, case=False, na=False)
                                    print(f"Excluding rows with name containing: '{exclude_term}'")  # Debug print
                            else:  # Inclusion term
                                term_mask = self.df['Name'].str.contains(term, case=False, na=False)
                                print(f"Including rows with name containing: '{term}'")  # Debug print
                            mask = mask & term_mask
                    
                    # Debug print matches
                    print("\nMatching results:")
                    for idx, row in self.df[mask].iterrows():
                        print(f"Match found in row {idx}: {row['Name']}")
                    
                    filtered_df = self.df[mask].copy()
                    print(f"\nFound {len(filtered_df)} matching files")  # Debug print
                else:
                    filtered_df = self.df.copy()
                    print("No filter applied, showing all files")  # Debug print
                
                # Update table
                self.table.model.df = filtered_df
                
                # Only update column widths if we have data
                if not filtered_df.empty:
                    # Preserve column widths
                    for col in filtered_df.columns:
                        if col in self.table.columnwidths:
                            width = max(
                                len(str(filtered_df[col].max())),
                                len(str(filtered_df[col].min())),
                                len(col),
                                self.table.columnwidths[col]
                            )
                            self.table.columnwidths[col] = width
                
                # Redraw the table
                self.table.redraw()
                
            except Exception as e:
                print(f"Error in filter_images: {str(e)}")
                traceback.print_exc()  # Print the full traceback for debugging

    def browse_folder(self):
        """Open a directory chooser dialog and update the file list"""
        print("\n=== Browse folder called ===")  # Debug print
        directory = filedialog.askdirectory(
            initialdir=self.current_directory or os.path.dirname(os.path.abspath(__file__))
        )
        if directory:
            print(f"Selected directory: {directory}")  # Debug print
            self.current_directory = directory
            
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
        """Update the list of image files"""
        print("\n=== Updating image files ===")  # Debug print
        
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
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                            full_path = os.path.normpath(os.path.join(root, file))
                            if os.path.exists(full_path):
                                self.image_files.append(full_path)
            else:
                # Get files only from current directory
                files = os.listdir(normalized_directory)
                self.image_files = [os.path.normpath(os.path.join(normalized_directory, f)) 
                                  for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) 
                                  and os.path.isfile(os.path.join(normalized_directory, f))]
            
            print(f"Found {len(self.image_files)} image files")  # Debug print
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
                
                row_cells.append((cell_frame, cell))
            self.grid_cells.append(row_cells)
        
        # Configure grid weights
        for i in range(self.grid_rows):
            self.grid_frame.grid_rowconfigure(i, weight=1)
        for j in range(self.grid_cols):
            self.grid_frame.grid_columnconfigure(j, weight=1)
            
        print(f"Created grid with {self.grid_rows}x{self.grid_cols} cells")  # Debug print

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
                   
        # Add rotate image button
        ttk.Button(self.toolbar, text="Rotate Image",
                   command=self.rotate_image).pack(side="left", padx=5)

        # Add refresh button
        ttk.Button(self.toolbar, text="Refresh", command=self.refresh_file_list).pack(side="left", padx=5)               

    def rename_all_files(self):
        """Rename all files where constructed name differs from current name"""
        try:
            renamed_count = 0
            for idx, row in self.df.iterrows():
                current_name = row['Name']
                new_name = self.reconstruct_filename(row)
                
                if new_name != current_name:
                    old_path = row['File_Path']
                    new_path = self.rename_csv_file(old_path, new_name)
                    
                    # Update the DataFrame
                    self.df.at[idx, 'Name'] = new_name
                    self.df.at[idx, 'File_Path'] = new_path
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
            
        # Redraw with all annotations
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
                    x1, y1 = annotation["start_x"], annotation["start_y"]
                    x2, y2 = annotation["end_x"], annotation["end_y"]
                    # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)
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
                    x1, y1 = annotation["start_x"], annotation["start_y"]
                    x2, y2 = annotation["end_x"], annotation["end_y"]
                    # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)
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
            
    def rotate_image(self):
        """Rotate the selected image by 90 degrees clockwise"""
        if self.selected_cell is None or self.original_image is None or self.current_image_path is None:
            messagebox.showinfo("No Image Selected", "Please select an image to rotate first")
            return
            
        try:
            # Create a dialog to ask for rotation angle
            rotation_options = ["90° Clockwise", "180°", "90° Counter-Clockwise"]
            rotation_choice = simpledialog.askstring(
                "Rotate Image",
                "Select rotation angle:",
                initialvalue=rotation_options[0],
                parent=self.master
            )
            
            if rotation_choice is None:  # User cancelled
                return
                
            # Determine rotation angle in degrees
            if rotation_choice == "90° Clockwise":
                angle = -90  # PIL rotates counter-clockwise, so negative for clockwise
            elif rotation_choice == "180°":
                angle = 180
            elif rotation_choice == "90° Counter-Clockwise":
                angle = 90
            else:
                messagebox.showinfo("Invalid Selection", "Please select a valid rotation angle")
                return
                
            # Rotate the original image
            rotated_image = self.original_image.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            
            # Update the original image reference
            self.original_image = rotated_image
            
            # Reset zoom and pan
            self.zoom_level = 1.0
            self.crop_x = 0
            self.crop_y = 0
            
            # Display the rotated image
            # Use the apply_zoom method to display the rotated image
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
            
            # Draw all annotations on the image
            if self.current_image_path in self.annotations:
                for annotation in self.annotations[self.current_image_path]:
                    color = annotation["color"]
                    
                    if annotation["type"] == "text":
                        # Draw text annotation
                        try:
                            font = ImageFont.truetype("arial.ttf", 16)
                        except IOError:
                            font = ImageFont.load_default()
                        
                        draw.text((annotation["x"], annotation["y"]), annotation["text"], 
                                fill=color, font=font)
                                
                    elif annotation["type"] == "arrow":
                        # Draw arrow annotation
                        draw.line([(annotation["start_x"], annotation["start_y"]), 
                                  (annotation["end_x"], annotation["end_y"])], 
                                 fill=color, width=2)
                        # Draw arrowhead
                        self._draw_arrowhead(draw, annotation["start_x"], annotation["start_y"],
                                           annotation["end_x"], annotation["end_y"], color)
                                
                    elif annotation["type"] == "rectangle":
                        # Draw rectangle - ensure coordinates are properly ordered
                        x1, y1 = annotation["start_x"], annotation["start_y"]
                        x2, y2 = annotation["end_x"], annotation["end_y"]
                        # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                        x1, x2 = min(x1, x2), max(x1, x2)
                        y1, y2 = min(y1, y2), max(y1, y2)
                        draw.rectangle([(x1, y1), (x2, y2)],
                                     outline=color, width=2)
                                
                    elif annotation["type"] == "circle":
                        # Draw circle - ensure coordinates are properly ordered
                        x1, y1 = annotation["start_x"], annotation["start_y"]
                        x2, y2 = annotation["end_x"], annotation["end_y"]
                        # Sort coordinates to ensure x1 <= x2 and y1 <= y2
                        x1, x2 = min(x1, x2), max(x1, x2)
                        y1, y2 = min(y1, y2), max(y1, y2)
                        draw.ellipse([(x1, y1), (x2, y2)],
                                   outline=color, width=2)
            
            # Save the image
            image.save(file_path)
            
            messagebox.showinfo("Image Saved", f"Annotated image saved to {file_path}")
            
        except Exception as e:
            print(f"Error saving annotated image: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save annotated image: {str(e)}")
    
    def select_cell(self, row, col):
        """Select a grid cell and make its image the selected image for further actions"""
        try:
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
                    try:
                        self.original_image = Image.open(self.current_image_path)
                        # Also update self.current_image to maintain consistency
                        self.current_image = self.current_image_path
                        print(f"Selected image: {self.current_image_path}")  # Debug print
                        
                        # Reset zoom and pan for the newly selected image
                        self.zoom_level = 1.0
                        self.crop_x = 0
                        self.crop_y = 0
                        
                        # If annotation mode is active, show annotations for this image
                        if self.annotation_mode:
                            self.show_annotations()
                        
                        # Return True to indicate successful selection with image
                        return True
                    except Exception as e:
                        print(f"Error loading image in select_cell: {e}")
                        # Clear the image reference if it can't be loaded
                        self.current_image_path = None
                        self.original_image = None
                        self.current_image = None
            
            # Return False to indicate successful selection but no image
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
            moved_files = []
            for row in selected_rows:
                if row < len(self.df):
                    filename = self.df.iloc[row]['Name']
                    src_path = self.df.iloc[row]['File_Path']  # Use full file path from DataFrame
                    dst_path = os.path.join(dest_dir, filename)
                    
                    # Check if file already exists in destination
                    if os.path.exists(dst_path):
                        if not messagebox.askyesno("File Exists", 
                            f"File {filename} already exists in destination.\nDo you want to overwrite it?"):
                            continue
                    
                    # Move the file
                    shutil.move(src_path, dst_path)
                    moved_files.append(filename)
                    
                    # Clear image display if it was the moved image
                    if self.current_image == src_path and self.selected_cell is not None:
                        self.current_image = None
                        row, col = self.selected_cell
                        _, label = self.grid_cells[row][col]
                        if label:
                            label.configure(image='')
                            label.image = None

            # Update the DataFrame and table
            if moved_files:
                self.df = self.df[~self.df['Name'].isin(moved_files)]
                self.table.model.df = self.df
                self.table.redraw()
                
                # Update image files list
                self.image_files = [f for f in self.image_files if f not in moved_files]
                
                # Show success message with count of moved files
                messagebox.showinfo("Success", f"Moved {len(moved_files)} files to:\n{dest_dir}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move files:\n{str(e)}")

    def delete_selected_files(self):
        """Delete selected files"""
        # Get selected rows from the table's multiplerowlist
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select files to delete")
            return

        # Show confirmation dialog with count of files
        if not messagebox.askyesno("Confirm Delete", 
                               f"Are you sure you want to delete {len(selected_rows)} selected files?",
                               icon='warning'):
            return

        deleted_files = []
        try:
            for row in selected_rows:
                if row < len(self.df):
                    filename = self.df.iloc[row]['Name']
                    # Use the File_Path column directly instead of constructing the path
                    filepath = self.df.iloc[row]['File_Path']

                    try:
                        # Delete the file
                        os.remove(filepath)
                        deleted_files.append(filename)
                        
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
            if deleted_files:
                self.df = self.df[~self.df['Name'].isin(deleted_files)]
                self.table.model.df = self.df
                self.table.redraw()
                
                # Update image files list
                self.image_files = [f for f in self.image_files if f not in deleted_files]
                
                messagebox.showinfo("Success", f"Deleted {len(deleted_files)} files")
                
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
        """Update the list of CSV files"""
        print("\n=== Updating file list ===")  # Debug print
        files = os.listdir(self.current_directory)
        self.csv_files = [f for f in files if f.lower().endswith('.png')]
        print(f"Found {len(self.csv_files)} CSV files")  # Debug print

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

if __name__ == "__main__":
    try:
        app = ImageBrowser()
        logging.info("ImageBrowser application started")
        
        # Add a proper shutdown mechanism
        def on_closing():
            logging.info("Application is closing")
            try:
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