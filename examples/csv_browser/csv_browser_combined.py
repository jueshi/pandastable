"""
CSV Browser Application with Excel-like File List
"""
# Import os and sys first
import os
import sys

# Add custom pandastable path to sys.path BEFORE importing pandastable
custom_pandastable_path = r"C:\Users\juesh\OneDrive\Documents\windsurf\pandastable\pandastable"
if os.path.exists(custom_pandastable_path):
    # Insert at the beginning of sys.path to prioritize this version
    sys.path.insert(0, custom_pandastable_path)
    print(f"Using custom pandastable from: {custom_pandastable_path}")
    
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np
import traceback
import difflib
import warnings
import shutil
import subprocess
import json
from datetime import datetime
from pandastable import Table, TableModel
import time
import pyperclip
import copy
import types
from table_utils import FileTableUtils
from plot_utils import PlotUtils
from csv_browser_plot_methods import PlotMethodsMixin
from csv_browser_new_methods import CorrelationAnalysisMixin

warnings.filterwarnings('ignore', category=FutureWarning)

class CSVBrowser(tk.Tk, PlotMethodsMixin, CorrelationAnalysisMixin):
    def __init__(self):
        super().__init__()
        
        self.title("CSV Browser")
        self.state('zoomed')
        
        # Suppress specific warnings globally
        warnings.filterwarnings('ignore', message='.*color.*and.*colormap.*cannot be used simultaneously.*')
        warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
        
        # Initialize variables
        self.current_file = None
        self.is_horizontal = False  # Start with vertical layout

        # Initialize csv_files before FileTableUtils
        self.csv_files = []
        
        # Initialize utility classes
        self.file_table_utils = FileTableUtils(self)
        self.plot_utils = PlotUtils(self)
        
        self.filter_text = tk.StringVar()
        self.filter_text.trace_add("write", self.file_table_utils.filter_files)
        self.last_clicked_row = None
        self.csv_frame = None
        self.include_subfolders = tk.BooleanVar(value=False)
        
        # Initialize CSV filter variables
        self.current_csv_filter = ""
        self.csv_filter_text = tk.StringVar(value="")
        self.csv_filter_text.trace_add("write", self.filter_csv_content)
        
        # Initialize column search variable
        self.column_search_var = tk.StringVar(value="")
        self.column_search_var.trace_add("write", self.search_columns)
        
        # Initialize column filter variable
        self.column_filter_var = tk.StringVar(value="")
        self.column_filter_var.trace_add("write", self.filter_columns)
        self.visible_columns = None  # Store currently visible columns
        
        # Store saved filters (row and column)
        self.saved_filters = []  # List to store saved filter configurations
        
        # Store saved file filters
        self.saved_file_filters = []  # List to store saved file filter configurations
        
        # Set maximum number of recent directories to store
        self.max_recent_directories = 5
        
        # Initialize recent directories list
        self.recent_directories = []
        
        # File to store settings (recent directories and filters)
        self.settings_file = os.path.join(os.path.expanduser("~"), "csv_browser_settings.json")
        print(f"Settings file path: {self.settings_file}")
        
        # Load settings from file
        self.load_settings()
        
        # Track highlighted columns
        self.highlighted_columns = {}
        
        # Initialize last_searched_column
        self.last_searched_column = None
        
        # Set default directory
        self.current_directory = r"D:\hp-jue\downloads"
        
        # Add current directory to recent directories
        self.add_to_recent_directories(self.current_directory)
        
        # Get initial list of CSV files
        self.file_table_utils.update_file_list()
        
        # Calculate max fields for the current directory
        self.max_fields = self.file_table_utils.get_max_fields()
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create and pack the toolbar
        self.toolbar = ttk.Frame(self.main_container)
        self.toolbar.pack(fill="x", padx=5, pady=5)
        self.setup_toolbar()
        
        # Create and pack the panels
        self.setup_panels()
        
        # Create the file browser and CSV viewer
        self.setup_file_browser()
        self.setup_csv_viewer()
        
        # Setup column search menu
        self.setup_column_search_menu()
        
        # Set up keyboard shortcuts
        self.bind("<Control-f>", self.focus_column_search)
        
        # Create the application menu
        self.create_menu()
        
        # Patch the showPlot method to handle our plot settings
        def patched_showPlot(self, *args, **kwargs):
            # Save current plot columns before showing the plot
            self.save_current_plot_columns()
            # Call the original showPlot method
            self._original_showPlot(*args, **kwargs)
            # Restore plot settings after showing the plot
            self.restore_plot_settings()
        
        # Store the original showPlot method
        if hasattr(self, 'csv_table'):
            self.csv_table._original_showPlot = self.csv_table.showPlot
            self.csv_table.showPlot = types.MethodType(patched_showPlot, self.csv_table)

    def load_csv_file(self, file_path):
        """Load and display the selected CSV file with comprehensive error handling and diagnostics"""
        try:
            # Save current plot settings and columns before loading new file
            if hasattr(self, 'csv_table'):
                self.plot_utils.save_current_plot_columns()
                self.plot_utils.save_plot_settings()
                
                # Save table settings (including index)
                self.save_table_settings()
            
            # Load the CSV file using advanced file reading method
            df = self._advanced_file_read(file_path)
            if df is None:
                return
            
            # Create or update the CSV viewer
            if self.csv_frame is None:
                self.setup_csv_viewer()
            
            # Update the CSV table with new data
            self.csv_table.model.df = df
            self.csv_table.redraw()
            
            # Store the current file path
            self.current_file = file_path
            
            # Apply any stored column filter
            self._apply_column_filter()
            
            # Ensure the index is properly preserved
            self._safe_preserve_index()
            
            # Adjust column widths to fit content
            self.adjust_column_widths()
            
            # Update window title with filename
            filename = os.path.basename(file_path)
            self.title(f"CSV Browser - {filename}")
            
            # Restore table settings (including index)
            self.restore_table_settings()
            
            # Restore plot columns and settings through PlotUtils
            if hasattr(self, 'plot_utils'):
                self.plot_utils.restore_plot_columns()
                self.plot_utils.restore_plot_settings()
                
                # If plot viewer is open, update it
                if hasattr(self.csv_table, 'pf') and self.csv_table.pf is not None:
                    self.plot_utils._safe_replot_with_index_preservation(self.csv_table.pf)
            
            print(f"Successfully loaded CSV file with {len(df)} rows and {len(df.columns)} columns")
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error loading CSV file:\n{str(e)}"
            )
            traceback.print_exc()

if __name__ == "__main__":
    app = CSVBrowser()
    app.mainloop()
