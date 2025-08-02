# low ram consumption single-tab web browser

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import sys
import re
import sqlite3
from datetime import datetime
import threading
from tkinterweb import HtmlFrame

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

class WebBrowserGUI:
    def __init__(self, root):
        # Convert root to Tk root if it's not already
        if not isinstance(root, tk.Tk):
            self.root = tk.Tk()
            self.root.geometry(root.geometry())
        else:
            self.root = root
            
        self.root.title("Lightweight Web Browser")
        self.root.geometry("1024x768")
        
        # Initialize URL history dictionary and database
        self.url_history = {}
        self.setup_history_db()
        
        # Make the root window resizable
        self.root.resizable(True, True)
        
        # Create main frame with padding and expansion
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        
        # Create a frame for input controls
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=0, column=0, sticky='ew')
        
        # Web Address bar (formerly Search Directory)
        ttk.Label(input_frame, text="Web Address:").grid(row=0, column=0, sticky='w', pady=2)
        self.web_address = tk.StringVar(value="https://www.google.com")
        self.address_entry = ttk.Entry(input_frame, textvariable=self.web_address)
        self.address_entry.grid(row=0, column=1, sticky='ew', padx=(5, 5))
        self.address_entry.bind('<Return>', self.load_url)
        go_button = ttk.Button(input_frame, text="Go", command=self.load_url)
        go_button.grid(row=0, column=2, padx=5, sticky='w')
        
        # Add tooltip for address bar
        CreateToolTip(self.address_entry, "Enter a web address (URL) to navigate to a website.\nPress Enter or click Go to navigate.")
        
        # History search (formerly File Pattern)
        ttk.Label(input_frame, text="History Search:").grid(row=1, column=0, sticky='w', pady=2)
        self.history_search = tk.StringVar()
        self.history_search.trace_add("write", self.on_history_search_change)
        history_entry = ttk.Entry(input_frame, textvariable=self.history_search, width=200)
        history_entry.grid(row=1, column=1, columnspan=2, sticky='w', padx=(5, 5))
        
        # Add tooltip for history search
        CreateToolTip(history_entry,
            "Search your browsing history:\n" +
            "- Type text to match URLs or page titles\n" +
            "- Results will appear in the Filtered URLs list below")
        
        # Configure column weights
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Create paned window for resizable sections
        self.paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        self.paned.grid(row=1, column=0, sticky='nsew')
        
        # Filtered URLs frame (formerly Filtered Files)
        filtered_frame = ttk.LabelFrame(self.paned, text="Filtered URLs", padding=(5, 5, 5, 5))
        
        # Create filtered URLs listbox with scrollbar
        listbox_frame = ttk.Frame(filtered_frame)
        listbox_frame.pack(fill='both', expand=True)
        
        # Create treeview with columns
        columns = ('date', 'title', 'url')
        self.filtered_urls = ttk.Treeview(listbox_frame, columns=columns, show='headings', height=10,
                                         selectmode='browse')  # Single selection for URLs
        
        # Define column headings and widths
        self.filtered_urls.heading('date', text='Date Visited', anchor='w', command=lambda: self.sort_treeview('date', False))
        self.filtered_urls.heading('title', text='Page Title', anchor='w', command=lambda: self.sort_treeview('title', False))
        self.filtered_urls.heading('url', text='URL', anchor='w', command=lambda: self.sort_treeview('url', False))
        
        # Configure column properties
        self.filtered_urls.column('date', width=140, minwidth=140, stretch=False, anchor='w')
        self.filtered_urls.column('title', width=250, minwidth=150, stretch=True, anchor='w')
        self.filtered_urls.column('url', width=400, minwidth=200, stretch=True, anchor='w')
        
        # Add scrollbars
        yscrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.filtered_urls.yview)
        xscrollbar = ttk.Scrollbar(listbox_frame, orient="horizontal", command=self.filtered_urls.xview)
        self.filtered_urls.configure(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
        
        # Layout with scrollbars
        self.filtered_urls.grid(row=0, column=0, sticky='nsew')
        yscrollbar.grid(row=0, column=1, sticky='ns')
        xscrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights for proper expansion
        listbox_frame.grid_rowconfigure(0, weight=1)
        listbox_frame.grid_columnconfigure(0, weight=1)
        
        # Create right-click context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open URL", command=self.load_selected_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy URL", command=self.copy_url_to_clipboard)
        self.context_menu.add_command(label="Delete from History", command=self.delete_from_history)
        
        # Bind events to filtered URLs treeview
        self.filtered_urls.bind('<Button-3>', self.show_context_menu)
        self.filtered_urls.bind('<Double-Button-1>', self.on_url_double_click)
        
        # Web Browser frame
        browser_frame = ttk.LabelFrame(self.paned, text="Web Browser", padding=(5, 5, 5, 5))
        
        # Add frames to paned window with adjusted weights
        self.paned.add(filtered_frame, weight=1)
        self.paned.add(browser_frame, weight=3)
        
        # Browser controls frame with buttons
        browser_controls = ttk.Frame(main_frame)
        browser_controls.grid(row=2, column=0, sticky='ew', pady=(5,0))
        
        # Add browser control buttons
        self.back_button = ttk.Button(browser_controls, text="Back", command=self.browser_back)
        self.back_button.pack(side='left', padx=5)
        
        self.forward_button = ttk.Button(browser_controls, text="Forward", command=self.browser_forward)
        self.forward_button.pack(side='left', padx=5)
        
        self.reload_button = ttk.Button(browser_controls, text="Reload", command=self.browser_reload)
        self.reload_button.pack(side='left', padx=5)
        
        self.home_button = ttk.Button(browser_controls, text="Home", command=self.browser_home)
        self.home_button.pack(side='left', padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief='sunken')
        self.status_bar.grid(row=3, column=0, sticky='ew', pady=(5, 0))
        
        # Configure weights for resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Configure main_frame grid weights
        main_frame.grid_rowconfigure(0, weight=0)  # input frame - fixed height
        main_frame.grid_rowconfigure(1, weight=1)  # paned window - expandable
        main_frame.grid_rowconfigure(2, weight=0)  # browser controls - fixed height
        main_frame.grid_rowconfigure(3, weight=0)  # status bar - fixed height
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Initialize browser
        self.init_browser(browser_frame)
        
        # Load browsing history
        self.load_history()
        
        # Initialize with Google homepage
        self.current_title = "Google"
        self.load_url()
        
        # Register shutdown handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_history_db(self):
        """Set up SQLite database for browsing history"""
        db_path = os.path.join(os.path.expanduser("~"), "browser_history.db")
        try:
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            
            # Create history table if it doesn't exist
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                visit_date TEXT,
                visit_timestamp INTEGER
            )
            ''')
            self.conn.commit()
            print(f"Successfully initialized history database at {db_path}")
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            messagebox.showerror("Database Error", f"Could not initialize history database: {e}")

    def init_browser(self, browser_frame):
        """Initialize the browser widget"""
        # Create HtmlFrame browser
        self.browser = HtmlFrame(browser_frame, messages_enabled=False)
        self.browser.pack(fill="both", expand=True)
        
        # Connect load event - ensure we capture title changes properly
        self.browser.on_load = self.on_page_load
        self.browser.on_title_change = self.on_title_change
        
        # Track our page titles
        self.current_title = "Google"
        self.title_monitor_active = False
        self.last_url = ""
        
        # Update status
        self.status_var.set("Initializing browser...")

    def on_page_load(self, frame):
        """Callback when a page finishes loading"""
        # Get the URL and title
        url = self.web_address.get()
        title = self.current_title
        
        # Update status
        self.status_var.set(f"Loaded: {url}")
        
        print(f"Page loaded: {url} - Current title: {title}")
        
        # Reset title monitor
        self.stop_title_monitor()
        
        # Start a more aggressive approach to monitor title changes
        self.start_title_monitor(url)
        
        # Add to history database with current title (will be updated later if title changes)
        self.add_to_history(url, title)
        
        # Force history to update
        self.load_history()

    def start_title_monitor(self, url):
        """Start monitoring for title changes on a regular interval"""
        self.title_monitor_active = True
        self.last_url = url
        
        # Try immediate title extraction
        self.extract_title_from_page()
        
        # Schedule repeated title checks (every 500ms for 5 seconds)
        self.schedule_title_checks(10)
        
    def schedule_title_checks(self, remaining_checks):
        """Schedule title checks at intervals"""
        if not self.title_monitor_active or remaining_checks <= 0:
            return
            
        # Only continue checking if we're still on the same URL
        if self.web_address.get() != self.last_url:
            print("URL changed, stopping title monitor")
            self.title_monitor_active = False
            return
            
        # Schedule the next check
        self.root.after(500, lambda: self.perform_title_check(remaining_checks))
        
    def perform_title_check(self, remaining_checks):
        """Perform a title check and schedule the next one if needed"""
        self.extract_title_from_page()
        self.schedule_title_checks(remaining_checks - 1)
        
    def stop_title_monitor(self):
        """Stop the title monitor"""
        self.title_monitor_active = False

    def extract_title_from_page(self):
        """Attempt to extract title from the loaded page if not set properly"""
        url = self.web_address.get()
        
        # Don't extract if we don't have a URL
        if not url:
            return
            
        try:
            # Try multiple approaches to get the title
            
            # Method 1: Use document.title
            js_title = self.browser.run_js("document.title")
            
            # Method 2: Try to get from title tag
            if not js_title or not js_title.strip():
                js_title = self.browser.run_js("(document.getElementsByTagName('title')[0] || {}).textContent")
            
            # Check if we got a valid title
            if js_title and js_title.strip() and js_title != "Google" and js_title != self.current_title:
                print(f"Extracted new title from {url}: '{js_title}' (was: '{self.current_title}')")
                self.on_title_change(self.browser, js_title)
                return True
            else:
                domain = url.split("://")[-1].split("/")[0].replace("www.", "")
                # If the title is still "Google" but we're on a different domain
                if self.current_title == "Google" and "google" not in domain:
                    fallback_title = domain.capitalize()
                    print(f"Using fallback title for {url}: {fallback_title}")
                    self.on_title_change(self.browser, fallback_title)
                    return True
        except Exception as e:
            print(f"Error extracting title: {e}")
            
        return False

    def on_title_change(self, frame, title):
        """Called when page title changes"""
        if not title or not title.strip():
            print("Received empty title, ignoring")
            return
        
        # Check for actually new title    
        if self.current_title == title:
            return
            
        print(f"Title changed to: '{title}' (was: '{self.current_title}')")
        self.current_title = title
        self.root.title(f"{title} - Lightweight Browser")
        
        # Update the title in history for the current URL
        self.update_title_in_history(title)

    def update_title_in_history(self, title):
        """Update the title for the current URL in history"""
        url = self.web_address.get()
        if not url or not title:
            return
            
        try:
            # Update title in database for this URL
            self.cursor.execute(
                "UPDATE history SET title = ? WHERE url = ? ORDER BY visit_timestamp DESC LIMIT 1",
                (title, url)
            )
            self.conn.commit()
            
            # Refresh the history display
            self.on_history_search_change()
            print(f"Updated title in history for {url} to: {title}")
        except sqlite3.Error as e:
            print(f"Error updating title in history: {e}")

    def load_url(self, event=None):
        """Load URL from address bar"""
        url = self.web_address.get()
        if not url:
            return
        
        # Stop any ongoing title monitoring
        self.stop_title_monitor()
            
        # Add http:// if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.web_address.set(url)
        
        # Reset the title immediately when loading a new URL
        # This prevents the previous page's title from persisting
        domain = url.split("://")[-1].split("/")[0].replace("www.", "")
        temp_title = f"Loading {domain}..."
        self.current_title = temp_title
        self.root.title(f"{temp_title} - Lightweight Browser")
        
        # Load the URL
        try:
            # Load the URL
            self.browser.load_url(url)
            self.status_var.set(f"Loading {url}...")
            
            # Manually add to history in case the load event doesn't fire
            # Use a small delay to allow the page title to be set
            def delayed_history_update():
                if self.current_title == temp_title:
                    # Title hasn't been updated by events, so try to extract it
                    try:
                        self.extract_title_from_page()
                    except:
                        # If extraction fails, use domain as fallback
                        self.current_title = domain.capitalize()
                        self.root.title(f"{self.current_title} - Lightweight Browser")
                
                # Add to history with whatever title we have
                self.add_to_history(url, self.current_title)
                
            self.root.after(3000, delayed_history_update)
        except Exception as e:
            self.status_var.set(f"Error loading {url}: {str(e)}")

    def browser_back(self):
        """Navigate back in browser history"""
        try:
            self.browser.go_back()
            self.status_var.set("Navigating back")
        except:
            self.status_var.set("Cannot go back")

    def browser_forward(self):
        """Navigate forward in browser history"""
        try:
            self.browser.go_forward()
            self.status_var.set("Navigating forward")
        except:
            self.status_var.set("Cannot go forward")

    def browser_reload(self):
        """Reload current page"""
        url = self.web_address.get()
        if url:
            self.browser.load_url(url)
            self.status_var.set("Reloading page")

    def browser_home(self):
        """Go to home page (Google)"""
        self.web_address.set("https://www.google.com")
        self.load_url()

    def add_to_history(self, url, title):
        """Add URL to history database"""
        # Check if this URL is already the most recent in history
        try:
            self.cursor.execute(
                "SELECT url FROM history ORDER BY visit_timestamp DESC LIMIT 1"
            )
            last_url = self.cursor.fetchone()
            
            # If this is the same as the last URL, don't add it again
            if last_url and last_url[0] == url:
                print(f"URL already in history (most recent): {url}")
                return
                
            # Add to history
            now = datetime.now()
            timestamp = int(now.timestamp())
            date_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            self.cursor.execute(
                "INSERT INTO history (url, title, visit_date, visit_timestamp) VALUES (?, ?, ?, ?)",
                (url, title or "Untitled", date_str, timestamp)
            )
            self.conn.commit()
            
            # Force a sync to disk
            self.cursor.execute("PRAGMA wal_checkpoint(FULL)")
            
            print(f"Added to history: {url} - {title} at {date_str}")
            
            # Update history view if search matches
            self.on_history_search_change()
        except sqlite3.Error as e:
            print(f"Database error in add_to_history: {e}")
            self.status_var.set(f"Error saving to history: {e}")

    def load_history(self):
        """Load browsing history from database"""
        try:
            self.cursor.execute(
                "SELECT url, title, visit_date, visit_timestamp FROM history ORDER BY visit_timestamp DESC LIMIT 100"
            )
            history = self.cursor.fetchall()
            
            # Clear treeview
            for item in self.filtered_urls.get_children():
                self.filtered_urls.delete(item)
            
            # Add history items
            for url, title, visit_date, _ in history:
                self.filtered_urls.insert('', 'end', values=(visit_date, title or "", url))
            
            # Update status
            self.status_var.set(f"Loaded {len(history)} history items")
        except sqlite3.Error as e:
            self.status_var.set(f"Error loading history: {e}")

    def on_history_search_change(self, *_):
        """Search history when search term changes"""
        search_term = self.history_search.get().lower()
        
        try:
            # Clear treeview
            for item in self.filtered_urls.get_children():
                self.filtered_urls.delete(item)
            
            if not search_term:
                # If no search term, show recent history
                self.cursor.execute(
                    "SELECT url, title, visit_date, visit_timestamp FROM history ORDER BY visit_timestamp DESC LIMIT 100"
                )
            else:
                # If search term provided, filter history
                self.cursor.execute(
                    "SELECT url, title, visit_date, visit_timestamp FROM history " +
                    "WHERE LOWER(url) LIKE ? OR LOWER(title) LIKE ? ORDER BY visit_timestamp DESC LIMIT 100",
                    (f"%{search_term}%", f"%{search_term}%")
                )
            
            history = self.cursor.fetchall()
            
            # Add matching history items
            for url, title, visit_date, _ in history:
                self.filtered_urls.insert('', 'end', values=(visit_date, title or "", url))
            
            # Update status
            self.status_var.set(f"Found {len(history)} matching history items")
        except sqlite3.Error as e:
            self.status_var.set(f"Error searching history: {e}")

    def get_selected_url(self):
        """Get the selected URL from the filtered URLs treeview"""
        selection = self.filtered_urls.selection()
        if not selection:
            return None
        
        values = self.filtered_urls.item(selection[0])['values']
        if not values:
            return None
        
        # URL is the third column
        return values[2]

    def load_selected_url(self):
        """Load selected URL in browser"""
        url = self.get_selected_url()
        if url:
            self.web_address.set(url)
            self.load_url()

    def on_url_double_click(self, event):
        """Handle double click on URL in history"""
        self.load_selected_url()

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        if self.filtered_urls.selection():
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_url_to_clipboard(self):
        """Copy selected URL to clipboard"""
        url = self.get_selected_url()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status_var.set(f"Copied to clipboard: {url}")

    def delete_from_history(self):
        """Delete selected URL from history"""
        url = self.get_selected_url()
        if url:
            try:
                self.cursor.execute("DELETE FROM history WHERE url = ?", (url,))
                self.conn.commit()
                self.on_history_search_change()  # Refresh display
                self.status_var.set(f"Deleted from history: {url}")
            except sqlite3.Error as e:
                self.status_var.set(f"Error deleting from history: {e}")

    def sort_treeview(self, col, reverse):
        """Sort treeview contents by column"""
        items = [(self.filtered_urls.set(k, col), k) for k in self.filtered_urls.get_children('')]
        items.sort(reverse=reverse)
        
        # Rearrange items in sorted positions
        for index, (val, item) in enumerate(items):
            self.filtered_urls.move(item, '', index)
        
        # Reverse sort next time
        self.filtered_urls.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def on_closing(self):
        """Clean up resources and close database connection"""
        try:
            if hasattr(self, 'conn'):
                # Force a final checkpoint and sync
                try:
                    self.cursor.execute("PRAGMA wal_checkpoint(FULL)")
                    print("Final database checkpoint completed")
                except:
                    pass
                self.conn.commit()
                self.conn.close()
                print("Database connection closed")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Destroy tkinter window
        self.root.destroy()

def main():
    root = tk.Tk()
    app = WebBrowserGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()