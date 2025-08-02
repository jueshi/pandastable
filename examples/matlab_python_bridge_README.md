# MATLAB-Python Bidirectional Communication

This set of examples demonstrates how to establish bidirectional communication between MATLAB and Python, allowing each environment to call functions in the other.

## Files Included

1. **Basic Example:**
   - `reversed_callback_Py2Matlab.m` - MATLAB script that calls Python functions and handles callbacks
   - `matlab_python_bridge.py` - Python module with functions callable from MATLAB

2. **Advanced Example:**
   - `advanced_matlab_python_bridge.m` - Advanced MATLAB script with complex data handling
   - `advanced_matlab_python_bridge.py` - Advanced Python module with plotting, array processing and long-running processes

## Requirements

- MATLAB with Python interface enabled
- Python with the following packages:
  - NumPy
  - Matplotlib (for advanced example)

## How to Use

### Basic Setup in MATLAB

1. Ensure Python is properly configured with MATLAB:
   ```matlab
   pyversion % Check which Python version MATLAB is using
   ```

2. Ensure required Python packages are installed in the Python environment MATLAB is using:
   ```
   pip install numpy matplotlib
   ```

3. Place all files in the same directory

### Running Basic Example

1. Open MATLAB and navigate to the directory containing the files
2. Run the MATLAB script:
   ```matlab
   reversed_callback_Py2Matlab
   ```

### Running Advanced Example

1. Open MATLAB and navigate to the directory containing the files
2. Run the advanced MATLAB script:
   ```matlab
   advanced_matlab_python_bridge
   ```

## How It Works

### Basic Communication Flow

1. MATLAB initializes and adds the current directory to Python's path
2. MATLAB registers one or more callback functions with Python
3. MATLAB calls Python functions, passing data as arguments
4. Python processes the data and returns results to MATLAB
5. Python can call back to MATLAB functions registered earlier
6. MATLAB receives and processes the callback data

### Advanced Features

The advanced example demonstrates:
- Complex data structure conversions between MATLAB and Python
- Processing MATLAB arrays using NumPy in Python
- Generating plots in Python and displaying them in MATLAB
- Long-running processes in Python with progress updates to MATLAB
- Handling asynchronous callbacks from Python to MATLAB

## Troubleshooting

### Common Issues

1. **Python path not found:**
   - Make sure files are in the same directory
   - Verify MATLAB can see Python using `pyversion`

2. **Missing Python packages:**
   - Install required packages in the Python environment MATLAB is using
   - Check with `py.sys.modules` to see what modules are available

3. **Type conversion errors:**
   - MATLAB and Python have different data types
   - Use appropriate conversion functions:
     - `double()` to convert Python numbers to MATLAB
     - `py.list()` or `py.numpy.array()` to convert MATLAB arrays to Python

### Data Type Conversion

- MATLAB arrays → Python: Use `py.numpy.array()` or `py.list()`
- Python numpy arrays → MATLAB: Use `double(py.array.array('d', py.numpy.nditer(array)))`
- Python dictionaries → MATLAB: Convert keys and values individually

## Extending the Examples

You can extend these examples by:
1. Adding more callback functions
2. Handling different data types
3. Implementing error handling and recovery
4. Creating a more sophisticated application that leverages both environments
