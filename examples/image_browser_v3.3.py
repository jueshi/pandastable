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
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pandas as pd
from pandastable import Table, TableModel
from datetime import datetime
import shutil
import traceback
import logging
import sys

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
        self.grid_rows = 2
        self.grid_cols = 2
        self.cell_width = 200
        self.cell_height = 200
        self.is_horizontal = False  # Start with vertical layout
        self.filter_text = tk.StringVar()
        self.filter_text.trace_add("write", self.filter_images)
        self.selected_cell = None  # Initialize selected_cell
        self.grid_cells = []  # Initialize grid_cells list
        
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
        
        # Create DataFrame for files
        self.update_file_dataframe()
        
        # Create pandastable
        self.table = Table(self.pt_frame, dataframe=self.df,
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
        for file in os.listdir(self.current_directory):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                full_path = os.path.join(self.current_directory, file)
                file_stat = os.stat(full_path)
                
                # Get basic file info
                file_info = {
                    'Name': file,
                    'File_Path': full_path,  # Add full path for direct access
                    'Date_Modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'Size_(KB)': round(file_stat.st_size / 1024, 2)
                }
                
                # Add fields from filename
                name_without_ext = os.path.splitext(file)[0]
                fields = name_without_ext.split('_')
                for i in range(self.max_fields):
                    field_name = f'Field_{i+1}'
                    file_info[field_name] = fields[i] if i < len(fields) else ''
                
                data.append(file_info)               
        
        # Create DataFrame with a reset index
        self.df = pd.DataFrame(data)
        if not self.df.empty:
            # Ensure consistent column order
            columns = ['Name', 'File_Path', 'Date_Modified', 'Size_(KB)']
            columns.extend([f'Field_{i+1}' for i in range(self.max_fields)])
            self.df = self.df[columns]
            self.df.sort_values(by='Date_Modified', ascending=False, inplace=True)            

    def reconstruct_filename(self, row):
        """Reconstruct filename from columns starting with 'F_'"""
        # Find columns starting with 'F_'
        f_columns = [col for col in row.index if col.startswith('Field_')]
        
        # Sort the columns to maintain order, in case the user changed the column order in the table
        # f_columns.sort(key=lambda x: int(x.split('_')[1]))
        
        # Extract values from these columns, skipping None/empty values
        filename_parts = [str(row[col]) for col in f_columns if pd.notna(row[col]) and str(row[col]).strip()]
        
        # Join with underscore, add .csv extension
        new_filename = '_'.join(filename_parts).replace('\n', '') + '.png'
        
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
                        self.display_image(filename)
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

    def display_image(self, filename):
        """Display the selected image in the selected grid cell"""
        print(f"\n=== Displaying image: {filename} ===")  # Debug print
        
        if self.selected_cell is None:
            messagebox.showinfo("Info", "Please select a grid cell first")
            return
            
        try:
            # Open image
            image_path = os.path.join(self.current_directory, filename)
            print(f"Loading image from: {image_path}")  # Debug print
            image = Image.open(image_path)
            
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
            
            # Store current image path
            self.current_image = image_path
            print("Image displayed successfully")  # Debug print
            
        except Exception as e:
            print(f"Error displaying image: {e}")  # Debug print
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

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
            filter_text = self.filter_text.get().lower()
            if filter_text:
                # Apply filter across all columns
                mask = self.df.apply(lambda x: x.astype(str).str.contains(filter_text, case=False)).any(axis=1)
                filtered_df = self.df[mask]
            else:
                filtered_df = self.df
            
            # Update table
            self.table.model.df = filtered_df
            self.table.redraw()

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
        files = os.listdir(self.current_directory)
        self.image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        print(f"Found {len(self.image_files)} image files")  # Debug print

    def get_max_fields(self):
        """Get the maximum number of underscore-separated fields in filenames"""
        max_fields = 0
        for file in self.image_files:
            # Remove extension and split by underscore
            name_without_ext = os.path.splitext(file)[0]
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
        
        # Create new grid cells
        for i in range(self.grid_rows):
            row_cells = []
            for j in range(self.grid_cols):
                # Create frame for cell
                cell_frame = ttk.Frame(self.grid_frame, borderwidth=1, relief="solid", width=200, height=200)
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
                  
        # Add move files button
        ttk.Button(self.toolbar, text="Move Files", 
                  command=self.move_selected_files).pack(side="left", padx=5)
                  
        # Add delete files button
        ttk.Button(self.toolbar, text="Delete Files", 
                  command=self.delete_selected_files).pack(side="left", padx=5)

        # Add rename all files button
        ttk.Button(self.toolbar, text="Rename All Files",
                  command=self.rename_all_files).pack(side="left", padx=5)

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
                    src_path = os.path.join(self.current_directory, filename)
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
                    filepath = os.path.join(self.current_directory, filename)

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

    def refresh_file_list(self):
        print(f"current directory: {self.current_directory}")  # Debug print
        
        # Update file list
        self.update_file_list()
        
        # # Update max fields
        # old_max = self.max_fields
        # self.max_fields = self.get_max_fields()
        # print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
        
        # Update file browser
        self.setup_file_browser()

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