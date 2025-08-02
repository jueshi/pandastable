%% MATLAB-Python Bidirectional Communication Example
% This script demonstrates how to call Python from MATLAB and handle callbacks

% Initialize the Python environment
if count(py.sys.path, '') == 0
    % Add current directory to Python path
    insert(py.sys.path, int32(0), '');
end

%% Define a MATLAB function that Python can call back
function result = matlabFunction(input)
    % This function can be called from Python
    disp(['MATLAB received: ', num2str(input)]);
    
    % Do some MATLAB-specific computation
    result = input * 2;
    
    disp(['MATLAB returning: ', num2str(result)]);
end

%% Register the MATLAB callback function with Python
function registerMatlabCallback()
    % Create a Python function handle to this MATLAB function
    py.matlab_python_bridge.register_matlab_callback(@matlabFunction);
    
    disp('MATLAB callback registered with Python');
end

%% Main function to start the bidirectional communication
function main()
    disp('Starting MATLAB-Python bidirectional communication...');
    
    % Ensure Python script exists in the same directory
    scriptPath = fullfile(pwd, 'matlab_python_bridge.py');
    if ~exist(scriptPath, 'file')
        error('Python script not found: %s', scriptPath);
    end
    
    % Register the MATLAB callback with Python
    registerMatlabCallback();
    
    % Call a Python function with a parameter
    result = py.matlab_python_bridge.python_function(42);
    disp(['Python returned: ', num2str(double(result))]);
    
    % Call a Python function that will call back to MATLAB
    py.matlab_python_bridge.call_matlab_function(10);
    
    disp('MATLAB-Python communication test completed.');
end

% Run the main function
main();
