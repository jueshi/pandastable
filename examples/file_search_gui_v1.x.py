import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path
import threading
import fnmatch
import os
import subprocess
import sys
import re
from tkinter import messagebox

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
            "- Use * as wildcard: *.txt, *.py\n" +
            "- Multiple patterns: *.txt *.py\n" +
            "- All files: *.*\n" +
            "- Specific names: test*.py, data.*")
        
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
        
        # Search button in controls frame
        ttk.Button(controls_frame, text="Search", command=self.start_search).pack(side='left')
        
        # Configure column weights
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky='nsew', pady=(10, 0))
        
        # Filtered files frame
        filtered_frame = ttk.LabelFrame(paned, text="Filtered Files", padding=(5, 5, 5, 5))
        
        # Create filtered files listbox with scrollbar
        listbox_frame = ttk.Frame(filtered_frame)
        listbox_frame.pack(fill='both', expand=True)
        
        self.filtered_files = tk.Listbox(listbox_frame, selectmode=tk.BROWSE, cursor="hand2")
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.filtered_files.yview)
        self.filtered_files.configure(yscrollcommand=scrollbar.set)
        
        self.filtered_files.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open with Notepad++", command=self.open_with_notepadpp)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Show in Explorer", command=self.show_in_explorer)
        self.context_menu.add_command(label="Open with Default App", command=self.open_with_default)
        
        # Bind events to filtered files listbox
        self.filtered_files.bind('<Button-3>', self.show_context_menu)
        self.filtered_files.bind('<Double-Button-1>', self.on_double_click)
        
        # Results frame
        results_frame = ttk.LabelFrame(paned, text="Search Results (Click to open file)", padding=(5, 5, 5, 5))
        
        # Create results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, height=20)
        self.results_text.pack(fill='both', expand=True)
        
        # Add frames to paned window
        paned.add(filtered_frame, weight=1)
        paned.add(results_frame, weight=2)
        
        # Bind click event
        self.results_text.tag_configure("clickable", foreground="blue", underline=1)
        self.results_text.tag_bind("clickable", "<Button-1>", self.on_click)
        self.results_text.tag_bind("clickable", "<Enter>", lambda e: self.results_text.configure(cursor="hand2"))
        self.results_text.tag_bind("clickable", "<Leave>", lambda e: self.results_text.configure(cursor=""))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief='sunken')
        self.status_bar.grid(row=3, column=0, sticky='ew', pady=(5, 0))
        
        # Configure weights for resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Store file locations for clicking
        self.file_locations = {}
        self.next_tag_id = 0
        
        # Update filtered files on startup
        self.update_filtered_files()

    def on_pattern_change(self, *_):
        """Called when the file pattern is changed"""
        self.update_filtered_files()

    def matches_patterns(self, filename, patterns):
        """Check if filename matches all space-separated patterns"""
        patterns = [p.strip().lower() for p in patterns.split()]
        filename_lower = filename.lower()
        return all(pattern in filename_lower or fnmatch.fnmatch(filename_lower, pattern) for pattern in patterns)

    def update_filtered_files(self):
        """Update the list of filtered files based on current pattern"""
        search_path = self.dir_path.get()
        file_pattern = self.file_pattern.get()
        
        # Clear the list
        self.filtered_files.delete(0, tk.END)
        
        if not search_path:
            return
            
        try:
            # Store full paths for lookup
            self.file_paths = {}  # Reset file paths dictionary
            
            # Walk through directory and find matching files
            for root, _, files in os.walk(search_path):
                matched_files = [f for f in files if self.matches_patterns(f, file_pattern)]
                for filename in matched_files:
                    full_path = os.path.abspath(os.path.join(root, filename))
                    rel_path = os.path.relpath(full_path, search_path)
                    self.file_paths[rel_path] = full_path
                    self.filtered_files.insert(tk.END, rel_path)
                    
            # Update status with file count
            file_count = self.filtered_files.size()
            self.status_var.set(f"Found {file_count} matching file{'s' if file_count != 1 else ''}")
        except (PermissionError, OSError) as e:
            self.status_var.set(f"Error accessing files: {str(e)}")

    def get_selected_file(self):
        """Get the selected file path from the filtered files listbox"""
        try:
            selection = self.filtered_files.curselection()
            if not selection:
                return None
                
            rel_path = self.filtered_files.get(selection[0])
            if not rel_path:
                return None
                
            # Get the full path from our stored mapping
            full_path = self.file_paths.get(rel_path)
            if full_path and os.path.isfile(full_path):
                return full_path
                
            return None
            
        except Exception as e:
            print(f"Error getting selected file: {str(e)}")
            return None

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_path.set(directory)
            self.update_filtered_files()  # Update files when directory changes

    def safe_update_results(self, text, clickable=False, filepath=None, line_number=None):
        if clickable:
            tag_name = f"clickable_{self.next_tag_id}"
            self.next_tag_id += 1
            self.file_locations[tag_name] = (filepath, line_number)
            
            def update():
                start = self.results_text.index("end-1c")
                self.results_text.insert("end", text)
                end = self.results_text.index("end-1c")
                self.results_text.tag_add(tag_name, start, end)
                self.results_text.tag_add("clickable", start, end)
            
            self.root.after(0, update)
        else:
            self.root.after(0, lambda t=text: self.results_text.insert("end", t))

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
                matches.append(term)
        return matches

    def split_search_terms(self, keyword):
        """Split search string into terms using OR or | as delimiters"""
        # Replace 'OR' with '|' and split on '|'
        terms = []
        for term in keyword.replace(' OR ', '|').split('|'):
            term = term.strip()
            if term:  # Only add non-empty terms
                terms.append(term)
        return terms

    def search_files(self, search_path, file_pattern, keyword, case_sensitive=False):
        try:
            self.safe_update_results("Starting search...\n")
            self.safe_update_results(f"Directory: {search_path}\n")
            self.safe_update_results(f"Pattern: {file_pattern}\n")
            self.safe_update_results(f"Keyword: {keyword}\n")
            self.safe_update_results(f"Case sensitive: {case_sensitive}\n\n")

            path = Path(search_path)
            if not path.exists():
                self.safe_update_results(f"Error: Path '{search_path}' does not exist\n")
                return

            # Split keyword into search terms
            search_terms = self.split_search_terms(keyword)
            if not search_terms:
                self.safe_update_results("Error: No search terms provided\n")
                return

            # Clear filtered files list
            self.root.after(0, self.filtered_files.delete, 0, tk.END)
            
            found_matches = False
            files_searched = 0
            show_first = self.show_first.get()
            show_last = self.show_last.get()
            
            for root, _, files in os.walk(search_path):
                matched_files = [f for f in files if self.matches_patterns(f, file_pattern)]
                for filename in matched_files:
                    # Add to filtered files list
                    rel_path = os.path.relpath(os.path.join(root, filename), search_path)
                    self.root.after(0, self.filtered_files.insert, tk.END, rel_path)
                    
                    files_searched += 1
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            self.safe_update_results(f"Searching file: {file_path}\n")
                            lines = file.readlines()
                            # Dictionary to store matches for each term
                            term_matches = {}
                            
                            for line_num, line in enumerate(lines, 1):
                                matching_terms = self.matches_search_terms(line, search_terms, case_sensitive)
                                if matching_terms:
                                    for term in matching_terms:
                                        if term not in term_matches:
                                            term_matches[term] = []
                                        term_matches[term].append((line_num, line.strip()))
                            
                            if term_matches:
                                found_matches = True
                                self.safe_update_results(f"\nFound in {file_path}:\n")
                                
                                for term in search_terms:
                                    if term in term_matches:
                                        matches = term_matches[term]
                                        if show_first and not show_last:
                                            matches = [matches[0]]
                                        elif show_last and not show_first:
                                            matches = [matches[-1]]
                                        elif show_first and show_last and len(matches) > 2:
                                            matches = [matches[0], matches[-1]]
                                        
                                        self.safe_update_results(f"\n  Matches for '{term}':\n")
                                        for line_num, line_text in matches:
                                            # Highlight the current term
                                            highlighted_text = line_text
                                            if case_sensitive:
                                                start = 0
                                                while (pos := highlighted_text.find(term, start)) != -1:
                                                    highlighted_text = (
                                                        highlighted_text[:pos] + 
                                                        "**" + highlighted_text[pos:pos+len(term)] + "**" + 
                                                        highlighted_text[pos+len(term):]
                                                    )
                                                    start = pos + len(term) + 4
                                            else:
                                                text_lower = highlighted_text.lower()
                                                term_lower = term.lower()
                                                start = 0
                                                while (pos := text_lower.find(term_lower, start)) != -1:
                                                    highlighted_text = (
                                                        highlighted_text[:pos] + 
                                                        "**" + highlighted_text[pos:pos+len(term)] + "**" + 
                                                        highlighted_text[pos+len(term):]
                                                    )
                                                    start = pos + len(term) + 4
                                                    text_lower = highlighted_text.lower()
                                            
                                            self.safe_update_results("    ", clickable=False)
                                            self.safe_update_results(f"{file_path}:{line_num}", 
                                                                   clickable=True,
                                                                   filepath=file_path,
                                                                   line_number=line_num)
                                            self.safe_update_results(f"\n      {highlighted_text}\n")
                                        
                                        if len(matches) < len(term_matches[term]):
                                            remaining = len(term_matches[term]) - len(matches)
                                            self.safe_update_results(f"      ... {remaining} more matches for '{term}' ...\n")
                                
                    except UnicodeDecodeError:
                        self.safe_update_results(f"Warning: Could not read {file_path} - not a text file\n")
                    except (PermissionError, OSError) as e:
                        self.safe_update_results(f"Error reading {file_path}: {str(e)}\n")
            
            self.safe_update_results(f"\nFiles searched: {files_searched}\n")
            if not found_matches:
                self.safe_update_results("No matches found.\n")
            
        except (PermissionError, OSError) as e:
            self.safe_update_results(f"Error accessing files: {str(e)}\n")
        finally:
            self.root.after(0, lambda: self.status_var.set("Search completed"))

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

    def show_context_menu(self, event):
        """Show the context menu on right click"""
        try:
            # Get the index of the item under the cursor
            index = self.filtered_files.nearest(event.y)
            if index < 0:  # No item under cursor
                return
                
            # Select the item
            self.filtered_files.selection_clear(0, tk.END)
            self.filtered_files.selection_set(index)
            self.filtered_files.activate(index)
            self.filtered_files.see(index)  # Ensure item is visible
            
            # Get the file path and verify it exists
            file_path = self.get_selected_file()
            if file_path and os.path.isfile(file_path):
                # Position menu at mouse coordinates
                self.context_menu.tk_popup(event.x_root, event.y_root)
            
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

def main():
    root = tk.Tk()
    app = FileSearchGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()