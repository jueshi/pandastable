#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Advanced MATLAB-Python Bidirectional Communication Example
This script demonstrates handling complex data structures and executing
longer-running processes with bidirectional communication
"""

import numpy as np
import matplotlib.pyplot as plt
import threading
import time
import os

# Global variable to store the MATLAB callbacks
matlab_callbacks = {}
execution_results = {}

def register_matlab_callback(name, callback_func):
    """
    Register a MATLAB function that Python can call using a specified name
    
    Args:
        name: String identifier for the callback
        callback_func: A MATLAB function handle
    """
    global matlab_callbacks
    matlab_callbacks[name] = callback_func
    print(f"Python: MATLAB callback '{name}' registered successfully")
    return True

def process_array(array_data):
    """
    Process a numpy array received from MATLAB
    
    Args:
        array_data: Numpy array (converted from MATLAB array)
    
    Returns:
        Processed array and statistics
    """
    # Convert MATLAB array to numpy array if needed
    if not isinstance(array_data, np.ndarray):
        array_data = np.array(array_data)
    
    print(f"Python received array with shape: {array_data.shape}")
    
    # Perform some calculations
    mean_val = np.mean(array_data)
    std_val = np.std(array_data)
    max_val = np.max(array_data)
    min_val = np.min(array_data)
    
    # Process the array (example: apply a filter)
    processed = array_data * 2 + 10
    
    # Create a result structure
    result = {
        'processed_array': processed,
        'statistics': {
            'mean': mean_val,
            'std': std_val,
            'max': max_val,
            'min': min_val
        }
    }
    
    print(f"Python returning processed array with statistics")
    return result

def generate_plot(x_data, y_data, title, save_path=None):
    """
    Generate a plot from data sent from MATLAB and save it
    
    Args:
        x_data: X-axis data points
        y_data: Y-axis data points
        title: Plot title
        save_path: Path to save the plot image
    
    Returns:
        Path to the saved plot
    """
    # Convert inputs if needed
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    
    print(f"Python creating plot with {len(x_data)} data points")
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(x_data, y_data, 'b-', linewidth=2)
    plt.grid(True)
    plt.title(title)
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    
    # Save the plot
    if save_path is None:
        save_path = os.path.join(os.getcwd(), 'matlab_python_plot.png')
    
    plt.savefig(save_path)
    plt.close()
    
    print(f"Python saved plot to: {save_path}")
    return save_path

def start_long_process(process_id, duration, update_interval=1.0):
    """
    Start a long-running process and periodically call back to MATLAB with updates
    
    Args:
        process_id: Identifier for the process
        duration: Duration in seconds
        update_interval: How often to send updates to MATLAB
    
    Returns:
        Process ID
    """
    def run_process():
        start_time = time.time()
        end_time = start_time + duration
        
        # Store initial state
        execution_results[process_id] = {
            'status': 'running',
            'progress': 0,
            'start_time': start_time,
            'end_time': end_time
        }
        
        while time.time() < end_time:
            # Calculate progress percentage
            elapsed = time.time() - start_time
            progress = min(100, (elapsed / duration) * 100)
            
            # Update status
            execution_results[process_id]['progress'] = progress
            
            # Call MATLAB with progress update if callback exists
            if 'progress_update' in matlab_callbacks:
                try:
                    matlab_callbacks['progress_update'](process_id, progress)
                except Exception as e:
                    print(f"Error calling MATLAB callback: {e}")
            
            # Sleep for update interval
            time.sleep(update_interval)
        
        # Final result
        result = {
            'process_id': process_id,
            'duration': duration,
            'completion_time': time.time(),
            'result_data': np.random.rand(5, 5)  # Example result data
        }
        
        # Update status
        execution_results[process_id] = {
            'status': 'completed',
            'progress': 100,
            'result': result
        }
        
        # Call MATLAB with completion notice if callback exists
        if 'process_complete' in matlab_callbacks:
            try:
                matlab_callbacks['process_complete'](process_id, result)
            except Exception as e:
                print(f"Error calling MATLAB callback: {e}")
    
    # Start the process in a background thread
    thread = threading.Thread(target=run_process)
    thread.daemon = True
    thread.start()
    
    print(f"Python: Started long process with ID: {process_id}")
    return process_id

def get_process_status(process_id):
    """
    Get the status of a long-running process
    
    Args:
        process_id: Identifier for the process
    
    Returns:
        Current status information
    """
    if process_id not in execution_results:
        return {'status': 'unknown', 'error': 'Process ID not found'}
    
    return execution_results[process_id]

if __name__ == "__main__":
    print("This is the advanced Python-MATLAB bridge module")
    print("Run the corresponding MATLAB script to use these functions")
