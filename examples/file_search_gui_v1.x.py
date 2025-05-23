# live monitoring 

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from pathlib import Path
import threading
import fnmatch
import os
import subprocess
import sys
import re
import shutil
from datetime import datetime

class CreateToolTip(object):
    """
    Create a tooltip for a given widget with delayed show/hide
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # miliseconds
        self.wraplength = 300   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        if self.tw:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 5
        y = self.widget.winfo_rooty()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        
        # Create tooltip content
        label = ttk.Label(self.tw, text=self.text, justify=tk.LEFT,
                         wraplength=self.wraplength, padding=(5, 2))
        label.grid(row=0, column=0)
        
        # Style the tooltip
        self.tw.configure(background='#ffffe0')
        style = ttk.Style(self.tw)
        style.configure('Tooltip.TLabel', 
                      background='#ffffe0',
                      foreground='black',
                      font=('Segoe UI', 9))
        label.configure(style='Tooltip.TLabel')
        
        # Position the tooltip
        self.tw.wm_geometry(f"+{x}+{y}")
        self.tw.lift()

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()

class FileSearchGUI:
    def __init__(self, root):
        # Convert root to Tix root if it's not already
        if not isinstance(root, tk.Tk):
            self.root = tk.Tk()
            self.root.geometry(root.geometry())
        else:
            self.root = root
            
        self.root.title("File Search Tool")
        self.root.geometry("800x600")
        
        # Initialize file paths dictionary
        self.file_paths = {}
        
        # Make the root window resizable
        self.root.resizable(True, True)
        
        # Create main frame with padding and expansion
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # Create a frame for input controls
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=0, column=0, sticky='ew')
        
        # Directory selection
        ttk.Label(input_frame, text="Search Directory:").grid(row=0, column=0, sticky='w', pady=2)
        self.dir_path = tk.StringVar()
        dir_entry = ttk.Entry(input_frame, textvariable=self.dir_path)
        dir_entry.grid(row=0, column=1, sticky='ew', padx=(5, 5))
        ttk.Button(input_frame, text="Browse", command=self.browse_directory).grid(row=0, column=2, padx=5, sticky='w')
        
        # File pattern
        ttk.Label(input_frame, text="File Pattern:").grid(row=1, column=0, sticky='w', pady=2)
        self.file_pattern = tk.StringVar(value="*")  # Default to show all files
        self.file_pattern.trace_add("write", self.on_pattern_change)
        pattern_entry = ttk.Entry(input_frame, textvariable=self.file_pattern, width=200)
        pattern_entry.grid(row=1, column=1, columnspan=2, sticky='w', padx=(5, 5))
        
        # Add tooltips
        CreateToolTip(pattern_entry,
            "Enter file patterns to filter files:\n" +
            "- Type text to match anywhere: rx3 (matches files containing 'rx3')\n" +
            "- Use * for wildcards: *.txt, test.py\n" +
            "- Space for AND: rx3 tx4 (matches files containing both)\n" +
            "- | for OR: rx3|tx4 (matches either)\n" +
            "- ! to exclude: !test (excludes files containing 'test')\n" +
            "- Exclude directories: !results or !results/\n" +
            "- Exclude nested directories: !**/results\n" +
            "Examples:\n" +
            "- rx3|tx4 !temp\n" +
            "- data !results\n" +
            "- rx3 !backup")
        
        # Search keyword row (with case sensitive and search button)
        ttk.Label(input_frame, text="Search inside files:").grid(row=2, column=0, sticky='w', pady=2)
        self.keyword = tk.StringVar()
        search_entry = ttk.Entry(input_frame, textvariable=self.keyword, width=200)  # Fixed width
        search_entry.grid(row=2, column=1, columnspan=2, sticky='w', padx=(5, 5))
        
        # Add tooltip for search entry
        CreateToolTip(search_entry,
            "Enter search terms to find in files:\n" +
            "- Single term: error\n" +
            "- Multiple terms (OR): error OR warning\n" +
            "- Alternative syntax: error|warning\n" +
            "- Multiple OR terms: error|warning|fatal\n" +
            "Use checkboxes below to:\n" +
            "- Filter case sensitivity\n" +
            "- Show only first/last matches")
        
        # Create a frame for checkboxes and button
        controls_frame = ttk.Frame(input_frame)
        controls_frame.grid(row=2, column=2, sticky='w')
        
        # Case sensitivity checkbox in controls frame
        self.case_sensitive = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Case Sensitive", variable=self.case_sensitive).pack(side='left', padx=(0, 5))
        
        # First/Last result checkboxes
        self.show_first = tk.BooleanVar(value=False)
        self.show_last = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="1st match", variable=self.show_first).pack(side='left', padx=(0, 5))
        ttk.Checkbutton(controls_frame, text="Last match", variable=self.show_last).pack(side='left', padx=(0, 5))
        
        # Simple results checkbox
        self.simple_results = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Simple Results", variable=self.simple_results).pack(side='left', padx=(0, 5))
        
        # Auto-refresh controls
        self.auto_refresh = tk.BooleanVar(value=False)
        self.auto_refresh_interval = tk.StringVar(value="60")
        auto_refresh_frame = ttk.Frame(controls_frame)
        auto_refresh_frame.pack(side='left', padx=(5, 0))
        ttk.Checkbutton(auto_refresh_frame, text="Auto-refresh", variable=self.auto_refresh, command=self.toggle_auto_refresh).pack(side='left')
        ttk.Entry(auto_refresh_frame, textvariable=self.auto_refresh_interval, width=4).pack(side='left', padx=(2, 0))
        ttk.Label(auto_refresh_frame, text="s").pack(side='left')
        
        # Search button in controls frame
        ttk.Button(controls_frame, text="Search", command=self.start_search).pack(side='left')
        
        # Generate Code button
        ttk.Button(controls_frame, text="Generate Code", command=self.generate_search_code).pack(side='left', padx=(5, 0))
        
        # Configure column weights
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky='nsew')
        
        # Filtered files frame
        filtered_frame = ttk.LabelFrame(paned, text="Filtered Files", padding=(5, 5, 5, 5))
        
        # Create filtered files listbox with scrollbar
        listbox_frame = ttk.Frame(filtered_frame)
        listbox_frame.pack(fill='both', expand=True)
        
        # Create treeview with columns
        columns = ('size', 'date', 'path')
        self.filtered_files = ttk.Treeview(listbox_frame, columns=columns, show='headings', height=10,
                                         selectmode='extended')  # Allow multiple selections
        
        # Define column headings and widths
        self.filtered_files.heading('size', text='Size', anchor='w', command=lambda: self.sort_treeview('size', False))
        self.filtered_files.heading('date', text='Modified', anchor='w', command=lambda: self.sort_treeview('date', False))
        self.filtered_files.heading('path', text='File Name', anchor='w', command=lambda: self.sort_treeview('path', False))
        
        # Configure column properties
        self.filtered_files.column('size', width=80, minwidth=80, stretch=False, anchor='w')
        self.filtered_files.column('date', width=140, minwidth=140, stretch=False, anchor='w')
        self.filtered_files.column('path', width=400, minwidth=200, stretch=True, anchor='w')
        
        # Add scrollbars
        yscrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.filtered_files.yview)
        xscrollbar = ttk.Scrollbar(listbox_frame, orient="horizontal", command=self.filtered_files.xview)
        self.filtered_files.configure(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
        
        # Layout with scrollbars
        self.filtered_files.grid(row=0, column=0, sticky='nsew')
        yscrollbar.grid(row=0, column=1, sticky='ns')
        xscrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights for proper expansion
        listbox_frame.grid_rowconfigure(0, weight=1)
        listbox_frame.grid_columnconfigure(0, weight=1)
        
        # Create right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open with Notepad++", command=self.open_with_notepadpp)
        self.context_menu.add_command(label="Open with Default App", command=self.open_with_default)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Show in Explorer", command=self.show_in_explorer)
        self.context_menu.add_separator()
        # Store menu indices for dynamic updates
        self.copy_menu_index = self.context_menu.index(tk.END) + 1
        self.context_menu.add_command(label="Copy to...", command=self.copy_file)
        self.move_menu_index = self.context_menu.index(tk.END) + 1
        self.context_menu.add_command(label="Move to...", command=self.move_file)
        self.context_menu.add_separator()
        self.delete_menu_index = self.context_menu.index(tk.END) + 1
        self.context_menu.add_command(label="Delete", command=self.delete_file)
        
        # Bind events to filtered files treeview
        self.filtered_files.bind('<Button-3>', self.show_context_menu)
        self.filtered_files.bind('<Double-Button-1>', self.on_double_click)
        
        # Results frame
        results_frame = ttk.LabelFrame(paned, text="Search Results (Click to open file)", padding=(5, 5, 5, 5))
        
        # Create results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD)
        self.results_text.pack(fill='both', expand=True)
        
        # Add tooltips
        CreateToolTip(self.results_text,
            "Search results are displayed here.\n" +
            "Click on a file path to open the file.")
        
        # Add frames to paned window with adjusted weights
        paned.add(filtered_frame, weight=1)
        paned.add(results_frame, weight=3)
        
        # Bind click event
        self.results_text.tag_configure("clickable", foreground="blue", underline=1)
        self.results_text.tag_bind("clickable", "<Button-1>", self.on_click)
        self.results_text.tag_bind("clickable", "<Enter>", lambda e: self.results_text.configure(cursor="hand2"))
        self.results_text.tag_bind("clickable", "<Leave>", lambda e: self.results_text.configure(cursor=""))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief='sunken')
        self.status_bar.grid(row=2, column=0, sticky='ew', pady=(5, 0))
        
        # Configure weights for resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Configure main_frame grid weights - only row 1 (paned window) should expand
        main_frame.grid_rowconfigure(0, weight=0)  # input frame - fixed height
        main_frame.grid_rowconfigure(1, weight=1)  # paned window - expandable
        main_frame.grid_rowconfigure(2, weight=0)  # status bar - fixed height
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Store file locations for clicking
        self.file_locations = {}
        self.next_tag_id = 0
        
        # Update filtered files on startup
        self.update_filtered_files()

    def on_pattern_change(self, *_):
        """Called when the file pattern is changed"""
        self.update_filtered_files()

    def matches_patterns(self, filename, patterns):
        """Check if filename matches patterns, supporting AND (space), OR (|), and exclusion (!)"""
        # First split by spaces (AND operator)
        and_patterns = [p.strip().lower() for p in patterns.split()]
        filename_lower = filename.lower()
        
        # For each AND pattern, check if it matches (considering OR and exclusion)
        for pattern_group in and_patterns:
            # Split by | for OR patterns
            or_patterns = pattern_group.split('|')
            
            # Split into include and exclude OR patterns and add wildcards for inclusive matching
            include_patterns = []
            exclude_patterns = []
            for p in or_patterns:
                if p.startswith('!'):
                    # For exclusion patterns, add wildcards if not already a wildcard pattern
                    p = p[1:]  # Remove !
                    if not any(c in p for c in '*?[]'):
                        # For directories, match the path segment
                        if '/' in p:
                            exclude_patterns.append(p)
                        else:
                            # Add trailing slash to ensure we match directory names
                            exclude_patterns.append(f"{p}/")
                            # Also match the pattern in filenames
                            exclude_patterns.append(f"*{p}*")
                    else:
                        exclude_patterns.append(p)
                else:
                    # For inclusion patterns, add wildcards if not already a wildcard pattern
                    if not any(c in p for c in '*?[]'):
                        p = f'*{p}*'
                    include_patterns.append(p)
            
            # Check exclusion patterns first
            for pattern in exclude_patterns:
                if '/' in pattern:
                    # For directory patterns, check if it's part of the path
                    pattern = pattern.rstrip('/')  # Remove trailing slash for comparison
                    if f"/{pattern}/" in f"/{filename_lower}/":
                        return False
                elif fnmatch.fnmatch(filename_lower, pattern):
                    return False  # File matches an exclude pattern
            
            # If there are no include patterns in this group, it's implicitly included
            if not include_patterns:
                continue
                
            # Check if file matches any of the include patterns
            matches_include = False
            for pattern in include_patterns:
                if fnmatch.fnmatch(filename_lower, pattern):
                    matches_include = True
                    break
            
            if not matches_include:
                return False  # File doesn't match any include pattern in this group
        
        # All AND groups matched
        return True

    def format_size(self, size):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:6.1f} {unit}"
            size /= 1024
        return f"{size:6.1f} TB"

    def format_date(self, timestamp):
        """Format modification date"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def update_filtered_files(self):
        """Update the list of filtered files based on current pattern"""
        search_path = self.dir_path.get()
        file_pattern = self.file_pattern.get()
        
        # Clear the list
        for item in self.filtered_files.get_children():
            self.filtered_files.delete(item)
        
        if not search_path:
            return
            
        try:
            # Store full paths for lookup
            self.file_paths = {}  # Reset file paths dictionary
            error_count = 0
            
            # Walk through directory and find matching files
            for root, _, files in os.walk(search_path):
                for filename in files:
                    try:
                        full_path = os.path.abspath(os.path.join(root, filename))
                        rel_path = os.path.relpath(full_path, search_path)
                        
                        # Check if the relative path matches the pattern
                        if self.matches_patterns(rel_path.replace('\\', '/'), file_pattern):
                            try:
                                stat = os.stat(full_path)
                                size = self.format_size(stat.st_size)
                                mtime = self.format_date(stat.st_mtime)
                                
                                # Insert into treeview
                                self.file_paths[rel_path] = full_path
                                self.filtered_files.insert('', 'end', values=(size, mtime, rel_path))
                            except (OSError, IOError) as e:
                                error_count += 1
                    except (OSError, IOError) as e:
                        error_count += 1
            
            # Sort by date by default (newest first)
            self.sort_treeview('date', True)
            
            # Update status with file count and errors
            file_count = len(self.filtered_files.get_children())
            status = f"Found {file_count} matching file{'s' if file_count != 1 else ''}"
            if error_count > 0:
                status += f" ({error_count} access error{'s' if error_count != 1 else ''})"
            self.status_var.set(status)
        except (PermissionError, OSError) as e:
            self.status_var.set(f"Error accessing directory: {str(e)}")

    def get_selected_files(self):
        """Get a list of selected file paths from the filtered files treeview"""
        try:
            # Get selected items
            selections = self.filtered_files.selection()
            if not selections:
                return []
            
            # Get file paths from selected items
            selected_files = []
            for item in selections:
                # Get values from the selected item
                values = self.filtered_files.item(item)['values']
                if not values:
                    continue
                
                # File path is the third column
                rel_path = values[2]
                
                # Get the full path from our stored mapping
                full_path = self.file_paths.get(rel_path)
                if full_path and os.path.isfile(full_path):
                    selected_files.append(full_path)
            
            return selected_files
            
        except Exception as e:
            print(f"Error getting selected files: {str(e)}")
            return []

    def get_selected_file(self):
        """Get the selected file path from the filtered files treeview"""
        try:
            # Get selected item
            selection = self.filtered_files.selection()
            if not selection:
                return None
            
            # Get values from the selected item
            values = self.filtered_files.item(selection[0])['values']
            if not values:
                return None
            
            # File path is the third column
            rel_path = values[2]
            
            # Get the full path from our stored mapping
            full_path = self.file_paths.get(rel_path)
            if full_path and os.path.isfile(full_path):
                return full_path
            
            return None
            
        except Exception as e:
            print(f"Error getting selected file: {str(e)}")
            return None

    def safe_update_results(self, text, clickable=False, filepath=None, line_number=None):
        """Thread-safe update of results text widget"""
        def update():
            if self.simple_results.get():
                # For simple results, only show the matched line
                if clickable and text.strip():  # Only show non-empty lines
                    self.results_text.insert("end", text + "\n")
            else:
                # Normal display with all context
                if clickable:
                    tag = f"clickable_{self.next_tag_id}"
                    self.next_tag_id += 1
                    self.file_locations[tag] = (filepath, line_number)
                    
                    start = self.results_text.index("end-1c")
                    self.results_text.insert("end", text + "\n")
                    end = self.results_text.index("end-1c")
                    self.results_text.tag_add(tag, start, end)
                    self.results_text.tag_add("clickable", start, end)
                else:
                    self.results_text.insert("end", text + "\n")
        
        self.root.after(0, update)

    def open_file(self, filepath, line_number):
        try:
            if sys.platform == 'win32':
                os.startfile(filepath)
            else:
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', filepath])
                else:  # linux
                    subprocess.run(['xdg-open', filepath])
            self.status_var.set(f"Opened {filepath}")
        except Exception as e:
            self.status_var.set(f"Error opening file: {str(e)}")

    def on_click(self, event):
        for tag in self.results_text.tag_names(tk.CURRENT):
            if tag.startswith("clickable_"):
                filepath, line_number = self.file_locations[tag]
                self.open_file(filepath, line_number)
                break

    def matches_search_terms(self, line, search_terms, case_sensitive):
        """Check if line matches any of the search terms (OR logic) and return matching terms"""
        matches = []
        line_to_search = line if case_sensitive else line.lower()
        for term in search_terms:
            term_to_search = term if case_sensitive else term.lower()
            if term_to_search in line_to_search:
                matches.append(term)  # Add all matching terms for OR logic
        return matches

    def split_search_terms(self, keyword):
        """Split search string into terms using OR or | as delimiters"""
        if not keyword:
            return []
            
        # Replace 'OR' with '|' for consistent splitting
        # Handle both uppercase and mixed case 'OR'
        keyword = keyword.replace(' OR ', '|').replace(' Or ', '|').replace(' or ', '|')
        
        # Split on '|' and clean up terms
        terms = []
        for term in keyword.split('|'):
            term = term.strip()
            if term:  # Only add non-empty terms
                terms.append(term)
        return terms

    def search_files(self, search_path, file_pattern, keyword, case_sensitive=False):
        """Search for keyword in files"""
        try:
            # Clear previous results
            self.results_text.delete('1.0', tk.END)
            self.file_locations.clear()
            self.next_tag_id = 0
            
            if not keyword:
                return
            
            search_terms = self.split_search_terms(keyword)
            if not search_terms:
                self.status_var.set("No search terms provided")
                return
                
            files_searched = 0
            matches_found = 0
            
            # Get list of files from treeview
            for item in self.filtered_files.get_children():
                rel_path = self.filtered_files.item(item)['values'][2]  # Path is the third column
                full_path = self.file_paths.get(rel_path)
                if not full_path:
                    continue
                
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        files_searched += 1
                        lines = f.readlines()
                        
                        # Track matches for first/last options
                        file_matches = []
                        
                        for i, line in enumerate(lines, 1):
                            matching_terms = self.matches_search_terms(line, search_terms, case_sensitive)
                            if matching_terms:
                                matches_found += 1
                                file_matches.append((i, line.strip(), matching_terms))
                        
                        # Process matches based on first/last options
                        if file_matches:
                            if not self.simple_results.get():
                                self.safe_update_results(f"\nIn {rel_path}:")
                            
                            matches_to_show = []
                            if self.show_first.get():
                                matches_to_show.append(file_matches[0])
                            if self.show_last.get() and len(file_matches) > 1:
                                # Show only first and last match
                                matches_to_show.append(file_matches[-1])
                            if not self.show_first.get() and not self.show_last.get():
                                matches_to_show = file_matches
                            
                            for line_num, line_text, terms in matches_to_show:
                                if self.simple_results.get():
                                    self.safe_update_results(f"{line_text}", True, full_path, line_num)
                                else:
                                    term_str = " or ".join(terms)
                                    self.safe_update_results(f"Line {line_num} (matches: {term_str}): {line_text}", True, full_path, line_num)
                
                except Exception as e:
                    if not self.simple_results.get():
                        self.safe_update_results(f"\nError reading {rel_path}: {str(e)}")
            
            # Update status
            status = f"Searched {files_searched} files, found {matches_found} matches"
            self.status_var.set(status)
            
        except Exception as e:
            self.status_var.set(f"Search error: {str(e)}")

    def update_results(self, text):
        self.results_text.insert(tk.END, text)
        self.results_text.see(tk.END)
        self.results_text.update_idletasks()

    def start_search(self):
        # Get search parameters
        search_path = self.dir_path.get()
        file_pattern = self.file_pattern.get()
        keyword = self.keyword.get()
        case_sensitive = self.case_sensitive.get()
        
        if not search_path or not keyword:
            self.results_text.delete(1.0, tk.END)
            self.update_results("Error: Please provide both search directory and keyword\n")
            self.status_var.set("Ready")
            return
        
        # Clear previous results and file locations
        self.results_text.delete(1.0, tk.END)
        self.file_locations.clear()
        self.next_tag_id = 0
        
        # Update status
        self.status_var.set("Searching...")
        
        # Start search in a separate thread
        thread = threading.Thread(
            target=self.search_files,
            args=(search_path, file_pattern, keyword, case_sensitive)
        )
        thread.daemon = True
        thread.start()

    def toggle_auto_refresh(self):
        if self.auto_refresh.get():
            try:
                interval = int(self.auto_refresh_interval.get())
                if interval < 1:
                    raise ValueError("Interval must be positive")
                self.schedule_auto_refresh()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid positive number for refresh interval")
                self.auto_refresh.set(False)
        else:
            if hasattr(self, '_auto_refresh_id'):
                self.root.after_cancel(self._auto_refresh_id)
                self._auto_refresh_id = None

    def schedule_auto_refresh(self):
        if self.auto_refresh.get():
            self.start_search()
            interval = int(self.auto_refresh_interval.get()) * 1000  # Convert to milliseconds
            self._auto_refresh_id = self.root.after(interval, self.schedule_auto_refresh)

    def show_context_menu(self, event):
        """Show the context menu on right click"""
        try:
            # Identify the item under cursor
            item = self.filtered_files.identify_row(event.y)
            if not item:  # No item under cursor
                return
                
            # If the item under cursor isn't selected, clear selection and select only this item
            if item not in self.filtered_files.selection():
                self.filtered_files.selection_set(item)
            # Otherwise keep the current multiple selection
            
            self.filtered_files.focus(item)
            
            # Get the file paths and verify at least one exists
            if self.get_selected_files():
                # Update menu labels based on selection count
                count = len(self.filtered_files.selection())
                if count > 1:
                    self.context_menu.entryconfig(self.copy_menu_index, 
                        label=f"Copy {count} files to...")
                    self.context_menu.entryconfig(self.move_menu_index, 
                        label=f"Move {count} files to...")
                    self.context_menu.entryconfig(self.delete_menu_index, 
                        label=f"Delete {count} files")
                else:
                    self.context_menu.entryconfig(self.copy_menu_index, 
                        label="Copy to...")
                    self.context_menu.entryconfig(self.move_menu_index, 
                        label="Move to...")
                    self.context_menu.entryconfig(self.delete_menu_index, 
                        label="Delete")
                
                # Position menu at mouse coordinates
                self.context_menu.post(event.x_root, event.y_root)
            
        except Exception as e:
            print(f"Error showing context menu: {str(e)}")
        finally:
            # Make sure to release the grab
            self.context_menu.grab_release()

    def on_double_click(self, event):
        """Handle double-click on filtered files listbox"""
        file_path = self.get_selected_file()
        if file_path:
            self.open_with_default()

    def open_with_notepadpp(self):
        """Open selected file with Notepad++"""
        file_path = self.get_selected_file()
        if file_path:
            try:
                subprocess.Popen([r"C:\Program Files\Notepad++\notepad++.exe", file_path])
            except FileNotFoundError:
                messagebox.showerror("Error", "Notepad++ is not installed or not in PATH")
                try:
                    # Try opening with regular Notepad as fallback
                    subprocess.Popen(['notepad.exe', file_path])
                except:
                    messagebox.showerror("Error", "Failed to open file with Notepad")

    def show_in_explorer(self):
        """Show selected file in Windows Explorer"""
        file_path = self.get_selected_file()
        if file_path:
            try:
                subprocess.Popen(f'explorer /select,"{file_path}"')
            except:
                messagebox.showerror("Error", "Failed to open File Explorer")

    def open_with_default(self):
        """Open selected file with default application"""
        file_path = self.get_selected_file()
        if file_path:
            try:
                os.startfile(file_path)
            except:
                messagebox.showerror("Error", "Failed to open file with default application")

    def copy_file(self):
        """Copy selected files to a chosen destination"""
        file_paths = self.get_selected_files()
        if not file_paths:
            return
            
        try:
            # Ask user for destination directory
            dest_dir = filedialog.askdirectory(title="Select Destination Directory")
            if not dest_dir:
                return
            
            # Track success and failures
            success_count = 0
            failed_files = []
            
            for file_path in file_paths:
                try:
                    # Get file name from path
                    file_name = os.path.basename(file_path)
                    dest_path = os.path.join(dest_dir, file_name)
                    
                    # Check if destination file already exists
                    if os.path.exists(dest_path):
                        if not messagebox.askyesno("File Exists", 
                            f"File '{file_name}' already exists in destination.\nDo you want to replace it?"):
                            failed_files.append(f"{file_name} (Skipped)")
                            continue
                    
                    # Copy the file
                    shutil.copy2(file_path, dest_path)
                    success_count += 1
                    
                except Exception as e:
                    failed_files.append(f"{file_name} ({str(e)})")
            
            # Show summary message
            message = f"Successfully copied {success_count} file(s) to:\n{dest_dir}"
            if failed_files:
                message += "\n\nFailed to copy:\n" + "\n".join(failed_files)
            
            if success_count > 0:
                messagebox.showinfo("Copy Complete", message)
            else:
                messagebox.showerror("Copy Failed", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy files:\n{str(e)}")

    def move_file(self):
        """Move selected files to a chosen destination"""
        file_paths = self.get_selected_files()
        if not file_paths:
            return
            
        try:
            # Ask user for destination directory
            dest_dir = filedialog.askdirectory(title="Select Destination Directory")
            if not dest_dir:
                return
            
            # Track success and failures
            success_count = 0
            failed_files = []
            
            for file_path in file_paths:
                try:
                    # Get file name from path
                    file_name = os.path.basename(file_path)
                    dest_path = os.path.join(dest_dir, file_name)
                    
                    # Check if destination file already exists
                    if os.path.exists(dest_path):
                        if not messagebox.askyesno("File Exists", 
                            f"File '{file_name}' already exists in destination.\nDo you want to replace it?"):
                            failed_files.append(f"{file_name} (Skipped)")
                            continue
                    
                    # Move the file
                    shutil.move(file_path, dest_path)
                    success_count += 1
                    
                except Exception as e:
                    failed_files.append(f"{file_name} ({str(e)})")
            
            # Show summary message
            message = f"Successfully moved {success_count} file(s) to:\n{dest_dir}"
            if failed_files:
                message += "\n\nFailed to move:\n" + "\n".join(failed_files)
            
            if success_count > 0:
                messagebox.showinfo("Move Complete", message)
            else:
                messagebox.showerror("Move Failed", message)
            
            # Update the file list since we moved files
            self.update_filtered_files()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move files:\n{str(e)}")

    def delete_file(self):
        """Delete selected files"""
        file_paths = self.get_selected_files()
        if not file_paths:
            return
            
        try:
            # Confirm deletion
            file_count = len(file_paths)
            if not messagebox.askyesno("Confirm Delete", 
                f"Are you sure you want to delete {file_count} file(s)?\nThis cannot be undone."):
                return
            
            # Track success and failures
            success_count = 0
            failed_files = []
            
            for file_path in file_paths:
                try:
                    # Get file name for display
                    file_name = os.path.basename(file_path)
                    
                    # Delete the file
                    os.remove(file_path)
                    success_count += 1
                    
                except Exception as e:
                    failed_files.append(f"{file_name} ({str(e)})")
            
            # Show summary message
            message = f"Successfully deleted {success_count} file(s)"
            if failed_files:
                message += "\n\nFailed to delete:\n" + "\n".join(failed_files)
            
            if success_count > 0:
                messagebox.showinfo("Delete Complete", message)
            else:
                messagebox.showerror("Delete Failed", message)
            
            # Update the file list since we deleted files
            self.update_filtered_files()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete files:\n{str(e)}")

    def browse_directory(self):
        """Browse for a directory and update the file list"""
        directory = filedialog.askdirectory()
        if directory:
            self.dir_path.set(directory)
            self.update_filtered_files()  # Update files when directory changes

    def sort_treeview(self, col, reverse):
        """Sort treeview by column"""
        # Get all items
        items = [(self.filtered_files.set(item, col), item) for item in self.filtered_files.get_children('')]
        
        # Custom sort for size column
        if col == 'size':
            # Convert size strings to bytes for sorting
            def size_to_bytes(size_str):
                try:
                    number = float(''.join(c for c in size_str if c.isdigit() or c == '.'))
                    unit = size_str.strip('0123456789. ')
                    multiplier = {
                        'B': 1,
                        'KB': 1024,
                        'MB': 1024**2,
                        'GB': 1024**3,
                        'TB': 1024**4
                    }.get(unit.upper(), 1)
                    return number * multiplier
                except:
                    return 0
            
            items = [(size_to_bytes(item[0]), item[1]) for item in items]
        
        # Custom sort for date column
        elif col == 'date':
            # Convert date strings to timestamps for sorting
            def date_to_timestamp(date_str):
                try:
                    from datetime import datetime
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').timestamp()
                except:
                    return 0
            
            items = [(date_to_timestamp(item[0]), item[1]) for item in items]
        
        # Sort the items
        items.sort(reverse=reverse)
        
        # Rearrange items in sorted positions
        for index, (val, item) in enumerate(items):
            self.filtered_files.move(item, '', index)
        
        # Reverse sort next time
        self.filtered_files.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def generate_search_code(self):
        """Generate a standalone Python script that reproduces the current search configuration"""
        search_path = self.dir_path.get()
        if not search_path:
            messagebox.showerror("Error", "Please select a search directory first")
            return
            
        file_pattern = self.file_pattern.get()
        keyword = self.keyword.get()
        case_sensitive = self.case_sensitive.get()
        show_first = self.show_first.get()
        show_last = self.show_last.get()
        simple_results = self.simple_results.get()

        # Save the generated code in the search directory
        output_path = os.path.join(search_path, 'generated_code.py')

        code_template = f'''# Generated search script
import os
import fnmatch
import re
from datetime import datetime

def format_size(size):
    """Format file size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{{size:.1f}} {{unit}}"
        size /= 1024
    return f"{{size:.1f}} TB"

def search_files():
    search_path = r"{search_path}"
    file_pattern = "{file_pattern}"
    keyword = "{keyword}"
    case_sensitive = {case_sensitive}
    show_first = {show_first}
    show_last = {show_last}
    simple_results = {simple_results}

    # Compile regex pattern for keyword if provided
    if keyword:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(keyword, flags)
        except re.error:
            print(f"Invalid regex pattern: {{keyword}}")
            return

    # Walk through directory
    for root, _, files in os.walk(search_path):
        for filename in fnmatch.filter(files, file_pattern):
            filepath = os.path.join(root, filename)
            
            try:
                # Get file info
                stat = os.stat(filepath)
                size = format_size(stat.st_size)
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                if not keyword:
                    # If no keyword search, just print file info
                    if simple_results:
                        print(filepath)
                    else:
                        print(f"{{size:>10}} | {{modified}} | {{filepath}}")
                    continue

                # Search for keyword in file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        matches = []
                        
                        for i, line in enumerate(lines, 1):
                            if pattern.search(line):
                                matches.append((i, line.strip()))
                        
                        if matches:
                            if simple_results:
                                print(filepath)
                                continue

                            print(f"\\nFile: {{filepath}}")
                            print(f"Size: {{size}}, Modified: {{modified}}")
                            
                            if show_first and show_last and len(matches) > 2:
                                # Show only first and last match
                                print(f"Line {{matches[0][0]}}: {{matches[0][1]}}")
                                print("...")
                                print(f"Line {{matches[-1][0]}}: {{matches[-1][1]}}")
                            elif show_first and matches:
                                # Show only first match
                                print(f"Line {{matches[0][0]}}: {{matches[0][1]}}")
                            elif show_last and matches:
                                # Show only last match
                                print(f"Line {{matches[-1][0]}}: {{matches[-1][1]}}")
                            else:
                                # Show all matches
                                for line_num, line in matches:
                                    print(f"Line {{line_num}}: {{line}}")
                            
                except (UnicodeDecodeError, IOError) as e:
                    print(f"Error reading {{filepath}}: {{e}}")
                    
            except OSError as e:
                print(f"Error accessing {{filepath}}: {{e}}")

if __name__ == '__main__':
    search_files()
'''
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(code_template)
            self.status_var.set(f"Search code generated: {output_path}")
        except IOError as e:
            messagebox.showerror("Error", f"Failed to save generated code: {e}")

def main():
    root = tk.Tk()
    app = FileSearchGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()