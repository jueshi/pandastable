"""
S-Parameter Browser Application with Excel-like File List

A tkinter-based S-parameter browser that displays s2p/s4p files in a dual-pane layout.
The first panel shows the list of S-parameter files with filtering and sorting capabilities.
The second panel displays the SDD11/SDD21 plots for s4p files or S11/S21 plots for s2p files.

Features:
- File browser with:
  - Sorting by name, date, size, and filename fields
  - Dynamic columns based on filename structure
  - Filter functionality across all fields
  - Horizontal scrolling for many fields
- S-parameter visualization in second panel
- Vertical and horizontal layout options
- Directory selection
- File operations (move, delete)
"""
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
import os
import sys

# Add custom pandastable path to sys.path BEFORE importing pandastable
custom_pandastable_path = r"C:\Users\juesh\OneDrive\Documents\windsurf\pandastable\pandastable"
# custom_pandastable_path = r"C:\Users\JueShi\OneDrive - Astera Labs, Inc\Documents\windsurf\pandastable\pandastable"
if os.path.exists(custom_pandastable_path):
    # Insert at the beginning of sys.path to prioritize this version
    sys.path.insert(0, custom_pandastable_path)
    print(f"Using custom pandastable from: {custom_pandastable_path}")

import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
from pandastable import Table, TableModel
from datetime import datetime
import shutil
import traceback
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle, Circle
from matplotlib.path import Path
from matplotlib.spines import Spine
import skrf as rf  # RF toolbox for S-parameters
import re
import traceback
import csv
from matplotlib import projections
from matplotlib.projections import PolarAxes
from matplotlib.transforms import Affine2D
import mpl_toolkits.axisartist.floating_axes as floating_axes
import mpl_toolkits.axisartist.grid_finder as grid_finder

class SmithAxes(PolarAxes):
    """Custom Smith chart projection"""
    name = 'smith'

    class SmithTransform(PolarAxes.PolarTransform):
        def transform_path_non_affine(self, path):
            # Transform path using the Smith chart mapping: z -> (z-1)/(z+1)
            vertices = path.vertices
            transformed = (vertices[:, 0] + 1j * vertices[:, 1] - 1) / (vertices[:, 0] + 1j * vertices[:, 1] + 1)
            return np.column_stack((transformed.real, transformed.imag))

        def transform_non_affine(self, points):
            # Transform points using the Smith chart mapping
            complex_points = points[:, 0] + 1j * points[:, 1]
            transformed = (complex_points - 1) / (complex_points + 1)
            return np.column_stack((transformed.real, transformed.imag))

    def __init__(self, *args, **kwargs):
        PolarAxes.__init__(self, *args, **kwargs)
        self.grid_finder = grid_finder.GridFinder(
            extremes=(-1, 1, -1, 1),
            grid_locator1=grid_finder.FixedLocator([-1, -0.5, 0, 0.5, 1]),
            grid_locator2=grid_finder.FixedLocator([-1, -0.5, 0, 0.5, 1])
        )
        self.set_transform(self.SmithTransform())

    def _gen_axes_patch(self):
        return Circle((0, 0), 1, fill=False)

    def _gen_axes_spines(self):
        path = Path.unit_circle()
        spine = Spine(self, 'polar', path)
        spine.set_transform(self.transAxes)
        return {'polar': spine}

# Register the Smith chart projection
projections.register_projection(SmithAxes)

class SParamBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("S-Parameter Browser")
        self.geometry("1200x800")
        
        # Create main container for S-parameter viewer
        self.sparam_view_container = ttk.Frame(self)
        self.sparam_view_container.pack(fill=tk.BOTH, expand=True)
        
        # Initialize variables
        self.current_file = None
        self.is_horizontal = False  # Start with vertical layout
        self.filter_text = tk.StringVar()
        self.filter_text.trace_add("write", self.filter_files)
        self.last_clicked_row = None
        self.sparam_frame = None
        self.include_subfolders = tk.BooleanVar(value=False)
        
        # Port mapping (default 1-to-1)
        self.port_mapping = [1, 2, 3, 4]  # Maps logical ports to physical ports
        
        # Initialize plot variables
        self.figure = None
        self.canvas = None
        self.last_networks = []
        self.markers = []  # List to store marker frequencies
        self.marker_text = None  # Text widget for marker values
        
        # Initialize specification data
        self.spec_data = {}  # Dictionary to store specification data for each parameter
        
        # Initialize plot control variables
        self.plot_mag_var = tk.BooleanVar(value=True)
        self.plot_phase_var = tk.BooleanVar(value=False)  # Start with phase unselected
        self.plot_sdd11_var = tk.BooleanVar(value=True)
        self.plot_sdd21_var = tk.BooleanVar(value=True)
        self.show_spec_var = tk.BooleanVar(value=True)
        self.show_tdr_var = tk.BooleanVar(value=False)  # Add TDR control variable
        self.show_pulse_var = tk.BooleanVar(value=False)  # Add pulse response control variable
        self.show_impedance_var = tk.BooleanVar(value=False)  # Add impedance profile control variable
        
        # Add zoom control variables
        self.freq_min = tk.StringVar(value='')
        self.freq_max = tk.StringVar(value='')
        self.mag_min = tk.StringVar(value='')
        self.mag_max = tk.StringVar(value='')
        self.phase_min = tk.StringVar(value='')
        self.phase_max = tk.StringVar(value='')       
        self.dist_min = tk.StringVar(value='')  # Add distance control for TDR
        self.dist_max = tk.StringVar(value='')  # Add distance control for TDR
        self.time_min = tk.StringVar(value='')  # Add time control for pulse response
        self.time_max = tk.StringVar(value='')  # Add time control for pulse response
        self.amp_min = tk.StringVar(value='')   # Add amplitude control for pulse response
        self.amp_max = tk.StringVar(value='')   # Add amplitude control for pulse response
        
        # Add time domain resolution control variables
        self.padding_factor = tk.StringVar(value='4')  # Zero-padding factor
        self.window_type = tk.StringVar(value='exponential')  # Window function type
        
        # Add Smith chart window variable
        self.smith_window = None
        
        # Set and validate default directory
        default_dir = r"C:\Users\JueShi\Astera Labs, Inc\Silicon Engineering - T3_MPW_Rx_C2M_Test_Results"
        self.current_directory = default_dir if self.validate_directory(default_dir) else None
        
        if self.current_directory is None:
            self.set_safe_directory()
        
        # Get initial list of S-parameter files
        self.update_file_list()
        
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
        
        # Create the file browser and S-parameter viewer
        self.setup_file_browser()
        self.setup_sparam_viewer()

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

        # Create S-parameter viewer container frame
        self.sparam_container = ttk.Frame(self.paned)
        self.paned.add(self.sparam_container, weight=2)

        # Set minimum sizes to prevent collapse
        if self.is_horizontal:
            self.file_frame.configure(width=400)
            self.sparam_container.configure(width=800)
        else:
            self.file_frame.configure(height=300)
            self.sparam_container.configure(height=500)

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
        ttk.Label(filter_frame, text="Filter Files:").pack(side="left", padx=(0, 5))
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_text)
        filter_entry.pack(side="left", fill="x", expand=True)
        
        # Create table frame
        table_frame = ttk.Frame(self.pt_frame)
        table_frame.pack(fill="both", expand=True)
        
        # Create DataFrame for files
        self.update_file_dataframe()
        
        # Create pandastable with editable cells
        self.table = Table(table_frame, dataframe=self.df,
                        showtoolbar=True, showstatusbar=True)
        
        # Enable editing and bind to key events
        self.table.editable = True
        self.table.bind('<Key>', self.on_key_press)
        self.table.bind('<Return>', self.on_return_press)
        self.table.bind('<FocusOut>', self.on_focus_out)
        
        self.table.show()
        
        # Configure table options
        self.table.autoResizeColumns()
        
        # Set default column widths
        default_widths = {
            'Name': 200,
            'File_Path': 400,
            'Date_Modified': 150,
            'Size_(KB)': 100
        }
        
        # Set column widths
        for col in self.df.columns:
            if col in default_widths:
                self.table.columnwidths[col] = default_widths[col]
            else:
                # For empty DataFrame or other columns, set a reasonable default
                if self.df.empty:
                    self.table.columnwidths[col] = 100
                else:
                    try:
                        max_width = max(len(str(x)) for x in self.df[col].head(20))
                        self.table.columnwidths[col] = max(min(max_width * 10, 200), 50)
                    except:
                        self.table.columnwidths[col] = 100

        self.table.redraw()
        
        # Bind selection event
        self.table.bind('<ButtonRelease-1>', self.on_table_select)
        self.table.bind('<Up>', self.on_key_press)
        self.table.bind('<Down>', self.on_key_press)

    def filter_files(self, *args):
        """Filter files based on the filter text with optimized performance"""
        if hasattr(self, 'table'):
            try:
                # Get filter text and remove any quotes
                filter_text = self.filter_text.get().lower().strip('"\'')
                
                if filter_text:
                    # Split filter text by AND (both & and +)
                    filter_terms = [term.strip() for term in filter_text.replace('&', '+').split('+')]
                    
                    # Convert DataFrame to string only once and cache it
                    if not hasattr(self, '_str_df') or len(self._str_df) != len(self.df):
                        self._str_df = self.df.astype(str).apply(lambda x: x.str.lower())
                    
                    # Use vectorized operations for better performance
                    mask = pd.Series([True] * len(self._str_df), index=self._str_df.index)
                    
                    for term in filter_terms:
                        term = term.strip()
                        if term.startswith('!'):
                            exclude_term = term[1:].strip()
                            if exclude_term:
                                # Use numpy's vectorized operations
                                term_mask = ~self._str_df.apply(lambda x: x.str.contains(exclude_term, regex=False)).any(axis=1)
                        else:
                            term_mask = self._str_df.apply(lambda x: x.str.contains(term, regex=False)).any(axis=1)
                        mask &= term_mask
                    
                    # Debug print matches
                    print("\nMatching results:")
                    for idx, row in self._str_df[mask].iterrows():
                        print(f"Match found in row {idx}:")
                        for col in self._str_df.columns:
                            matches = []
                            col_value = str(row[col]).lower()
                            for term in filter_terms:
                                term = term.strip()
                                if term.startswith('!'):
                                    continue  # Skip exclusion terms in match display
                                if term in col_value:
                                    matches.append(term)
                            if matches:
                                print(f"  Column '{col}': {row[col]} (matched terms: {matches})")
                    
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
                print(f"Error in filter_files: {str(e)}")
                traceback.print_exc()  # Print the full traceback for debugging

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
                
                # Get filename and path directly from the displayed DataFrame
                displayed_df = self.table.model.df
                if row < 0 or row >= len(displayed_df): # Add this check
                    print(f"Row index {row} out of bounds for displayed_df of length {len(displayed_df)}")
                    return
                file_path = str(displayed_df.iloc[new_row]['File_Path'])

                # Load the S-parameter file
                self.load_sparam_file(file_path)   
            elif event.char and event.char.isprintable():
                row = self.table.getSelectedRow()
                col = self.table.getSelectedColumn()
                if row is not None and col is not None:
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
            # Get the displayed DataFrame before any filter operations
            displayed_df = self.table.model.df
            if row < len(displayed_df):
                # Get current filename and path from displayed DataFrame
                file_path = os.path.normpath(str(displayed_df.iloc[row]['File_Path']))
                current_name = displayed_df.iloc[row]['Name']
                
                # Reconstruct filename from Field_ columns
                new_filename = self.reconstruct_filename(displayed_df.iloc[row])
                
                # If filename is different, rename the file
                if new_filename != current_name:
                    print(f"Renaming file from {current_name} to {new_filename}")  # Debug print
                    new_filepath = self.rename_sparam_file(file_path, new_filename)
                    
                    if new_filepath != file_path:  # Only update if rename was successful
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
                        
                        # Store current filter text
                        filter_text = self.filter_text.get()
                        
                        # Temporarily disable filter to update the model
                        if filter_text:
                            self.filter_text.set('')
                            self.table.model.df = displayed_df
                            self.table.redraw()
                        
                        # Reapply the filter if it was active
                        if filter_text:
                            self.filter_text.set(filter_text)
                        
                        # Show confirmation
                        messagebox.showinfo("File Renamed", 
                                        f"File has been renamed from:\n{current_name}\nto:\n{new_filename}")
                        
                else:
                    print("No changes detected")  # Debug print
            
        except Exception as e:
            print(f"Error checking for changes: {e}")
            traceback.print_exc()
 
    def setup_sparam_viewer(self):
        """Setup the S-parameter viewer interface"""
        try:
            # Create top button frame
            top_btn_frame = ttk.Frame(self.sparam_view_container)
            top_btn_frame.grid(row=0, column=0, sticky='ew', padx=2, pady=2)
            
            # Add status labels
            self.td_status = ttk.Label(top_btn_frame, text="")
            self.td_status.pack(side=tk.RIGHT, padx=2)
            
            self.window_preview = ttk.Label(top_btn_frame, text="")
            self.window_preview.pack(side=tk.RIGHT, padx=10)
            
            # Create frame for S-parameter viewer
            if hasattr(self, 'sparam_frame') and self.sparam_frame is not None:
                self.sparam_frame.destroy()
            self.sparam_frame = ttk.Frame(self.sparam_container)
            self.sparam_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Create a container frame that will use grid
            self.sparam_view_container = ttk.Frame(self.sparam_frame)
            self.sparam_view_container.pack(fill="both", expand=True)
            
            # Add filter entry for S-parameter viewer using grid
            self.sparam_filter_frame = ttk.Frame(self.sparam_view_container)
            self.sparam_filter_frame.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
            self.sparam_filter_frame.columnconfigure(1, weight=1)  # Make the entry expand
            
            # Use the existing StringVar - don't add another trace
            # print(f"Current filter value: '{self.filter_text.get()}'")  # Debug print
            
            # # Create and set up the entry widget
            # filter_entry = ttk.Entry(self.sparam_filter_frame, textvariable=self.filter_text)
            # filter_entry.grid(row=0, column=1, sticky='ew')
            
            # Create frame for plot using grid
            self.sparam_plot_frame = ttk.Frame(self.sparam_view_container)
            self.sparam_plot_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
            
            # Configure grid weights
            self.sparam_view_container.rowconfigure(1, weight=1)
            self.sparam_view_container.columnconfigure(0, weight=1)
            
            # Create empty plot for S-parameter viewing
            self.setup_plot_area()
            
            # Store original data
            self.original_sparam_df = None
            
            # Add marker controls
            self.marker_frame = ttk.LabelFrame(self.sparam_view_container, text="Markers")
            self.marker_frame.grid(row=2, column=0, sticky='ew', padx=5, pady=5)
            
            # self.marker_entry = ttk.Entry(self.marker_frame, width=15)
            # self.marker_entry.pack(side=tk.LEFT, padx=5)
            
            self.add_marker_button = ttk.Button(self.marker_frame, text="Add Marker", command=self.add_marker)
            self.add_marker_button.pack(side=tk.LEFT, padx=5)
            
            self.clear_markers_button = ttk.Button(self.marker_frame, text="Clear Markers", command=self.clear_markers)
            self.clear_markers_button.pack(side=tk.LEFT, padx=5)
            
            # Create marker text box
            self.marker_text = tk.Text(self.sparam_view_container, height=2, width=50)
            self.marker_text.grid(row=3, column=0, sticky='ew', padx=5, pady=5)
            
            # Create plot control frame with more compact layout
            self.plot_control_frame = ttk.Frame(self.sparam_view_container)
            self.plot_control_frame.grid(row=4, column=0, sticky='ew', padx=2, pady=2)
            
            # Create a single frame for all controls
            controls_frame = ttk.Frame(self.plot_control_frame)
            controls_frame.pack(fill='x', padx=2)
            
            # View type controls (Magnitude/Phase) - more compact
            ttk.Label(controls_frame, text="View:").pack(side=tk.LEFT, padx=2)
            ttk.Checkbutton(controls_frame, text="Mag", variable=self.plot_mag_var, 
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Checkbutton(controls_frame, text="Ph", variable=self.plot_phase_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Parameter controls (SDD11/SDD21) - more compact
            ttk.Label(controls_frame, text="Params:").pack(side=tk.LEFT, padx=2)
            ttk.Checkbutton(controls_frame, text="SDD11", variable=self.plot_sdd11_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Checkbutton(controls_frame, text="SDD21", variable=self.plot_sdd21_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Specification controls - more compact
            ttk.Button(controls_frame, text="Load Spec", command=self.load_specification,
                      width=8).pack(side=tk.LEFT, padx=2)
            ttk.Checkbutton(controls_frame, text="Show", variable=self.show_spec_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Time Domain controls - more compact
            ttk.Label(controls_frame, text="Time:").pack(side=tk.LEFT, padx=2)
            ttk.Checkbutton(controls_frame, text="TDR", variable=self.show_tdr_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Checkbutton(controls_frame, text="Pulse", variable=self.show_pulse_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Impedance profile control - more compact
            ttk.Checkbutton(controls_frame, text="Z Profile", variable=self.show_impedance_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            # Add zoom control frame with compact layout
            zoom_frame = ttk.LabelFrame(self.sparam_view_container, text="Zoom")
            zoom_frame.grid(row=5, column=0, sticky='ew', padx=2, pady=2)
            
            # Create main zoom controls container
            zoom_container = ttk.Frame(zoom_frame)
            zoom_container.pack(fill='x', padx=2, pady=2)
            
            # Frequency domain controls - more compact
            freq_frame = ttk.Frame(zoom_container)
            freq_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(freq_frame, text="f(GHz):").pack(side=tk.LEFT)
            ttk.Entry(freq_frame, textvariable=self.freq_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(freq_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(freq_frame, textvariable=self.freq_max, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Magnitude controls - more compact
            mag_frame = ttk.Frame(zoom_container)
            mag_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(mag_frame, text="dB:").pack(side=tk.LEFT)
            ttk.Entry(mag_frame, textvariable=self.mag_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(mag_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(mag_frame, textvariable=self.mag_max, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Phase controls - more compact
            phase_frame = ttk.Frame(zoom_container)
            phase_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(phase_frame, text="Ph(°):").pack(side=tk.LEFT)
            ttk.Entry(phase_frame, textvariable=self.phase_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(phase_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(phase_frame, textvariable=self.phase_max, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Time domain controls - more compact
            time_frame = ttk.Frame(zoom_container)
            time_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(time_frame, text="t(ps):").pack(side=tk.LEFT)
            ttk.Entry(time_frame, textvariable=self.time_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(time_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(time_frame, textvariable=self.time_max, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Distance controls - more compact
            dist_frame = ttk.Frame(zoom_container)
            dist_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(dist_frame, text="d(mm):").pack(side=tk.LEFT)
            ttk.Entry(dist_frame, textvariable=self.dist_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(dist_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(dist_frame, textvariable=self.dist_max, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Amplitude controls - more compact
            amp_frame = ttk.Frame(zoom_container)
            amp_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(amp_frame, text="Amp:").pack(side=tk.LEFT)
            ttk.Entry(amp_frame, textvariable=self.amp_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(amp_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(amp_frame, textvariable=self.amp_max, width=6).pack(side=tk.LEFT, padx=1)
            
            # Zoom buttons - more compact
            btn_frame = ttk.Frame(zoom_container)
            btn_frame.pack(side=tk.RIGHT, padx=2)
            ttk.Button(btn_frame, text="Apply", command=self.apply_zoom, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Button(btn_frame, text="Reset", command=self.reset_zoom, width=6).pack(side=tk.LEFT, padx=1)

            # Add time domain settings frame with compact layout
            td_settings_frame = ttk.LabelFrame(self.sparam_view_container, text="Time Domain")
            td_settings_frame.grid(row=6, column=0, sticky='ew', padx=2, pady=2)
            
            # Create compact settings container
            settings_container = ttk.Frame(td_settings_frame)
            settings_container.pack(fill='x', padx=2, pady=2)
            
            # Padding factor control - more compact
            pad_frame = ttk.Frame(settings_container)
            pad_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(pad_frame, text="Pad:").pack(side=tk.LEFT)
            vcmd = (self.register(self._validate_padding_factor), '%P')
            padding_entry = ttk.Entry(pad_frame, textvariable=self.padding_factor, 
                                    width=5, validate='key', validatecommand=vcmd)
            padding_entry.pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(settings_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Window function control - more compact
            window_frame = ttk.Frame(settings_container)
            window_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(window_frame, text="Win:").pack(side=tk.LEFT)
            window_combo = ttk.Combobox(window_frame, textvariable=self.window_type,
                                      values=['none', 'hamming', 'hanning', 'blackman', 'kaiser', 'flattop', 'exponential'],
                                      width=8, state='readonly')
            window_combo.pack(side=tk.LEFT, padx=1)
            
            # Add Low Pass checkbox
            lowpass_frame = ttk.Frame(settings_container)
            lowpass_frame.pack(side=tk.LEFT, padx=2)
            # Create the variable here to ensure it exists
            if not hasattr(self, 'low_pass_mode'):
                self.low_pass_mode = tk.BooleanVar(value=True)
            lowpass_check = ttk.Checkbutton(lowpass_frame, text="Low Pass", variable=self.low_pass_mode)
            lowpass_check.pack(side=tk.LEFT, padx=1)
            
            # Apply button - more compact
            ttk.Button(settings_container, text="Apply", width=6,
                      command=self._apply_td_settings).pack(side=tk.RIGHT, padx=2)
            
            # Initialize markers
            self.markers = []
            
        except Exception as e:
            print(f"Error in setup_sparam_viewer: {e}")
            traceback.print_exc()

    def setup_plot_area(self):
        """Setup the matplotlib figure and canvas with optimized configuration"""
        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor='white')
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.sparam_plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar with custom buttons
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.sparam_plot_frame)
        self.toolbar.update()
        
        # Initialize empty plot with grid
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.text(0.5, 0.5, 'Select files to cascade', 
                     horizontalalignment='center',
                     verticalalignment='center')
        
        # Enable fast rendering
        self.figure.set_tight_layout(True)
        self.canvas.draw()
        
    def _validate_padding_factor(self, value):
        """Validate the zero-padding factor input"""
        if value == "":
            return True
        try:
            factor = int(value)
            return 2 <= factor <= 128
        except ValueError:
            return False
            
    def _update_window_preview(self):
        """Update window function preview information"""
        window_type = self.window_type.get()
        descriptions = {
            'none': 'No window - Keep original spectrum',
            'hamming': 'Hamming window - Good frequency resolution',
            'hanning': 'Hanning window - Reduced spectral leakage',
            'blackman': 'Blackman window - Best sidelobe suppression',
            'kaiser': 'Kaiser window - Adjustable main lobe width'
        }
        self.window_preview.config(text=descriptions.get(window_type, ''))
        
    def _apply_td_settings(self):
        """Apply time domain analysis settings"""
        try:
            # Validate settings
            pad_factor = int(self.padding_factor.get())
            if not (2 <= pad_factor <= 128):
                raise ValueError("Zero-padding factor must be between 2-128")
                
            # Update status safely
            self.update_status("Applying settings...")
            self.update_idletasks()
            
            # Update plots
            self.update_plot()
            
            # Success message
            self.update_status("Settings applied", clear_after=2000)
            
        except Exception as e:
            print(f"TD Settings Error: {str(e)}")
            self.update_status(f"Error: {str(e)}", clear_after=2000)
            
    def update_status(self, message, clear_after=None):
        """Safely update the status message"""
        try:
            if hasattr(self, 'td_status') and self.td_status.winfo_exists():
                self.td_status.config(text=message)
                if clear_after:
                    self.after(clear_after, lambda: self.update_status(""))
        except Exception as ui_error:
            print(f"Status Update Error: {str(ui_error)}")

    def update_file_dataframe(self):
        """Update the pandas DataFrame with file information"""
        print("\n=== Updating file DataFrame ===")  # Debug print
        
        # Define columns
        columns = ['Name', 'File_Path', 'Date_Modified', 'Size_(KB)']
        columns.extend([f'Field_{i+1}' for i in range(self.max_fields)])
        
        # Create empty DataFrame with correct columns if no files found
        if not self.sparam_files:
            print("No S-parameter files found")  # Debug print
            self.df = pd.DataFrame(columns=columns)
            return
            
        # Prepare all data at once
        data_list = []
        
        for file_path in self.sparam_files:
            try:
                file_stat = os.stat(file_path)
                file_name = os.path.basename(file_path)
                
                # Get basic file info
                file_info = {
                    'Name': file_name,
                    'File_Path': file_path,
                    'Date_Modified': pd.to_datetime(datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')),
                    'Size_(KB)': round(file_stat.st_size / 1024, 2)
                }
                
                # Add fields from filename
                name_without_ext = os.path.splitext(file_name)[0]
                fields = name_without_ext.split('_')
                
                # Add all field columns at once
                for i in range(self.max_fields):
                    field_name = f'Field_{i+1}'
                    file_info[field_name] = fields[i] if i < len(fields) else ''
                
                data_list.append(file_info)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        # Create DataFrame with predefined columns
        if data_list:
            self.df = pd.DataFrame(data_list, columns=columns)
            # Sort by date modified (newest first)
            self.df.sort_values(by='Date_Modified', ascending=False, inplace=True)
        else:
            # Create empty DataFrame with correct columns if no valid files found
            self.df = pd.DataFrame(columns=columns)

    def reconstruct_filename(self, row):
        """Reconstruct filename from columns starting with 'F_'"""
        # Find columns starting with 'F_'
        f_columns = [col for col in row.index if col.startswith('Field_')]
        
        # Sort the columns to maintain order, in case the user changed the column order in the table
        # f_columns.sort(key=lambda x: int(x.split('_')[1]))
        
        # Extract values from these columns, skipping None/empty values
        filename_parts = [str(row[col]) for col in f_columns if pd.notna(row[col]) and str(row[col]).strip()]
        
        # Join with underscore, add .csv extension
        new_filename = '_'.join(filename_parts).replace('\n', '') + '.s4p'
        
        return new_filename

    def rename_sparam_file(self, old_filepath, new_filename):
        """Rename S-parameter file on disk"""
        try:
            # Convert to raw string and normalize path separators
            old_filepath = os.path.normpath(str(old_filepath).replace('/', os.sep))
            directory = os.path.dirname(old_filepath)
            new_filepath = os.path.normpath(os.path.join(directory, new_filename))
            
            print("\nRenaming file details:")  # Debug prints
            print(f"Original path: {old_filepath}")
            print(f"Directory: {directory}")
            print(f"New filename: {new_filename}")
            print(f"New full path: {new_filepath}")
            
            # Check if source file exists
            if not os.path.exists(old_filepath):
                print(f"Source file not found: {old_filepath}")  # Debug print
                # Try with forward slashes
                alt_path = old_filepath.replace(os.sep, '/')
                if os.path.exists(alt_path):
                    old_filepath = alt_path
                    print(f"Found file using alternative path: {alt_path}")  # Debug print
                else:
                    raise FileNotFoundError(f"Source file not found: {old_filepath}")
            
            # Check if target directory exists
            if not os.path.exists(directory):
                raise FileNotFoundError(f"Target directory not found: {directory}")
            
            # Check if target file already exists
            if os.path.exists(new_filepath):
                raise FileExistsError(f"Target file already exists: {new_filepath}")
            
            # Rename the file
            print(f"Performing rename operation...")  # Debug print
            os.rename(old_filepath, new_filepath)
            print(f"Rename successful")  # Debug print
            return new_filepath
            
        except Exception as e:
            print(f"\nError renaming file:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Old path: {old_filepath}")
            print(f"New filename: {new_filename}")
            print(f"Directory: {directory}")
            print("\nFull traceback:")
            traceback.print_exc()
            return old_filepath

    def on_table_select(self, event):
        """Handle table row selection"""
        try:
            selected_rows = self.table.multiplerowlist
            if not selected_rows:
                return
                
            networks = []
            for row in selected_rows:
                file_path = self.df.iloc[row].get('File_Path', os.path.join(self.current_directory, self.df.iloc[row]['Name']))
                # Fix potential path separator inconsistencies
                file_path = os.path.normpath(file_path.replace('\\', '/'))
                try:
                    network = rf.Network(os.path.normpath(file_path))
                    networks.append(network)
                except Exception as e:
                    print(f"Error loading network {file_path}: {str(e)}")
                    continue
            
            if networks:
                self.last_networks = networks
                self.plot_network_params(*networks, show_mag=self.plot_mag_var.get(), show_phase=self.plot_phase_var.get())
                
                # Update Smith chart if it's open
                if self.smith_window and tk.Toplevel.winfo_exists(self.smith_window):
                    self.update_smith_chart()
                
        except Exception as e:
            print(f"Error in table selection: {str(e)}")
            traceback.print_exc()

    def parse_sparam_file(self, file_path):
        """Parse an S-parameter file and return frequency and S-parameters."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Find header line and data format
            header = None
            format_line = None
            data_start = 0
            
            # Parse header section
            for i, line in enumerate(lines):
                if line.strip().startswith('#'):
                    if 'hz' in line.lower():  # Look for the main header line
                        header = line.strip().split()
                        print(f"Found header: {header}")
                    elif 'format' in line.lower():
                        format_line = line
                        print(f"Found format line: {format_line}")
                elif line.strip().startswith('!'):
                    data_start = i + 1
                else:
                    break

            if not header:
                raise ValueError("No valid header found in file")

            # Get frequency unit from header
            unit = 'hz'  # Default to Hz
            for i, val in enumerate(header):
                if val.lower() in ['hz', 'khz', 'mhz', 'ghz']:
                    unit = val.lower()
                    break
            print(f"Frequency unit: {unit}")

            # Parse the data section
            data = []
            current_freq = None
            current_values = []
            invalid_lines = 0

            i = data_start
            while i < len(lines):
                line = lines[i].strip()
                
                if not line or line.startswith('#') or line.startswith('!'):
                    i += 1
                    continue

                try:
                    values = [float(x) for x in line.split()]
                    
                    # Check if this is a single-line format (33 values) or multi-line format
                    if len(values) == 33:  # Single line format
                        data.append(values)
                        i += 1
                        continue
                        
                    # Multi-line format handling
                    if len(values) == 9 and current_freq is None:  # First line of group
                        current_freq = values[0]
                        current_values = values[1:]
                    elif len(values) == 8 and current_freq is not None:  # Continuation line
                        current_values.extend(values)
                    else:
                        print(f"Unexpected line format at line {i+1}: {line}")
                        i += 1
                        continue

                    # Check if we have a complete set of values for multi-line format
                    if len(current_values) >= 32:  # 4x4 matrix * 2 values per entry
                        all_values = [current_freq] + current_values[:32]  # Trim any extra values
                        data.append(all_values)
                        current_freq = None
                        current_values = []
                        
                except Exception as e:
                    invalid_lines += 1
                    if invalid_lines <= 5:
                        print(f"Line {i+1}: Failed to parse: {str(e)}")
                        print(f"Line content: {line}")
                
                i += 1

            print(f"Found {len(data)} valid frequency points")
            print(f"Found {invalid_lines} invalid lines")

            if not data:
                raise ValueError("No valid data found in file")

            # Convert to numpy array
            data = np.array(data)
            print(f"Data array shape: {data.shape}")

            # Extract frequency and S-parameters
            freq = data[:, 0]
            s_data = data[:, 1:]  # All columns except frequency
            
            # Convert magnitude/angle format to complex S-parameters
            n_freq = len(freq)
            s_params = np.zeros((n_freq, 4, 4), dtype=complex)
            
            for i in range(4):
                for j in range(4):
                    idx = 2*(i*4 + j)  # Index into the magnitude/angle data
                    mag = s_data[:, idx]
                    ang = s_data[:, idx+1] * np.pi/180  # Convert to radians
                    s_params[:, i, j] = mag * np.exp(1j*ang)
            
            print(f"Frequency range: {freq[0]} to {freq[-1]} {unit}")
            print(f"S-parameter matrix shape: {s_params.shape}")

            return freq, s_params

        except Exception as e:
            print(f"Error parsing S-parameter file: {str(e)}")
            raise

    def calculate_sdd_params(self, s_params):
        """Calculate differential S-parameters from single-ended S-parameters
        Port mapping:
        Differential port 1: P1-P3 (positive-negative)
        Differential port 2: P2-P4 (positive-negative)
        """
        # Transformation matrix for P1-P3, P2-P4 pairing
        M = np.array([[1, 0, -1, 0],
                     [0, 1, 0, -1]]) / np.sqrt(2)  # Changed from [1, 0, -1, 0] to [1, -1, 0, 0]
        M_inv = M.T / 2  # M^-1 = M^T/2 for this specific M

        # Initialize differential S-parameter matrix
        sdd = np.zeros((s_params.shape[0], 2, 2), dtype=complex)

        # Calculate differential S-parameters for each frequency point
        for i in range(s_params.shape[0]):
            # Convert single-ended to differential
            sdd[i] = M @ s_params[i] @ M_inv

        return sdd

    def plot_sparam(self, freq, s_params, n_ports):
        """Plot S-parameters with markers"""
        if freq is None or s_params is None:
            return

        # Store current data
        self.current_freq = freq
        self.current_s_params = s_params
        self.current_n_ports = n_ports

        # Clear the existing plot
        self.figure.clear()

        if n_ports == 4:
            # Create 2x2 subplots for SDD11 and SDD21, magnitude and phase
            ((ax_sdd11_mag, ax_sdd21_mag), 
             (ax_sdd11_phase, ax_sdd21_phase)) = self.figure.subplots(2, 2)
            
            # Calculate differential parameters
            sdd_params = self.calculate_sdd_params(s_params)
            sdd11 = 20 * np.log10(np.abs(sdd_params[:, 0, 0]))
            sdd21 = 20 * np.log10(np.abs(sdd_params[:, 1, 0]))
            sdd11_phase = np.angle(sdd_params[:, 0, 0], deg=True)
            sdd21_phase = np.angle(sdd_params[:, 1, 0], deg=True)

            # Plot SDD11 magnitude
            ax_sdd11_mag.plot(freq/1e9, sdd11, label='SDD11')
            # Add markers for SDD11 magnitude
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_sdd11_mag.plot(marker_freq/1e9, sdd11[idx], 'ro', markersize=8)
                ax_sdd11_mag.annotate(f'{marker_freq/1e9:.3f} GHz\n{sdd11[idx]:.2f} dB',
                           (marker_freq/1e9, sdd11[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_sdd11_mag.set_xlabel('Frequency (GHz)')
            ax_sdd11_mag.set_ylabel('Magnitude (dB)')
            ax_sdd11_mag.set_title('SDD11 Magnitude')
            ax_sdd11_mag.grid(True)
            ax_sdd11_mag.legend()

            # Plot SDD21 magnitude
            ax_sdd21_mag.plot(freq/1e9, sdd21, label='SDD21')
            # Add markers for SDD21 magnitude
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_sdd21_mag.plot(marker_freq/1e9, sdd21[idx], 'ro', markersize=8)
                ax_sdd21_mag.annotate(f'{marker_freq/1e9:.3f} GHz\n{sdd21[idx]:.2f} dB',
                           (marker_freq/1e9, sdd21[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_sdd21_mag.set_xlabel('Frequency (GHz)')
            ax_sdd21_mag.set_ylabel('Magnitude (dB)')
            ax_sdd21_mag.set_title('SDD21 Magnitude')
            ax_sdd21_mag.grid(True)
            ax_sdd21_mag.legend()

            # Plot SDD11 phase
            ax_sdd11_phase.plot(freq/1e9, sdd11_phase, label='SDD11')
            # Add markers for SDD11 phase
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_sdd11_phase.plot(marker_freq/1e9, sdd11_phase[idx], 'ro', markersize=8)
                ax_sdd11_phase.annotate(f'{marker_freq/1e9:.3f} GHz\n{sdd11_phase[idx]:.2f}°',
                           (marker_freq/1e9, sdd11_phase[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_sdd11_phase.set_xlabel('Frequency (GHz)')
            ax_sdd11_phase.set_ylabel('Phase (degrees)')
            ax_sdd11_phase.set_title('SDD11 Phase')
            ax_sdd11_phase.grid(True)
            ax_sdd11_phase.legend()

            # Plot SDD21 phase
            ax_sdd21_phase.plot(freq/1e9, sdd21_phase, label='SDD21')
            # Add markers for SDD21 phase
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_sdd21_phase.plot(marker_freq/1e9, sdd21_phase[idx], 'ro', markersize=8)
                ax_sdd21_phase.annotate(f'{marker_freq/1e9:.3f} GHz\n{sdd21_phase[idx]:.2f}°',
                           (marker_freq/1e9, sdd21_phase[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_sdd21_phase.set_xlabel('Frequency (GHz)')
            ax_sdd21_phase.set_ylabel('Phase (degrees)')
            ax_sdd21_phase.set_title('SDD21 Phase')
            ax_sdd21_phase.grid(True)
            ax_sdd21_phase.legend()

        else:  # n_ports == 2
            # Create 2x2 subplots for S11 and S21, magnitude and phase
            ((ax_s11_mag, ax_s21_mag), 
             (ax_s11_phase, ax_s21_phase)) = self.figure.subplots(2, 2)
            
            # Calculate S-parameters
            s11 = 20 * np.log10(np.abs(s_params[:, 0, 0]))
            s21 = 20 * np.log10(np.abs(s_params[:, 1, 0]))
            s11_phase = np.angle(s_params[:, 0, 0], deg=True)
            s21_phase = np.angle(s_params[:, 1, 0], deg=True)

            # Plot S11 magnitude
            ax_s11_mag.plot(freq/1e9, s11, label='S11')
            # Add markers for S11 magnitude
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_s11_mag.plot(marker_freq/1e9, s11[idx], 'ro', markersize=8)
                ax_s11_mag.annotate(f'{marker_freq/1e9:.3f} GHz\n{s11[idx]:.2f} dB',
                           (marker_freq/1e9, s11[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_s11_mag.set_xlabel('Frequency (GHz)')
            ax_s11_mag.set_ylabel('Magnitude (dB)')
            ax_s11_mag.set_title('S11 Magnitude')
            ax_s11_mag.grid(True)
            ax_s11_mag.legend()

            # Plot S21 magnitude
            ax_s21_mag.plot(freq/1e9, s21, label='S21')
            # Add markers for S21 magnitude
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_s21_mag.plot(marker_freq/1e9, s21[idx], 'ro', markersize=8)
                ax_s21_mag.annotate(f'{marker_freq/1e9:.3f} GHz\n{s21[idx]:.2f} dB',
                           (marker_freq/1e9, s21[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_s21_mag.set_xlabel('Frequency (GHz)')
            ax_s21_mag.set_ylabel('Magnitude (dB)')
            ax_s21_mag.set_title('S21 Magnitude')
            ax_s21_mag.grid(True)
            ax_s21_mag.legend()

            # Plot S11 phase
            ax_s11_phase.plot(freq/1e9, s11_phase, label='S11')
            # Add markers for S11 phase
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_s11_phase.plot(marker_freq/1e9, s11_phase[idx], 'ro', markersize=8)
                ax_s11_phase.annotate(f'{marker_freq/1e9:.3f} GHz\n{s11_phase[idx]:.2f}°',
                           (marker_freq/1e9, s11_phase[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_s11_phase.set_xlabel('Frequency (GHz)')
            ax_s11_phase.set_ylabel('Phase (degrees)')
            ax_s11_phase.set_title('S11 Phase')
            ax_s11_phase.grid(True)
            ax_s11_phase.legend()

            # Plot S21 phase
            ax_s21_phase.plot(freq/1e9, s21_phase, label='S21')
            # Add markers for S21 phase
            for marker_freq in self.markers:
                idx = np.abs(freq - marker_freq).argmin()
                ax_s21_phase.plot(marker_freq/1e9, s21_phase[idx], 'ro', markersize=8)
                ax_s21_phase.annotate(f'{marker_freq/1e9:.3f} GHz\n{s21_phase[idx]:.2f}°',
                           (marker_freq/1e9, s21_phase[idx]), xytext=(10, 10),
                           textcoords='offset points', ha='left')
            ax_s21_phase.set_xlabel('Frequency (GHz)')
            ax_s21_phase.set_ylabel('Phase (degrees)')
            ax_s21_phase.set_title('S21 Phase')
            ax_s21_phase.grid(True)
            ax_s21_phase.legend()

        # Adjust layout and redraw
        self.figure.tight_layout()
        self.canvas.draw()
        
    def load_sparam_file(self, file_path):
        """Load and display the selected S-parameter file"""
        try:
            print(f"\n=== Loading S-parameter file: {file_path} ===")  # Debug print
            
            # Parse the S-parameter file
            freq, s_params = self.parse_sparam_file(file_path)
            
            if freq is not None and s_params is not None:
                # Plot the S-parameters
                self.plot_sparam(freq, s_params, 4)
                
                # Store current file path
                self.current_file = file_path
                
                # Update window title
                self.title(f"S-Parameter Browser - {os.path.basename(file_path)}")
            else:
                messagebox.showerror("Error", "Failed to parse S-parameter file")
                
        except Exception as e:
            print(f"Error loading S-parameter file: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load S-parameter file:\n{str(e)}")

    def setup_toolbar(self):
        """Setup the toolbar with necessary controls"""
        # File operation buttons
        ttk.Button(self.toolbar, text="Browse Folder", command=self.browse_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Load Subfolders", command=self.load_subfolders).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Move Files", command=self.move_selected_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Copy Files", command=self.copy_selected_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Delete Files", command=self.delete_selected_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Rename All Files", command=self.rename_all_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Embed-Left", command=self.embed_left_sparams).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Embed-Right", command=self.embed_right_sparams).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="De-embed Left", command=self.deembed_sparams).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="De-embed Right", command=self.deembed_sparams_right).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Open in Notepad++", command=self.open_in_notepadpp).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Smith Chart", command=self.show_smith_chart).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Port Mapping", command=self.show_port_mapping_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Refresh", command=self.refresh_file_list).pack(side=tk.RIGHT, padx=2)

    def open_in_notepadpp(self):
        """Open the selected S-parameter file in Notepad++"""
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select a file to open in Notepad++")
            return

        try:
            notepadpp_path = r"C:\Program Files\Notepad++\notepad++.exe"
            for row in selected_rows:
                if row < len(self.df):
                    file_path = self.df.iloc[row].get('File_Path', os.path.join(self.current_directory, self.df.iloc[row]['Name']))
                    # Fix potential path separator inconsistencies
                    file_path = os.path.normpath(file_path.replace('\\', '/'))
                    # Launch Notepad++ with the selected file
                    subprocess.Popen([notepadpp_path, file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file in Notepad++:\n{str(e)}")

    def browse_folder(self):
        """Open a directory chooser dialog and update the file list"""
        print("\n=== Browse folder called ===")  # Debug print
        directory = filedialog.askdirectory(
            initialdir=self.current_directory
        )
        if directory:
            print(f"Selected directory: {directory}")  # Debug print
            self.current_directory = directory
            self.include_subfolders.set(False)  # Reset to not include subfolders
            
            # Update file list
            self.update_file_list()
            
            # Update max fields
            old_max = self.max_fields
            self.max_fields = self.get_max_fields()
            print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
            
            # Update file browser
            self.setup_file_browser()
            self.setup_sparam_viewer()

    def update_file_list(self):
        """Update the list of S-parameter files in the current directory"""
        self.sparam_files = []
        
        if not self.validate_directory(self.current_directory):
            print(f"Warning: Directory '{self.current_directory}' is not accessible")
            self.set_safe_directory()
            
        if self.include_subfolders.get():
            try:
                for root, _, files in os.walk(self.current_directory):
                    for file in files:
                        if file.lower().endswith(('.s4p', '.s2p')):
                            full_path = os.path.normpath(os.path.join(root, file))
                            if os.path.exists(full_path):
                                self.sparam_files.append(full_path)
                            else:
                                print(f"Warning: File in directory walk doesn't exist: {full_path}")
                print(f"Found {len(self.sparam_files)} S-parameter files in all subfolders")
            except Exception as e:
                print(f"Error walking directory tree: {str(e)}")
                self.sparam_files = []
        else:
            try:
                files = os.listdir(self.current_directory)
                self.sparam_files = []
                for f in files:
                    if f.lower().endswith(('.s4p', '.s2p')):
                        full_path = os.path.normpath(os.path.join(self.current_directory, f))
                        if os.path.exists(full_path):
                            self.sparam_files.append(full_path)
                        else:
                            print(f"Warning: File in listing doesn't exist: {full_path}")
            except Exception as e:
                print(f"Error listing directory: {str(e)}")
                self.sparam_files = []

    def get_max_fields(self):
        """Get the maximum number of underscore-separated fields in filenames"""
        max_fields = 0
        for file_path in self.sparam_files:
            # Get just the filename without path
            file_name = os.path.basename(file_path)
            # Remove extension and split by underscore
            name_without_ext = os.path.splitext(file_name)[0]
            fields = name_without_ext.split('_')
            
            # Update max fields
            max_fields = max(max_fields, len(fields))
        
        # Ensure max_fields is at least 30
        max_fields = max(max_fields, 30)
        
        print(f"Max fields found: {max_fields}")  # Debug print
        return max_fields

    def refresh_file_list(self):
        print(f"current directory: {self.current_directory}")  # Debug print
        
        # Update file list
        self.update_file_list()
        
        # Update file browser
        self.setup_file_browser()
        self.setup_sparam_viewer()        

    def toggle_layout(self):
        """Toggle between horizontal and vertical layouts"""
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
        
        # Restore file browser and S-parameter viewer
        self.setup_file_browser()
        self.setup_sparam_viewer()
        
        # Force geometry update
        self.update_idletasks()
        
        # Set final sash position
        if self.is_horizontal:
            self.paned.sashpos(0, 400)
        else:
            self.paned.sashpos(0, 300)



    def copy_selected_files(self):
        """Copy selected files to another folder"""
        # Get selected rows from the table's multiplerowlist
        selected_rows = self.table.multiplerowlist
        if not selected_rows:
            messagebox.showinfo("Info", "Please select files to copy")
            return

        # Ask for destination directory
        dest_dir = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=os.path.dirname(self.current_directory)
        )
        
        if not dest_dir:
            return

        try:
            copied_files = []
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
                    
                    # Copy the file
                    shutil.copy2(src_path, dst_path)  # copy2 preserves metadata
                    copied_files.append(filename)
            
            if copied_files:
                messagebox.showinfo("Success", f"Successfully copied {len(copied_files)} file(s) to {dest_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy files:\n{str(e)}")
            
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
                    
                    # Clear S-parameter viewer if it was the moved file
                    if self.current_file == src_path:
                        self.current_file = None
                        self.sparam_table.model.df = pd.DataFrame()
                        self.sparam_table.redraw()

            # Update the DataFrame and table
            if moved_files:
                self.df = self.df[~self.df['Name'].isin(moved_files)]
                self.table.model.df = self.df
                self.table.redraw()
                
                # Update file list
                self.sparam_files = [f for f in self.sparam_files if f not in moved_files]
                
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
                        
                        # Clear S-parameter viewer if it was the deleted file
                        if self.current_file == filepath:
                            self.current_file = None
                            self.sparam_table.model.df = pd.DataFrame()
                            self.sparam_table.redraw()
                                
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete file {filename}:\n{str(e)}")

            # Update the DataFrame and table
            if deleted_files:
                self.df = self.df[~self.df['Name'].isin(deleted_files)]
                self.table.model.df = self.df
                self.table.redraw()
                
                # Update file list
                self.sparam_files = [f for f in self.sparam_files if f not in deleted_files]
                
                messagebox.showinfo("Success", f"Deleted {len(deleted_files)} files")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error during deletion:\n{str(e)}")

    def rename_all_files(self):
        """Rename all files where constructed name differs from current name"""
        try:
            renamed_count = 0
            for idx, row in self.df.iterrows():
                current_name = row['Name']
                new_name = self.reconstruct_filename(row)
                
                if new_name != current_name:
                    old_path = row['File_Path']
                    new_path = self.rename_sparam_file(old_path, new_name)
                    
                    # Update the DataFrame
                    self.df.at[idx, 'Name'] = new_name
                    self.df.at[idx, 'File_Path'] = new_path
                    
                    # Update the table display
                    self.table.model.df = self.df
                    self.table.redraw()
                    
                    renamed_count += 1
            
            if renamed_count > 0:
                messagebox.showinfo("Files Renamed", 
                                 f"Renamed {renamed_count} files based on field values")
            else:
                messagebox.showinfo("No Changes", 
                                 "All filenames already match their field values")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename files: {str(e)}")


    def load_subfolders(self):
        """Load all S-parameter files from current directory and all subdirectories"""
        try:
            print("\n=== Loading files from subfolders ===")  # Debug print
            directory = filedialog.askdirectory(
                initialdir=self.current_directory
            )
            if directory:
                print(f"Selected directory: {directory}")  # Debug print
                self.current_directory = directory
                self.include_subfolders.set(True)
                
                # Update file list
                self.update_file_list()
                
                # Update max fields
                old_max = self.max_fields
                self.max_fields = self.get_max_fields()
                print(f"Max fields changed from {old_max} to {self.max_fields}")  # Debug print
                
                # Update file browser
                self.setup_file_browser()
                self.setup_sparam_viewer()
                print("Completed loading files from subfolders")  # Debug print
        except Exception as e:
            print(f"Error loading subfolders: {e}")
            traceback.print_exc()

    def add_marker(self):
        """Add a marker at the specified frequency"""
        try:
            if not self.last_networks:
                messagebox.showinfo("Info", "Please load S-parameter files first")
                return
                
            # Create a dialog to get the marker frequency
            freq = simpledialog.askfloat("Add Marker", "Enter frequency (GHz):", parent=self)
            if freq is None:  # User cancelled
                return
                
            self.markers.append(freq)
            self.plot_network_params(*self.last_networks, show_mag=self.plot_mag_var.get(), show_phase=self.plot_phase_var.get())
            
        except Exception as e:
            print(f"Error adding marker: {str(e)}")
            traceback.print_exc()

    def clear_markers(self):
        """Clear all markers"""
        self.markers = []
        if self.last_networks:
            self.plot_network_params(*self.last_networks, show_mag=self.plot_mag_var.get(), show_phase=self.plot_phase_var.get())

    def calculate_tdr(self, network=None):
        """Calculate Time Domain Reflectometry (TDR) response"""
        print(f"\n==== TDR Calculation ====")
        print(f"Padding Factor: {self.padding_factor.get()}")
        print(f"Window Type: {self.window_type.get()}")
        
        if network is None:
            network = self.data[0]  # Use first network if none specified
            
        # Get frequency points and S-parameters
        f = network.f
        s11 = network.s[:, 0, 0]  # Get S11 parameter
        
        # Apply window function
        s11_windowed = self.apply_window(s11)
        print(f"Applied {self.window_type.get()} window")
        
        # Zero padding
        pad_factor = int(self.padding_factor.get())
        n_orig = len(f)
        n_padded = n_orig * pad_factor
        print(f"Original points: {n_orig}, Padded points: {n_padded}, Improvement factor: {pad_factor}x")
        
        # Pad the frequency domain data
        s11_padded = np.pad(s11_windowed, (0, n_padded - n_orig), mode='constant')
        
        # Create padded frequency array
        f_step = f[1] - f[0]  # Original frequency step
        f_padded = np.linspace(f[0], f[0] + f_step * (n_padded - 1), n_padded)
        
        # Calculate time domain response
        dt = 1 / (2 * f_padded[-1])  # Time step
        t = np.arange(n_padded) * dt
        
        # Make sure DC component is appropriate for step response
        # For step response, ensure we have a valid DC component
        if f[0] > 0:  # No DC point
            # Add an estimated DC value (often set to average of first few points)
            dc_est = np.mean(np.real(s11_windowed[:5]))
            print(f"Estimated DC component: {dc_est}")
            # Prepend DC point to padded data
            s11_padded = np.concatenate(([dc_est], s11_padded))
            # Adjust frequency array
            f_step = f[1] - f[0]  # Original frequency step
            f_padded = np.concatenate(([0], f_padded))
            n_padded += 1
            # Regenerate time array with updated n_padded
            t = np.arange(n_padded) * dt
        
        # For step response, divide by j*2*pi*f in frequency domain (integration)
        # Avoid division by zero at DC
        freq_response = s11_padded.copy()
        for k in range(1, len(f_padded)):  # Skip DC
            freq_response[k] = freq_response[k] / (1j * 2 * np.pi * f_padded[k])
        
        # Get time domain step response
        tdr = np.fft.ifft(freq_response)
        
        # Calculate distance (assuming speed of light in vacuum)
        c = 299792458  # Speed of light in m/s
        v_f = float(self.velocity_factor.get()) if hasattr(self, 'velocity_factor') else 0.67  # Velocity factor
        distance = t * c * v_f / 2  # Divide by 2 for round trip
        
        # Print TDR resolution information
        time_res = dt * 1e12  # Time resolution in picoseconds
        dist_res = c * v_f * dt / 2 * 1000  # Distance resolution in mm
        print(f"TDR resolution: {time_res:.2f} ps, {dist_res:.2f} mm")
        
        # Normalize the TDR response to proper reflection coefficient range (-1 to 1)
        # First, ensure we're working with real part only for normalization
        tdr_real = np.real(tdr)
        
        # Strong normalization - force to reasonable reflection coefficient range
        # Find maximum magnitude
        max_abs = np.max(np.abs(tdr_real))
        if max_abs > 1e-10:  # Only normalize if signal isn't completely zero
            # Scale to make the maximum reflection about 0.5 (typical for real-world TDR)
            scale_factor = 0.5 / max_abs
            print(f"TDR scale factor: {scale_factor}")
            # Create normalized TDR with proper reflection coefficient scaling
            tdr = tdr * scale_factor
        else:
            print("Warning: TDR response is extremely small, normalization skipped")
        
        # Add small baseline shift to center around zero
        tdr_mean = np.mean(np.real(tdr))
        if np.abs(tdr_mean) < 0.1:  # Only adjust if mean is small
            tdr = tdr - tdr_mean
        
        
        # Artificially enhance signal variations for better visualization
        # This doesn't change the shape of the data, just amplifies small variations
        tdr_real = np.real(tdr)
        mean_val = np.mean(tdr_real)
        variations = tdr_real - mean_val
        # Amplify variations by 10x while preserving mean
        amplification = 10.0
        enhanced_variations = variations * amplification
        tdr_real_enhanced = mean_val + enhanced_variations
        # Reconstruct complex data with enhanced real part
        tdr = tdr_real_enhanced + 1j * np.imag(tdr)
        print(f"Enhanced TDR variations by {amplification}x factor")

        # TDR FINAL DIAGNOSTICS
        tdr_real = np.real(tdr)
        tdr_min = np.min(tdr_real)
        tdr_max = np.max(tdr_real)
        tdr_mean = np.mean(tdr_real)
        tdr_abs_max = np.max(np.abs(tdr_real))
        print(f"FINAL TDR DIAGNOSTICS:")
        print(f"  Min: {tdr_min:.6f}, Max: {tdr_max:.6f}, Mean: {tdr_mean:.6f}, Abs Max: {tdr_abs_max:.6f}")
        print(f"  Number of samples: {len(tdr_real)}")

        return distance, tdr

    def calculate_pulse_response(self, network=None):
        """Calculate pulse response with enhanced resolution"""
        if network is None:
            network = self.data[0]  # Use first network if none specified
            
        # Get frequency points and S-parameters
        f = network.f
        s21 = network.s[:, 1, 0]  # Get S21 parameter
        
        # Apply window function
        s21_windowed = self.apply_window(s21)
        
        # Zero padding
        pad_factor = int(self.padding_factor.get())
        n_orig = len(f)
        n_padded = n_orig * pad_factor
        
        # Pad the frequency domain data
        s21_padded = np.pad(s21_windowed, (0, n_padded - n_orig), mode='constant')
        
        # Create padded frequency array
        f_step = f[1] - f[0]  # Original frequency step
        f_padded = np.linspace(f[0], f[0] + f_step * (n_padded - 1), n_padded)
        
        # Create Gaussian pulse in frequency domain
        sigma = 0.1 / (2 * np.pi * f_padded[-1])  # Adjust pulse width
        gauss = np.exp(-0.5 * (f_padded * sigma)**2)
        
        # Multiply with S-parameters and transform to time domain
        pulse = np.fft.ifft(s21_padded * gauss)
        
        # Calculate time array
        dt = 1 / (2 * f_padded[-1])  # Time step
        t = np.arange(n_padded) * dt  # Initial time array, may be updated later
        
        # Normalize and enhance pulse response for better visualization

        pulse_mag = np.abs(pulse)

        max_val = np.max(pulse_mag)

        

        # Print pulse response diagnostics

        print(f"Pulse response diagnostics:")

        print(f"  Max amplitude: {max_val:.6f}")

        print(f"  Time range: {t[0]*1e12:.1f} to {t[-1]*1e12:.1f} ps")

        print(f"  Time step: {(t[1]-t[0])*1e12:.3f} ps")

        

        # Check if normalization is needed

        if max_val > 0 and max_val != 1.0:

            # Normalize to unity amplitude

            pulse = pulse / max_val

            print(f"  Normalized pulse to unity amplitude")

        

        # Convert time to picoseconds for easier reading

        t_ps = t * 1e12  # Convert to picoseconds

        

        return t_ps, pulse

    def apply_window(self, freq_data):
        """Apply window function to frequency domain data with optional low pass filtering"""
        window_type = self.window_type.get()
        
        # Get low_pass_mode value with safety check
        try:
            low_pass = self.low_pass_mode.get()
        except (AttributeError, tk.TclError):
            low_pass = False
        
        if window_type == 'none' and not low_pass:
            low_pass = False
        
        if window_type == 'none' and not low_pass:
            return freq_data
            
        n = len(freq_data)
        
        # Create base window function
        if window_type == 'hamming':
            window = np.hamming(n)
        elif window_type == 'hanning':
            window = np.hanning(n)
        elif window_type == 'blackman':
            window = np.blackman(n)
        elif window_type == 'kaiser':
            # Kaiser window with beta=8 gives a good balance
            window = np.kaiser(n, 8.0)
        elif window_type == 'flattop':
            # Custom flattop window implementation
            # Coefficients for a flat top window
            a = [0.21557895, 0.41663158, 0.277263158, 0.083578947, 0.006947368]
            
            # Create a flattop window manually
            window = np.zeros(n)
            N = n - 1
            for i in range(n):
                # Sum of cosines implementation
                w = a[0]
                for j in range(1, len(a)):
                    w += a[j] * np.cos(2 * np.pi * j * i / N)
                window[i] = w
        elif window_type == 'exponential':
            # Implementation of the PLTS Exponential window: w(f) = e^(-c*(f^2/f_0^2))
            # where f is the frequency and c is the coefficient (default=1)
            c = 1.0  # Default coefficient
            # Create normalized frequency array from 0 to 1
            f = np.linspace(0, 1, n)  # Normalized frequency from 0 to 1
            # Calculate f^2/f_0^2 where f_0 is the max frequency (normalized to 1)
            f_squared = f**2
            # Apply exponential window formula
            window = np.exp(-c * f_squared)
            print(f"Applying PLTS exponential window with coefficient c={c}")
        else:
            # Default to hamming if window type not recognized
            window = np.hamming(n)
        
        # Apply low pass filtering if enabled
        if low_pass:
            # Create a low pass filter that gradually rolls off the high frequencies
            # Use a half-cosine rolloff for the upper half of the frequency range
            cutoff_idx = n // 3  # Cut off at 1/3 of the frequency range
            lp_filter = np.ones(n)
            
            # Apply cosine rolloff from cutoff to end
            for i in range(cutoff_idx, n):
                # Cosine taper from 1 to 0
                lp_filter[i] = 0.5 * (1 + np.cos(np.pi * (i - cutoff_idx) / (n - cutoff_idx)))
            
            # Combine the window with the low pass filter
            window = window * lp_filter
            print(f"Applying {window_type} window with low pass filter (cutoff at {cutoff_idx/n:.2f} * fmax)")
        else:
            print(f"Applying {window_type} window without low pass filtering")
            
        return freq_data * window

    def plot_network_params(self, *networks, show_mag=True, show_phase=True):
        """Plot S-parameters for multiple networks"""
        if not networks:
            return
            
        try:
            # Clear the current figure
            self.figure.clear()

            # Check if time domain plots are enabled
            show_tdr = self.show_tdr_var.get()
            show_pulse = self.show_pulse_var.get()
            show_impedance = self.show_impedance_var.get()
            
            if show_tdr or show_pulse or show_impedance:
                if show_tdr and show_pulse and show_impedance:
                    # Create three subplots for TDR, pulse response, and impedance profile
                    ax_tdr = self.figure.add_subplot(131)
                    ax_pulse = self.figure.add_subplot(132)
                    ax_imp = self.figure.add_subplot(133)
                elif show_tdr and show_pulse:
                    # Create two subplots for TDR and pulse response
                    ax_tdr = self.figure.add_subplot(121)
                    ax_pulse = self.figure.add_subplot(122)
                elif show_tdr and show_impedance:
                    # Create two subplots for TDR and impedance profile
                    ax_tdr = self.figure.add_subplot(121)
                    ax_imp = self.figure.add_subplot(122)
                elif show_pulse and show_impedance:
                    # Create two subplots for pulse response and impedance profile
                    ax_pulse = self.figure.add_subplot(121)
                    ax_imp = self.figure.add_subplot(122)
                else:
                    # Create single plot for either TDR, pulse response, or impedance profile
                    ax = self.figure.add_subplot(111)
                
                for i, net in enumerate(networks):
                    label = f'Net{i+1}' if len(net.name) == 0 else net.name
                    
                    if show_tdr:
                        distance, tdr = self.calculate_tdr(net)
                        ax_plot = ax_tdr if show_pulse or show_impedance else ax
                        # Plot magnitude of TDR response in millimeters
                        ax_plot.plot(distance * 1000, np.real(tdr), label=label)
                        ax_plot.set_xlabel('Distance (mm)')
                        ax_plot.set_ylabel('Reflection Coefficient')
                        ax_plot.set_title('Time Domain Reflectometry (TDR)')
                        # Set y-axis limits based on data to avoid scientific notation
                        y_min = np.min(np.real(tdr))
                        y_max = np.max(np.real(tdr))
                        margin = (y_max - y_min) * 0.1
                        ax_plot.set_ylim([y_min - margin, y_max + margin])
                        # Disable scientific notation for y-axis
                        ax_plot.ticklabel_format(axis='y', style='plain', useOffset=False)
                        ax_plot.grid(True)
                        ax_plot.legend()
                    
                    if show_pulse:
                        time, pulse = self.calculate_pulse_response(net)
                        ax_plot = ax_pulse if show_tdr or show_impedance else ax
                        # Plot magnitude of pulse response
                        ax_plot.plot(time, np.abs(pulse), label=label)
                        ax_plot.set_xlabel('Time (ps)')
                        ax_plot.set_ylabel('Amplitude')
                        ax_plot.set_title('Pulse Response')
                        # Set appropriate y-axis formatting
                        ax_plot.ticklabel_format(axis='y', style='plain', useOffset=False)
                        ax_plot.grid(True)
                        ax_plot.legend()
                    
                    if show_impedance:
                        distance, tdr = self.calculate_tdr(net)
                        impedance = self.calculate_impedance_profile(tdr)
                        ax_plot = ax_imp if show_tdr or show_pulse else ax
                        # Plot impedance vs. distance
                        ax_plot.plot(distance * 1000, np.real(impedance), label=label)
                        ax_plot.set_xlabel('Distance (mm)')
                        ax_plot.set_ylabel('Impedance (Ω)')
                        ax_plot.set_title('Impedance Profile')
                        # Explicitly set y-axis limits to avoid scientific notation
                        y_min = max(10, np.min(np.real(impedance)))
                        y_max = min(200, np.max(np.real(impedance)))
                        # Set reasonable limits with some margin
                        margin = (y_max - y_min) * 0.1
                        ax_plot.set_ylim([y_min - margin, y_max + margin])
                        # Use simple, non-scientific notation for y-axis
                        ax_plot.ticklabel_format(axis='y', style='plain', useOffset=False)
                        ax_plot.grid(True)
                        ax_plot.legend()
                        
                        # Add reference line at Z0=100Ω
                        ax_plot.axhline(y=100, color='r', linestyle='--', alpha=0.5, label='Z0=100Ω')
                        ax_plot.legend()
                
            else:
                # Original frequency domain plotting code continues here...
                # Determine which parameters to show
                show_sdd11 = self.plot_sdd11_var.get()
                show_sdd21 = self.plot_sdd21_var.get()
                show_spec = self.show_spec_var.get() and bool(self.spec_data)
                
                # Count how many subplots we need
                n_plots = 0
                if show_mag:
                    n_plots += (show_sdd11 + show_sdd21)
                if show_phase:
                    n_plots += (show_sdd11 + show_sdd21)
                    
                if n_plots == 0:
                    return  # Nothing to plot
                
                # Create subplots based on what's shown
                if n_plots == 1:
                    axes = [self.figure.add_subplot(111)]
                elif n_plots == 2:
                    axes = self.figure.subplots(1, 2)
                elif n_plots == 3:
                    gs = self.figure.add_gridspec(2, 2)
                    axes = [
                        self.figure.add_subplot(gs[0, 0]),
                        self.figure.add_subplot(gs[0, 1]),
                        self.figure.add_subplot(gs[1, 0:])
                    ]
                else:  # n_plots == 4
                    axes = self.figure.subplots(2, 2)
                    axes = [ax for row in axes for ax in row]  # Flatten 2D array
                
                # Clear marker text box
                if self.marker_text:
                    self.marker_text.delete(1.0, tk.END)
                
                # Keep track of which axis is for what
                ax_map = {}
                ax_idx = 0
                
                if show_mag and show_sdd11:
                    ax_map['sdd11_mag'] = axes[ax_idx]
                    ax_idx += 1
                if show_mag and show_sdd21:
                    ax_map['sdd21_mag'] = axes[ax_idx]
                    ax_idx += 1
                if show_phase and show_sdd11:
                    ax_map['sdd11_phase'] = axes[ax_idx]
                    ax_idx += 1
                if show_phase and show_sdd21:
                    ax_map['sdd21_phase'] = axes[ax_idx]
                    ax_idx += 1
                
                # Plot specification lines if available
                if show_spec and show_mag and self.spec_data:
                    def plot_step_spec(ax, freq, spec):
                        # Create step-like plot by duplicating points
                        x = []
                        y = []
                        for i in range(len(freq)):
                            if i > 0:
                                # Add vertical line by duplicating x coordinate
                                x.append(freq[i])
                                y.append(spec[i-1])
                            # Add horizontal line
                            x.append(freq[i])
                            y.append(spec[i])
                        
                        # Plot the step line
                        ax.plot(x, y, 'r-', label='Specification', linewidth=2)
                    
                    if show_sdd11 and 'sdd11' in self.spec_data:
                        ax = ax_map['sdd11_mag']
                        plot_step_spec(ax, self.spec_data['freq'], self.spec_data['sdd11'])
                    
                    if show_sdd21 and 'sdd21' in self.spec_data:
                        ax = ax_map['sdd21_mag']
                        plot_step_spec(ax, self.spec_data['freq'], self.spec_data['sdd21'])
                
                # Plot each network
                for i, net in enumerate(networks):
                    # Convert to differential parameters
                    sdd = self.s2sdd(net.s)
                    
                    label = f'Net{i+1}' if len(net.name) == 0 else net.name
                    
                    # Plot enabled parameters
                    if show_mag:
                        if show_sdd11:
                            ax = ax_map['sdd11_mag']
                            ax.plot(net.f/1e9, 20*np.log10(np.abs(sdd[:, 0, 0])), label=label)
                            ax.set_xlabel('Frequency (GHz)')
                            ax.set_ylabel('Magnitude (dB)')
                            ax.set_title('SDD11 Magnitude')
                            ax.grid(True)
                            ax.legend()
                        
                        if show_sdd21:
                            ax = ax_map['sdd21_mag']
                            ax.plot(net.f/1e9, 20*np.log10(np.abs(sdd[:, 1, 0])), label=label)
                            ax.set_xlabel('Frequency (GHz)')
                            ax.set_ylabel('Magnitude (dB)')
                            ax.set_title('SDD21 Magnitude')
                            ax.grid(True)
                            ax.legend()
                    
                    if show_phase:
                        if show_sdd11:
                            ax = ax_map['sdd11_phase']
                            ax.plot(net.f/1e9, np.angle(sdd[:, 0, 0], deg=True), label=label)
                            ax.set_xlabel('Frequency (GHz)')
                            ax.set_ylabel('Phase (degrees)')
                            ax.set_title('SDD11 Phase')
                            ax.grid(True)
                            ax.legend()
                        
                        if show_sdd21:
                            ax = ax_map['sdd21_phase']
                            ax.plot(net.f/1e9, np.angle(sdd[:, 1, 0], deg=True), label=label)
                            ax.set_xlabel('Frequency (GHz)')
                            ax.set_ylabel('Phase (degrees)')
                            ax.set_title('SDD21 Phase')
                            ax.grid(True)
                            ax.legend()
                    
                    # Add markers if any
                    for marker_freq in self.markers:
                        # Find closest frequency point
                        idx = np.abs(net.f/1e9 - marker_freq).argmin()
                        f = net.f[idx]/1e9
                        
                        # Calculate values
                        sdd11_mag = 20*np.log10(np.abs(sdd[idx, 0, 0]))
                        sdd21_mag = 20*np.log10(np.abs(sdd[idx, 1, 0]))
                        sdd11_phase = np.angle(sdd[idx, 0, 0], deg=True)
                        sdd21_phase = np.angle(sdd[idx, 1, 0], deg=True)
                        
                        # Add markers to enabled plots
                        if show_mag:
                            if show_sdd11:
                                ax = ax_map['sdd11_mag']
                                ax.plot(f, sdd11_mag, 'ko')
                                ax.annotate(f'{sdd11_mag:.2f} dB', (f, sdd11_mag),
                                        xytext=(10, 10), textcoords='offset points')
                            
                            if show_sdd21:
                                ax = ax_map['sdd21_mag']
                                ax.plot(f, sdd21_mag, 'ko')
                                ax.annotate(f'{sdd21_mag:.2f} dB', (f, sdd21_mag),
                                        xytext=(10, 10), textcoords='offset points')
                        
                        if show_phase:
                            if show_sdd11:
                                ax = ax_map['sdd11_phase']
                                ax.plot(f, sdd11_phase, 'ko')
                                ax.annotate(f'{sdd11_phase:.2f}°', (f, sdd11_phase),
                                        xytext=(10, 10), textcoords='offset points')
                            
                            if show_sdd21:
                                ax = ax_map['sdd21_phase']
                                ax.plot(f, sdd21_phase, 'ko')
                                ax.annotate(f'{sdd21_phase:.2f}°', (f, sdd21_phase),
                                        xytext=(10, 10), textcoords='offset points')
                        
                        # Add values to text box
                        if self.marker_text:
                            marker_text = [f"Network: {label}", f"Frequency: {f:.2f} GHz"]
                            if show_mag:
                                if show_sdd11:
                                    marker_text.append(f"SDD11 Mag: {sdd11_mag:.2f} dB")
                                if show_sdd21:
                                    marker_text.append(f"SDD21 Mag: {sdd21_mag:.2f} dB")
                            if show_phase:
                                if show_sdd11:
                                    marker_text.append(f"SDD11 Phase: {sdd11_phase:.2f}°")
                                if show_sdd21:
                                    marker_text.append(f"SDD21 Phase: {sdd21_phase:.2f}°")
                            self.marker_text.insert(tk.END, "\n".join(marker_text) + "\n\n")
            
            # Adjust layout and redraw
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error plotting networks: {str(e)}")
            traceback.print_exc()

    def s2sdd(self, s):
        """Convert single-ended S-parameters to differential S-parameters with port mapping"""
        # Apply port mapping to the S-matrix
        mapped_s = np.zeros_like(s)
        for i in range(4):
            for j in range(4):
                mapped_s[:, i, j] = s[:, self.port_mapping[i]-1, self.port_mapping[j]-1]
        
        # Now calculate differential parameters from mapped matrix
        # Assuming ports are arranged as:
        # Logical ports 1,3 = differential pair 1 (p,n)
        # Logical ports 2,4 = differential pair 2 (p,n)
        sdd = np.zeros((s.shape[0], 2, 2), dtype=complex)
        
        # Calculate differential S-parameters
        for f in range(s.shape[0]):
            # Convert 4x4 single-ended to 2x2 differential
            # For each differential port pair (i,j):
            # Sdd = 1/2[(Sij - Si(j+2)) - (S(i+2)j - S(i+2)(j+2))]
            sdd[f, 0, 0] = 0.5 * ((mapped_s[f, 0, 0] - mapped_s[f, 0, 2]) - 
                                 (mapped_s[f, 2, 0] - mapped_s[f, 2, 2]))  # SDD11
            sdd[f, 0, 1] = 0.5 * ((mapped_s[f, 0, 1] - mapped_s[f, 0, 3]) - 
                                 (mapped_s[f, 2, 1] - mapped_s[f, 2, 3]))  # SDD12
            sdd[f, 1, 0] = 0.5 * ((mapped_s[f, 1, 0] - mapped_s[f, 1, 2]) - 
                                 (mapped_s[f, 3, 0] - mapped_s[f, 3, 2]))  # SDD21
            sdd[f, 1, 1] = 0.5 * ((mapped_s[f, 1, 1] - mapped_s[f, 1, 3]) - 
                                 (mapped_s[f, 3, 1] - mapped_s[f, 3, 3]))  # SDD22
        
        return sdd

    def update_plot(self):
        """Update the plot based on checkbox states"""
        if self.last_networks:
            self.plot_network_params(*self.last_networks, show_mag=self.plot_mag_var.get(), show_phase=self.plot_phase_var.get())

    def apply_zoom(self):
        """Apply zoom settings to the plots"""
        try:
            # Get zoom values, using None for empty fields
            freq_min = float(self.freq_min.get()) if self.freq_min.get() else None
            freq_max = float(self.freq_max.get()) if self.freq_max.get() else None
            mag_min = float(self.mag_min.get()) if self.mag_min.get() else None
            mag_max = float(self.mag_max.get()) if self.mag_max.get() else None
            phase_min = float(self.phase_min.get()) if self.phase_min.get() else None
            phase_max = float(self.phase_max.get()) if self.phase_max.get() else None
            dist_min = float(self.dist_min.get()) if self.dist_min.get() else None
            dist_max = float(self.dist_max.get()) if self.dist_max.get() else None
            time_min = float(self.time_min.get()) if self.time_min.get() else None
            time_max = float(self.time_max.get()) if self.time_max.get() else None
            amp_min = float(self.amp_min.get()) if self.amp_min.get() else None
            amp_max = float(self.amp_max.get()) if self.amp_max.get() else None
            
            # Update all subplot axes limits
            for ax in self.figure.get_axes():
                title = ax.get_title()
                if 'TDR' in title:
                    if dist_min is not None and dist_max is not None:
                        ax.set_xlim(dist_min, dist_max)
                    if mag_min is not None and mag_max is not None:
                        ax.set_ylim(mag_min, mag_max)
                elif 'Pulse Response' in title:
                    if time_min is not None and time_max is not None:
                        ax.set_xlim(time_min, time_max)
                    if amp_min is not None and amp_max is not None:
                        ax.set_ylim(amp_min, amp_max)
                elif 'Impedance Profile' in title:
                    if dist_min is not None and dist_max is not None:
                        ax.set_xlim(dist_min, dist_max)
                    if mag_min is not None and mag_max is not None:
                        ax.set_ylim(mag_min, mag_max)
                elif 'Magnitude' in title:
                    if freq_min is not None and freq_max is not None:
                        ax.set_xlim(freq_min, freq_max)
                    if mag_min is not None and mag_max is not None:
                        ax.set_ylim(mag_min, mag_max)
                elif 'Phase' in title:
                    if freq_min is not None and freq_max is not None:
                        ax.set_xlim(freq_min, freq_max)
                    if phase_min is not None and phase_max is not None:
                        ax.set_ylim(phase_min, phase_max)
            
            # Redraw the canvas
            self.canvas.draw()
            
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid numbers for zoom ranges")
    
    def reset_zoom(self):
        """Reset zoom to show full range"""
        # Clear zoom values
        self.freq_min.set('')
        self.freq_max.set('')
        self.mag_min.set('')
        self.mag_max.set('')
        self.phase_min.set('')
        self.phase_max.set('')
        self.dist_min.set('')
        self.dist_max.set('')
        self.time_min.set('')
        self.time_max.set('')
        self.amp_min.set('')
        self.amp_max.set('')
        
        # Auto-scale all axes
        for ax in self.figure.get_axes():
            ax.autoscale()
        
        # Redraw the canvas
        self.canvas.draw()

    def embed_left_sparams(self):
        """Embed the second S-parameter to the left side of the first (formerly cascaded)."""
        selected_rows = self.table.multiplerowlist
        if len(selected_rows) != 2:
            messagebox.showinfo("Info", "Please select exactly two S-parameter files to embed")
            return

        try:
            # Get file paths for selected files
            file1_path = self.df.iloc[selected_rows[0]].get('File_Path', os.path.join(self.current_directory, self.df.iloc[selected_rows[0]]['Name']))
            file2_path = self.df.iloc[selected_rows[1]].get('File_Path', os.path.join(self.current_directory, self.df.iloc[selected_rows[1]]['Name']))

            # Load networks using scikit-rf
            device = rf.Network(os.path.normpath(file1_path))
            fixture = rf.Network(os.path.normpath(file2_path))

            # Check if the frequencies match
            if not np.array_equal(device.f, fixture.f):
                device = device.interpolate(fixture.f)

            if device.nports != 4 or fixture.nports != 4:
                messagebox.showerror("Error", "Both networks must be 4-port for this embedding method")
                return

            # Initialize embedded S-parameters with same shape as device/fixture
            s_embedded = np.zeros_like(device.s)

            # Reorder ports to group differential pairs
            reorder_idx = [0, 2, 1, 3]

            for i in range(len(device.f)):
                dev_s = device.s[i]
                fix_s = fixture.s[i]

                # Reorder indices to group differential pairs
                dev_s_reordered = dev_s[np.ix_(reorder_idx, reorder_idx)]
                fix_s_reordered = fix_s[np.ix_(reorder_idx, reorder_idx)]

                # Extract submatrices for cascade calculation
                dev_s11 = dev_s_reordered[0:2, 0:2]
                dev_s12 = dev_s_reordered[0:2, 2:4]
                dev_s21 = dev_s_reordered[2:4, 0:2]
                dev_s22 = dev_s_reordered[2:4, 2:4]

                fix_s11 = fix_s_reordered[0:2, 0:2]
                fix_s12 = fix_s_reordered[0:2, 2:4]
                fix_s21 = fix_s_reordered[2:4, 0:2]
                fix_s22 = fix_s_reordered[2:4, 2:4]

                # Identity matrix for calculations
                I = np.eye(2)

                # Calculate embedded S-parameters
                try:
                    inv_term = np.linalg.inv(I - fix_s22 @ dev_s11)
                except np.linalg.LinAlgError:
                    inv_term = np.linalg.pinv(I - fix_s22 @ dev_s11)

                emb_s11 = fix_s11 + fix_s12 @ dev_s11 @ inv_term @ fix_s21
                emb_s12 = fix_s12 @ (dev_s12 + dev_s11 @ inv_term @ fix_s22 @ dev_s12)
                emb_s21 = dev_s21 @ inv_term @ fix_s21
                emb_s22 = dev_s22 + dev_s21 @ inv_term @ fix_s22 @ dev_s12

                emb_s_reordered = np.block([
                    [emb_s11, emb_s12],
                    [emb_s21, emb_s22]
                ])

                # Reorder back to the original port order
                back_idx = [0, 2, 1, 3]
                s_embedded[i] = emb_s_reordered[np.ix_(back_idx, back_idx)]

            # Create a new network object with the embedded S-parameters
            embedded = rf.Network(
                s=s_embedded,
                frequency=device.frequency,
                name='Left-Embedded Network'
            )

            # Save the embedded result
            base_name1 = os.path.splitext(os.path.basename(file1_path))[0]
            base_name2 = os.path.splitext(os.path.basename(file2_path))[0]
            output_filename = os.path.join(self.current_directory, f"{base_name1}_with_{base_name2}_embedded_left.s4p")
            # Normalize path to fix separator issues
            output_filename = os.path.normpath(output_filename)
            embedded.write_touchstone(output_filename)

            # Update the GUI
            self.refresh_file_list()
            messagebox.showinfo("Success", f"Left-side embedding completed successfully\nSaved as: {output_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to embed S-parameters:\n{str(e)}")
            traceback.print_exc()

    def embed_right_sparams(self):
        """Embed the second S-parameter to the right side of the first"""
        selected_rows = self.table.multiplerowlist
        if len(selected_rows) != 2:
            messagebox.showinfo("Info", "Please select exactly two S-parameter files to embed")
            return

        try:
            # Get file paths for selected files
            file1_path = self.df.iloc[selected_rows[0]].get('File_Path', os.path.join(self.current_directory, self.df.iloc[selected_rows[0]]['Name']))
            file2_path = self.df.iloc[selected_rows[1]].get('File_Path', os.path.join(self.current_directory, self.df.iloc[selected_rows[1]]['Name']))

            # Load networks using scikit-rf
            device = rf.Network(os.path.normpath(file1_path))
            fixture = rf.Network(os.path.normpath(file2_path))

            # Check if the frequencies match
            if not np.array_equal(device.f, fixture.f):
                device = device.interpolate(fixture.f)

            if device.nports != 4 or fixture.nports != 4:
                messagebox.showerror("Error", "Both networks must be 4-port for this embedding method")
                return

            # Initialize embedded S-parameters with same shape as device/fixture
            s_embedded = np.zeros_like(device.s)

            # Reorder ports to group differential pairs
            reorder_idx = [0, 2, 1, 3]

            for i in range(len(device.f)):
                dev_s = device.s[i]
                fix_s = fixture.s[i]

                # Reorder indices to group differential pairs
                dev_s_reordered = dev_s[np.ix_(reorder_idx, reorder_idx)]
                fix_s_reordered = fix_s[np.ix_(reorder_idx, reorder_idx)]

                # Extract submatrices for cascade calculation
                dev_s11 = dev_s_reordered[0:2, 0:2]
                dev_s12 = dev_s_reordered[0:2, 2:4]
                dev_s21 = dev_s_reordered[2:4, 0:2]
                dev_s22 = dev_s_reordered[2:4, 2:4]

                fix_s11 = fix_s_reordered[0:2, 0:2]
                fix_s12 = fix_s_reordered[0:2, 2:4]
                fix_s21 = fix_s_reordered[2:4, 0:2]
                fix_s22 = fix_s_reordered[2:4, 2:4]

                # Identity matrix for calculations
                I = np.eye(2)

                # Calculate embedded S-parameters for right-side embedding
                # For right-side embedding, the formula is different from left-side embedding
                try:
                    inv_term = np.linalg.inv(I - dev_s22 @ fix_s11)
                except np.linalg.LinAlgError:
                    inv_term = np.linalg.pinv(I - dev_s22 @ fix_s11)

                # Calculate the four S-parameter blocks for the cascaded network
                emb_s11 = dev_s11 + dev_s12 @ fix_s11 @ inv_term @ dev_s21
                emb_s12 = dev_s12 @ (fix_s12 + fix_s11 @ inv_term @ dev_s22 @ fix_s12)
                emb_s21 = dev_s21 @ inv_term @ fix_s21
                emb_s22 = fix_s22 + fix_s21 @ inv_term @ dev_s22 @ fix_s12

                emb_s_reordered = np.block([
                    [emb_s11, emb_s12],
                    [emb_s21, emb_s22]
                ])

                # Reorder back to the original port order
                back_idx = [0, 2, 1, 3]
                s_embedded[i] = emb_s_reordered[np.ix_(back_idx, back_idx)]

            # Create a new network with the embedded S-parameters
            embedded = rf.Network(
                s=s_embedded,
                frequency=device.frequency,
                name='Right-Embedded Network'
            )

            # Save the embedded result
            base_name1 = os.path.splitext(os.path.basename(file1_path))[0]
            base_name2 = os.path.splitext(os.path.basename(file2_path))[0]
            output_filename = os.path.join(self.current_directory, f"{base_name1}_with_{base_name2}_embedded_right.s4p")
            # Normalize path to fix separator issues
            output_filename = os.path.normpath(output_filename)
            embedded.write_touchstone(output_filename)

            # Update the GUI
            self.refresh_file_list()
            messagebox.showinfo("Success", f"Right-side embedding completed successfully\nSaved as: {output_filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to embed S-parameters:\n{str(e)}")
            traceback.print_exc()

    def load_specification(self):
        """Load specification data from a CSV file"""
        try:
            filetypes = [('CSV files', '*.csv'), ('All files', '*.*')]
            filename = filedialog.askopenfilename(
                title='Select Specification File',
                filetypes=filetypes
            )
            
            if not filename:
                return
                
            # Clear existing specification data
            self.spec_data.clear()
            
            # Read CSV file
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header row
                
                # Initialize data lists
                freq = []
                sdd11 = []
                sdd21 = []
                
                # Read data
                for row in reader:
                    if len(row) >= 3:  # Ensure row has enough columns
                        freq.append(float(row[0]))  # Frequency in GHz
                        sdd11.append(float(row[1]))  # SDD11 spec in dB
                        sdd21.append(float(row[2]))  # SDD21 spec in dB
                
                # Store data
                self.spec_data['freq'] = np.array(freq)
                self.spec_data['sdd11'] = np.array(sdd11)
                self.spec_data['sdd21'] = np.array(sdd21)
            
            # Update plot
            if self.last_networks:
                self.plot_network_params(*self.last_networks, 
                                       show_mag=self.plot_mag_var.get(),
                                       show_phase=self.plot_phase_var.get())
            
            messagebox.showinfo("Success", "Specification data loaded successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load specification data:\n{str(e)}")
            traceback.print_exc()

    def calculate_impedance_profile(self, tdr_response):
        """Calculate impedance profile from TDR response assuming Z0=100Ω differential"""
        Z0 = 100  # Differential characteristic impedance
        
        # Extract real part only as reflection coefficient
        refl = np.real(tdr_response)
        print(f"IMPEDANCE CALCULATION DIAGNOSTICS:")
        print(f"  Initial reflection coef - min: {np.min(refl):.6f}, max: {np.max(refl):.6f}, mean: {np.mean(refl):.6f}")
        
        # Ensure our reflection coefficient has reasonable swing
        max_abs = np.max(np.abs(refl))
        if max_abs < 0.05:  # If reflection is too small, scale it up
            print(f"  Reflection coefficient too small ({max_abs:.6f}), scaling up")
            # Target a moderate reflection of +/-0.3
            scale = 0.3 / max_abs if max_abs > 1e-10 else 1.0
            refl = refl * scale
            print(f"  After scaling - min: {np.min(refl):.6f}, max: {np.max(refl):.6f}")
        elif max_abs > 0.9:  # If reflection is too large, scale it down
            print(f"  Reflection coefficient too large ({max_abs:.6f}), scaling down")
            scale = 0.5 / max_abs
            refl = refl * scale
            print(f"  After scaling - min: {np.min(refl):.6f}, max: {np.max(refl):.6f}")
        
        # Center the reflection coefficient around zero to produce impedance around Z0
        mean_val = np.mean(refl)
        if np.abs(mean_val) > 0.01:  # Only center if there's a significant offset
            print(f"  Centering reflection coefficient (offset: {mean_val:.6f})")
            refl = refl - mean_val
            print(f"  After centering - min: {np.min(refl):.6f}, max: {np.max(refl):.6f}, mean: {np.mean(refl):.6f}")
        
        # Apply tight limits on reflection coefficient to avoid impedance extremes
        refl = np.clip(refl, -0.5, 0.5)
        print(f"  After clipping - min: {np.min(refl):.6f}, max: {np.max(refl):.6f}")
        
        # Calculate impedance using standard formula: Z = Z0 * (1+Γ)/(1-Γ)
        Z = Z0 * (1 + refl) / (1 - refl)
        print(f"  Calculated impedance - min: {np.min(Z):.1f}Ω, max: {np.max(Z):.1f}Ω, mean: {np.mean(Z):.1f}Ω")
        
        # Display samples that produce max and min impedance
        max_Z_idx = np.argmax(Z)
        min_Z_idx = np.argmin(Z)
        print(f"  Max Z at index {max_Z_idx}: reflection = {refl[max_Z_idx]:.6f}, Z = {Z[max_Z_idx]:.1f}Ω")
        print(f"  Min Z at index {min_Z_idx}: reflection = {refl[min_Z_idx]:.6f}, Z = {Z[min_Z_idx]:.1f}Ω")
        
        # Apply final clipping to ensure reasonable impedance range
        # Enhance impedance variations for better visualization
        Z_mean = np.mean(Z)
        Z_variations = Z - Z_mean
        # Apply a reasonable amplification factor
        Z_amplification = 5.0
        Z_enhanced = Z_mean + (Z_variations * Z_amplification)
        Z = Z_enhanced
        print(f"Enhanced impedance variations by {Z_amplification}x factor")

        # Apply reasonable limits after enhancement
        Z = np.clip(Z, max(50, Z_mean-25), min(150, Z_mean+25))
        print(f"Final enhanced impedance - min: {np.min(Z):.1f}Ω, max: {np.max(Z):.1f}Ω, mean: {np.mean(Z):.1f}Ω")

        return Z
        """Calculate impedance profile from TDR response assuming Z0=100Ω differential"""
        Z0 = 100  # Differential characteristic impedance
        
        # Use real part of TDR response as reflection coefficient
        reflection_coef = np.real(tdr_response)
        
        # First normalize the reflection coefficient to ensure it's in valid range
        max_abs_val = np.max(np.abs(reflection_coef))
        if max_abs_val > 0.01:  # Only normalize if there's significant signal
            reflection_coef = reflection_coef / max_abs_val * 0.5  # Scale to +/-0.5 range for reasonable impedance
        
        # Center around Z0 by removing DC offset if it's small
        dc_offset = np.mean(reflection_coef)
        if np.abs(dc_offset) < 0.1:  # Only center if offset is small
            reflection_coef = reflection_coef - dc_offset
        
        # Apply safety limits to avoid division problems
        reflection_coef = np.clip(reflection_coef, -0.8, 0.8)
        
        # Calculate impedance using standard transmission line formula
        impedance = Z0 * (1 + reflection_coef)/(1 - reflection_coef)
        
        # Apply reasonable limits for typical transmission lines
        impedance = np.clip(impedance, 25, 200)
        
        print(f"Impedance profile stats - min: {np.min(impedance):.1f}Ω, max: {np.max(impedance):.1f}Ω, mean: {np.mean(impedance):.1f}Ω")
        
        return impedance
    def validate_directory(self, directory):
        """Validate if a directory exists and is accessible"""
        try:
            if os.path.exists(directory) and os.path.isdir(directory):
                return True
            return False
        except Exception:
            return False

    def set_safe_directory(self):
        """Set a safe default directory if the specified one doesn't exist"""
        # Try user's documents folder first
        documents = os.path.expanduser("~/Documents")
        if self.validate_directory(documents):
            self.current_directory = documents
        else:
            # Fall back to the directory containing this script
            self.current_directory = os.path.dirname(os.path.abspath(__file__))
        
        print(f"Using directory: {self.current_directory}")

    def read_data_file(self, file_path):
        """Read data from the specified S-parameter file and return frequency and data points.
        
        Returns:
            tuple: (frequencies, data_points) where frequencies is a list of frequency values
                  and data_points is a list of lists containing S-parameter magnitude/phase values
        """
        frequencies = []
        data_points = []
        expected_columns = 33  # 1 frequency column + 32 S-parameter values (16 pairs of mag/phase)
        
        print(f"\nDebug: Reading file {file_path}")
        with open(file_path, 'r') as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Skip comment lines and format specifier
                if line.startswith('!') or line.startswith('#'):
                    if line_number <= 5:  # Print first few header lines for debugging
                        print(f"Debug: Skipping header line {line_number}: {line}")
                    continue
                
                # Split on any whitespace (handles both tabs and spaces)
                components = line.split()
                
                # Debug first few data lines
                if len(frequencies) < 2:
                    print(f"Debug: Processing line {line_number} with {len(components)} columns")
                    print(f"Debug: First few values: {components[:5]}")
                
                # Validate number of columns
                if len(components) != expected_columns:
                    print(f"Warning: Line {line_number} has {len(components)} columns, expected {expected_columns}")
                    print(f"Debug: Line content: {line}")
                    continue
                
                try:
                    # Convert all values to float, handling scientific notation
                    values = []
                    for value in components:
                        # Handle scientific notation with 'e' or 'E'
                        value = value.replace('e+', 'e').replace('E+', 'e')
                        values.append(float(value))
                    
                    frequencies.append(values[0])  # First value is frequency
                    data_points.append(values[1:])  # Rest are S-parameter values
                    
                    # Print progress every 1000 lines
                    if len(frequencies) % 1000 == 0:
                        print(f"Processed {len(frequencies)} lines...")
                        
                except ValueError as e:
                    print(f"Line {line_number}: Failed to parse: {str(e)}")
                    if len(frequencies) < 2:  # Show problematic values for first few lines
                        print(f"Debug: Problematic values: {components}")
                    continue
        
        print(f"Successfully read {len(frequencies)} frequency points")
        if not frequencies:
            raise ValueError("No valid data found in file")
            
        return np.array(frequencies), np.array(data_points)

    def update_smith_chart(self):
        """Update the Smith chart with current data"""
        try:
            if not self.smith_window or not tk.Toplevel.winfo_exists(self.smith_window):
                return
                
            # Clear the window
            for widget in self.smith_window.winfo_children():
                widget.destroy()
                
            # Create button frame at the top
            btn_frame = ttk.Frame(self.smith_window)
            btn_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Add port mapping button
            ttk.Button(btn_frame, text="Port Mapping", 
                      command=self.show_port_mapping_dialog).pack(side=tk.LEFT, padx=2)
            
            # Add close button
            ttk.Button(btn_frame, text="Close", 
                      command=self.close_smith_chart).pack(side=tk.RIGHT, padx=2)
                
            # Create figure with subplots based on checkbox status
            num_plots = sum([self.plot_sdd11_var.get(), self.plot_sdd21_var.get()])
            if num_plots == 0:
                messagebox.showwarning("Warning", "Please select at least one parameter (SDD11 or SDD21)")
                self.smith_window.destroy()
                return
                
            fig = Figure(figsize=(8, 4 if num_plots > 1 else 8))
            canvas = FigureCanvasTkAgg(fig, master=self.smith_window)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar = NavigationToolbar2Tk(canvas, self.smith_window)
            toolbar.update()
            
            plot_idx = 1
            if self.plot_sdd11_var.get():
                ax_sdd11 = fig.add_subplot(1 if num_plots == 1 else 2, 1, plot_idx, projection='polar')
                self.plot_smith_parameter(ax_sdd11, 'sdd11')
                plot_idx += 1
                
            if self.plot_sdd21_var.get():
                ax_sdd21 = fig.add_subplot(1 if num_plots == 1 else 2, 1, plot_idx, projection='polar')
                self.plot_smith_parameter(ax_sdd21, 'sdd21')
            
            fig.tight_layout()
            canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update Smith chart: {str(e)}")
            if self.smith_window:
                self.smith_window.destroy()

    def close_smith_chart(self):
        """Close the Smith chart window and clean up"""
        if self.smith_window and tk.Toplevel.winfo_exists(self.smith_window):
            self.smith_window.destroy()
        self.smith_window = None

    def show_smith_chart(self):
        """Display Smith chart in a pop-up window"""
        if not hasattr(self, 'last_networks') or not self.last_networks:
            messagebox.showwarning("Warning", "No S-parameter data loaded")
            return
            
        try:
            # Create new window if it doesn't exist or was destroyed
            if self.smith_window is None or not tk.Toplevel.winfo_exists(self.smith_window):
                self.smith_window = tk.Toplevel(self)
                self.smith_window.title("Smith Chart")
                self.smith_window.geometry("800x600")
                
                # Set up window close handler
                self.smith_window.protocol("WM_DELETE_WINDOW", self.close_smith_chart)
                
            self.update_smith_chart()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create Smith chart: {str(e)}")
            if self.smith_window:
                self.smith_window.destroy()

    def plot_smith_parameter(self, ax, param):
        """Plot a specific S-parameter on a Smith chart"""
        try:
            for i, network in enumerate(self.last_networks):
                # Get the differential S-parameters
                sdd = self.s2sdd(network.s)
                
                if param == 'sdd11':
                    s_data = sdd[:, 0, 0]
                    title = 'SDD11 Smith Chart'
                else:  # sdd21
                    s_data = sdd[:, 1, 0]
                    title = 'SDD21 Smith Chart'
                
                # Plot using polar coordinates
                angles = np.angle(s_data)
                magnitudes = np.abs(s_data)
                ax.plot(angles, magnitudes, label=f'Network {i+1}')
                
            ax.set_title(title)
            ax.grid(True)
            ax.legend()
            
            # Customize polar plot
            ax.set_theta_zero_location('E')  # 0 degrees at right (east)
            ax.set_theta_direction(-1)       # clockwise
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot {param}: {str(e)}")
            
    def show_port_mapping_dialog(self):
        """Show dialog to configure port mapping"""
        dialog = tk.Toplevel(self)
        dialog.title("Port Mapping Configuration")
        dialog.geometry("300x200")
        dialog.transient(self)  # Make dialog modal
        dialog.grab_set()
        
        # Create and pack the explanation label
        ttk.Label(dialog, text="Map logical ports to physical ports:").pack(pady=10)
        
        # Create entry fields for each port
        port_vars = []
        entries = []
        for i in range(4):
            frame = ttk.Frame(dialog)
            frame.pack(fill=tk.X, padx=20, pady=2)
            
            ttk.Label(frame, text=f"Logical Port {i+1} →").pack(side=tk.LEFT)
            var = tk.StringVar(value=str(self.port_mapping[i]))
            port_vars.append(var)
            entry = ttk.Entry(frame, textvariable=var, width=5)
            entry.pack(side=tk.LEFT, padx=5)
            entries.append(entry)
            
        def validate_and_apply():
            try:
                # Get values and validate
                new_mapping = [int(var.get()) for var in port_vars]
                
                # Check if all ports are between 1 and 4
                if not all(1 <= p <= 4 for p in new_mapping):
                    raise ValueError("Ports must be between 1 and 4")
                    
                # Check if all ports are unique
                if len(set(new_mapping)) != 4:
                    raise ValueError("Each port must be used exactly once")
                
                # Apply the mapping
                self.port_mapping = new_mapping
                
                # Update plots if we have data
                if hasattr(self, 'last_networks') and self.last_networks:
                    self.update_plot()
                    if self.smith_window and tk.Toplevel.winfo_exists(self.smith_window):
                        self.update_smith_chart()
                
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e))
        
        # Create button frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Button(btn_frame, text="Apply", command=validate_and_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)


    def deembed_sparams(self):
        """De-embed the first S-parameter file using the second file as the fixture"""
        try:
            # Check if we have exactly two networks selected
            if not hasattr(self, 'last_networks') or len(self.last_networks) != 2:
                messagebox.showwarning("Warning", "Please select exactly two S-parameter files.\nFirst: DUT with fixture\nSecond: Fixture only")
                return

            dut_with_fixture = self.last_networks[0]
            fixture = self.last_networks[1]

            # Check if frequencies match
            if not np.allclose(dut_with_fixture.f, fixture.f):
                messagebox.showerror("Error", "Frequency points must match between the two files")
                return

            # Reorder ports to group differential pairs
            reorder_idx = [0, 2, 1, 3]

            # Convert S to T parameters for both networks
            dut_reordered = dut_with_fixture.s[:, reorder_idx][:, :, reorder_idx]
            fixture_reordered = fixture.s[:, reorder_idx][:, :, reorder_idx]

            dut_t = rf.s2t(dut_reordered)
            fixture_t = rf.s2t(fixture_reordered)

            # De-embed by multiplying by inverse of fixture T-parameters
            deembedded_t = np.zeros_like(dut_t)
            for i in range(len(dut_t)):
                try:
                    # T_dut = T_fixture * T_actual
                    # Therefore: T_actual = inv(T_fixture) * T_dut
                    fixture_inv = np.linalg.inv(fixture_t[i])
                    deembedded_t[i] = fixture_inv @ dut_t[i]
                except np.linalg.LinAlgError:
                    messagebox.showerror("Error", f"Matrix inversion failed at frequency point {dut_with_fixture.f[i]/1e9:.2f} GHz")
                    return

            # Convert de-embedded T-parameters back to S-parameters
            deembedded_s = rf.t2s(deembedded_t)

            # Reorder back to the original port order
            back_idx = [0, 2, 1, 3]
            deembedded_s = deembedded_s[:, back_idx][:, :, back_idx]

            # Create a new network with the de-embedded parameters
            deembedded = rf.Network()
            deembedded.frequency = dut_with_fixture.frequency
            deembedded.s = deembedded_s  # Convert back to S-parameters
            
            # Save the de-embedded network
            base_name = os.path.splitext(dut_with_fixture.name)[0]
            output_filename = os.path.join(self.current_directory, f"{base_name}_deembedded_left.s4p")
            # Normalize path to fix separator issues
            output_filename = os.path.normpath(output_filename)
            deembedded.write_touchstone(output_filename)
            
            # Add to the list of networks with a descriptive name
            deembedded.name = f"{base_name}_deembedded_left"
            self.last_networks = [deembedded]
            
            # Update plots
            self.update_plot()
            if self.smith_window and tk.Toplevel.winfo_exists(self.smith_window):
                self.update_smith_chart()
                
            # Refresh the file list to show the new file
            self.refresh_file_list()
            
            messagebox.showinfo("Success", f"Left-side de-embedding completed successfully\nSaved as: {output_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"De-embedding failed: {str(e)}")
            traceback.print_exc()

    def deembed_sparams_right(self):
        """De-embed the first S-parameter file using the second file as the right-side fixture"""
        try:
            # Check if we have exactly two networks selected
            if not hasattr(self, 'last_networks') or len(self.last_networks) != 2:
                messagebox.showwarning("Warning", "Please select exactly two S-parameter files.\nFirst: DUT with fixture\nSecond: Fixture only")
                return

            dut_with_fixture = self.last_networks[0]
            fixture = self.last_networks[1]

            # Check if frequencies match
            if not np.allclose(dut_with_fixture.f, fixture.f):
                messagebox.showerror("Error", "Frequency points must match between the two files")
                return

            # Reorder ports to group differential pairs
            reorder_idx = [0, 2, 1, 3]

            # Convert S to T parameters for both networks
            dut_reordered = dut_with_fixture.s[:, reorder_idx][:, :, reorder_idx]
            fixture_reordered = fixture.s[:, reorder_idx][:, :, reorder_idx]

            dut_t = rf.s2t(dut_reordered)
            fixture_t = rf.s2t(fixture_reordered)

            # De-embed by multiplying by inverse of fixture T-parameters
            deembedded_t = np.zeros_like(dut_t)
            for i in range(len(dut_t)):
                try:
                    # T_dut = T_actual * T_fixture
                    # Therefore: T_actual = T_dut * inv(T_fixture)
                    fixture_inv = np.linalg.inv(fixture_t[i])
                    deembedded_t[i] = dut_t[i] @ fixture_inv
                except np.linalg.LinAlgError:
                    messagebox.showerror("Error", f"Matrix inversion failed at frequency point {dut_with_fixture.f[i]/1e9:.2f} GHz")
                    return

            # Convert de-embedded T-parameters back to S-parameters
            deembedded_s = rf.t2s(deembedded_t)

            # Reorder back to the original port order
            back_idx = [0, 2, 1, 3]
            deembedded_s = deembedded_s[:, back_idx][:, :, back_idx]

            # Create a new network with the de-embedded parameters
            deembedded = rf.Network()
            deembedded.frequency = dut_with_fixture.frequency
            deembedded.s = deembedded_s  # Convert back to S-parameters
            
            # Save the de-embedded network
            base_name = os.path.splitext(dut_with_fixture.name)[0]
            output_filename = os.path.join(self.current_directory, f"{base_name}_deembedded_right.s4p")
            # Normalize path to fix separator issues
            output_filename = os.path.normpath(output_filename)
            deembedded.write_touchstone(output_filename)
            
            # Add to the list of networks with a descriptive name
            deembedded.name = f"{base_name}_deembedded_right"
            self.last_networks = [deembedded]
            
            # Update plots
            self.update_plot()
            if self.smith_window and tk.Toplevel.winfo_exists(self.smith_window):
                self.update_smith_chart()
                
            # Refresh the file list to show the new file
            self.refresh_file_list()
            
            messagebox.showinfo("Success", f"Right-side de-embedding completed successfully\nSaved as: {output_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Right-side de-embedding failed: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    app = SParamBrowser()
    app.mainloop()
