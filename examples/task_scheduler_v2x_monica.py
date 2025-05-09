import subprocess
import time
from queue import Queue, Empty
from threading import Thread, Event
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
from enum import Enum
import json
import signal
import psutil

class TaskStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    KILLED = "Killed"

class TaskSchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Tasks Scheduler")
        
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
        # Removed automatic start to allow manual control
        # self.scheduler.start()

    def create_control_panel(self):
        """Create the control panel with file browser and buttons"""
        # Create control panel frame
        control_frame = ttk.LabelFrame(self.main_container, text="Control Panel")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create input frame for script path and arguments
        input_frame = ttk.Frame(control_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Script path input
        script_frame = ttk.Frame(input_frame)
        script_frame.pack(fill=tk.X, pady=2)
        ttk.Label(script_frame, text="Script Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(script_frame, textvariable=self.path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,5))
        ttk.Button(script_frame, text="Browse", command=self.browse_file).pack(side=tk.RIGHT)
        
        # Arguments input
        args_frame = ttk.Frame(input_frame)
        args_frame.pack(fill=tk.X, pady=2)
        ttk.Label(args_frame, text="Arguments:").pack(side=tk.LEFT)
        self.args_var = tk.StringVar()
        ttk.Entry(args_frame, textvariable=self.args_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Scheduled time input
        time_frame = ttk.Frame(input_frame)
        time_frame.pack(fill=tk.X, pady=2)
        ttk.Label(time_frame, text="Schedule:").pack(side=tk.LEFT)
        self.schedule_var = tk.StringVar()
        ttk.Entry(time_frame, textvariable=self.schedule_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(time_frame, text="(YYYY-MM-DD HH:MM:SS or HH:MM:SS)").pack(side=tk.RIGHT)
        
        # Create button frame
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        ttk.Button(left_buttons, text="Add Task", command=self.add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Start Selected", command=self.start_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Reset Status", command=self.reset_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Clear Completed", command=self.clear_completed).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Kill Task", command=self.scheduler.kill_current_task).pack(side=tk.LEFT, padx=5)
        
        # Middle buttons (move up/down)
        middle_buttons = ttk.Frame(button_frame)
        middle_buttons.pack(side=tk.LEFT, padx=20)
        ttk.Button(middle_buttons, text="↑ Move Up", command=self.move_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_buttons, text="↓ Move Down", command=self.move_down).pack(side=tk.LEFT, padx=5)
        
        # Right side buttons (save/load)
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        ttk.Button(right_buttons, text="Save Tasks", command=self.save_tasks).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_buttons, text="Load Tasks", command=self.load_tasks).pack(side=tk.LEFT, padx=5)

    def start_selected(self):
        """Start execution from the selected task"""
        selected_items = self.tree.selection()
        if not selected_items:
            # If no task is selected, start processing all tasks in order
            self.scheduler.start_task_processing()
            return
        
        # Get the selected task ID
        item = selected_items[0]
        values = self.tree.item(item)['values']
        task_id = values[0]
        
        # Start task processing and execution from this task
        self.scheduler.start_task_processing()
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
        
        # Create main table with added Scheduled Time column
        columns = ('ID', 'Script', 'Arguments', 'Status', 'Added Time', 'Start Time', 'End Time', 'Scheduled Time')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings')
        
        # Configure columns
        self.tree.heading('ID', text='ID')
        self.tree.heading('Script', text='Script')
        self.tree.heading('Arguments', text='Arguments')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Added Time', text='Added Time')
        self.tree.heading('Start Time', text='Start Time')
        self.tree.heading('End Time', text='End Time')
        self.tree.heading('Scheduled Time', text='Scheduled Time')
        
        # Set column widths
        self.tree.column('ID', width=30)
        self.tree.column('Script', width=200)
        self.tree.column('Arguments', width=150)
        self.tree.column('Status', width=100)
        self.tree.column('Added Time', width=150)
        self.tree.column('Start Time', width=150)
        self.tree.column('End Time', width=150)
        self.tree.column('Scheduled Time', width=150)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(left_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Pack the treeview and scrollbars
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
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
        
        # Add event bindings
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Button-3>', self.show_context_menu)
        
        # Create context menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Open in Notepad++", command=self.open_in_notepad)

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
        """Open file browser dialog for multiple file selection"""
        filenames = filedialog.askopenfilenames(
            title="Select Python Scripts",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
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
        
        # Get arguments
        args = self.args_var.get().strip().split() if self.args_var.get().strip() else None
        
        # Get scheduled time
        scheduled_time = self.schedule_var.get().strip() or None
        
        # Add task to scheduler
        self.scheduler.add_task(script_path, args=args, scheduled_time=scheduled_time)
        
        # Clear entries
        self.path_var.set("")
        self.args_var.set("")
        self.schedule_var.set("")

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
            if status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.KILLED.value):
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
                self.output_text.insert(tk.END, str(task_output))
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
            self.tree.selection_set(item)

    def move_down(self):
        """Move selected task down in the list"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        next_item = self.tree.next(item)
        if next_item:
            self._swap_items(item, next_item)
            self.tree.selection_set(item)

    def _swap_items(self, item1, item2):
        """Swap two items in the treeview"""
        # Get values
        values1 = self.tree.item(item1)['values']
        values2 = self.tree.item(item2)['values']
        
        # Swap values in tree
        self.tree.item(item1, values=values2)
        self.tree.item(item2, values=values1)
        
        # Update task order in scheduler
        self.scheduler.reorder_tasks()

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
                    'status': task['status'],  # Store as string
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
        self.worker_thread = None
        self.is_running = False
        self.task_counter = 0
        self.task_outputs = {}  # Store outputs separately
        self.tasks = {}  # Store all tasks by ID
        self.currently_running_process = None
        self.currently_running_task = None
        self.auto_start = False  # New flag to control task execution
        
        # Thread to monitor and auto-start scheduled tasks
        self.scheduler_monitor_thread = None
        self.start_scheduler_monitor()

    def start_scheduler_monitor(self):
        """Start a thread to monitor and auto-start scheduled tasks"""
        def monitor_scheduled_tasks():
            while not self.stop_event.is_set():
                # Check if there are any scheduled tasks
                scheduled_tasks = [
                    task for task in self.tasks.values() 
                    if task.get('scheduled_time') and task['status'] == TaskStatus.PENDING.value
                ]
                
                if scheduled_tasks:
                    # If not running, start the scheduler
                    if not self.is_running:
                        self.start()
                    
                    # Enable auto-start for scheduled tasks
                    self.auto_start = True
            
                # Sleep to prevent tight looping
                time.sleep(10)  # Check every 10 seconds
        
        # Create and start the monitor thread
        self.scheduler_monitor_thread = Thread(target=monitor_scheduled_tasks, daemon=True)
        self.scheduler_monitor_thread.start()

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
                'status': old_task['status'],  # Store as string
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
            task['status'] = TaskStatus.PENDING.value
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
            if (task1['status'] != TaskStatus.RUNNING.value and 
                task2['status'] != TaskStatus.RUNNING.value):
                # Create new task dictionaries with swapped properties but keeping original IDs
                new_task1 = {
                    'id': task_id1,  # Keep original ID
                    'script': task2['script'],
                    'args': task2['args'],
                    'status': task2['status'],  # Store as string
                    'added_time': task2['added_time'],
                    'start_time': task2['start_time'],
                    'end_time': task2['end_time'],
                    'output': task2['output']
                }
                
                new_task2 = {
                    'id': task_id2,  # Keep original ID
                    'script': task1['script'],
                    'args': task1['args'],
                    'status': task1['status'],  # Store as string
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
            
            # Find and update the existing item
            item_to_update = None
            for item in self.gui.tree.get_children():
                if self.gui.tree.item(item)['values'][0] == task['id']:
                    item_to_update = item
                    break
            
            if item_to_update:
                # Get the scheduled time string
                scheduled_time_str = (task['scheduled_time'].strftime("%Y-%m-%d %H:%M:%S") 
                                    if task.get('scheduled_time') else "Not Scheduled")
                
                print(f"Updating tree item {task['id']} with status: {task['status']}")
                # Update the existing item
                self.gui.tree.item(item_to_update, values=(
                    task['id'],
                    task['script'],
                    ' '.join(task['args']),
                    task['status'],
                    task['added_time'],
                    task['start_time'],
                    task['end_time'],
                    scheduled_time_str
                ))
                
                # Update output display if this task is selected
                if item_to_update in self.gui.tree.selection():
                    self.gui.output_text.delete('1.0', tk.END)
                    self.gui.output_text.insert(tk.END, str(task['output']))
        
        self.gui.root.after(0, update)

    def move_task(self, task_id, target_position):
        """Move a task to a new position in the tree"""
        # Find the task's current item
        source_item = None
        for item in self.gui.tree.get_children():
            if self.gui.tree.item(item)['values'][0] == task_id:
                source_item = item
                break
        
        if not source_item:
            return
            
        # Get all items
        items = self.gui.tree.get_children()
        
        # If moving to the end
        if target_position >= len(items):
            self.gui.tree.move(source_item, '', 'end')
            return
            
        # Get the target item to move before
        target_item = items[target_position]
        
        # Move the item
        self.gui.tree.move(source_item, '', target_item)

    def add_task(self, script_path, args=None, scheduled_time=None):
        """Add task to queue and update GUI with improved task signaling"""
        # Increment task counter
        self.task_counter += 1
        
        # Parse scheduled time if provided
        if scheduled_time and isinstance(scheduled_time, str):
            try:
                # Try parsing different time formats
                scheduled_time = datetime.datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    scheduled_time = datetime.datetime.strptime(scheduled_time, "%H:%M:%S")
                    # If only time is provided, use today's date
                    today = datetime.date.today()
                    scheduled_time = datetime.datetime.combine(today, scheduled_time.time())
                except ValueError:
                    # Invalid time format
                    scheduled_time = None
        
        # Create task dictionary with scheduled time
        task = {
            'id': self.task_counter,
            'script': script_path,
            'args': args or [],
            'status': TaskStatus.PENDING.value,  # Store as string
            'added_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'start_time': None,
            'end_time': None,
            'output': None,
            'scheduled_time': scheduled_time  # New field for scheduled execution
        }
        
        # Store the task in tasks dictionary
        self.tasks[task['id']] = task
        
        # Add task to queue WITHOUT starting it
        self.task_queue.put(task)
        
        def insert_to_table():
            # Format scheduled time for display
            scheduled_time_str = (scheduled_time.strftime("%Y-%m-%d %H:%M:%S") 
                                  if scheduled_time else "Not Scheduled")
            
            # Insert task into the treeview
            self.gui.tree.insert('', 'end', values=(
                task['id'],
                task['script'],
                ' '.join(task['args']) if task['args'] else '',
                task['status'],  # Use string status directly
                task['added_time'],
                task['start_time'],
                task['end_time'],
                scheduled_time_str  # Add scheduled time to table
            ))
            # Adjust column widths after insertion
            self.gui.adjust_column_widths()
        
        # Schedule the insert in the main thread
        self.gui.root.after(0, insert_to_table)
        return task['id']

    def start_task_processing(self):
        """Manually start processing tasks in the queue"""
        # Clear the queue first
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except Empty:
                break
        
        # Get tasks in current GUI order and queue pending ones
        tasks_ordered = self._get_tasks_in_gui_order()
        for task in tasks_ordered:
            if task['status'] == TaskStatus.PENDING.value:
                self.task_queue.put(task)
        
        # Enable auto_start to process all queued tasks
        self.auto_start = True
        
        # If no worker thread is running, start one
        if not self.is_running:
            self.start()

    def start_from_task(self, task_id):
        """Start executing tasks from the specified task ID"""
        # Clear the queue first
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except Empty:
                break
        
        # Get tasks in current GUI order
        tasks_ordered = self._get_tasks_in_gui_order()
        
        # Find the index of the starting task
        start_idx = -1
        for i, task in enumerate(tasks_ordered):
            if task['id'] == task_id:
                start_idx = i
                break
                
        if start_idx == -1:
            return
            
        # Queue tasks starting from the selected one
        for task in tasks_ordered[start_idx:]:
            if task['status'] == TaskStatus.PENDING.value:
                self.task_queue.put(task)
        
        # Enable auto_start to process all queued tasks
        self.auto_start = True
        
        # Start the worker if not already running
        if not self.is_running:
            self.start()

    def _get_tasks_in_gui_order(self):
        """Get tasks in the current GUI tree order"""
        tasks_ordered = []
        tree_items = self.gui.tree.get_children()
        
        for item in tree_items:
            values = self.gui.tree.item(item)['values']
            task_id = values[0]  # Use task ID instead of script and args
            
            # Get the task directly from our tasks dictionary
            if task_id in self.tasks:
                tasks_ordered.append(self.tasks[task_id])
        
        return tasks_ordered

    def _execute_task(self, task):
        """Execute a task and update GUI"""
        try:
            task['status'] = TaskStatus.RUNNING.value
            task['start_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._update_task_in_tree(task)
            
            # Execute process and wait for completion
            self.currently_running_process = subprocess.Popen(
                ['python', task['script']] + task['args'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.currently_running_task = task
            
            # Wait for process completion
            stdout, stderr = self.currently_running_process.communicate()
            
            # Update status based on return code
            task['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if self.currently_running_process.returncode == 0:
                task['status'] = TaskStatus.COMPLETED.value
                task['output'] = stdout
            else:
                task['status'] = TaskStatus.FAILED.value
                task['output'] = stderr
                
            self._update_task_in_tree(task)
            
            # Reset current process
            self.currently_running_process = None
            self.currently_running_task = None
        except Exception as e:
            print(f"Error executing task: {e}")

    def reorder_tasks(self):
        """Update task order based on current GUI order"""
        # Get current task order from GUI
        ordered_tasks = {}
        for item in self.gui.tree.get_children():
            values = self.gui.tree.item(item)['values']
            task_id = values[0]
            if task_id in self.tasks:
                ordered_tasks[task_id] = self.tasks[task_id]
                print(f"Task {task_id}: {self.tasks[task_id]['script']} - {self.tasks[task_id]['status']}")
        
        # Replace tasks dictionary with ordered version
        self.tasks = ordered_tasks
        
        # Requeue pending tasks if auto_start is True
        if self.auto_start:
            # Clear the queue
            while not self.task_queue.empty():
                try:
                    self.task_queue.get_nowait()
                except Empty:
                    break
            
            # Find currently running task
            current_task_id = None
            current_task_found = False
            
            # First find if any task is currently running
            for task in self.tasks.values():
                if task['status'] == TaskStatus.RUNNING.value:
                    current_task_id = task['id']
                    print(f"Found running task: {current_task_id}")
                    break
            
            # Queue pending tasks after current task
            for task in self.tasks.values():
                if current_task_id:
                    # If we have a running task, wait until we find it
                    if not current_task_found:
                        if task['id'] == current_task_id:
                            current_task_found = True
                            print(f"Found current task position: {task['id']}")
                        continue
                
                # Queue pending tasks after current position
                if task['status'] == TaskStatus.PENDING.value:
                    print(f"Queueing task: {task['id']}")
                    self.task_queue.put(task)

    def kill_current_task(self):
        """Kill the currently running task"""
        if self.currently_running_process:
            # Store the task ID before killing
            killed_task_id = self.currently_running_task['id'] if self.currently_running_task else None
            killed_task = self.tasks.get(killed_task_id) if killed_task_id else None
                    
            try:
                # Update task status in the tasks dictionary and currently running task
                if killed_task and self.currently_running_task:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Update the task in tasks dictionary
                    killed_task['status'] = TaskStatus.KILLED.value
                    killed_task['end_time'] = current_time
                    self.tasks[killed_task_id] = killed_task
                    
                    # Update the currently running task to match
                    self.currently_running_task['status'] = TaskStatus.KILLED.value
                    self.currently_running_task['end_time'] = current_time
                    
                    # Update the tree immediately in the main thread
                    def update_tree():
                        for item in self.gui.tree.get_children():
                            if str(self.gui.tree.item(item)['values'][0]) == str(killed_task_id):
                                self.gui.tree.item(item, values=(
                                    killed_task['id'],
                                    killed_task['script'],
                                    ' '.join(killed_task['args']),
                                    killed_task['status'],
                                    killed_task['added_time'],
                                    killed_task['start_time'],
                                    killed_task['end_time'],
                                    killed_task.get('scheduled_time', '')
                                ))
                                # Force the tree to refresh
                                self.gui.tree.update()
                                break
                    
                    # Schedule the update in the main thread
                    self.gui.root.after(0, update_tree)
                
                # Kill the process
                self.currently_running_process.kill()
                self.currently_running_process = None
                self.currently_running_task = None
                
            except Exception as e:
                print(f"Error killing process: {e}")
                
            messagebox.showinfo("Task Killed", "The current task has been terminated.")
        else:
            messagebox.showinfo("No Task", "No task is currently running.")

    def _worker(self):
        """Worker thread to process tasks"""
        while not self.stop_event.is_set():
            try:
                # Only process tasks if auto_start is True
                if not self.auto_start:
                    time.sleep(0.5)  # Prevent tight looping
                    continue

                # Use a timeout to periodically check the stop event and auto_start flag
                task = self.task_queue.get(timeout=1)
                
                # Skip killed tasks unless they've been reset
                if task['status'] == TaskStatus.KILLED.value:
                    continue
                                
                # Store task ID before execution
                current_task_id = task['id']
                
                # Execute the task
                self._execute_task(task)
                
                # After task completes, requeue remaining tasks in current GUI order
                if self.auto_start:
                    # Clear the current queue
                    while not self.task_queue.empty():
                        try:
                            self.task_queue.get_nowait()
                        except Empty:
                            break
                    
                    # Get tasks in current GUI order and queue pending ones
                    tasks_ordered = self._get_tasks_in_gui_order()
                    found_current = False
                    
                    # Queue all pending tasks that come after the current task in GUI order
                    for task in tasks_ordered:
                        if not found_current:
                            if task['id'] == current_task_id:
                                found_current = True
                            continue
                        
                        if task['status'] == TaskStatus.PENDING.value:
                            self.task_queue.put(task)
                
            except Empty:
                # No tasks available, continue waiting
                continue
            except Exception as e:
                print(f"Error in worker thread: {e}")
                continue

    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.stop_event.clear()
            self.auto_start = False  # Prevent automatic task processing
            self.worker_thread = Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            self.is_running = True

    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.stop_event.set()
            self.worker_thread.join()
            self.is_running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskSchedulerGUI(root)
    root.mainloop()
