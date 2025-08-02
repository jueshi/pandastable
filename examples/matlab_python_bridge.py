#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MATLAB-Python Bidirectional Communication Example
This script provides functions that can be called from MATLAB
and also demonstrates calling back to MATLAB functions
"""

import numpy as np

# Global variable to store the MATLAB callback function
matlab_callback = None

def register_matlab_callback(callback_func):
    """
    Register a MATLAB function that Python can call
    
    Args:
        callback_func: A MATLAB function handle
    """
    global matlab_callback
    matlab_callback = callback_func
    print("Python: MATLAB callback registered successfully")
    return True

def python_function(input_value):
    """
    A Python function that can be called from MATLAB
    
    Args:
        input_value: Numeric input from MATLAB
    
    Returns:
        Processed value (input_value * 3)
    """
    print(f"Python received: {input_value}")
    
    # Perform Python-specific computation
    result = input_value * 3
    
    print(f"Python returning: {result}")
    return result

def call_matlab_function(input_value):
    """
    Call the registered MATLAB function
    
    Args:
        input_value: Value to pass to MATLAB
    
    Returns:
        Result from MATLAB function or None if no callback registered
    """
    global matlab_callback
    
    if matlab_callback is None:
        print("Python: No MATLAB callback registered")
        return None
    
    print(f"Python: Calling MATLAB function with input {input_value}")
    
    # Call the MATLAB function
    result = matlab_callback(input_value)
    
    # Convert MATLAB result to Python
    python_result = float(result)
    print(f"Python: MATLAB function returned {python_result}")
    
    return python_result

def demonstrate_standalone():
    """
    Demonstrate Python functionality when run directly
    (not called from MATLAB)
    """
    print("This is a standalone demonstration of the Python module")
    print("In actual use, these functions would be called from MATLAB")
    
    # Example of Python function
    result = python_function(15)
    print(f"Result from python_function: {result}")
    
    print("\nNote: The MATLAB callback cannot be demonstrated in standalone mode")
    print("Run the MATLAB script 'reversed_callback_Py2Matlab.m' instead")

if __name__ == "__main__":
    demonstrate_standalone()
