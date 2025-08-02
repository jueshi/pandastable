"""
CSV Browser Application with Excel-like File List
"""
import os
import sys
import json
import copy
import types
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import traceback
import pandas as pd
import numpy as np
from pandastable import Table
from table_utils import FileTableUtils
from plot_utils import PlotUtils
from csv_browser_plot_methods import PlotMethodsMixin
from csv_browser_new_methods import CorrelationAnalysisMixin

class CSVBrowser(tk.Tk, PlotMethodsMixin, CorrelationAnalysisMixin):
    def __init__(self):
        super().__init__()
        
        self.title("CSV Browser")
        self.state('zoomed')
        
        # Suppress specific warnings globally
        import warnings
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
        def patched_showPlot(table_instance, *args, **kwargs):
            # Save current plot columns before showing the plot
            if hasattr(table_instance, 'parent') and hasattr(table_instance.parent, 'plot_utils'):
                table_instance.parent.plot_utils.save_current_plot_columns()
            # Call the original showPlot method
            table_instance._original_showPlot(*args, **kwargs)
            # Restore plot settings after showing the plot
            if hasattr(table_instance, 'parent') and hasattr(table_instance.parent, 'plot_utils'):
                table_instance.parent.plot_utils.restore_plot_settings()
        
        # Store the original showPlot method
        if hasattr(self, 'csv_table'):
            self.csv_table._original_showPlot = self.csv_table.showPlot
            self.csv_table.showPlot = types.MethodType(patched_showPlot, self.csv_table)
            # Store a reference to self in the table for access in the patched method
            self.csv_table.parent = self
