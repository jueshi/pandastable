import subprocess
import time
from queue import Queue, Empty
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
from enum import Enum
import json

class TaskStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
class TaskSchedulerGUI:
    def browse_python_path(self):
        path = filedialog.askopenfilename(title="选择Python解释器", filetypes=[("Python Executable", "python.exe"), ("All Files", "*")])
        if path:
            self.python_path_var.set(path)

    def browse_script_path(self):
        path = filedialog.askopenfilename(title="选择要运行的脚本", filetypes=[("Python Files", "*.py"), ("All Files", "*")])
        if path:
            self.script_path_var.set(path)

    def launch_script(self):
        python_path = self.python_path_var.get().strip()
        script_path = self.script_path_var.get().strip()
        if not os.path.isfile(python_path):
            messagebox.showerror("错误", "无效的Python解释器路径!")
            return
        if not os.path.isfile(script_path):
            messagebox.showerror("错误", "无效的脚本路径!")
            return
        try:
            subprocess.Popen([python_path, script_path])
        except Exception as e:
            messagebox.showerror("运行出错", f"无法启动脚本:\n{e}")

    def __init__(self, root):
        self.root = root
        self.root.title("Windows App Launcher")

        # --- Python path and Script path configuration ---
        python_path_frame = ttk.Frame(self.root)
        python_path_frame.pack(fill='x', padx=10, pady=3)
        ttk.Label(python_path_frame, text="Python解释器路径:").pack(side='left')
        self.python_path_var = tk.StringVar(value=r"C:\Users\juesh\OneDrive\Documents\windsurf\AI_trading\AI_stock_predictor\venv\Scripts\python.exe")
        python_entry = ttk.Entry(python_path_frame, textvariable=self.python_path_var, width=70)
        python_entry.pack(side='left', padx=2)
        python_browse = ttk.Button(python_path_frame, text="选择...", command=self.browse_python_path)
        python_browse.pack(side='left')

        script_path_frame = ttk.Frame(self.root)
        script_path_frame.pack(fill='x', padx=10, pady=3)
        ttk.Label(script_path_frame, text="脚本路径:").pack(side='left')
        self.script_path_var = tk.StringVar(value=r"C:\Users\juesh\OneDrive\Documents\windsurf\PocketFlow-Tutorial-Codebase-Knowledge\path_gui.py")
        script_entry = ttk.Entry(script_path_frame, textvariable=self.script_path_var, width=70)
        script_entry.pack(side='left', padx=2)
        script_browse = ttk.Button(script_path_frame, text="选择...", command=self.browse_script_path)
        script_browse.pack(side='left')

        # Initialize the task scheduler
        self.scheduler = TaskScheduler(self)
        
        # Create main container
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add style configuration for the output display
        style = ttk.Style()
        style.configure("Output.TLabel", wraplength=300)
        # Create and pack the components
        self.create_control_panel()
        self.create_task_table()
        
        # Start the scheduler
        self.scheduler.start()

        # Load default tasks file if it exists
        default_tasks_file = os.path.join(os.path.dirname(__file__), "my_apps.tasks")
        if os.path.exists(default_tasks_file):
            try:
                with open(default_tasks_file, 'r') as f:
                    tasks = json.load(f)
                
                # Add loaded tasks
                for task in tasks:
                    # Create a task in the scheduler first
                    task_id = self.scheduler.task_counter + 1
                    scheduler_task = {
                        'id': task_id,
                        'script': task['script'],
                        'args': task['args'],
                        'status': TaskStatus(task['status']),  # Convert string to enum
                        'added_time': task['added_time'],
                        'start_time': task['start_time'],
                        'end_time': task['end_time'],
                        'output': ''  # Initialize empty output
                    }
                    
                    # Update scheduler state
                    self.scheduler.tasks[task_id] = scheduler_task
                    self.scheduler.task_counter = task_id
                    
                    # Add to tree
                    self.tree.insert('', 'end', values=(
                        task_id,
                        task['script'],
                        ' '.join(task['args']) if task['args'] else '',
                        task['status'],
                        task['added_time'],
                        task['start_time'],
                        task['end_time']
                    ))
                
                # Adjust column widths after loading all tasks
                self.adjust_column_widths()
            except Exception as e:
                messagebox.showwarning("Warning", f"Failed to load default tasks file: {str(e)}")

    def create_control_panel(self):
        """Create the control panel with file browser and buttons"""
        control_frame = ttk.LabelFrame(self.main_container, text="Control Panel")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File path entry and browse button
        path_frame = ttk.Frame(control_frame)
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(path_frame, text="Script Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        browse_btn = ttk.Button(path_frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side=tk.LEFT)
        
        # Arguments entry
        arg_frame = ttk.Frame(control_frame)
        arg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(arg_frame, text="Arguments:").pack(side=tk.LEFT)
        self.args_var = tk.StringVar()
        self.args_entry = ttk.Entry(arg_frame, textvariable=self.args_var)
        self.args_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Buttons frame
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Add Task", command=self.add_task).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Start Selected", command=self.start_selected).pack(side=tk.LEFT, padx=5)
        # Add the Stop Task button
        ttk.Button(btn_frame, text="Stop Task", command=self.stop_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset Status", command=self.reset_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Completed", command=self.clear_completed).pack(side=tk.LEFT, padx=5)
        
        # Combined move and save/load frame
        bottom_frame = ttk.Frame(control_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Move buttons (left side)
        move_frame = ttk.Frame(bottom_frame)
        move_frame.pack(side=tk.LEFT)
        ttk.Button(move_frame, text="▲ Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(move_frame, text="▼ Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)

        # Save/Load buttons (right side)
        save_load_frame = ttk.Frame(bottom_frame)
        save_load_frame.pack(side=tk.RIGHT)
        ttk.Button(save_load_frame, text="Save Tasks", command=self.save_tasks).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_load_frame, text="Load Tasks", command=self.load_tasks).pack(side=tk.LEFT, padx=5)

    def stop_selected(self):
        """Stop the selected running task"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select a task to stop")
            return
        
        item = selected_items[0]
        values = self.tree.item(item)['values']
        task_id = values[0]
        
        # Only try to stop if task is running
        if values[3] == TaskStatus.RUNNING.value:
            self.scheduler.stop_task(task_id)
        else:
            messagebox.showinfo("Info", "Can only stop running tasks")

    def reveal_in_explorer(self):
        """Reveal the selected script in Windows Explorer"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # Get the script path from the selected item
        item = selected_items[0]
        values = self.tree.item(item)['values']
        script_path = values[1]  # Script path is in the second column
        
        try:
            # Normalize the path and get the directory
            script_path = os.path.normpath(script_path)
            script_dir = os.path.dirname(script_path)
            
            # Open explorer and select the file
            subprocess.run(['explorer', '/select,', script_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open explorer: {str(e)}")

        
    def start_selected(self):
        """Start execution from the selected task"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select a task to start")
            return
        
        # Get the selected task ID
        item = selected_items[0]
        values = self.tree.item(item)['values']
        task_id = values[0]
        
        # Start execution from this task
        self.scheduler.start_from_task(task_id)

    def create_task_table(self):
        """Create the task table to display tasks"""
        # Create table frame
        table_frame = ttk.LabelFrame(self.main_container, text="Tasks")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create split pane for table and output
        paned = ttk.PanedWindow(table_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Table with scrollbars
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # Create main table
        columns = ('ID', 'Script', 'Arguments', 'Status', 'Added Time', 'Start Time', 'End Time')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings')
        
        # Configure columns
        self.tree.heading('ID', text='ID')
        self.tree.heading('Script', text='Script')
        self.tree.heading('Arguments', text='Arguments')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Added Time', text='Added Time')
        self.tree.heading('Start Time', text='Start Time')
        self.tree.heading('End Time', text='End Time')
        
        # Set column widths
        self.tree.column('ID', width=30)
        self.tree.column('Script', width=200)
        self.tree.column('Arguments', width=150)
        self.tree.column('Status', width=100)
        self.tree.column('Added Time', width=150)
        self.tree.column('Start Time', width=150)
        self.tree.column('End Time', width=150)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(left_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for table and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Right side: Output
        right_frame = ttk.LabelFrame(paned, text="Output")
        paned.add(right_frame, weight=1)
        
        # Create output text widget
        self.output_text = tk.Text(right_frame, wrap=tk.WORD, width=50)
        output_vsb = ttk.Scrollbar(right_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_vsb.set)
        
        # Pack output components
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind events
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Up>', lambda e: self.move_up())     # Add this line
        self.tree.bind('<Down>', lambda e: self.move_down())  # Add this line

        # Create context menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Open in Notepad++", command=self.open_in_notepad)
        self.context_menu.add_command(label="Reveal in Explorer", command=self.reveal_in_explorer)

        
        # Bind right-click event
        self.tree.bind('<Button-3>', self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu on right click"""
        item = self.tree.identify_row(event.y)
        if item:
            # Select the item under cursor
            self.tree.selection_set(item)
            # Show context menu
            self.context_menu.post(event.x_root, event.y_root)

    def open_in_notepad(self):
        """Open the selected script in Notepad++"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        # Get the script path from the selected item
        item = selected_items[0]
        values = self.tree.item(item)['values']
        script_path = values[1]  # Script path is in the second column
        
        try:
            # Try to open with Notepad++
            subprocess.Popen(['notepad++.exe', script_path])
        except FileNotFoundError:
            # If Notepad++ is not in PATH, try common installation locations
            notepad_paths = [
                r"C:\Program Files\Notepad++\notepad++.exe",
                r"C:\Program Files (x86)\Notepad++\notepad++.exe"
            ]
            
            for path in notepad_paths:
                if os.path.exists(path):
                    subprocess.Popen([path, script_path])
                    break
            else:
                messagebox.showerror("Error", "Notepad++ not found. Please make sure it's installed.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
                            
    def browse_file(self):
        """Open file browser dialog for any executable or file"""
        filenames = filedialog.askopenfilenames(
            title="Select Applications or Files",
            filetypes=[
                ("All Executable Files", "*.exe;*.bat;*.cmd"),
                ("Python Files", "*.py"),
                ("All Files", "*.*")
            ]
        )
        
        # Add each selected file as a task
        for filename in filenames:
            self.path_var.set(filename)  # Set current file path
            self.add_task()  # Add as task

    def add_task(self):
        """Add a new task to the scheduler"""
        script_path = self.path_var.get().strip()
        if not script_path:
            messagebox.showerror("Error", "Please select a script file")
            return
            
        args = self.args_var.get().strip().split()
        self.scheduler.add_task(script_path, args)
        
        # Clear entries
        self.path_var.set("")
        self.args_var.set("")

    def adjust_column_widths(self):
        """Adjust column widths based on content"""
        columns = ('ID', 'Script', 'Arguments', 'Status', 'Added Time', 'Start Time', 'End Time')
        
        # Initialize minimum widths
        min_widths = {
            'ID': 30,
            'Script': 100,
            'Arguments': 80,
            'Status': 70,
            'Added Time': 120,
            'Start Time': 120,
            'End Time': 120
        }
        
        # Include header text in width calculation
        for col in columns:
            header_width = len(col) * 7  # Approximate pixel width for header
            min_widths[col] = max(min_widths[col], header_width)
        
        # Calculate width needed for content
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values:
                for i, col in enumerate(columns):
                    if values[i]:
                        content_width = len(str(values[i])) * 7  # Approximate pixel width
                        min_widths[col] = max(min_widths[col], content_width)
        
        # Set column widths
        for col in columns:
            self.tree.column(col, width=min_widths[col])

    def remove_selected(self):
        """Remove selected task from the table"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select a task to remove")
            return
            
        for item in selected_items:
            status = self.tree.item(item)['values'][3]
            if status == TaskStatus.RUNNING.value:
                messagebox.showwarning("Warning", "Cannot remove running task")
                continue
            self.tree.delete(item)
        
        # Renumber remaining tasks
        self.scheduler.renumber_tasks()
        # Adjust column widths
        self.adjust_column_widths()

    def clear_completed(self):
        """Clear completed tasks from the table"""
        for item in self.tree.get_children():
            status = self.tree.item(item)['values'][3]
            if status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
                self.tree.delete(item)
        
        # Renumber remaining tasks
        self.scheduler.renumber_tasks()
        # Adjust column widths
        self.adjust_column_widths()

    def on_double_click(self, event):
        """Handle double click on table cell"""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            
            # Only allow editing arguments column
            if column == '#3':  # Arguments column
                self.edit_cell(item, column)

    def on_select(self, event):
        """Update output display when selecting a row"""
        selected_items = self.tree.selection()
        if selected_items:
            # Get the task ID from the selected row
            item = selected_items[0]  # Get the first selected item
            task_id = self.tree.item(item)['values'][0]
            
            # Get the task output from the scheduler
            task_output = self.scheduler.get_task_output(task_id)
            
            # Clear current output
            self.output_text.delete('1.0', tk.END)
            
            # Insert new output if available
            if task_output:
                self.output_text.insert('1.0', task_output)
    def edit_cell(self, item, column):
        """Create entry widget for editing cell"""
        # Get cell bounds
        x, y, w, h = self.tree.bbox(item, column)
        
        # Get current value
        values = self.tree.item(item)['values']
        current_value = values[2]  # Arguments column
        
        # Create entry widget
        entry = ttk.Entry(self.tree)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        
        def save_edit(event=None):
            """Save the edited value"""
            new_value = entry.get()
            values = list(self.tree.item(item)['values'])
            values[2] = new_value
            self.tree.item(item, values=values)
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<FocusOut>', save_edit)
        
        # Position entry widget
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()

    def reset_selected(self):
        """Reset status of selected tasks to PENDING"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select tasks to reset")
            return
        
        for item in selected_items:
            values = list(self.tree.item(item)['values'])
            task_id = values[0]
            if values[3] != TaskStatus.RUNNING.value:  # Don't reset running tasks
                self.scheduler.reset_task(task_id)
                # Maintain selection
                self.tree.selection_set(item)

    def move_up(self):
        """Move selected task up in the list"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        prev = self.tree.prev(item)
        if prev:
            self._swap_items(item, prev)
            self.tree.selection_set(prev)

    def move_down(self):
        """Move selected task down in the list"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        next_ = self.tree.next(item)
        if next_:
            self._swap_items(item, next_)
            self.tree.selection_set(next_)

    def _swap_items(self, item1, item2):
        """Swap two items in the treeview and update task order"""
        # Get values
        values1 = self.tree.item(item1)['values']
        values2 = self.tree.item(item2)['values']
        
        # Swap values in tree
        self.tree.item(item1, values=values2)
        self.tree.item(item2, values=values1)
        
        # Renumber all tasks to maintain consistency
        self.scheduler.renumber_tasks()

    def save_tasks(self):
        """Save current task list to a file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".tasks",
            filetypes=[("Task files", "*.tasks"), ("All files", "*.*")],
            title="Save Task List"
        )
        
        if not filename:
            return
            
        tasks_to_save = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            task = {
                'script': values[1],
                'args': values[2].split() if values[2] else [],
                'status': values[3],
                'added_time': values[4],
                'start_time': values[5],
                'end_time': values[6]
            }
            tasks_to_save.append(task)
        
        try:
            with open(filename, 'w') as f:
                json.dump(tasks_to_save, f, indent=2)
            messagebox.showinfo("Success", "Task list saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save task list: {str(e)}")

    def load_tasks(self):
        """Load task list from a file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Task files", "*.tasks"), ("All files", "*.*")],
            title="Load Task List"
        )
        
        if not filename:
            return
            
        try:
            with open(filename, 'r') as f:
                tasks = json.load(f)
            
            # Clear current tasks
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Reset scheduler state
            self.scheduler.tasks = {}
            self.scheduler.task_outputs = {}
            self.scheduler.task_counter = 0
            
            # Add loaded tasks
            for task in tasks:
                # Create a task in the scheduler first
                task_id = self.scheduler.task_counter + 1
                scheduler_task = {
                    'id': task_id,
                    'script': task['script'],
                    'args': task['args'],
                    'status': TaskStatus(task['status']),  # Convert string to enum
                    'added_time': task['added_time'],
                    'start_time': task['start_time'],
                    'end_time': task['end_time'],
                    'output': ''  # Initialize empty output
                }
                
                # Update scheduler state
                self.scheduler.tasks[task_id] = scheduler_task
                self.scheduler.task_counter = task_id
                
                # Add to tree
                self.tree.insert('', 'end', values=(
                    task_id,
                    task['script'],
                    ' '.join(task['args']) if task['args'] else '',
                    task['status'],
                    task['added_time'],
                    task['start_time'],
                    task['end_time']
                ))
            
            # Adjust column widths after loading all tasks
            self.adjust_column_widths()
            messagebox.showinfo("Success", "Task list loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load task list: {str(e)}")

class TaskScheduler:
    def __init__(self, gui):
        self.gui = gui
        self.task_queue = Queue()
        self.stop_event = Event()
        self.executor = None  # ThreadPoolExecutor for concurrent tasks
        self.is_running = False
        self.task_counter = 0
        self.task_outputs = {}  # Store outputs separately
        self.tasks = {}  # Store all tasks by ID

    def stop_task(self, task_id):
        """Stop a running task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task['status'] == TaskStatus.RUNNING:
                try:
                    # Find the process by looking up script name
                    script_name = os.path.basename(task['script'])
                    if os.name == 'nt':  # Windows
                        # Kill process and its children
                        subprocess.run(['taskkill', '/F', '/T', '/IM', script_name], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
                    else:  # Unix/Linux
                        subprocess.run(['pkill', '-f', script_name], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
                    
                    # Update task status
                    task['status'] = TaskStatus.FAILED
                    task['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    task['output'] += "\nTask stopped by user"
                    self._update_task_in_tree(task)
                    
                    messagebox.showinfo("Success", f"Task {task_id} has been stopped")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to stop task: {str(e)}")

    def renumber_tasks(self):
        """Renumber all tasks based on their current order in the table"""
        tree_items = self.gui.tree.get_children()
        new_tasks = {}
        new_outputs = {}
        new_counter = 0
        
        # Create a mapping of old ID to new ID
        id_mapping = {}
        
        # First pass: create new tasks with new IDs
        for item in tree_items:
            new_counter += 1
            values = self.gui.tree.item(item)['values']
            old_id = values[0]
            old_task = self.tasks[old_id]
            
            # Create new task with new ID
            new_task = {
                'id': new_counter,
                'script': old_task['script'],
                'args': old_task['args'],
                'status': old_task['status'],
                'added_time': old_task['added_time'],
                'start_time': old_task['start_time'],
                'end_time': old_task['end_time'],
                'output': old_task['output']
            }
            
            # Store new task and output
            new_tasks[new_counter] = new_task
            new_outputs[new_counter] = self.task_outputs.get(old_id, '')
            
            # Update the tree item with new ID
            values = list(values)
            values[0] = new_counter
            self.gui.tree.item(item, values=values)
            
            # Store mapping
            id_mapping[old_id] = new_counter
        
        # Update task queue if necessary
        new_queue = Queue()
        while not self.task_queue.empty():
            try:
                task = self.task_queue.get_nowait()
                if task['id'] in id_mapping:
                    task['id'] = id_mapping[task['id']]
                    new_queue.put(task)
            except Empty:
                break
        
        # Update scheduler state
        self.tasks = new_tasks
        self.task_outputs = new_outputs
        self.task_queue = new_queue
        self.task_counter = new_counter
        
    def reset_task(self, task_id):
        """Reset a task to PENDING status"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task['status'] = TaskStatus.PENDING
            task['start_time'] = ''
            task['end_time'] = ''
            task['output'] = ''
            self.task_outputs[task_id] = ''
            self._update_task_in_tree(task)

    def swap_tasks(self, task_id1, task_id2):
        """Swap the order of two tasks"""
        if task_id1 in self.tasks and task_id2 in self.tasks:
            # Get both tasks
            task1 = self.tasks[task_id1]
            task2 = self.tasks[task_id2]
            
            # Only swap if neither task is running
            if (task1['status'] != TaskStatus.RUNNING and 
                task2['status'] != TaskStatus.RUNNING):
                # Create new task dictionaries with swapped properties but keeping original IDs
                new_task1 = {
                    'id': task_id1,  # Keep original ID
                    'script': task2['script'],
                    'args': task2['args'],
                    'status': task2['status'],
                    'added_time': task2['added_time'],
                    'start_time': task2['start_time'],
                    'end_time': task2['end_time'],
                    'output': task2['output']
                }
                
                new_task2 = {
                    'id': task_id2,  # Keep original ID
                    'script': task1['script'],
                    'args': task1['args'],
                    'status': task1['status'],
                    'added_time': task1['added_time'],
                    'start_time': task1['start_time'],
                    'end_time': task1['end_time'],
                    'output': task1['output']
                }
                
                # Update tasks dictionary
                self.tasks[task_id1] = new_task1
                self.tasks[task_id2] = new_task2
                
                # Swap outputs
                output1 = self.task_outputs.get(task_id1, '')
                output2 = self.task_outputs.get(task_id2, '')
                self.task_outputs[task_id1] = output2
                self.task_outputs[task_id2] = output1
                
    def get_task_output(self, task_id):
        """Get the output for a specific task"""
        return self.task_outputs.get(task_id, "")

    def _update_task_in_tree(self, task):
        """Update task status in the treeview"""
        def update():
            # Store output separately
            self.task_outputs[task['id']] = task['output']
            
            # Update tree
            for item in self.gui.tree.get_children():
                if self.gui.tree.item(item)['values'][0] == task['id']:
                    self.gui.tree.item(item, values=(
                        task['id'],
                        task['script'],
                        ' '.join(task['args']),
                        task['status'].value,
                        task['added_time'],
                        task['start_time'],
                        task['end_time']
                    ))
                    
                    # Update output display if this task is selected
                    if item in self.gui.tree.selection():
                        self.gui.output_text.delete('1.0', tk.END)
                        self.gui.output_text.insert('1.0', task['output'])
                    break
        
        self.gui.root.after(0, update)

    def add_task(self, script_path, args=None):
        """Add task to queue and update GUI"""
        script_path = os.path.normpath(script_path)
        self.task_counter += 1
        
        task_id = self.task_counter
        added_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create task
        task = {
            'id': task_id,
            'script': script_path,
            'args': args or [],
            'status': TaskStatus.PENDING,
            'added_time': added_time,
            'start_time': '',
            'end_time': '',
            'output': ''
        }
        
        # Store task
        self.tasks[task_id] = task
        
        # Add to table using the main thread
        def insert_to_table():
            self.gui.tree.insert('', 'end', values=(
                task['id'],
                task['script'],
                ' '.join(task['args']) if task['args'] else '',
                task['status'].value,
                task['added_time'],
                task['start_time'],
                task['end_time']
            ))
            # Adjust column widths after insertion
            self.gui.adjust_column_widths()
        
        # Schedule the insert in the main thread
        self.gui.root.after(0, insert_to_table)

    def start_from_task(self, task_id):
        """Start executing the selected task"""
        # Get tasks in current tree order
        tree_items = self.gui.tree.get_children()
        
        for item in tree_items:
            values = self.gui.tree.item(item)['values']
            current_id = values[0]
            
            if current_id == task_id:
                # Find the task with matching script and arguments
                current_script = values[1]
                current_args = values[2]
                
                # Find the matching task in our tasks dictionary
                matching_task = None
                for task in self.tasks.values():
                    if (task['script'] == current_script and 
                        ' '.join(task['args']) == current_args):
                        matching_task = task
                        break
                
                if matching_task and matching_task['status'] == TaskStatus.PENDING:
                    # Start the executor if not already running
                    if not self.is_running:
                        self.start()
                    # Submit only the selected task
                    self.executor.submit(self._execute_task, matching_task)
                break

    def _execute_task(self, task):
        """Execute a task and update GUI"""
        try:
            # Update status to running
            task['status'] = TaskStatus.RUNNING
            task['start_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._update_task_in_tree(task)

            # Determine how to launch the file based on its extension
            file_ext = os.path.splitext(task['script'])[1].lower()
            
            if file_ext == '.py':
                # For Python files, use python interpreter
                command = ['python', task['script']] + task['args']
            elif file_ext in ('.exe', '.bat', '.cmd'):
                # For executables and batch files, run directly
                command = [task['script']] + task['args']
            else:
                # For other files, use the default associated program
                command = ['start', '', task['script']] + task['args']
                shell = True

            # Run the process
            if file_ext in ('.exe', '.bat', '.cmd', '.py'):
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                # Store process object in task for potential stopping
                task['process'] = process
                stdout, stderr = process.communicate()
            else:
                # For files opened with associated programs
                process = subprocess.Popen(
                    ' '.join(command),
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                task['process'] = process
                stdout, stderr = process.communicate()

            # Update task status and output
            task['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if process.returncode == 0:
                task['status'] = TaskStatus.COMPLETED
                task['output'] = stdout if stdout else "Process completed successfully"
            else:
                task['status'] = TaskStatus.FAILED
                task['output'] = stderr if stderr else "Process failed with return code: " + str(process.returncode)

            self._update_task_in_tree(task)

        except Exception as e:
            task['status'] = TaskStatus.FAILED
            task['output'] = str(e)
            task['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._update_task_in_tree(task)

    def start(self):
        """Start the scheduler and initialize thread pool"""
        if not self.is_running:
            self.is_running = True
            if self.executor is None:
                self.executor = ThreadPoolExecutor(max_workers=4) # Example max_workers, adjust as needed

    def stop(self):
        """Stop the scheduler and shutdown thread pool"""
        if self.is_running:
            self.is_running = False
            if self.executor:
                self.executor.shutdown(wait=True) # Wait for all tasks to complete
                self.executor = None
if __name__ == "__main__":
    root = tk.Tk()
    app = TaskSchedulerGUI(root)
    root.mainloop()
