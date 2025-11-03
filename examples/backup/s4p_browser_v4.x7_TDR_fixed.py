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
# custom_pandastable_path = r"C:\Users\juesh\OneDrive\Documents\windsurf\pandastable\pandastable"
custom_pandastable_path = r"C:\Users\JueShi\OneDrive - Astera Labs, Inc\Documents\windsurf\pandastable\pandastable"
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
from scipy import signal
# Import ICZT function from local module
from iczt_function import calculate_tdr_iczt
import scipy.linalg

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
        self.plot_s11_var = tk.BooleanVar(value=False)
        self.plot_s21_var = tk.BooleanVar(value=False)
        self.plot_s33_var = tk.BooleanVar(value=False)
        self.plot_s43_var = tk.BooleanVar(value=False)
        self.overlay_charts_var = tk.BooleanVar(value=False)
        self.show_spec_var = tk.BooleanVar(value=True)
        self.show_tdr_var = tk.BooleanVar(value=False)  # Add TDR control variable
        self.show_pulse_var = tk.BooleanVar(value=False)  # Add pulse response control variable
        self.show_impedance_var = tk.BooleanVar(value=False)  # Add impedance profile control variable
        self.show_impedance_time_var = tk.BooleanVar(value=False)  # Add impedance profile vs time control variable
        
        # Add velocity factor control variable
        self.velocity_factor = tk.StringVar(value='0.5')  # Default velocity factor for PCB materials
        
        # Custom Sij selections
        self.custom_sij = []  # list of (i,j) tuples, 1-based
        self.sij_i_var = tk.StringVar(value='1')
        self.sij_j_var = tk.StringVar(value='1')
        # History of custom Sij per file: {file_path: ["Sij", ...]}
        self.sij_history = {}
        
        # Add zoom control variables
        self.freq_min = tk.StringVar(value='')
        self.freq_max = tk.StringVar(value='')
        self.mag_min = tk.StringVar(value='')
        self.mag_max = tk.StringVar(value='')
        self.phase_min = tk.StringVar(value='')
        self.phase_max = tk.StringVar(value='')       
        self.dist_min = tk.StringVar(value='0')  # Add distance control for TDR
        self.dist_max = tk.StringVar(value='30')  # Add distance control for TDR
        self.time_min = tk.StringVar(value='-1')  # Add time control for pulse response
        self.time_max = tk.StringVar(value='5')  # Add time control for pulse response
        self.amp_min = tk.StringVar(value='')   # Add amplitude control for pulse response
        self.amp_max = tk.StringVar(value='')   # Add amplitude control for pulse response
        self.imp_min = tk.StringVar(value='')   # Add impedance control for impedance profile
        self.imp_max = tk.StringVar(value='')   # Add impedance control for impedance profile
        
        # Add time domain resolution control variables
        self.padding_factor = tk.StringVar(value='2')  # Zero-padding factor
        self.window_type = tk.StringVar(value='none')  # Window function type
        self.freq_limit = tk.StringVar(value='')  # Add frequency limit variable for TDR
        
        # Add Smith chart window variable
        self.smith_window = None
        
        # Set and validate default directory
        default_dir = os.path.join(os.path.expanduser("~"), "OneDrive", "Documents", "MATLAB", "alab")  # Start in MATLAB/alab directory
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
            
        # Initialize fullscreen state and bind escape key
        self.is_plot_fullscreen = False
        self.bind('<Escape>', lambda e: self.toggle_plot_fullscreen())

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
                    # Split filter text by space
                    filter_terms = filter_text.split()
                    print(f"Searching for terms: {filter_terms}")  # Debug print
                    
                    # Start with all rows
                    mask = pd.Series([True] * len(self.df), index=self.df.index)
                    
                    # Apply each filter term with AND logic
                    for term in filter_terms:
                        term = term.strip()
                        if term:  # Skip empty terms
                            term_mask = None  # Initialize term_mask to avoid UnboundLocalError
                            if term.startswith('!'):  # Exclusion term
                                exclude_term = term[1:].strip()
                                if exclude_term:
                                    term_mask = ~self.df['Name'].str.contains(exclude_term, case=False, na=False)
                                    print(f"Excluding rows with name containing: '{exclude_term}'")  # Debug print
                            else:  # Inclusion term
                                term_mask = self.df['Name'].str.contains(term, case=False, na=False)
                                print(f"Including rows with name containing: '{term}'")  # Debug print
                            
                            # Only apply the mask if term_mask was properly set
                            if term_mask is not None:
                                mask = mask & term_mask
                    
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
                if new_row < 0 or new_row >= len(displayed_df):
                    print(f"Row index {new_row} out of bounds for displayed_df of length {len(displayed_df)}")
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
            ttk.Checkbutton(controls_frame, text="S11", variable=self.plot_s11_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Checkbutton(controls_frame, text="S21", variable=self.plot_s21_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Checkbutton(controls_frame, text="S33", variable=self.plot_s33_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Checkbutton(controls_frame, text="S43", variable=self.plot_s43_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            ttk.Checkbutton(controls_frame, text="Overlay", variable=self.overlay_charts_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            # Compact Arbitrary Sij picker
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            ttk.Label(controls_frame, text="Sij:").pack(side=tk.LEFT)
            self.sij_i_spin = tk.Spinbox(controls_frame, from_=1, to=4, width=2, textvariable=self.sij_i_var)
            self.sij_i_spin.pack(side=tk.LEFT)
            ttk.Label(controls_frame, text=",").pack(side=tk.LEFT)
            self.sij_j_spin = tk.Spinbox(controls_frame, from_=1, to=4, width=2, textvariable=self.sij_j_var)
            self.sij_j_spin.pack(side=tk.LEFT)
            ttk.Button(controls_frame, text="Add", width=4, command=self.add_custom_sij).pack(side=tk.LEFT, padx=2)
            ttk.Button(controls_frame, text="Clr", width=3, command=self.clear_custom_sij).pack(side=tk.LEFT, padx=1)
            self.sij_status = ttk.Label(controls_frame, text="", width=14)
            self.sij_status.pack(side=tk.LEFT, padx=2)
            # History dropdown (per file)
            ttk.Label(controls_frame, text="History:").pack(side=tk.LEFT, padx=(6,2))
            self.sij_combo = ttk.Combobox(controls_frame, width=10, state='readonly', values=[])
            self.sij_combo.pack(side=tk.LEFT)
            self.sij_combo.bind('<<ComboboxSelected>>', self.on_select_sij_history)
            
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
            ttk.Checkbutton(controls_frame, text="Z Profile(t)", variable=self.show_impedance_time_var,
                           command=self.update_plot).pack(side=tk.LEFT)
            
            ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Velocity factor control for TDR distance calculation
            ttk.Label(controls_frame, text="v_rel:").pack(side=tk.LEFT, padx=2)
            velocity_entry = ttk.Entry(controls_frame, textvariable=self.velocity_factor, width=6)
            velocity_entry.pack(side=tk.LEFT, padx=2)
            velocity_entry.bind('<Return>', lambda e: self.update_plot())
            
            # Add tooltip for velocity factor guidance
            self.create_velocity_tooltip(velocity_entry)
            
            # Add zoom control frame with compact layout
            zoom_frame = ttk.LabelFrame(self.sparam_view_container, text="Zoom")
            zoom_frame.grid(row=5, column=0, sticky='ew', padx=2, pady=2)
            
            # Create zoom container
            zoom_container = ttk.Frame(zoom_frame)
            zoom_container.pack(fill='x', padx=2, pady=2)
            
            # Frequency controls - more compact
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
            ttk.Label(time_frame, text="t(ns):").pack(side=tk.LEFT)
            ttk.Entry(time_frame, textvariable=self.time_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(time_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(time_frame, textvariable=self.time_max, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Distance controls - more compact
            dist_frame = ttk.Frame(zoom_container)
            dist_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(dist_frame, text="d(inch):").pack(side=tk.LEFT)
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
            
            ttk.Separator(zoom_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Impedance controls - more compact
            imp_frame = ttk.Frame(zoom_container)
            imp_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(imp_frame, text="Z(Ω):").pack(side=tk.LEFT)
            ttk.Entry(imp_frame, textvariable=self.imp_min, width=6).pack(side=tk.LEFT, padx=1)
            ttk.Label(imp_frame, text="-").pack(side=tk.LEFT, padx=1)
            ttk.Entry(imp_frame, textvariable=self.imp_max, width=6).pack(side=tk.LEFT, padx=1)
            
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
            ttk.Label(pad_frame, text="Pad:2-128").pack(side=tk.LEFT)
            vcmd = (self.register(self._validate_padding_factor), '%P')
            padding_entry = ttk.Entry(pad_frame, textvariable=self.padding_factor, 
                                    width=10, validate='key', validatecommand=vcmd)
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
            
            ttk.Separator(settings_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Add frequency limit control - more compact
            freq_limit_frame = ttk.Frame(settings_container)
            freq_limit_frame.pack(side=tk.LEFT, padx=2)
            ttk.Label(freq_limit_frame, text="Freq Limit (GHz):").pack(side=tk.LEFT)
            ttk.Entry(freq_limit_frame, textvariable=self.freq_limit, width=6).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(settings_container, orient='vertical').pack(side=tk.LEFT, padx=4, fill='y')
            
            # Add Low Pass checkbox
            lowpass_frame = ttk.Frame(settings_container)
            lowpass_frame.pack(side=tk.LEFT, padx=2)
            # Create the variable here to ensure it exists
            if not hasattr(self, 'low_pass_mode'):
                self.low_pass_mode = tk.BooleanVar(value=False)
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
            return 1 <= factor <= 128
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
                # Ask user for confirmation before overwriting
                from tkinter import messagebox
                result = messagebox.askyesno(
                    "File Exists", 
                    f"Target file already exists:\n{new_filepath}\n\nDo you want to overwrite it?",
                    icon='warning'
                )
                if not result:
                    print(f"Rename operation cancelled by user")
                    return old_filepath  # Return original path if user cancels
                else:
                    print(f"User confirmed overwrite of existing file")
                    # On Windows, os.rename() cannot overwrite existing files
                    # So we need to delete the target file first
                    try:
                        os.remove(new_filepath)
                        print(f"Deleted existing target file: {new_filepath}")
                    except Exception as delete_error:
                        print(f"Warning: Could not delete existing file: {delete_error}")
            
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
                # Use the displayed DataFrame (filtered) instead of the original DataFrame
                displayed_df = self.table.model.df
                if row >= len(displayed_df):  # Check if row index is valid
                    continue
                    
                file_path = displayed_df.iloc[row].get('File_Path', os.path.join(self.current_directory, displayed_df.iloc[row]['Name']))
                # Fix potential path separator inconsistencies
                file_path = os.path.normpath(file_path.replace('\\', '/'))
                
                # Update current_file when a single file is selected
                if len(selected_rows) == 1:
                    self.current_file = file_path
                
                try:
                    # First try loading with scikit-rf's native loader
                    try:
                        network = rf.Network(os.path.normpath(file_path))
                    except Exception as rf_error:
                        print(f"Native loader failed, trying custom parser: {str(rf_error)}")
                        # If native loader fails, use our custom parser
                        freq, s_params = self.parse_sparam_file(file_path)
                        network = rf.Network()
                        network.frequency = rf.Frequency.from_f(freq, unit='hz')
                        network.s = s_params
                        network.z0 = 50  # Standard impedance
                        network.name = os.path.splitext(os.path.basename(file_path))[0]  # Set name from filename
                    networks.append(network)
                except Exception as e:
                    print(f"Error loading network {file_path}: {str(e)}")
                    traceback.print_exc()
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
            format_token = 'ri'  # default
            param_token = 's'
            r_ref = 50.0
            data_start = 0
            
            # Parse header section
            for i, line in enumerate(lines):
                if line.strip().startswith('#'):
                    header = line.strip().split()
                    # Touchstone v1 header like: '# Hz S RI R 50'
                    low = [x.lower() for x in header]
                    # Unit
                    unit = next((x for x in low if x in ['hz', 'khz', 'mhz', 'ghz']), 'hz')
                    # Parameter type (we only support S for plotting, but parse anyway)
                    if any(x in low for x in ['y','z','h','g']):
                        param_token = next((x for x in low if x in ['s','y','z','h','g']), 's')
                    else:
                        param_token = 's'
                    # Data format
                    if 'ri' in low:
                        format_token = 'ri'
                    elif 'ma' in low:
                        format_token = 'ma'
                    elif 'db' in low:
                        format_token = 'db'
                    # Reference R
                    if 'r' in low:
                        try:
                            idx = low.index('r')
                            r_ref = float(header[idx+1])
                        except Exception:
                            r_ref = 50.0
                elif line.strip() and not line.strip().startswith('!'):
                    data_start = i
                    break

            if not header:
                raise ValueError("No valid header found in file")

            # Get frequency unit from header parsed above
            unit = next((x.lower() for x in header if x.lower() in ['hz','khz','mhz','ghz']), 'hz')

            # Parse the data section
            data_rows = []
            for line in lines[data_start:]:
                line = line.strip()
                if not line or line.startswith('!') or line.startswith('#'):
                    continue
                parts = line.split()
                # Only accept lines with numeric values
                try:
                    row = [float(x) for x in parts]
                except ValueError:
                    continue
                data_rows.append(row)
            
            if not data_rows:
                raise ValueError("No valid data found in file")
            
            # Determine n_ports from columns per row (Touchstone v1 assumed on single line)
            # Expected counts: 2-port -> 1 + 8 = 9, 4-port -> 1 + 32 = 33
            from collections import Counter
            counts = Counter(len(r) for r in data_rows)
            common_len = counts.most_common(1)[0][0]
            if common_len not in (9, 33):
                # Fallback: try to detect by divisibility of pairs
                if (common_len - 1) % 2 == 0:
                    pairs = (common_len - 1) // 2
                    n_ports = int(round(pairs ** 0.5))
                    if n_ports not in (2, 4):
                        raise ValueError(f"Unsupported record length {common_len}")
                else:
                    raise ValueError(f"Unsupported record length {common_len}")
            else:
                n_ports = 2 if common_len == 9 else 4

            # Keep only rows matching common_len
            data = np.array([r for r in data_rows if len(r) == common_len], dtype=float)
            if len(data) == 0:
                raise ValueError("No consistent data rows found")

            # Frequency column with unit scaling
            freq = data[:, 0]
            scale = {'hz': 1.0, 'khz': 1e3, 'mhz': 1e6, 'ghz': 1e9}.get(unit.lower(), 1.0)
            freq = freq * scale

            # S-parameter raw columns (pairs per element)
            vals = data[:, 1:]
            # Prepare output
            s_params = np.zeros((len(freq), n_ports, n_ports), dtype=complex)

            def pair_to_complex(a, b):
                if format_token == 'ri':
                    return a + 1j*b
                elif format_token == 'ma':
                    # magnitude & angle(deg)
                    return a * (np.cos(np.deg2rad(b)) + 1j*np.sin(np.deg2rad(b)))
                elif format_token == 'db':
                    # dB & angle(deg)
                    mag = 10**(a/20.0)
                    return mag * (np.cos(np.deg2rad(b)) + 1j*np.sin(np.deg2rad(b)))
                else:
                    return a + 1j*b

            if n_ports == 2:
                # Order: S11 S21 S12 S22 (each as pair)
                reim = vals.reshape(len(freq), 4, 2)
                s11 = pair_to_complex(reim[:,0,0], reim[:,0,1])
                s21 = pair_to_complex(reim[:,1,0], reim[:,1,1])
                s12 = pair_to_complex(reim[:,2,0], reim[:,2,1])
                s22 = pair_to_complex(reim[:,3,0], reim[:,3,1])
                s_params[:,0,0] = s11
                s_params[:,1,0] = s21
                s_params[:,0,1] = s12
                s_params[:,1,1] = s22
            else:  # n_ports == 4
                # Touchstone ordering for 4-port v1: by column j=1..4, within each column i=1..4
                # Sequence (i,j): (1,1),(2,1),(3,1),(4,1),(1,2)...(4,4)
                reim = vals.reshape(len(freq), 16, 2)
                idx = 0
                for j in range(4):
                    for i in range(4):
                        comp = pair_to_complex(reim[:, idx, 0], reim[:, idx, 1])
                        s_params[:, i, j] = comp
                        idx += 1

            print(f"Successfully parsed {len(freq)} frequency points")
            print(f"Frequency range: {freq[0]} to {freq[-1]} Hz")
            
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
            # Build list of selected parameters to plot
            selected_params = []
            # Calculate differential parameters once if needed
            sdd_params = None
            if self.plot_sdd11_var.get() or self.plot_sdd21_var.get():
                sdd_params = self.calculate_sdd_params(s_params)
            if self.plot_sdd11_var.get():
                selected_params.append(('SDD11',
                                        20 * np.log10(np.abs(sdd_params[:, 0, 0])),
                                        np.angle(sdd_params[:, 0, 0], deg=True)))
            if self.plot_sdd21_var.get():
                selected_params.append(('SDD21',
                                        20 * np.log10(np.abs(sdd_params[:, 1, 0])),
                                        np.angle(sdd_params[:, 1, 0], deg=True)))
            if self.plot_s11_var.get():
                # Single-ended S11 from port 1
                s11_mag = 20 * np.log10(np.abs(s_params[:, 0, 0]))
                s11_phase = np.angle(s_params[:, 0, 0], deg=True)
                selected_params.append(('S11', s11_mag, s11_phase))
            if self.plot_s21_var.get():
                # Single-ended S21 from port 2 to 1
                s21_mag = 20 * np.log10(np.abs(s_params[:, 1, 0]))
                s21_phase = np.angle(s_params[:, 1, 0], deg=True)
                selected_params.append(('S21', s21_mag, s21_phase))
            if self.plot_s33_var.get():
                # Return loss at port 3
                s33_mag = 20 * np.log10(np.abs(s_params[:, 2, 2]))
                s33_phase = np.angle(s_params[:, 2, 2], deg=True)
                selected_params.append(('S33', s33_mag, s33_phase))
            if self.plot_s43_var.get():
                # Transmission from port 3 to port 4 (S43)
                s43_mag = 20 * np.log10(np.abs(s_params[:, 3, 2]))
                s43_phase = np.angle(s_params[:, 3, 2], deg=True)
                selected_params.append(('S43', s43_mag, s43_phase))
            # Add custom Sij selections
            if self.custom_sij:
                bad = []
                for (ii, jj) in self.custom_sij:
                    if 1 <= ii <= n_ports and 1 <= jj <= n_ports:
                        name = f"S{ii}{jj}"
                        vals = s_params[:, ii-1, jj-1]
                        selected_params.append((name, 20*np.log10(np.abs(vals)), np.angle(vals, deg=True)))
                    else:
                        bad.append((ii, jj))
                if bad and hasattr(self, 'td_status') and self.td_status is not None:
                    self.td_status.config(text=f"Invalid Sij: {','.join([f'S{i}{j}' for i,j in bad])}", foreground='orange')

            if not selected_params:
                # Default to SDD11 and SDD21 if nothing selected
                sdd_params = self.calculate_sdd_params(s_params)
                selected_params = [
                    ('SDD11', 20 * np.log10(np.abs(sdd_params[:, 0, 0])), np.angle(sdd_params[:, 0, 0], deg=True)),
                    ('SDD21', 20 * np.log10(np.abs(sdd_params[:, 1, 0])), np.angle(sdd_params[:, 1, 0], deg=True))
                ]

            # Determine which rows to show based on View checkboxes
            show_mag = self.plot_mag_var.get()
            show_phase = self.plot_phase_var.get()
            rows = (1 if show_mag else 0) + (1 if show_phase else 0)
            if rows == 0:
                show_mag = True
                rows = 1

            if self.overlay_charts_var.get():
                # Overlay mode: one mag and one phase subplot
                if rows == 2:
                    ax_mag, ax_phase = self.figure.subplots(2, 1)
                else:
                    ax_mag = self.figure.add_subplot(111)
                    ax_phase = None

                for (name, mag_vals, phase_vals) in selected_params:
                    if show_mag:
                        ax_mag.plot(freq/1e9, mag_vals, label=name)
                    if show_phase and ax_phase is not None:
                        ax_phase.plot(freq/1e9, phase_vals, label=name)

                if show_mag:
                    ax_mag.set_xlabel('Frequency (GHz)')
                    ax_mag.set_ylabel('Magnitude (dB)')
                    ax_mag.set_title('Magnitude (Overlay)')
                    ax_mag.grid(True)
                    ax_mag.legend()
                if show_phase and ax_phase is not None:
                    ax_phase.set_xlabel('Frequency (GHz)')
                    ax_phase.set_ylabel('Phase (degrees)')
                    ax_phase.set_title('Phase (Overlay)')
                    ax_phase.grid(True)
                    ax_phase.legend()
            else:
                # Non-overlay: Create subplots with 1 or 2 rows and N columns (selected params)
                ncols = len(selected_params)
                if rows == 2:
                    axes = self.figure.subplots(2, ncols)
                    if ncols == 1:
                        axes = np.array([[axes[0]], [axes[1]]])
                else:
                    # single row
                    row_axes = self.figure.subplots(1, ncols)
                    if ncols == 1:
                        row_axes = [row_axes]
                    # convert to 2D array with one row for consistent indexing
                    axes = np.array([row_axes])

                for idx, (name, mag_vals, phase_vals) in enumerate(selected_params):
                    if show_mag:
                        ax_mag = axes[0, idx]
                        ax_mag.plot(freq/1e9, mag_vals, label=name)
                        ax_mag.set_xlabel('Frequency (GHz)')
                        ax_mag.set_ylabel('Magnitude (dB)')
                        ax_mag.set_title(f'{name} Magnitude')
                        ax_mag.grid(True)
                        ax_mag.legend()

                    if show_phase:
                        # If only phase row, it's the first row; if both, it's second row
                        ax_phase = axes[0 if rows == 1 else 1, idx]
                        ax_phase.plot(freq/1e9, phase_vals, label=name)
                        ax_phase.set_xlabel('Frequency (GHz)')
                        ax_phase.set_ylabel('Phase (degrees)')
                        ax_phase.set_title(f'{name} Phase')
                        ax_phase.grid(True)
                        ax_phase.legend()

        else:  # n_ports == 2
            # Warn if user requested S33/S43 which are not available for 2-port
            try:
                if self.plot_s33_var.get() or self.plot_s43_var.get():
                    if hasattr(self, 'td_status') and self.td_status is not None:
                        self.td_status.config(text="S33/S43 not available for 2-port files", foreground='orange')
            except Exception:
                pass
            # Build list of selected single-ended parameters to plot based on checkboxes
            selected_params = []
            if self.plot_s11_var.get():
                s11_mag = 20 * np.log10(np.abs(s_params[:, 0, 0]))
                s11_phase = np.angle(s_params[:, 0, 0], deg=True)
                selected_params.append(('S11', s11_mag, s11_phase))
            if self.plot_s21_var.get():
                s21_mag = 20 * np.log10(np.abs(s_params[:, 1, 0]))
                s21_phase = np.angle(s_params[:, 1, 0], deg=True)
                selected_params.append(('S21', s21_mag, s21_phase))
            # Add custom Sij selections (limited to 2-port)
            if self.custom_sij:
                bad = []
                for (ii, jj) in self.custom_sij:
                    if 1 <= ii <= n_ports and 1 <= jj <= n_ports:
                        name = f"S{ii}{jj}"
                        vals = s_params[:, ii-1, jj-1]
                        selected_params.append((name, 20*np.log10(np.abs(vals)), np.angle(vals, deg=True)))
                    else:
                        bad.append((ii, jj))
                if bad and hasattr(self, 'td_status') and self.td_status is not None:
                    self.td_status.config(text=f"Invalid Sij: {','.join([f'S{i}{j}' for i,j in bad])}", foreground='orange')

            if not selected_params:
                # Default to both if user didn't select any
                s11_mag = 20 * np.log10(np.abs(s_params[:, 0, 0]))
                s21_mag = 20 * np.log10(np.abs(s_params[:, 1, 0]))
                s11_phase = np.angle(s_params[:, 0, 0], deg=True)
                s21_phase = np.angle(s_params[:, 1, 0], deg=True)
                selected_params = [('S11', s11_mag, s11_phase), ('S21', s21_mag, s21_phase)]

            # Respect View toggles
            show_mag = self.plot_mag_var.get()
            show_phase = self.plot_phase_var.get()
            rows = (1 if show_mag else 0) + (1 if show_phase else 0)
            if rows == 0:
                show_mag = True
                rows = 1

            overlay_mode = self.overlay_charts_var.get()

            if overlay_mode:
                # One mag and optionally one phase subplot
                if show_mag and show_phase:
                    ax_mag, ax_phase = self.figure.subplots(2, 1)
                elif show_mag:
                    ax_mag = self.figure.add_subplot(111)
                    ax_phase = None
                else:
                    ax_mag = None
                    ax_phase = self.figure.add_subplot(111)

                for name, mag_vals, phase_vals in selected_params:
                    if show_mag and ax_mag is not None:
                        ax_mag.plot(freq/1e9, mag_vals, label=name)
                    if show_phase and ax_phase is not None:
                        ax_phase.plot(freq/1e9, phase_vals, label=name)

                if show_mag and ax_mag is not None:
                    ax_mag.set_xlabel('Frequency (GHz)')
                    ax_mag.set_ylabel('Magnitude (dB)')
                    ax_mag.set_title('Magnitude (Overlay)')
                    ax_mag.grid(True)
                    ax_mag.legend()
                if show_phase and ax_phase is not None:
                    ax_phase.set_xlabel('Frequency (GHz)')
                    ax_phase.set_ylabel('Phase (degrees)')
                    ax_phase.set_title('Phase (Overlay)')
                    ax_phase.grid(True)
                    ax_phase.legend()
            else:
                # Non-overlay: 1 or 2 rows, N cols = selected params
                ncols = len(selected_params)
                if rows == 2:
                    axes = self.figure.subplots(2, ncols)
                    if ncols == 1:
                        axes = np.array([[axes[0]], [axes[1]]])
                else:
                    row_axes = self.figure.subplots(1, ncols)
                    if ncols == 1:
                        row_axes = [row_axes]
                    axes = np.array([row_axes])

                for idx, (name, mag_vals, phase_vals) in enumerate(selected_params):
                    if show_mag:
                        ax_mag = axes[0, idx]
                        ax_mag.plot(freq/1e9, mag_vals, label=name)
                        ax_mag.set_xlabel('Frequency (GHz)')
                        ax_mag.set_ylabel('Magnitude (dB)')
                        ax_mag.set_title(f'{name} Magnitude')
                        ax_mag.grid(True)
                        ax_mag.legend()
                    if show_phase:
                        ax_phase = axes[0 if rows == 1 else 1, idx]
                        ax_phase.plot(freq/1e9, phase_vals, label=name)
                        ax_phase.set_xlabel('Frequency (GHz)')
                        ax_phase.set_ylabel('Phase (degrees)')
                        ax_phase.set_title(f'{name} Phase')
                        ax_phase.grid(True)
                        ax_phase.legend()

        # Adjust layout and redraw
        self.figure.tight_layout()
        self.canvas.draw()
        
    def load_sparam_file(self, file_path):
        """Load and display the selected S-parameter file"""
        try:
            print(f"\n=== Loading S-parameter file: {file_path} ===")  # Debug print
            
            # Try scikit-rf first (handles .s2p/.s4p robustly)
            freq = None
            s_params = None
            try:
                net = rf.Network(os.path.normpath(file_path))
                # Ensure we have data
                if hasattr(net, 'f') and hasattr(net, 's') and net.s is not None:
                    freq = net.f  # Hz
                    s_params = net.s  # shape: (nf, n, n)
            except Exception as e:
                print(f"Native loader failed, trying custom parser: {e}")
                # Fallback to custom parser (supports simple 2-port RI format)
                freq, s_params = self.parse_sparam_file(file_path)
            
            if freq is not None and s_params is not None:
                # Plot the S-parameters using detected port count
                try:
                    n_ports = int(s_params.shape[1]) if hasattr(s_params, 'shape') and len(s_params.shape) >= 3 else 2
                except Exception:
                    n_ports = 2
                self.plot_sparam(freq, s_params, n_ports)
                
                # Store current file path
                self.current_file = file_path
                
                # Update window title
                self.title(f"S-Parameter Browser - {os.path.basename(file_path)}")
                # Clear status warning if any
                if hasattr(self, 'td_status') and self.td_status is not None:
                    try:
                        self.td_status.config(text="", foreground='black')
                    except Exception:
                        pass
                # Update Sij spinbox ranges to current port count
                try:
                    if hasattr(self, 'sij_i_spin'):
                        self.sij_i_spin.config(to=n_ports)
                    if hasattr(self, 'sij_j_spin'):
                        self.sij_j_spin.config(to=n_ports)
                except Exception:
                    pass
                # Update history dropdown for this file
                try:
                    self.update_sij_history_combobox()
                except Exception:
                    pass
            else:
                messagebox.showerror("Error", "Failed to parse S-parameter file")
                
        except Exception as e:
            print(f"Error loading S-parameter file: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load S-parameter file:\n{str(e)}")

    def setup_toolbar(self):
        """Setup the toolbar with necessary controls"""
        ttk.Button(self.toolbar, text="Browse Folder", command=self.browse_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Load Subfolders", command=self.load_subfolders).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="Refresh", command=self.refresh_file_list).pack(side=tk.RIGHT, padx=2)
        ttk.Button(self.toolbar, text="Fullscreen Plot", command=self.toggle_plot_fullscreen).pack(side=tk.RIGHT, padx=2)

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

        
        # Add 2x to 1x conversion menu button
        self.conversion_button = ttk.Menubutton(self.toolbar, text="Convert 2x → 1x")
        self.conversion_button.pack(side="left", padx=2)
        
        self.conversion_menu = tk.Menu(self.conversion_button, tearoff=0)
        self.conversion_button["menu"] = self.conversion_menu
        
        self.conversion_menu.add_command(
            label="ABCD Matrix Method",
            command=lambda: self.convert_2x_to_1x_sparam(method='abcd'))
        self.conversion_menu.add_command(
            label="对称网络假设法 (Symmetric Network)",
            command=lambda: self.convert_2x_to_1x_sparam(method='symmetric'))
        
        # # Add filter controls
        # ttk.Label(self.toolbar, text="Filter:").pack(side="left", padx=2)
        # self.filter_entry = ttk.Entry(self.toolbar, textvariable=self.filter_text)
        # self.filter_entry.pack(side="left", padx=2)
        
        # # Add include subfolders checkbox
        # ttk.Checkbutton(self.toolbar, text="Include Subfolders", 
        #                variable=self.include_subfolders,
        #                command=self.update_file_list).pack(side="left", padx=2)
        
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
            # Use the displayed DataFrame (filtered) instead of the original DataFrame
            displayed_df = self.table.model.df
            for row in selected_rows:
                if row < len(displayed_df):
                    filename = displayed_df.iloc[row]['Name']
                    src_path = displayed_df.iloc[row].get('File_Path', os.path.join(self.current_directory, filename))

                    try:
                        # Copy the file
                        shutil.copy2(src_path, dest_dir)  # copy2 preserves metadata
                        copied_files.append(filename)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to copy file {filename}:\n{str(e)}")

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
            # Use the displayed DataFrame (filtered) instead of the original DataFrame
            displayed_df = self.table.model.df
            for row in selected_rows:
                if row < len(displayed_df):
                    filename = displayed_df.iloc[row]['Name']
                    src_path = displayed_df.iloc[row].get('File_Path', os.path.join(self.current_directory, filename))
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
                self.table.model.df = displayed_df[~displayed_df['Name'].isin(moved_files)]
                self.table.redraw()
                
                # Update file list
                self.sparam_files = [f for f in self.sparam_files if os.path.basename(f) not in moved_files]
                
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
            # Use the displayed DataFrame (filtered) instead of the original DataFrame
            displayed_df = self.table.model.df
            for row in selected_rows:
                if row < len(displayed_df):
                    filename = displayed_df.iloc[row]['Name']
                    filepath = displayed_df.iloc[row].get('File_Path', os.path.join(self.current_directory, filename))

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
                self.table.model.df = displayed_df[~displayed_df['Name'].isin(deleted_files)]
                self.table.redraw()
                
                # Update file list
                self.sparam_files = [f for f in self.sparam_files if os.path.basename(f) not in deleted_files]
                
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

    def calculate_tdr(self, network=None, freq_limit=None):
        """Calculate Time Domain Reflectometry (TDR) response using MATLAB-style implementation
        
        Args:
            network: Network object with S-parameters (default: None, uses first network)
            freq_limit: Optional upper frequency limit in Hz (default: None, uses full range)
        """
        print(f"\n==== TDR Calculation (MATLAB-style) ====")
        print(f"Padding Factor: {self.padding_factor.get()}")
        print(f"Window Type: {self.window_type.get()}")
        if freq_limit:
            print(f"Frequency Limit: {freq_limit/1e9:.2f} GHz")

        if network is None:
            network = self.data[0]  # Use first network if none specified
        
        # Get frequency points and S-parameters
        f = network.f
        # Initialize SDD11 (or S11) complex array to use downstream
        sdd11_complex = None
        # Check if we have a 4-port network
        if network.s.shape[1] == 4:  # 4-port network
            # Extract the S-parameters we need
            # For a 4-port network with ports ordered as 1,2,3,4
            # where 1,3 are the input differential pair and 2,4 are the output differential pair
            # Sdd11 = (S11 - S13 - S31 + S33)/2
            s11 = network.s[:,0,0]  # S11
            s13 = network.s[:,0,2]  # S13
            s31 = network.s[:,2,0]  # S31
            s33 = network.s[:,2,2]  # S33
            # Calculate differential S-parameter Sdd11
            sdd11_complex = (s11 - s13 - s31 + s33) / 2.0
            print(f"Sdd11 (4-port) data shape: {sdd11_complex.shape}")
        else:
            # 2-port (or other) fallback: use S11 directly for TDR
            sdd11_complex = network.s[:, 0, 0]
            print(f"S11 (2-port) data shape: {sdd11_complex.shape}")
        
        # Apply frequency limit if specified
        if freq_limit is not None:
            if freq_limit < f[0]:
                raise ValueError(f"Frequency limit ({freq_limit/1e9:.2f} GHz) is below minimum frequency ({f[0]/1e9:.2f} GHz)")
            # Find indices where frequency is below limit
            freq_mask = f <= freq_limit
            f = f[freq_mask]
            sdd11_complex = sdd11_complex[freq_mask]
            print(f"Applied frequency limit: {len(freq_mask[freq_mask])} of {len(freq_mask)} points kept")
        
        # === Step 1: Preprocessing ===
        # First ensure we have DC (f=0) component
        if f[0] > 0:
            # Insert DC point by extrapolating from first few points
            f = np.insert(f, 0, 0)
            
            # Use complex extrapolation to preserve both magnitude and phase
            # Linear extrapolation: DC = 2*S(f1) - S(f2)
            dc_complex = 2*sdd11_complex[0] - sdd11_complex[1]
            
            # Apply physical constraints for passive network (|S| <= 1)
            dc_magnitude = np.abs(dc_complex)
            if dc_magnitude > 0.99:
                # Scale down to stay within physical bounds
                dc_complex = dc_complex * (0.99 / dc_magnitude)
            
            # For differential pairs, DC component should be real-dominated
            # but preserve some phase information for causality
            dc_real = np.clip(np.real(dc_complex), -0.99, 0.99)
            dc_imag = np.clip(np.imag(dc_complex), -0.1, 0.1)  # Small imaginary part
            dc_estimate = complex(dc_real, dc_imag)
            
            sdd11_complex = np.insert(sdd11_complex, 0, dc_estimate)
            print(f"Added DC point: {dc_estimate:.6f} (mag: {np.abs(dc_estimate):.6f}, phase: {np.angle(dc_estimate)*180/np.pi:.2f}°)")
        
        # === Step 2: Apply windowing ===
        # Use hamming window (more commonly used in MATLAB)
        # window = np.hamming(len(s11))
        # s11_windowed = s11 * window
        # print(f"Applied Hamming window")
        # Apply window function
        sdd11_complex_windowed = self.apply_window(sdd11_complex)
        
        # === Step 3: Padding with zeros ===
        pad_factor = int(self.padding_factor.get())
        n_orig = len(f)
        n_padded = n_orig * pad_factor
        print(f"Original points: {n_orig}, Padded points: {n_padded}")
        
        # Create padded arrays
        f_step = f[1] - f[0]
        f_padded = np.concatenate([f, np.linspace(f[-1] + f_step, f[-1] + f_step * (n_padded - n_orig), n_padded - n_orig)])
        sdd11_complex_padded = np.pad(sdd11_complex_windowed, (0, n_padded - n_orig), mode='constant')
        
        # === Step 4: Force Causality (MATLAB-style) ===
        # MATLAB ensures causality by making the response minimum phase
        # We can approximate this by ensuring the imaginary part has proper Hilbert transform relationship to real part
        sdd11_complex_real = np.real(sdd11_complex_padded)
        sdd11_complex_imag = np.imag(sdd11_complex_padded)
        
        # Filter higher frequencies (standard in MATLAB implementation)
        cutoff_idx = int(len(f_padded) * 0.8)  # Use 80% of bandwidth as in many MATLAB implementations
        for i in range(cutoff_idx, len(f_padded)):
            # Apply gentle roll-off
            roll_off = 0.5 * (1 + np.cos(np.pi * (i - cutoff_idx) / (len(f_padded) - cutoff_idx)))
            sdd11_complex_padded[i] *= roll_off
        
        # Create symmetric spectrum for real time-domain signal
        # Reverse and conjugate the array, excluding the first and last elements
        sdd11_complex_padded_sym = np.concatenate([sdd11_complex_padded, np.conj(sdd11_complex_padded[::-1][1:-1])])
        print(f"Symmetric spectrum shape: {sdd11_complex_padded_sym.shape}")

        # === Step 5: Compute time-domain response ===
        # Use IFFT for time domain conversion (standard approach)
        # tdr_raw = np.fft.ifft(s11_padded_sym)
        
        # Time-domain TDR (reflection) impulse response
        tdr_impulse = np.fft.ifft(sdd11_complex_padded_sym).real

        # Time axis (for plotting)
        n = len(sdd11_complex_padded_sym)
        # Correct time step calculation based on frequency span and number of points
        # For IFFT, the time step should be based on the frequency resolution
        df = (f_padded[-1] - f_padded[0]) / (len(f_padded) - 1)  # Frequency resolution
        dt = 1 / (2 * len(f_padded) * df)  # Correct time step for IFFT
        # Alternative: dt = 1 / (2 * (f_padded[-1] - f_padded[0]))  # Based on frequency span
        t = np.linspace(0, dt * (n - 1), n)

        # Fix causality: minimize rotation to avoid negative time responses
        # Use small rotation only if needed for peak alignment
        rotate_size = round(0.05e-9/dt)  # Much smaller rotation (0.05ns vs 1ns)
        rotate_size = max(0, min(rotate_size, len(t)//10))  # Limit to 10% of array length
        
        # Ensure causality: don't shift into negative time
        if rotate_size * dt > t[len(t)//4]:  # If rotation > 25% of time span
            rotate_size = 0  # Disable rotation to preserve causality
            print(f"Rotation disabled to preserve causality (would shift by {rotate_size*dt:.3f}ns)")
        
        t_rotate = t - rotate_size*dt
        tdr_impulse_rotate = np.roll(tdr_impulse, rotate_size)
        print(f"Applied rotation: {rotate_size} samples ({rotate_size*dt:.3f}ns)")

        # Enforce causality: zero out any response before t=0
        causal_mask = t_rotate >= 0
        tdr_impulse_causal = tdr_impulse_rotate.copy()
        tdr_impulse_causal[~causal_mask] = 0  # Zero out negative time responses
        
        # Count and report causality violations
        violations = np.sum(~causal_mask)
        if violations > 0:
            print(f"Causality enforced: zeroed {violations} samples at negative time")
        
        # Calculate step response (integral of impulse response)
        tdr_step = np.cumsum(tdr_impulse_causal)


        # === Step 6: Calculate distance ===
        c0 = 299792458  # Speed of light in vacuum (m/s)
        # Get velocity factor from user input (with fallback to default)
        try:
            v_rel = float(self.velocity_factor.get())
            if v_rel <= 0 or v_rel > 1:
                print(f"Warning: Invalid velocity factor {v_rel}, using default 0.5")
                v_rel = 0.5
        except (ValueError, AttributeError):
            print("Warning: Could not read velocity factor, using default 0.5")
            v_rel = 0.5
        
        c = c0 * v_rel  # Propagation velocity in material
        print(f"Using velocity factor: {v_rel} (v = {v_rel*100:.1f}% of c)")
        
        distance_step = c * dt / 2  # Divide by 2 for round-trip
        # Create distance array with the same length as the time array
        # Use the actual length of the final TDR result for consistency
        distance = np.arange(n) * distance_step * 39.3701  # Convert meters to inches (1m = 39.3701 inches)
        
        print(f"Time step: {dt*1e9:.2f} ns")
        print(f"Distance step: {distance_step*39.3701:.4f} inch")
        print(f"Max distance: {distance[-1]:.2f} inch")
        
        # === Step 7: Time-domain gating (commonly used in MATLAB) ===
        # Apply time-domain gating to remove unwanted reflections
        # Focus only on first 20% of the time domain response
        # gate_length = int(len(tdr_step) * 0.2)
        # gate = np.ones(len(tdr_step))
        
        # # Apply cosine rolloff from cutoff to end
        # for i in range(gate_length, len(tdr_step)):
        #     # Cosine taper from 1 to 0
        #     gate[i] = 0.5 * (1 + np.cos(np.pi * (i - gate_length) / gate_length))
        
        # tdr_gated = tdr_step * gate
        tdr_gated = tdr_step

        # === Step 8: Extract real part and process for display ===
        # tdr_real = np.real(tdr_gated)
        
        # # Center around mean value (like PLTS)
        # baseline = np.mean(tdr_real)
        # tdr_centered = tdr_real - baseline
        # print(f"Baseline value (mean): {baseline:.4f}")
        tdr_centered = tdr_gated

        # Convert to milli-units
        tdr_mU = tdr_centered * 1000
        
        # Apply smoothing to reduce noise (common in MATLAB)
        # from scipy.ndimage import gaussian_filter1d
        # tdr_smooth = gaussian_filter1d(tdr_mU, sigma=1.0)
        tdr_smooth = tdr_mU
        
        # === Step 9: Apply non-linear emphasis ===
        # Apply non-linear emphasis to enhance visibility
        # tdr_abs = np.abs(tdr_smooth)
        # tdr_sign = np.sign(tdr_smooth)
        
        # # More standard MATLAB-like emphasis approach
        # emphasis_factor = 5.0
        # # Square root emphasis (commonly used in RF applications)
        # tdr_emphasized = tdr_sign * emphasis_factor * np.sqrt(tdr_abs)
        
        # # Final light smoothing
        # tdr_final = gaussian_filter1d(tdr_emphasized, sigma=0.5)
        tdr_final = tdr_smooth

        # Print statistics
        tdr_min = np.min(tdr_final)
        tdr_max = np.max(tdr_final)
        tdr_mean = np.mean(tdr_final)
        tdr_abs_max = np.max(np.abs(tdr_final))
        
        print("=== TDR Results ===")
        print(f"  Min: {tdr_min:.2f}mU, Max: {tdr_max:.2f}mU, Mean: {tdr_mean:.2f}mU, Abs Max: {tdr_abs_max:.2f}mU")
        print(f"  Number of samples: {len(tdr_final)}")
        
        # Return only causal time values (t >= 0) to prevent causality violations in plots
        causal_indices = t_rotate >= 0
        t_causal = t_rotate[causal_indices] * 1e9  # Convert to nanoseconds
        distance_causal = distance[causal_indices]
        tdr_causal = tdr_final[causal_indices]
        
        print(f"Returning {len(t_causal)} causal samples (removed {len(t_rotate) - len(t_causal)} negative time samples)")
        
        return t_causal, distance_causal, tdr_causal

    def calculate_pulse_response(self, network=None, use_iczt=False):
        """Calculate pulse response with enhanced resolution
        
        Args:
            network: Network object with S-parameters (default: None, uses first network)
            use_iczt: Whether to use Inverse Chirp Z-Transform instead of IFFT (default: True)
                    ICZT provides higher resolution but is computationally more expensive
        """
        if network is None:
            network = self.data[0]  # Use first network if none specified
            
        # Get frequency points and S-parameters
        f = network.f
        # s11 = network.s[:, 0, 0]  # Get S11 parameter
        # Check if we have a 4-port network
        if network.s.shape[1] == 4:  # 4-port network
            # Extract the S-parameters we need
            # For a 4-port network with ports ordered as 1,2,3,4
            # where 1,3 are the input differential pair and 2,4 are the output differential pair
            # Sdd11 = (S11 - S13 - S31 + S33)/2
            
            # Get the individual S-parameters
            s11 = network.s[:,0,0]  # S11
            s13 = network.s[:,0,2]  # S13
            s31 = network.s[:,2,0]  # S31
            s33 = network.s[:,2,2]  # S33
            
            # Calculate differential S-parameter Sdd11
            sdd11_complex = (s11 - s13 - s31 + s33) / 2.0
            print(f"Sdd11 data shape: {sdd11_complex.shape}")
        
        # Apply window function
        sdd11_complex_windowed = self.apply_window(sdd11_complex)
        
        if use_iczt:
            # Use ICZT method for higher resolution and control
            print("Using ICZT method for pulse response calculation...")
            
            # Calculate appropriate time range based on frequency range
            t_max = 1 / (f[1] - f[0])  # Maximum time from frequency spacing
            
            # Number of points based on padding factor
            pad_factor = int(self.padding_factor.get())
            num_points = len(f) * pad_factor
            
            # Calculate pulse response using ICZT
            t, pulse = calculate_tdr_iczt(f, sdd11_complex_windowed, 0, t_max/2, num_points)
            
            # Print pulse response diagnostics
            print(f"ICZT pulse response diagnostics:")
            print(f"  Time range: {t[0]*1e9:.1f} to {t[-1]*1e9:.1f} ns")
            print(f"  Time resolution: {(t[1]-t[0])*1e9:.3f} ns")
            print(f"  Number of points: {len(t)}")
            
            # Normalize and enhance pulse response
            pulse_mag = np.abs(pulse)
            max_val = np.max(pulse_mag)
            
            if max_val > 0 and max_val != 1.0:
                # Normalize to unity amplitude
                pulse = pulse / max_val
                print(f"  Normalized pulse to unity amplitude")
                
            # Convert time to picoseconds for easier reading
            t_ns = t * 1e9
            
            return t_ns, pulse
        else:        
                    
            # Zero padding
            pad_factor = int(self.padding_factor.get())
            n_orig = len(f)
            n_padded = n_orig * pad_factor
            
            # Pad the frequency domain data
            sdd11_complex_padded = np.pad(sdd11_complex_windowed, (0, n_padded - n_orig), mode='constant')
            
            # Create padded frequency array
            f_step = f[1] - f[0]  # Original frequency step
            f_padded = np.linspace(f[0], f[0] + f_step * (n_padded - 1), n_padded)
            
            # Create Gaussian pulse in frequency domain
            sigma = 0.1 / (2 * np.pi * f_padded[-1])  # Adjust pulse width
            gauss = np.exp(-0.5 * (f_padded * sigma)**2)
            
            # Multiply with S-parameters and transform to time domain
            pulse = np.fft.ifft(sdd11_complex_padded * gauss)
            
            # Calculate time array
            dt = 1 / (2 * f_padded[-1])  # Time step
            t = np.arange(n_padded) * dt  # Initial time array, may be updated later
            
            # Normalize and enhance pulse response for better visualization

            pulse_mag = np.abs(pulse)

            max_val = np.max(pulse_mag)

            

            # Print pulse response diagnostics

            print(f"Pulse response diagnostics:")

            print(f"  Max amplitude: {max_val:.6f}")

            print(f"  Time range: {t[0]*1e9:.1f} to {t[-1]*1e9:.1f} ns")

            print(f"  Time step: {(t[1]-t[0])*1e9:.3f} ns")

            

            # Check if normalization is needed

            if max_val > 0 and max_val != 1.0:

                # Normalize to unity amplitude

                pulse = pulse / max_val

                print(f"  Normalized pulse to unity amplitude")

            

            # Convert time to picoseconds for easier reading

            t_ns = t * 1e9  # Convert to picoseconds

            

            return t_ns, pulse
    
    def calculate_s21_pulse_response(self, network=None, use_iczt=False):
        """Calculate pulse response with enhanced resolution
        
        Args:
            network: Network object with S-parameters (default: None, uses first network)
            use_iczt: Whether to use Inverse Chirp Z-Transform instead of IFFT (default: False)
                    ICZT provides higher resolution but is computationally more expensive
        """
        if network is None:
            network = self.data[0]  # Use first network if none specified
            
        # Get frequency points and S-parameters
        f = network.f
        s21 = network.s[:, 1, 0]  # Get S21 parameter
        
        # Apply window function
        s21_windowed = self.apply_window(s21)
        
        if use_iczt:
            # Use ICZT method for higher resolution and control
            print("Using ICZT method for pulse response calculation...")
            
            # Calculate appropriate time range based on frequency range
            t_max = 1 / (f[1] - f[0])  # Maximum time from frequency spacing
            
            # Number of points based on padding factor
            pad_factor = int(self.padding_factor.get())
            num_points = len(f) * pad_factor
            
            # Calculate pulse response using ICZT
            t, pulse = calculate_tdr_iczt(f, s21_windowed, 0, t_max/2, num_points)
            
            # Print pulse response diagnostics
            print(f"ICZT pulse response diagnostics:")
            print(f"  Time range: {t[0]*1e9:.1f} to {t[-1]*1e9:.1f} ns")
            print(f"  Time resolution: {(t[1]-t[0])*1e9:.3f} ns")
            print(f"  Number of points: {len(t)}")
            
            # Normalize and enhance pulse response
            pulse_mag = np.abs(pulse)
            max_val = np.max(pulse_mag)
            
            if max_val > 0 and max_val != 1.0:
                # Normalize to unity amplitude
                pulse = pulse / max_val
                print(f"  Normalized pulse to unity amplitude")
                
            # Convert time to picoseconds for easier reading
            t_ns = t * 1e9
            
            return t_ns, pulse
        else:        
                    
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

            print(f"  Time range: {t[0]*1e9:.1f} to {t[-1]*1e9:.1f} ns")

            print(f"  Time step: {(t[1]-t[0])*1e9:.3f} ns")

            

            # Check if normalization is needed

            if max_val > 0 and max_val != 1.0:

                # Normalize to unity amplitude

                pulse = pulse / max_val

                print(f"  Normalized pulse to unity amplitude")

            

            # Convert time to picoseconds for easier reading

            t_ns = t * 1e9  # Convert to picoseconds

            

            return t_ns, pulse

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
            cutoff_idx = n*2 // 3  # Cut off at 1/3 of the frequency range
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
            # Initialize overlay-related variables to avoid UnboundLocalError in non-frequency modes
            overlay_mode = self.overlay_charts_var.get() if hasattr(self, 'overlay_charts_var') else False
            ax_mag = None
            ax_phase = None

            # Check if time domain plots are enabled
            show_tdr = self.show_tdr_var.get()
            show_pulse = self.show_pulse_var.get()
            show_impedance = self.show_impedance_var.get()
            show_impedance_time = self.show_impedance_time_var.get()
            
            # Get frequency limit if specified
            try:
                freq_limit = float(self.freq_limit.get()) * 1e9 if self.freq_limit.get() else None
            except ValueError:
                freq_limit = None
            
            if show_tdr or show_pulse or show_impedance or show_impedance_time:
                # Count active plots
                active_plots = sum([show_tdr, show_pulse, show_impedance, show_impedance_time])
                
                if active_plots == 4:
                    # Create four subplots
                    ax_tdr = self.figure.add_subplot(221)
                    ax_pulse = self.figure.add_subplot(222)
                    ax_imp = self.figure.add_subplot(223)
                    ax_imp_time = self.figure.add_subplot(224)
                elif active_plots == 3:
                    # Create three subplots
                    if show_tdr and show_pulse and show_impedance:
                        ax_tdr = self.figure.add_subplot(131)
                        ax_pulse = self.figure.add_subplot(132)
                        ax_imp = self.figure.add_subplot(133)
                    elif show_tdr and show_pulse and show_impedance_time:
                        ax_tdr = self.figure.add_subplot(131)
                        ax_pulse = self.figure.add_subplot(132)
                        ax_imp_time = self.figure.add_subplot(133)
                    elif show_tdr and show_impedance and show_impedance_time:
                        ax_tdr = self.figure.add_subplot(131)
                        ax_imp = self.figure.add_subplot(132)
                        ax_imp_time = self.figure.add_subplot(133)
                    elif show_pulse and show_impedance and show_impedance_time:
                        ax_pulse = self.figure.add_subplot(131)
                        ax_imp = self.figure.add_subplot(132)
                        ax_imp_time = self.figure.add_subplot(133)
                elif active_plots == 2:
                    # Create two subplots
                    if show_tdr and show_pulse:
                        ax_tdr = self.figure.add_subplot(121)
                        ax_pulse = self.figure.add_subplot(122)
                    elif show_tdr and show_impedance:
                        ax_tdr = self.figure.add_subplot(121)
                        ax_imp = self.figure.add_subplot(122)
                    elif show_tdr and show_impedance_time:
                        ax_tdr = self.figure.add_subplot(121)
                        ax_imp_time = self.figure.add_subplot(122)
                    elif show_pulse and show_impedance:
                        ax_pulse = self.figure.add_subplot(121)
                        ax_imp = self.figure.add_subplot(122)
                    elif show_pulse and show_impedance_time:
                        ax_pulse = self.figure.add_subplot(121)
                        ax_imp_time = self.figure.add_subplot(122)
                    elif show_impedance and show_impedance_time:
                        ax_imp = self.figure.add_subplot(121)
                        ax_imp_time = self.figure.add_subplot(122)
                else:
                    # Create single plot
                    ax = self.figure.add_subplot(111)
                
                for i, net in enumerate(networks):
                    label = f'Net{i+1}' if len(net.name) == 0 else net.name
                    
                    if show_tdr:
                        t_ns, distance, tdr = self.calculate_tdr(net, freq_limit=freq_limit)
                        if active_plots > 1:
                            ax_plot = ax_tdr
                        else:
                            ax_plot = ax
                        # Use PLTS-style plotting
                        self.plot_tdr_and_impedance(ax_plot, t_ns, tdr, label)
                    
                    if show_pulse:
                        time, pulse = self.calculate_pulse_response(net)
                        if active_plots > 1:
                            ax_plot = ax_pulse
                        else:
                            ax_plot = ax
                        # Plot magnitude of pulse response
                        ax_plot.plot(time, np.abs(pulse), label=label)
                        ax_plot.set_xlabel('Time (ns)')
                        ax_plot.set_ylabel('Amplitude')
                        ax_plot.set_title('Pulse Response')
                        # Set appropriate y-axis formatting
                        ax_plot.ticklabel_format(axis='y', style='plain', useOffset=False)
                        ax_plot.grid(True)
                        ax_plot.legend(loc='upper right')
                    
                    if show_impedance:
                        t_ns, distance, tdr = self.calculate_tdr(net, freq_limit=freq_limit)

                        impedance = self.calculate_impedance_profile(tdr)
                        if active_plots > 1:
                            ax_plot = ax_imp
                        else:
                            ax_plot = ax
                        # Plot impedance vs. distance
                        ax_plot.plot(distance, np.real(impedance), label=label)
                        ax_plot.set_xlabel('Distance (inch)')
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
                        
                        # Add reference line at Z0=100Ω
                        ax_plot.axhline(y=100, color='r', linestyle='--', alpha=0.5, label='Z0=100Ω')
                        ax_plot.legend(loc='upper right')
                    
                    if show_impedance_time:
                        t_ns, distance, tdr = self.calculate_tdr(net, freq_limit=freq_limit)

                        impedance = self.calculate_impedance_profile(tdr)
                        if active_plots > 1:
                            ax_plot = ax_imp_time
                        else:
                            ax_plot = ax
                        # Plot impedance vs. time
                        ax_plot.plot(t_ns, np.real(impedance), label=label)
                        ax_plot.set_xlabel('Time (ns)')
                        ax_plot.set_ylabel('Impedance (Ω)')
                        ax_plot.set_title('Impedance Profile vs Time')
                        # Explicitly set y-axis limits to avoid scientific notation
                        y_min = max(10, np.min(np.real(impedance)))
                        y_max = min(200, np.max(np.real(impedance)))
                        # Set reasonable limits with some margin
                        margin = (y_max - y_min) * 0.1
                        ax_plot.set_ylim([y_min - margin, y_max + margin])
                        # Use simple, non-scientific notation for y-axis
                        ax_plot.ticklabel_format(axis='y', style='plain', useOffset=False)
                        ax_plot.grid(True)
                        
                        # Add reference line at Z0=100Ω
                        ax_plot.axhline(y=100, color='r', linestyle='--', alpha=0.5, label='Z0=100Ω')
                        ax_plot.legend(loc='upper right')
                
            else:
                # Original frequency domain plotting code continues here...
                # Determine which parameters to show
                show_sdd11 = self.plot_sdd11_var.get()
                show_sdd21 = self.plot_sdd21_var.get()
                show_s11 = self.plot_s11_var.get()
                show_s21 = self.plot_s21_var.get()
                show_s33 = self.plot_s33_var.get()
                show_s43 = self.plot_s43_var.get()
                show_spec = self.show_spec_var.get() and bool(self.spec_data)
                overlay_mode = self.overlay_charts_var.get()
                
                # Count how many subplots we need
                n_plots = 0
                if show_mag:
                    n_plots += (show_sdd11 + show_sdd21 + show_s11 + show_s21 + show_s33 + show_s43)
                if show_phase:
                    n_plots += (show_sdd11 + show_sdd21 + show_s11 + show_s21 + show_s33 + show_s43)
                    
                if n_plots == 0:
                    return  # Nothing to plot
                
                if overlay_mode:
                    # Overlay mode: one magnitude axis and one phase axis
                    if show_mag and show_phase:
                        ax_mag, ax_phase = self.figure.subplots(2, 1)
                    elif show_mag:
                        ax_mag = self.figure.add_subplot(111)
                        ax_phase = None
                    else:
                        ax_mag = None
                        ax_phase = self.figure.add_subplot(111)
                else:
                    # Create subplots based on what's shown
                    if n_plots <= 4:
                        if n_plots == 1:
                            axes = [self.figure.add_subplot(111)]
                        elif n_plots == 2:
                            axes = list(self.figure.subplots(1, 2))
                        elif n_plots == 3:
                            gs = self.figure.add_gridspec(2, 2)
                            axes = [
                                self.figure.add_subplot(gs[0, 0]),
                                self.figure.add_subplot(gs[0, 1]),
                                self.figure.add_subplot(gs[1, 0:])
                            ]
                        else:  # n_plots == 4
                            grid_axes = self.figure.subplots(2, 2)
                            axes = [ax for row in grid_axes for ax in row]  # Flatten 2D array
                    else:
                        # For >4 plots, create a 2-row grid with enough columns
                        import math
                        ncols = math.ceil(n_plots / 2)
                        grid_axes = self.figure.subplots(2, ncols)
                        # Ensure grid_axes is 2D
                        if ncols == 1:
                            grid_axes = np.array([[grid_axes[0]], [grid_axes[1]]])
                        axes = [ax for row in grid_axes for ax in row]
                
                # Clear marker text box
                if self.marker_text:
                    self.marker_text.delete(1.0, tk.END)
                
                # Keep track of which axis is for what
                ax_map = {}
                ax_idx = 0
                
                if not overlay_mode:
                    # Map magnitude axes first (row 1), then phase axes (row 2), in order
                    if show_mag:
                        if show_sdd11:
                            ax_map['sdd11_mag'] = axes[ax_idx]; ax_idx += 1
                        if show_sdd21:
                            ax_map['sdd21_mag'] = axes[ax_idx]; ax_idx += 1
                        if show_s11:
                            ax_map['s11_mag'] = axes[ax_idx]; ax_idx += 1
                        if show_s21:
                            ax_map['s21_mag'] = axes[ax_idx]; ax_idx += 1
                        if show_s33:
                            ax_map['s33_mag'] = axes[ax_idx]; ax_idx += 1
                        if show_s43:
                            ax_map['s43_mag'] = axes[ax_idx]; ax_idx += 1
                    if show_phase:
                        if show_sdd11:
                            ax_map['sdd11_phase'] = axes[ax_idx]; ax_idx += 1
                        if show_sdd21:
                            ax_map['sdd21_phase'] = axes[ax_idx]; ax_idx += 1
                        if show_s11:
                            ax_map['s11_phase'] = axes[ax_idx]; ax_idx += 1
                        if show_s21:
                            ax_map['s21_phase'] = axes[ax_idx]; ax_idx += 1
                        if show_s33:
                            ax_map['s33_phase'] = axes[ax_idx]; ax_idx += 1
                        if show_s43:
                            ax_map['s43_phase'] = axes[ax_idx]; ax_idx += 1
                
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
                    if overlay_mode:
                        # Overlay onto shared axes with descriptive labels
                        if show_mag and ax_mag is not None:
                            if show_sdd11:
                                ax_mag.plot(net.f/1e9, 20*np.log10(np.abs(sdd[:, 0, 0])), label=f"{label} SDD11")
                            if show_sdd21:
                                ax_mag.plot(net.f/1e9, 20*np.log10(np.abs(sdd[:, 1, 0])), label=f"{label} SDD21")
                            if show_s11:
                                s11_vals = 20*np.log10(np.abs(net.s[:, 0, 0]))
                                ax_mag.plot(net.f/1e9, s11_vals, label=f"{label} S11")
                            if show_s21:
                                s21_vals = 20*np.log10(np.abs(net.s[:, 1, 0]))
                                ax_mag.plot(net.f/1e9, s21_vals, label=f"{label} S21")
                            if show_s33:
                                if net.s.shape[1] >= 3:
                                    s33_vals = 20*np.log10(np.abs(net.s[:, 2, 2]))
                                    ax_mag.plot(net.f/1e9, s33_vals, label=f"{label} S33")
                                else:
                                    if hasattr(self, 'td_status'):
                                        self.td_status.config(text="S33 not available for this network", foreground='orange')
                            if show_s43:
                                if net.s.shape[1] >= 4:
                                    s43_vals = 20*np.log10(np.abs(net.s[:, 3, 2]))
                                    ax_mag.plot(net.f/1e9, s43_vals, label=f"{label} S43")
                                else:
                                    if hasattr(self, 'td_status'):
                                        self.td_status.config(text="S43 not available for this network", foreground='orange')
                            # Custom Sij
                            if getattr(self, 'custom_sij', None):
                                for (ii, jj) in self.custom_sij:
                                    if 1 <= ii <= net.s.shape[1] and 1 <= jj <= net.s.shape[2]:
                                        vals = 20*np.log10(np.abs(net.s[:, ii-1, jj-1]))
                                        ax_mag.plot(net.f/1e9, vals, label=f"{label} S{ii}{jj}")
                                    else:
                                        if hasattr(self, 'td_status'):
                                            self.td_status.config(text=f"S{ii}{jj} not available for this network", foreground='orange')
                        if show_phase and ax_phase is not None:
                            if show_sdd11:
                                ax_phase.plot(net.f/1e9, np.angle(sdd[:, 0, 0], deg=True), label=f"{label} SDD11")
                            if show_sdd21:
                                ax_phase.plot(net.f/1e9, np.angle(sdd[:, 1, 0], deg=True), label=f"{label} SDD21")
                            if show_s11:
                                s11_phase_vals = np.angle(net.s[:, 0, 0], deg=True)
                                ax_phase.plot(net.f/1e9, s11_phase_vals, label=f"{label} S11")
                            if show_s21:
                                s21_phase_vals = np.angle(net.s[:, 1, 0], deg=True)
                                ax_phase.plot(net.f/1e9, s21_phase_vals, label=f"{label} S21")
                            if show_s33:
                                if net.s.shape[1] >= 3:
                                    s33_phase_vals = np.angle(net.s[:, 2, 2], deg=True)
                                    ax_phase.plot(net.f/1e9, s33_phase_vals, label=f"{label} S33")
                            if show_s43:
                                if net.s.shape[1] >= 4:
                                    s43_phase_vals = np.angle(net.s[:, 3, 2], deg=True)
                                    ax_phase.plot(net.f/1e9, s43_phase_vals, label=f"{label} S43")
                            if getattr(self, 'custom_sij', None):
                                for (ii, jj) in self.custom_sij:
                                    if 1 <= ii <= net.s.shape[1] and 1 <= jj <= net.s.shape[2]:
                                        phase_vals = np.angle(net.s[:, ii-1, jj-1], deg=True)
                                        ax_phase.plot(net.f/1e9, phase_vals, label=f"{label} S{ii}{jj}")
                    else:
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
                            
                            if show_s11:
                                ax = ax_map['s11_mag']
                                s11_vals = 20*np.log10(np.abs(net.s[:, 0, 0]))
                                ax.plot(net.f/1e9, s11_vals, label=label)
                                ax.set_xlabel('Frequency (GHz)')
                                ax.set_ylabel('Magnitude (dB)')
                                ax.set_title('S11 Magnitude')
                                ax.grid(True)
                                ax.legend()
                            
                            if show_s21:
                                ax = ax_map['s21_mag']
                                s21_vals = 20*np.log10(np.abs(net.s[:, 1, 0]))
                                ax.plot(net.f/1e9, s21_vals, label=label)
                                ax.set_xlabel('Frequency (GHz)')
                                ax.set_ylabel('Magnitude (dB)')
                                ax.set_title('S21 Magnitude')
                                ax.grid(True)
                                ax.legend()
                            
                            if show_s33 and 's33_mag' in ax_map:
                                if net.s.shape[1] >= 3:
                                    ax = ax_map['s33_mag']
                                    s33_vals = 20*np.log10(np.abs(net.s[:, 2, 2]))
                                    ax.plot(net.f/1e9, s33_vals, label=label)
                                    ax.set_xlabel('Frequency (GHz)')
                                    ax.set_ylabel('Magnitude (dB)')
                                    ax.set_title('S33 Magnitude')
                                    ax.grid(True)
                                    ax.legend()
                                else:
                                    if hasattr(self, 'td_status'):
                                        self.td_status.config(text="S33 not available for this network", foreground='orange')
                            if show_s43 and 's43_mag' in ax_map:
                                if net.s.shape[1] >= 4:
                                    ax = ax_map['s43_mag']
                                    s43_vals = 20*np.log10(np.abs(net.s[:, 3, 2]))
                                    ax.plot(net.f/1e9, s43_vals, label=label)
                                    ax.set_xlabel('Frequency (GHz)')
                                    ax.set_ylabel('Magnitude (dB)')
                                    ax.set_title('S43 Magnitude')
                                    ax.grid(True)
                                    ax.legend()
                                else:
                                    if hasattr(self, 'td_status'):
                                        self.td_status.config(text="S43 not available for this network", foreground='orange')
                            # Custom Sij magnitude
                            if getattr(self, 'custom_sij', None):
                                for (ii, jj) in self.custom_sij:
                                    if 1 <= ii <= net.s.shape[1] and 1 <= jj <= net.s.shape[2]:
                                        ax = axes[0] if 'axes' in locals() else ax
                                        vals = 20*np.log10(np.abs(net.s[:, ii-1, jj-1]))
                                        # Choose a reasonable axis: if only one mag axis, use it; else create temp on first mag axis
                                        target_ax = ax_map.get(f's{ii}{jj}_mag') if f's{ii}{jj}_mag' in ax_map else None
                                        if target_ax is None:
                                            # If we didn't pre-allocate, put on the last used magnitude axis for simplicity
                                            target_ax = ax
                                        target_ax.plot(net.f/1e9, vals, label=f"{label} S{ii}{jj}")
                                        target_ax.set_xlabel('Frequency (GHz)')
                                        target_ax.set_ylabel('Magnitude (dB)')
                                        target_ax.set_title(f'S{ii}{jj} Magnitude')
                                        target_ax.grid(True)
                                        target_ax.legend()
                        
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
                            
                            if show_s11:
                                ax = ax_map['s11_phase']
                                s11_phase_vals = np.angle(net.s[:, 0, 0], deg=True)
                                ax.plot(net.f/1e9, s11_phase_vals, label=label)
                                ax.set_xlabel('Frequency (GHz)')
                                ax.set_ylabel('Phase (degrees)')
                                ax.set_title('S11 Phase')
                                ax.grid(True)
                                ax.legend()
                            
                            if show_s21:
                                ax = ax_map['s21_phase']
                                s21_phase_vals = np.angle(net.s[:, 1, 0], deg=True)
                                ax.plot(net.f/1e9, s21_phase_vals, label=label)
                                ax.set_xlabel('Frequency (GHz)')
                                ax.set_ylabel('Phase (degrees)')
                                ax.set_title('S21 Phase')
                                ax.grid(True)
                                ax.legend()
                            
                            if show_s33 and 's33_phase' in ax_map and net.s.shape[1] >= 3:
                                ax = ax_map['s33_phase']
                                s33_phase_vals = np.angle(net.s[:, 2, 2], deg=True)
                                ax.plot(net.f/1e9, s33_phase_vals, label=label)
                                ax.set_xlabel('Frequency (GHz)')
                                ax.set_ylabel('Phase (degrees)')
                                ax.set_title('S33 Phase')
                                ax.grid(True)
                                ax.legend()
                            if show_s43 and 's43_phase' in ax_map and net.s.shape[1] >= 4:
                                ax = ax_map['s43_phase']
                                s43_phase_vals = np.angle(net.s[:, 3, 2], deg=True)
                                ax.plot(net.f/1e9, s43_phase_vals, label=label)
                                ax.set_xlabel('Frequency (GHz)')
                                ax.set_ylabel('Phase (degrees)')
                                ax.set_title('S43 Phase')
                                ax.grid(True)
                                ax.legend()
                            # Custom Sij phase
                            if getattr(self, 'custom_sij', None):
                                for (ii, jj) in self.custom_sij:
                                    if 1 <= ii <= net.s.shape[1] and 1 <= jj <= net.s.shape[2]:
                                        # Choose axis similarly
                                        target_ax = ax_map.get(f's{ii}{jj}_phase') if f's{ii}{jj}_phase' in ax_map else ax
                                        phase_vals = np.angle(net.s[:, ii-1, jj-1], deg=True)
                                        target_ax.plot(net.f/1e9, phase_vals, label=f"{label} S{ii}{jj}")
                                        target_ax.set_xlabel('Frequency (GHz)')
                                        target_ax.set_ylabel('Phase (degrees)')
                                        target_ax.set_title(f'S{ii}{jj} Phase')
                                        target_ax.grid(True)
                                        target_ax.legend()
                    
                    # Add markers if any
                    for marker_freq in self.markers:
                        # Find closest frequency point
                        idx = np.abs(net.f/1e9 - marker_freq).argmin()
                        f = net.f[idx]/1e9
                        
                        # Calculate values
                        sdd11_mag = 20*np.log10(np.abs(sdd[idx, 0, 0]))
                        sdd21_mag = 20*np.log10(np.abs(sdd[idx, 1, 0]))
                        s11_mag = 20*np.log10(np.abs(net.s[idx, 0, 0]))
                        s21_mag = 20*np.log10(np.abs(net.s[idx, 1, 0]))
                        sdd11_phase = np.angle(sdd[idx, 0, 0], deg=True)
                        sdd21_phase = np.angle(sdd[idx, 1, 0], deg=True)
                        s11_phase_val = np.angle(net.s[idx, 0, 0], deg=True)
                        s21_phase_val = np.angle(net.s[idx, 1, 0], deg=True)
                        
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
                            
                            if show_s11:
                                ax = ax_map['s11_mag']
                                ax.plot(f, s11_mag, 'ko')
                                ax.annotate(f'{s11_mag:.2f} dB', (f, s11_mag),
                                        xytext=(10, 10), textcoords='offset points')
                            
                            if show_s21:
                                ax = ax_map['s21_mag']
                                ax.plot(f, s21_mag, 'ko')
                                ax.annotate(f'{s21_mag:.2f} dB', (f, s21_mag),
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
                            
                            if show_s11:
                                ax = ax_map['s11_phase']
                                ax.plot(f, s11_phase_val, 'ko')
                                ax.annotate(f'{s11_phase_val:.2f}°', (f, s11_phase_val),
                                        xytext=(10, 10), textcoords='offset points')
                            
                            if show_s21:
                                ax = ax_map['s21_phase']
                                ax.plot(f, s21_phase_val, 'ko')
                                ax.annotate(f'{s21_phase_val:.2f}°', (f, s21_phase_val),
                                        xytext=(10, 10), textcoords='offset points')
                        
                        # Add values to text box
                        if self.marker_text:
                            marker_text = [f"Network: {label}", f"Frequency: {f:.2f} GHz"]
                            if show_mag:
                                if show_sdd11:
                                    marker_text.append(f"SDD11 Mag: {sdd11_mag:.2f} dB")
                                if show_sdd21:
                                    marker_text.append(f"SDD21 Mag: {sdd21_mag:.2f} dB")
                                if show_s11:
                                    marker_text.append(f"S11 Mag: {s11_mag:.2f} dB")
                                if show_s21:
                                    marker_text.append(f"S21 Mag: {s21_mag:.2f} dB")
                            if show_phase:
                                if show_sdd11:
                                    marker_text.append(f"SDD11 Phase: {sdd11_phase:.2f}°")
                                if show_sdd21:
                                    marker_text.append(f"SDD21 Phase: {sdd21_phase:.2f}°")
                                if show_s11:
                                    marker_text.append(f"S11 Phase: {s11_phase_val:.2f}°")
                                if show_s21:
                                    marker_text.append(f"S21 Phase: {s21_phase_val:.2f}°")
                            self.marker_text.insert(tk.END, "\n".join(marker_text) + "\n\n")
            
            # Finalize axes titles/labels for overlay mode (only when axes exist)
            if overlay_mode:
                if ax_mag is not None:
                    ax_mag.set_xlabel('Frequency (GHz)')
                    ax_mag.set_ylabel('Magnitude (dB)')
                    if not ax_mag.get_title():
                        ax_mag.set_title('Magnitude (Overlay)')
                    ax_mag.grid(True)
                    ax_mag.legend()
                    # Overlay specification lines if present and known
                    try:
                        if 'show_spec' in locals() and show_spec and self.spec_data:
                            if 'show_sdd11' in locals() and show_sdd11 and 'sdd11' in self.spec_data:
                                ax_mag.plot(self.spec_data['freq'], self.spec_data['sdd11'], 'r-', linewidth=2, label='Spec SDD11')
                            if 'show_sdd21' in locals() and show_sdd21 and 'sdd21' in self.spec_data:
                                ax_mag.plot(self.spec_data['freq'], self.spec_data['sdd21'], 'g-', linewidth=2, label='Spec SDD21')
                            ax_mag.legend()
                    except Exception:
                        pass
                if ax_phase is not None:
                    ax_phase.set_xlabel('Frequency (GHz)')
                    ax_phase.set_ylabel('Phase (degrees)')
                    if not ax_phase.get_title():
                        ax_phase.set_title('Phase (Overlay)')
                    ax_phase.grid(True)
                    ax_phase.legend()


            # Adjust layout and redraw
            self.figure.tight_layout()
            self.canvas.draw()
            self.apply_zoom()  #update based on the checkbox selection
            
        except Exception as e:
            print(f"Error plotting networks: {str(e)}")
            traceback.print_exc()

    def s2sdd(self, s):
        """
        Convert single-ended S-parameters to differential S-parameters
        
        Detailed debug version with conversion information
        """
        # print("\n==== S-Parameter to Differential S-Parameter Conversion ====")
        # print(f"Input S-parameter shape: {s.shape}")
        
        # Check if input is a 2-port network
        if s.shape[1] == 2 and s.shape[2] == 2:
            print("Already a 2-port network, no conversion needed")
            return s
            
        # For 4-port networks, convert to differential
        nfreqs = s.shape[0]
        sdd = np.zeros((nfreqs, 2, 2), dtype=complex)
        
        # Conversion method similar to previous implementation
        for f in range(nfreqs):
            # Extract 4x4 single-ended S-parameters at this frequency
            s_f = s[f]
            
            # print(f"\n--- Frequency Point {f} ---")
            # print("Original 4x4 S-parameter matrix:")
            # print(s_f)
            
            # Differential conversion calculation
            # Ports: [P1+, P2+, P3-, P4-]
            # Differential pairs: (P1+ - P3-), (P2+ - P4-)
            sdd[f, 0, 0] = 0.5 * ((s_f[0, 0] - s_f[0, 2]) - (s_f[2, 0] - s_f[2, 2]))  # SDD11
            sdd[f, 0, 1] = 0.5 * ((s_f[0, 1] - s_f[0, 3]) - (s_f[2, 1] - s_f[2, 3]))  # SDD12
            sdd[f, 1, 0] = 0.5 * ((s_f[1, 0] - s_f[1, 2]) - (s_f[3, 0] - s_f[3, 2]))  # SDD21
            sdd[f, 1, 1] = 0.5 * ((s_f[1, 1] - s_f[1, 3]) - (s_f[3, 1] - s_f[3, 3]))  # SDD22
            
            # Debug print for each differential parameter
            # print("\nDifferential S-parameters:")
            # for i in range(2):
            #     for j in range(2):
            #         print(f"SDD{i+1}{j+1}: Magnitude = {20*np.log10(np.abs(sdd[f, i, j])):.2f} dB, "
            #               f"Phase = {np.angle(sdd[f, i, j], deg=True):.2f}°")
        
        return sdd
    def update_plot(self):
        """Update the plot based on checkbox states"""
        if self.last_networks:
            self.plot_network_params(*self.last_networks, show_mag=self.plot_mag_var.get(), show_phase=self.plot_phase_var.get())
        elif hasattr(self, 'current_freq') and getattr(self, 'current_freq', None) is not None \
             and hasattr(self, 'current_s_params') and getattr(self, 'current_s_params', None) is not None \
             and hasattr(self, 'current_n_ports') and getattr(self, 'current_n_ports', None) is not None:
            # Refresh the single-file plot using current data and checkbox states
            self.plot_sparam(self.current_freq, self.current_s_params, self.current_n_ports)

    def add_custom_sij(self):
        """Add an arbitrary Sij to the selection from the spinboxes."""
        try:
            ii = int(self.sij_i_var.get())
            jj = int(self.sij_j_var.get())
        except ValueError:
            if hasattr(self, 'td_status') and self.td_status is not None:
                self.td_status.config(text="Invalid Sij indices", foreground='orange')
            return

        # Determine current port count context
        n_ports = None
        if hasattr(self, 'current_n_ports') and getattr(self, 'current_n_ports', None):
            n_ports = int(self.current_n_ports)
        elif self.last_networks:
            try:
                n_ports = int(self.last_networks[0].s.shape[1])
            except Exception:
                n_ports = None

        if n_ports is None:
            n_ports = 2

        if not (1 <= ii <= n_ports and 1 <= jj <= n_ports):
            if hasattr(self, 'td_status') and self.td_status is not None:
                self.td_status.config(text=f"S{ii}{jj} out of range for {n_ports}-port", foreground='orange')
            return

        if (ii, jj) not in self.custom_sij:
            self.custom_sij.append((ii, jj))

        # Update compact status label
        if hasattr(self, 'sij_status') and self.sij_status is not None:
            try:
                items = [f"S{i}{j}" for i, j in self.custom_sij]
                self.sij_status.config(text=",".join(items)[:24])
            except Exception:
                pass

        # Add to per-file history and refresh combo
        try:
            sij_str = f"S{ii}{jj}"
            key = getattr(self, 'current_file', None)
            if key:
                hist = self.sij_history.get(key, [])
                if sij_str in hist:
                    # move to front
                    hist.remove(sij_str)
                hist.insert(0, sij_str)
                # Cap history length
                self.sij_history[key] = hist[:12]
                self.update_sij_history_combobox()
        except Exception:
            pass

        # Clear any prior warning
        if hasattr(self, 'td_status') and self.td_status is not None:
            try:
                self.td_status.config(text="", foreground='black')
            except Exception:
                pass

        # Refresh plot
        self.update_plot()

    def clear_custom_sij(self):
        """Clear all arbitrary Sij selections."""
        self.custom_sij = []
        if hasattr(self, 'sij_status') and self.sij_status is not None:
            try:
                self.sij_status.config(text="")
            except Exception:
                pass
        # Refresh plot
        self.update_plot()

    def update_sij_history_combobox(self):
        """Refresh the Sij history dropdown based on current file."""
        if hasattr(self, 'sij_combo') and self.sij_combo is not None:
            key = getattr(self, 'current_file', None)
            values = self.sij_history.get(key, []) if key else []
            self.sij_combo['values'] = values
            # Clear selection to avoid confusion
            if values:
                self.sij_combo.current(0)
            else:
                self.sij_combo.set("")

    def on_select_sij_history(self, event=None):
        """Handle user selection from Sij history: apply to current selection and replot."""
        try:
            choice = self.sij_combo.get().strip()
            if len(choice) >= 3 and choice[0].lower() == 's':
                ii = int(choice[1])
                jj = int(choice[2])
                # Set spinboxes to match and add
                self.sij_i_var.set(str(ii))
                self.sij_j_var.set(str(jj))
                self.add_custom_sij()
        except Exception:
            pass

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
            imp_min = float(self.imp_min.get()) if self.imp_min.get() else None
            imp_max = float(self.imp_max.get()) if self.imp_max.get() else None
            
            # Update all subplot axes limits
            for ax in self.figure.get_axes():
                title = ax.get_title()
                if 'TDR' in title:
                    if time_min is not None and time_max is not None:
                        ax.set_xlim(time_min, time_max)
                    if mag_min is not None and mag_max is not None:
                        ax.set_ylim([-max(abs(mag_min), abs(mag_max))*1.2, max(abs(mag_min), abs(mag_max))*1.2])
                elif 'Pulse Response' in title:
                    if time_min is not None and time_max is not None:
                        ax.set_xlim(time_min, time_max)
                    if amp_min is not None and amp_max is not None:
                        ax.set_ylim(amp_min, amp_max)
                elif 'Impedance Profile vs Time' in title:
                    if time_min is not None and time_max is not None:
                        ax.set_xlim(time_min, time_max)
                    if imp_min is not None and imp_max is not None:
                        ax.set_ylim(imp_min, imp_max)
                elif 'Impedance Profile' in title:
                    if dist_min is not None and dist_max is not None:
                        ax.set_xlim(dist_min, dist_max)
                    if imp_min is not None and imp_max is not None:
                        ax.set_ylim(imp_min, imp_max)
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
        self.imp_min.set('')
        self.imp_max.set('')
        
        # Auto-scale all axes
        for ax in self.figure.get_axes():
            ax.autoscale()
        
        # Redraw the canvas
        self.canvas.draw()
    
    def create_velocity_tooltip(self, widget):
        """Create a tooltip for the velocity factor input box"""
        def show_tooltip(event):
            # Create tooltip window
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            # Create tooltip content
            tooltip_text = (
                "Velocity Factor (v_rel) Guidelines:\n\n"
                "FR4 PCB: εᵣ ≈ 4.0-4.5, so v = c/√εᵣ ≈ 0.5c to 0.47c\n"
                "Low-loss PCB: εᵣ ≈ 3.0-3.5, so v ≈ 0.58c to 0.53c\n"
                "0.66c is more typical for coaxial cables or low dielectric materials\n\n"
                "Default: 0.5 (suitable for most FR4 PCBs)"
            )
            
            label = tk.Label(tooltip, text=tooltip_text, 
                           background="lightyellow", 
                           foreground="black",
                           font=("Arial", "9"),
                           justify="left",
                           padx=10, pady=5,
                           relief="solid", borderwidth=1)
            label.pack()
            
            # Auto-hide tooltip after 5 seconds
            tooltip.after(5000, tooltip.destroy)
            
            # Hide tooltip when clicking elsewhere
            def hide_tooltip(event=None):
                try:
                    tooltip.destroy()
                except:
                    pass
            
            # Bind click outside to hide tooltip
            tooltip.bind("<Button-1>", hide_tooltip)
            tooltip.bind("<FocusOut>", hide_tooltip)
        
        # Bind right-click to show tooltip
        widget.bind("<Button-3>", show_tooltip)

    def toggle_plot_fullscreen(self, event=None):
        """Toggle the plot area between normal and fullscreen mode using Escape key"""
        if not hasattr(self, 'is_plot_fullscreen'):
            self.is_plot_fullscreen = False
            
        if not self.is_plot_fullscreen:
            # Enter fullscreen mode - hide file frame to show only plot area
            try:
                # Store complete screen state before modifying
                self.screen_state = {
                    'figure_size': self.figure.get_size_inches() if hasattr(self, 'figure') else None,
                    'subplot_params': {
                        'top': self.figure.subplotpars.top,
                        'bottom': self.figure.subplotpars.bottom,
                        'left': self.figure.subplotpars.left,
                        'right': self.figure.subplotpars.right,
                        'hspace': self.figure.subplotpars.hspace,
                        'wspace': self.figure.subplotpars.wspace
                    } if hasattr(self, 'figure') else None,
                    'window_geometry': self.geometry(),
                    'plot_frame_info': self.sparam_plot_frame.grid_info() if hasattr(self, 'sparam_plot_frame') else None,
                    'row_weights': [
                        (i, self.sparam_view_container.grid_rowconfigure(i)['weight'])
                        for i in range(10)
                    ] if hasattr(self, 'sparam_view_container') else None,
                    'ui_elements_state': {
                        'marker_frame': {'visible': hasattr(self, 'marker_frame'), 'info': self.marker_frame.grid_info() if hasattr(self, 'marker_frame') else None},
                        'marker_text': {'visible': hasattr(self, 'marker_text'), 'info': self.marker_text.grid_info() if hasattr(self, 'marker_text') else None},
                        'plot_control_frame': {'visible': hasattr(self, 'plot_control_frame'), 'info': self.plot_control_frame.grid_info() if hasattr(self, 'plot_control_frame') else None},
                        'zoom_frame': {'visible': hasattr(self, 'zoom_frame'), 'info': self.zoom_frame.grid_info() if hasattr(self, 'zoom_frame') else None}
                    }
                }
                
                # Hide the file frame
                self.paned.forget(self.file_frame)
                
                # Hide UI elements
                ui_elements = ['marker_frame', 'marker_text', 'plot_control_frame', 'zoom_frame']
                for element in ui_elements:
                    if hasattr(self, element):
                        getattr(self, element).grid_remove()
                
                # Configure plot frame for fullscreen
                if hasattr(self, 'sparam_plot_frame'):
                    self.sparam_plot_frame.grid_remove()
                    self.sparam_plot_frame.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
                    self.sparam_plot_frame.pack_propagate(False)
                
                # Maximize figure
                if hasattr(self, 'figure'):
                    self.figure.set_size_inches(14, 10)
                    self.figure.subplots_adjust(top=0.98, bottom=0.05, left=0.05, right=0.98, hspace=0.1)
                    self.esc_text = self.figure.text(0.99, 0.01, "Press ESC to exit fullscreen", 
                                                   ha='right', va='bottom', fontsize=9, alpha=0.7,
                                                   bbox=dict(boxstyle='round,pad=0.5', 
                                                           facecolor='white', alpha=0.7))
                
                # Configure container for fullscreen
                if hasattr(self, 'sparam_view_container'):
                    for i in range(10):
                        self.sparam_view_container.rowconfigure(i, weight=0)
                    self.sparam_view_container.rowconfigure(0, weight=1)
                    self.sparam_view_container.columnconfigure(0, weight=1)
                
            except Exception as e:
                print(f"Error entering fullscreen mode: {e}")
                import traceback
                traceback.print_exc()
                
        else:
            # Exit fullscreen mode - restore file frame and UI elements
            try:
                # Restore file frame
                self.paned.insert(0, self.file_frame, weight=1)
                
                if hasattr(self, 'screen_state'):
                    try:
                        # Capture geometry before any other operations
                        geometry_to_restore = self.screen_state['window_geometry']
                        
                        # Restore UI elements with their original grid info
                        ui_state = self.screen_state['ui_elements_state']
                        for element, state in ui_state.items():
                            if state['visible']:
                                widget = getattr(self, element)
                                if state['info']:
                                    widget.grid(**state['info'])
                                else:
                                    widget.grid()
                        
                        # Restore figure state
                        if hasattr(self, 'figure'):
                            if self.screen_state['figure_size'] is not None:
                                self.figure.set_size_inches(*self.screen_state['figure_size'])
                            
                            if self.screen_state['subplot_params'] is not None:
                                params = self.screen_state['subplot_params']
                                self.figure.subplots_adjust(**params)
                            
                            if hasattr(self, 'esc_text'):
                                self.esc_text.remove()
                                delattr(self, 'esc_text')
                        
                        # Restore plot frame
                        if hasattr(self, 'sparam_plot_frame'):
                            self.sparam_plot_frame.grid_remove()
                            if self.screen_state['plot_frame_info']:
                                self.sparam_plot_frame.grid(**self.screen_state['plot_frame_info'])
                            else:
                                self.sparam_plot_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
                            self.sparam_plot_frame.pack_propagate(True)
                        
                        # Restore container state
                        if hasattr(self, 'sparam_view_container'):
                            if self.screen_state['row_weights']:
                                for row, weight in self.screen_state['row_weights']:
                                    self.sparam_view_container.rowconfigure(row, weight=weight)
                            else:
                                for i in range(10):
                                    self.sparam_view_container.rowconfigure(i, weight=0)
                                self.sparam_view_container.rowconfigure(1, weight=1)
                            self.sparam_view_container.columnconfigure(0, weight=1)
                    
                    finally:
                        # Clean up screen state
                        delattr(self, 'screen_state')
                        
                        # Schedule geometry restoration after cleanup
                        if geometry_to_restore:
                            self.after(100, lambda: self.restore_geometry_delayed(geometry_to_restore))
                
            except Exception as e:
                print(f"Error exiting fullscreen mode: {e}")
                import traceback
                traceback.print_exc()
        
        # Update state and redraw
        self.is_plot_fullscreen = not self.is_plot_fullscreen
        if hasattr(self, 'canvas'):
            self.canvas.draw()
            
    def restore_geometry_delayed(self, geometry):
        """Helper method to restore window geometry after a delay"""
        self.geometry(geometry)
        
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

            # Find common frequency range
            min_freq = max(device.f[0], fixture.f[0])
            max_freq = min(device.f[-1], fixture.f[-1])
            if min_freq > max_freq:
                messagebox.showerror("Error", "No overlapping frequency range between files")
                return

            # Get frequency points within common range
            device_mask = (device.f >= min_freq) & (device.f <= max_freq)
            fixture_mask = (fixture.f >= min_freq) & (fixture.f <= max_freq)
            device_points = sum(device_mask)
            fixture_points = sum(fixture_mask)

            # Use frequency points from file with higher resolution
            if device_points >= fixture_points:
                target_freq = device.f[device_mask]
                fixture = fixture.interpolate(target_freq)
            else:
                target_freq = fixture.f[fixture_mask]
                device = device.interpolate(target_freq)

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
            messagebox.showinfo("Success", 
                f"Left-side embedding completed successfully\nSaved as: {output_filename}")
            
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

            # Find common frequency range
            min_freq = max(device.f[0], fixture.f[0])
            max_freq = min(device.f[-1], fixture.f[-1])
            if min_freq > max_freq:
                messagebox.showerror("Error", "No overlapping frequency range between files")
                return

            # Get frequency points within common range
            device_mask = (device.f >= min_freq) & (device.f <= max_freq)
            fixture_mask = (fixture.f >= min_freq) & (fixture.f <= max_freq)
            device_points = sum(device_mask)
            fixture_points = sum(fixture_mask)

            # Use frequency points from file with higher resolution
            if device_points >= fixture_points:
                target_freq = device.f[device_mask]
                fixture = fixture.interpolate(target_freq)
            else:
                target_freq = fixture.f[fixture_mask]
                device = device.interpolate(target_freq)

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
            messagebox.showinfo("Success", 
                f"Right-side embedding completed successfully\nSaved as: {output_filename}")

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
        """Calculate impedance profile from TDR response assuming Z0=100 ohm differential"""
        Z0 = 100  # Differential characteristic impedance
    
        # Extract real part only as reflection coefficient
        tdr_real = np.real(tdr_response)
    
        # === Convert from MATLAB-style TDR back to reflection coefficient ===
        # The TDR is in milli-units (mU), centered at 0
    
        print("=== Impedance Profile Calculation ===")
        print(f"TDR values - min: {np.min(tdr_real):.2f}mU, max: {np.max(tdr_real):.2f}mU, mean: {np.mean(tdr_real):.2f}mU")
    
        # Convert from mU back to reflection coefficient
        # For our MATLAB implementation, we use a simpler linear conversion
        refl = tdr_real / 1000.0
    
        print(f"  After conversion - min: {np.min(refl):.6f}, max: {np.max(refl):.6f}")
    
        # Apply reasonable clipping to avoid extreme values
        refl = np.clip(refl, -0.8, 0.8)
    
        # Calculate impedance from reflection coefficient
        Z = Z0 * (1 + refl) / (1 - refl)
    
        # Apply reasonable clipping to impedance range
        Z = np.clip(Z, 20, 150)
    
        # Apply light smoothing to impedance profile
        from scipy.ndimage import gaussian_filter1d
        Z_smooth = gaussian_filter1d(Z, sigma=0.8)
    
        print(f"Final impedance range - min: {np.min(Z_smooth):.1f} ohm, max: {np.max(Z_smooth):.1f} ohm, mean: {np.mean(Z_smooth):.1f} ohm")
    
        # Display samples that produce max and min impedance
        max_Z_idx = np.argmax(Z_smooth)
        min_Z_idx = np.argmin(Z_smooth)
        print(f"  Max Z at index {max_Z_idx}: Z = {Z_smooth[max_Z_idx]:.1f} ohm")
        print(f"  Min Z at index {min_Z_idx}: Z = {Z_smooth[min_Z_idx]:.1f} ohm")
    
        return Z_smooth

    def plot_tdr_and_impedance(self, ax_plot, t_ns, tdr, label):
        """Plot TDR response in PLTS style"""
        # Plot TDR response in nanoseconds
        ax_plot.plot(t_ns, np.real(tdr), label=label)
        ax_plot.set_xlabel('Time (ns)')
        ax_plot.set_ylabel('Reflection Coefficient (mU)')
        ax_plot.set_title('Time Domain Reflectometry (TDR)')
    
        # Set y-axis limits for PLTS-style symmetrical display
        tdr_max_abs = np.max(np.abs(np.real(tdr)))
        plot_limit = max(50, tdr_max_abs * 1.2)  # At least ±50mU or 120% of peak
        ax_plot.set_ylim([-plot_limit, plot_limit])
    
        # Add horizontal zero reference line (PLTS style)
        ax_plot.axhline(y=0, color='r', linestyle='--', alpha=0.3)
    
        # PLTS-style grid
        ax_plot.grid(True, which='major', linestyle='-', alpha=0.6)
        ax_plot.grid(True, which='minor', linestyle=':', alpha=0.3)
        ax_plot.minorticks_on()
    
        # Format tick labels without scientific notation
        ax_plot.ticklabel_format(axis='y', style='plain', useOffset=False)
    
        # Add legend
        ax_plot.legend()
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
        # Try common locations in order of preference
        possible_dirs = [
            os.path.join(os.path.expanduser("~"), "OneDrive", "Documents", "MATLAB", "alab"),  # MATLAB/alab directory
            os.path.join(os.path.expanduser("~"), "OneDrive", "Documents", "LTspiceXVII"),  # LTspice directory
            os.path.join(os.path.expanduser("~"), "OneDrive", "Documents"),  # Documents directory
            os.path.expanduser("~"),  # User's home directory
            os.path.dirname(os.path.abspath(__file__)),  # Script directory
            os.getcwd()  # Current working directory
        ]
        
        for dir in possible_dirs:
            if self.validate_directory(dir):
                self.current_directory = dir
                print(f"Using directory: {dir}")
                return
                
        # If all else fails, use the current directory
        self.current_directory = os.getcwd()
        print(f"Using current directory: {self.current_directory}")

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
            btn_frame.pack(fill="x", padx=5, pady=2)
            
            # Add port mapping button
            ttk.Button(btn_frame, text="Port Mapping", 
                      command=self.show_port_mapping_dialog).pack(side="left", padx=2)
            
            # Add close button
            ttk.Button(btn_frame, text="Close", 
                      command=self.close_smith_chart).pack(side="right", padx=2)
                
            # Create figure with subplots based on checkbox status
            num_plots = sum([self.plot_sdd11_var.get(), self.plot_sdd21_var.get()])
            if num_plots == 0:
                messagebox.showwarning("Warning", "Please select at least one parameter (SDD11 or SDD21)")
                self.smith_window.destroy()
                return
                
            fig = Figure(figsize=(8, 4 if num_plots > 1 else 8))
            canvas = FigureCanvasTkAgg(fig, master=self.smith_window)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
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

            # Find common frequency range
            min_freq = max(dut_with_fixture.f[0], fixture.f[0])
            max_freq = min(dut_with_fixture.f[-1], fixture.f[-1])
            if min_freq > max_freq:
                messagebox.showerror("Error", "No overlapping frequency range between files")
                return

            # Get frequency points within common range
            dut_mask = (dut_with_fixture.f >= min_freq) & (dut_with_fixture.f <= max_freq)
            fixture_mask = (fixture.f >= min_freq) & (fixture.f <= max_freq)
            dut_points = sum(dut_mask)
            fixture_points = sum(fixture_mask)

            # Use frequency points from file with higher resolution
            if dut_points >= fixture_points:
                target_freq = dut_with_fixture.f[dut_mask]
                fixture = fixture.interpolate(target_freq)
            else:
                target_freq = fixture.f[fixture_mask]
                dut_with_fixture = dut_with_fixture.interpolate(target_freq)

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
            deembedded = rf.Network(
                s=deembedded_s,
                frequency=dut_with_fixture.frequency,
                name='Left-Deembedded Network'
            )

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
            
            messagebox.showinfo("Success", 
                f"Left-side de-embedding completed successfully\nSaved as: {output_filename}")
            
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

            # Find common frequency range
            min_freq = max(dut_with_fixture.f[0], fixture.f[0])
            max_freq = min(dut_with_fixture.f[-1], fixture.f[-1])
            if min_freq > max_freq:
                messagebox.showerror("Error", "No overlapping frequency range between files")
                return

            # Get frequency points within common range
            dut_mask = (dut_with_fixture.f >= min_freq) & (dut_with_fixture.f <= max_freq)
            fixture_mask = (fixture.f >= min_freq) & (fixture.f <= max_freq)
            dut_points = sum(dut_mask)
            fixture_points = sum(fixture_mask)

            # Use frequency points from file with higher resolution
            if dut_points >= fixture_points:
                target_freq = dut_with_fixture.f[dut_mask]
                fixture = fixture.interpolate(target_freq)
            else:
                target_freq = fixture.f[fixture_mask]
                dut_with_fixture = dut_with_fixture.interpolate(target_freq)

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
            deembedded = rf.Network(
                s=deembedded_s,
                frequency=dut_with_fixture.frequency,
                name='Right-Deembedded Network'
            )

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
            
            messagebox.showinfo("Success", 
                f"Right-side de-embedding completed successfully\nSaved as: {output_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Right-side de-embedding failed: {str(e)}")
            traceback.print_exc()

    def convert_2x_to_1x_sparam(self, method='abcd'):
        """
        Convert 2x S-parameters to 1x S-parameters using specified method.
        For .s2p files: Converts a 2-port measurement of cascaded devices to single device
        For .s4p files: Converts a 4-port measurement of cascaded differential pairs to single pair
        
        Args:
            method: Conversion method, either 'abcd' (ABCD matrix method) or 
                   'symmetric' (对称网络假设法, symmetric network assumption)
        
        Port mapping for 4-port networks:
        - Ports 1,3: Input differential pair (P1 positive, P3 negative)
        - Ports 2,4: Output differential pair (P2 positive, P4 negative)
        """
        # Import messagebox at function scope to avoid UnboundLocalError
        from tkinter import messagebox
        
        # Check if a file is selected in the table
        selected_rows = self.table.multiplerowlist
        if not selected_rows or len(selected_rows) != 1:
            if not self.current_file:
                messagebox.showerror("Error", "Please select an S-parameter file first.")
                return
        else:
            # Get the selected file from the filtered DataFrame
            displayed_df = self.table.model.df
            row = selected_rows[0]
            if row < len(displayed_df):
                self.current_file = displayed_df.iloc[row].get('File_Path', os.path.join(self.current_directory, displayed_df.iloc[row]['Name']))
                self.current_file = os.path.normpath(self.current_file.replace('\\', '/'))
            
        if not self.current_file.endswith(('.s2p', '.s4p')):
            messagebox.showerror("Error", 
                "Only .s2p and .s4p files are supported.\n\n"
                "A 2X S-parameter file represents a cascaded measurement:\n"
                "- .s2p: Two identical single-ended devices in series\n"
                "        (e.g., two cables connected end-to-end)\n"
                "- .s4p: Two identical differential pairs in series\n"
                "        (e.g., two differential cables connected end-to-end)")
            return
        
        try:
            # Read the network using scikit-rf
            network = rf.Network(self.current_file)
            
            # Check port count
            if network.nports == 2:
                # For 2-port networks (single-ended devices)
                if method == 'abcd':
                    # ABCD matrix method
                    abcd_matrix = rf.s2t(network.s)  # S to T (ABCD) conversion
                    # Calculate matrix square root
                    s_sqrt = np.zeros_like(network.s)
                    for f in range(len(network.f)):
                        try:
                            abcd_sqrt = scipy.linalg.sqrtm(abcd_matrix[f])
                            s_sqrt[f] = rf.t2s(abcd_sqrt.reshape(1, 2, 2))[0]
                        except Exception as e:
                            print(f"Error at frequency point {f}: {e}")
                            print(f"ABCD matrix:\n{abcd_matrix[f]}")
                            raise
                else:
                    # Symmetric network assumption method
                    s_sqrt = self.split_symmetric_adapter(network.s)
                    
            elif network.nports == 4:
                # For 4-port networks (differential pairs)
                # Original port order: [P1+, P2+, P3-, P4-]
                # We want: Input pair (P1+, P3-) and Output pair (P2+, P4-)
                
                # Mixed-mode conversion matrix for differential mode
                # Maps [P1+, P2+, P3-, P4-] to [Diff1, Diff2]
                # where Diff1 = (P1+ - P3-)/√2 and Diff2 = (P2+ - P4-)/√2
                M = np.array([[1, 0, -1, 0],
                            [0, 1, 0, -1]]) / np.sqrt(2)
                M_inv = np.linalg.pinv(M)  # Use proper pseudo-inverse for correct amplitude scaling
                
                # Initialize array for differential S-parameters
                sdd = np.zeros((len(network.f), 2, 2), dtype=complex)
                
                # Convert single-ended to differential for each frequency point
                for f in range(len(network.f)):
                    # Extract 4x4 single-ended S-parameters at this frequency
                    s_f = network.s[f]
                    # Convert to differential mode (2x2 matrix)
                    sdd[f] = M @ s_f @ M_inv
                
                if method == 'abcd':
                    # ABCD matrix method with numerical stability improvements
                    abcd_matrix = rf.s2t(sdd)
                    # Calculate matrix square root with improved numerical stability
                    s_sqrt = np.zeros_like(sdd)
                    fallback_count = 0  # Track how many times we fall back to symmetric method
                    fallback_reasons = []  # Track reasons for fallback
                    
                    for f in range(len(network.f)):
                        try:
                            # Get ABCD matrix for this frequency
                            abcd_f = abcd_matrix[f]
                            
                            # Check for numerical issues
                            if np.any(np.isnan(abcd_f)) or np.any(np.isinf(abcd_f)):
                                print(f"Warning: NaN or Inf detected in ABCD matrix at frequency {f}")
                                fallback_count += 1
                                if "NaN/Inf values" not in fallback_reasons:
                                    fallback_reasons.append("NaN/Inf values")
                                # Use symmetric method as fallback
                                s_sqrt[f] = self.split_symmetric_adapter(sdd[f:f+1])[0]
                                continue
                            
                            # Check condition number for numerical stability
                            cond_num = np.linalg.cond(abcd_f)
                            if cond_num > 1e12:
                                print(f"Warning: Ill-conditioned ABCD matrix at frequency {f} (cond={cond_num:.2e})")
                                fallback_count += 1
                                if "Ill-conditioned matrices" not in fallback_reasons:
                                    fallback_reasons.append("Ill-conditioned matrices")
                                # Use symmetric method as fallback
                                s_sqrt[f] = self.split_symmetric_adapter(sdd[f:f+1])[0]
                                continue
                            
                            # Use eigenvalue decomposition for more stable square root
                            eigenvals, eigenvecs = np.linalg.eig(abcd_f)
                            
                            # Check for negative or complex eigenvalues that could cause issues
                            if np.any(np.real(eigenvals) < 0):
                                print(f"Warning: Negative eigenvalues detected at frequency {f}")
                                fallback_count += 1
                                if "Negative eigenvalues" not in fallback_reasons:
                                    fallback_reasons.append("Negative eigenvalues")
                                # Use symmetric method as fallback
                                s_sqrt[f] = self.split_symmetric_adapter(sdd[f:f+1])[0]
                                continue
                            
                            # Calculate square root using eigenvalue decomposition
                            sqrt_eigenvals = np.sqrt(eigenvals)
                            abcd_sqrt = eigenvecs @ np.diag(sqrt_eigenvals) @ np.linalg.inv(eigenvecs)
                            
                            # Convert back to S-parameters
                            s_sqrt[f] = rf.t2s(abcd_sqrt.reshape(1, 2, 2))[0]
                            
                            # Additional check for spikes - compare with neighboring points
                            if f > 0:
                                # Check for sudden jumps in magnitude
                                mag_diff = np.abs(np.abs(s_sqrt[f]) - np.abs(s_sqrt[f-1]))
                                if np.any(mag_diff > 10):  # Threshold for spike detection
                                    print(f"Warning: Potential spike detected at frequency {f}")
                                    fallback_count += 1
                                    if "Spike detection" not in fallback_reasons:
                                        fallback_reasons.append("Spike detection")
                                    # Use interpolation or symmetric method
                                    if f > 1:
                                        # Linear interpolation between f-1 and f+1 (if available)
                                        s_sqrt[f] = (s_sqrt[f-1] + s_sqrt[f-1]) / 2  # Use previous point for now
                                    else:
                                        s_sqrt[f] = self.split_symmetric_adapter(sdd[f:f+1])[0]
                            
                        except Exception as e:
                            print(f"Error at frequency point {f}: {e}")
                            print(f"ABCD matrix:\n{abcd_matrix[f]}")
                            print(f"Using symmetric method as fallback")
                            fallback_count += 1
                            if "Matrix calculation errors" not in fallback_reasons:
                                fallback_reasons.append("Matrix calculation errors")
                            # Use symmetric method as fallback
                            s_sqrt[f] = self.split_symmetric_adapter(sdd[f:f+1])[0]
                    
                    # Show popup notification if fallback was used
                    if fallback_count > 0:
                        total_points = len(network.f)
                        fallback_percentage = (fallback_count / total_points) * 100
                        
                        reasons_text = "\n• ".join(fallback_reasons)
                        message = (
                            f"ABCD Matrix Method - Fallback Applied\n\n"
                            f"Due to numerical instabilities, the symmetric method was used "
                            f"instead of the ABCD matrix method for {fallback_count} out of "
                            f"{total_points} frequency points ({fallback_percentage:.1f}%).\n\n"
                            f"Reasons for fallback:\n• {reasons_text}\n\n"
                            f"The conversion has been completed successfully using a hybrid approach "
                            f"for optimal numerical stability."
                        )
                        
                        messagebox.showinfo(
                            "Conversion Method Notice",
                            message,
                            icon='info'
                        )
                else:
                    # Symmetric network assumption method
                    s_sqrt = self.split_symmetric_adapter(sdd)
                
            else:
                messagebox.showerror("Error", 
                    "Invalid port count. This function only works for:\n"
                    "- 2-port networks (.s2p files)\n"
                    "- 4-port networks (.s4p files)")
                return
            
            # Create a new network with the converted S-parameters
            sqrt_network = rf.Network(
                s=s_sqrt,
                frequency=network.frequency,
                name='Left-Embedded Network'
            )

            # Save the converted network in the same directory with appropriate postfix
            directory = os.path.dirname(self.current_file)
            filename = os.path.basename(self.current_file)
            base_name, ext = os.path.splitext(filename)
            
            # Determine output filename based on input file type and method
            postfix = "_1x_sym" if method == 'symmetric' else "_1x"
            if ext == '.s2p':
                output_filename = os.path.join(directory, f"{base_name}{postfix}.s1p")
                msg_detail = "Extracted single-ended device parameters"
            elif ext == '.s4p':
                output_filename = os.path.join(directory, f"{base_name}{postfix}.s2p")
                msg_detail = "Extracted differential pair parameters"
            
            # Write the converted network
            sqrt_network.write_touchstone(output_filename)
            
            method_name = "symmetric network assumption" if method == 'symmetric' else "ABCD matrix"
            messagebox.showinfo("Success", 
                f"Converted S-parameters saved to:\n{output_filename}\n\n"
                f"{msg_detail} using {method_name} method\n"
                "from a cascaded measurement of two identical devices.")
            
            # Refresh the file list to show the new file
            self.update_file_list()
            
        except Exception as e:
            messagebox.showerror("Conversion Error", 
                f"Failed to convert S-parameters:\n{str(e)}\n\n"
                "Make sure the file contains valid S-parameters\n"
                "of two identical devices in series.")
            traceback.print_exc()

    def split_symmetric_adapter(self, s):
        """
        Simplified decomposition method for symmetric adapters.
        适用于对称适配器的简化分解方法
        
        Args:
            s: Combined S-parameters of cascaded symmetric adapters
            
        Returns:
            Single adapter S-parameters assuming symmetry
        """
        nfreqs = s.shape[0]
        s_single = np.zeros_like(s)
        
        for f in range(len(s)):
            s11_combined = s[f, 0, 0]
            s21_combined = s[f, 1, 0]
            
            # Calculate single adapter S-parameters (assuming symmetry)
            # 计算单个适配器的S参数（假设对称）
            s11_single = 1 - np.sqrt(1 - s11_combined + 1e-20)  # Add small constant for numerical stability
            s21_single = np.sqrt(s21_combined + 1e-20)  # Add small constant for numerical stability
            
            s_single[f] = np.array([[s11_single, s21_single],
                                  [s21_single, s11_single]])
            
        return s_single

if __name__ == "__main__":
    app = SParamBrowser()
    app.mainloop()
