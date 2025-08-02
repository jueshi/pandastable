import os
import sys
from datetime import datetime

class FileTableUtils:
    def __init__(self, parent_app):
        """
        Initialize FileTableUtils with a reference to the parent CSVBrowser application
        This allows access to shared attributes and methods
        """
        self.parent_app = parent_app

    def normalize_long_path(self, path):
        """Normalize path and add long path prefix if needed"""
        # Same implementation as in csv_browser.py
        normalized_path = os.path.normpath(os.path.abspath(path))
        
        if len(normalized_path) > 250 and not normalized_path.startswith('\\\\?\\'):
            normalized_path = '\\\\?\\' + normalized_path
            print(f"Using long path format: {normalized_path}")
        
        return normalized_path

    def format_size(self, size):
        """Convert size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_date(self, timestamp):
        """Convert timestamp to readable format"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")

    def update_file_list(self):
        """Update the list of CSV and TSV files"""
        print("\n=== Updating file list ===")
        print(f"Current directory: {self.parent_app.current_directory}")
        print(f"Include subfolders: {self.parent_app.include_subfolders.get()}")
        
        # Normalize the current directory path
        try:
            normalized_directory = self.normalize_long_path(self.parent_app.current_directory)
            print(f"Normalized directory: {normalized_directory}")
        except Exception as e:
            print(f"Error normalizing directory path: {e}")
            normalized_directory = self.parent_app.current_directory
        
        # Reset csv_files
        self.parent_app.csv_files = []
        
        if self.parent_app.include_subfolders.get():
            # Walk through all subdirectories with error handling
            try:
                for root, _, files in os.walk(normalized_directory):
                    try:
                        # Normalize the root path for each iteration
                        normalized_root = self.normalize_long_path(root)
                        print(f"Searching in subdirectory: {normalized_root}")
                        
                        for file in files:
                            if file.lower().endswith(('.csv', '.tsv')):
                                # Use normpath to ensure consistent path separators
                                full_path = os.path.normpath(os.path.join(normalized_root, file))
                                
                                # Additional path validation
                                if os.path.exists(full_path):
                                    self.parent_app.csv_files.append(full_path)
                                    print(f"Found file: {full_path}")
                    except PermissionError:
                        print(f"Permission denied accessing directory: {normalized_root}")
                    except Exception as dir_error:
                        print(f"Error searching directory {normalized_root}: {dir_error}")
                
                print(f"Found {len(self.parent_app.csv_files)} CSV/TSV files in all subfolders")
            except Exception as walk_error:
                print(f"Critical error during file walk: {walk_error}")
                self.parent_app.csv_files = []
        else:
            # Only get files in current directory
            try:
                files = os.listdir(normalized_directory)
                # Use normpath for consistent path separators
                self.parent_app.csv_files = [
                    os.path.normpath(os.path.join(normalized_directory, f)) 
                    for f in files 
                    if f.lower().endswith(('.csv', '.tsv')) and os.path.isfile(os.path.join(normalized_directory, f))
                ]
                print(f"Found {len(self.parent_app.csv_files)} CSV/TSV files in current directory")
            except PermissionError:
                print(f"Permission denied accessing directory: {normalized_directory}")
                self.parent_app.csv_files = []
            except Exception as list_error:
                print(f"Error listing directory: {list_error}")
                self.parent_app.csv_files = []
        
        # Print out all found files for verification
        for file in self.parent_app.csv_files:
            print(f"Discovered file: {file}")
        
        if not self.parent_app.csv_files:
            print("WARNING: No CSV or TSV files found. Check directory path and permissions.")

    def get_max_fields(self):
        """Get the maximum number of underscore-separated fields in filenames"""
        max_fields = 0
        for file_path in self.parent_app.csv_files:
            # Get just the filename without path
            file_name = os.path.basename(file_path)
            # Remove extension and split by underscore
            name_without_ext = os.path.splitext(file_name)[0]
            fields = name_without_ext.split('_')
            
            # Add all field columns at once
            for i in range(len(fields)):
                max_fields = max(max_fields, i+1)
        
        # Ensure at least 25 fields even if directory is empty
        max_fields = max(max_fields, 25)
        print(f"Max fields found: {max_fields}")  # Debug print
        return max_fields

    def filter_files(self, *args):
        """Filter files based on the current filter text"""
        filter_text = self.parent_app.filter_text.get().lower()
        
        if not filter_text:
            # Show all files if no filter is applied
            self.parent_app.filtered_csv_files = self.parent_app.csv_files
        else:
            # Filter files that match the filter text
            self.parent_app.filtered_csv_files = [
                file for file in self.parent_app.csv_files 
                if filter_text in os.path.basename(file).lower()
            ]
        
        # Update the file list table
        self.parent_app.update_file_list_table()