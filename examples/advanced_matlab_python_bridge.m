%% Advanced MATLAB-Python Bidirectional Communication Example
% This script demonstrates complex data handling between MATLAB and Python
% with callbacks for long-running processes

%% Initialize the Python environment
if count(py.sys.path, '') == 0
    % Add current directory to Python path
    insert(py.sys.path, int32(0), '');
end

disp('Starting advanced MATLAB-Python bidirectional communication...');

%% Define MATLAB callback functions that Python can call

% Progress update callback
function progress_update_callback(process_id, progress)
    process_id = char(process_id);
    progress = double(progress);
    
    % Display progress information
    fprintf('MATLAB: Process %s progress: %.1f%%\n', process_id, progress);
    
    % Update progress bar (optional - requires figure to be created first)
    try
        h = findobj('Tag', ['progress_' process_id]);
        if ~isempty(h)
            waitbar(progress/100, h, sprintf('Process %s: %.1f%%', process_id, progress));
        end
    catch
        % Ignore errors if figure doesn't exist
    end
end

% Process completion callback
function process_complete_callback(process_id, result)
    process_id = char(process_id);
    
    % Convert Python dict to MATLAB structure
    result_struct = struct();
    keys = cell(result.keys());
    
    for i = 1:length(keys)
        key = char(keys{i});
        value = result{key};
        
        % Handle nested dictionaries
        if isa(value, 'py.dict')
            nested_struct = struct();
            nested_keys = cell(value.keys());
            
            for j = 1:length(nested_keys)
                nested_key = char(nested_keys{j});
                nested_struct.(nested_key) = double(value{nested_key});
            end
            
            result_struct.(key) = nested_struct;
        elseif isa(value, 'py.numpy.ndarray')
            % Convert numpy arrays to MATLAB arrays
            result_struct.(key) = double(py.array.array('d', py.numpy.nditer(value)));
        else
            % Try to convert other types
            try
                result_struct.(key) = double(value);
            catch
                result_struct.(key) = char(value);
            end
        end
    end
    
    % Display completion information
    fprintf('MATLAB: Process %s completed\n', process_id);
    
    % Close progress bar if exists
    try
        h = findobj('Tag', ['progress_' process_id]);
        if ~isempty(h)
            close(h);
        end
    catch
        % Ignore errors if figure doesn't exist
    end
    
    % Store results in base workspace
    assignin('base', ['result_' process_id], result_struct);
    
    fprintf('MATLAB: Results stored in workspace variable: result_%s\n', process_id);
end

%% Register MATLAB callbacks with Python
function register_callbacks()
    % Register the progress update callback
    py.advanced_matlab_python_bridge.register_matlab_callback('progress_update', @progress_update_callback);
    
    % Register the process completion callback
    py.advanced_matlab_python_bridge.register_matlab_callback('process_complete', @process_complete_callback);
    
    disp('MATLAB: Callbacks registered with Python');
end

%% Example: Process a MATLAB array using Python
function test_array_processing()
    % Create a test array in MATLAB
    test_array = rand(5, 5);
    
    disp('MATLAB: Sending array to Python for processing...');
    
    % Convert MATLAB array to Python numpy array
    py_array = py.numpy.array(test_array);
    
    % Call Python function to process array
    result = py.advanced_matlab_python_bridge.process_array(py_array);
    
    % Convert Python results back to MATLAB
    processed_array = double(py.array.array('d', py.numpy.nditer(result{'processed_array'})));
    processed_array = reshape(processed_array, size(test_array));
    
    % Extract statistics
    stats = result{'statistics'};
    stats_struct = struct();
    stats_keys = cell(stats.keys());
    
    for i = 1:length(stats_keys)
        key = char(stats_keys{i});
        stats_struct.(key) = double(stats{key});
    end
    
    % Display results
    disp('MATLAB: Results from Python processing:');
    disp(['Mean: ' num2str(stats_struct.mean)]);
    disp(['Standard Deviation: ' num2str(stats_struct.std)]);
    disp(['Min: ' num2str(stats_struct.min)]);
    disp(['Max: ' num2str(stats_struct.max)]);
    
    % Store results in base workspace
    assignin('base', 'processed_array', processed_array);
    assignin('base', 'array_stats', stats_struct);
    
    disp('MATLAB: Processed array and statistics stored in workspace');
end

%% Example: Generate a plot using Python's matplotlib
function test_plot_generation()
    % Create test data in MATLAB
    x = linspace(0, 10, 100);
    y = sin(x) .* exp(-0.1 * x);
    
    disp('MATLAB: Sending plot data to Python...');
    
    % Convert MATLAB arrays to Python lists
    py_x = py.list(num2cell(x));
    py_y = py.list(num2cell(y));
    
    % Call Python function to generate plot
    save_path = fullfile(pwd, 'matlab_python_plot.png');
    plot_path = py.advanced_matlab_python_bridge.generate_plot(py_x, py_y, 'MATLAB-Python Plot Example', save_path);
    
    % Display the saved plot in MATLAB
    plot_path_str = char(plot_path);
    disp(['MATLAB: Plot saved at: ' plot_path_str]);
    
    try
        figure;
        imshow(plot_path_str);
        title('Plot Generated by Python');
    catch e
        disp(['MATLAB: Error displaying plot: ' e.message]);
        disp(['MATLAB: You can view the plot directly at: ' plot_path_str]);
    end
end

%% Example: Start a long-running process with callbacks
function test_long_process()
    % Create a progress bar
    process_id = 'test_process_1';
    h = waitbar(0, 'Starting process...', 'Name', 'Long Process', 'Tag', ['progress_' process_id]);
    
    disp('MATLAB: Starting long-running process in Python...');
    
    % Start a process that will run for 10 seconds with updates every 0.5 seconds
    py.advanced_matlab_python_bridge.start_long_process(process_id, 10, 0.5);
    
    disp(['MATLAB: Process ' process_id ' started']);
    disp('MATLAB: You will receive progress updates via callbacks');
end

%% Main function - run all examples
function main()
    % Ensure Python script exists in the same directory
    scriptPath = fullfile(pwd, 'advanced_matlab_python_bridge.py');
    if ~exist(scriptPath, 'file')
        error('Python script not found: %s', scriptPath);
    end
    
    % Register callbacks
    register_callbacks();
    
    % Test array processing
    test_array_processing();
    
    % Test plot generation
    test_plot_generation();
    
    % Test long-running process
    test_long_process();
    
    disp('MATLAB: Advanced MATLAB-Python communication examples completed');
    disp('MATLAB: Long process will continue running in background');
end

% Run the main function
main();
