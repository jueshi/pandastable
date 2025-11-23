import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import cmath

def parse_s_parameter_file(file_path):
    """
    Parse the custom S-parameter file format with 16 S-parameters per frequency point.

    Args:
        file_path (str): Path to the S-parameter file.

    Returns:
        tuple: A tuple containing:
            - frequencies (np.array): Array of frequency points.
            - s_parameters (np.array): Array of S-parameters (complex values).
    """
    frequencies = []
    s_parameters = []

    with open(file_path, 'r') as f:
        lines = f.readlines()
        
        # Skip header and comment lines
        data_lines = [line.strip() for line in lines if not line.startswith('!') and not line.startswith('#')]
        
        print(f"Total data lines: {len(data_lines)}")
        
        i = 0
        while i < len(data_lines):
            try:
                # Verify we have enough lines for a complete frequency point
                if i + 3 >= len(data_lines):
                    print(f"Reached end of file at line {i}")
                    break
                
                # Parse frequency line
                freq_parts = data_lines[i].split()
                freq = float(freq_parts[0])
                frequencies.append(freq)
                
                # Collect S-parameters for this frequency
                s_params_block = []
                for j in range(1, 4):
                    line_parts = data_lines[i+j].split()
                    
                    # Verify line has expected number of elements
                    if len(line_parts) % 2 != 0:
                        print(f"Warning: Unexpected number of elements in line {i+j}")
                        break
                    
                    for k in range(0, len(line_parts), 2):
                        try:
                            mag = float(line_parts[k])
                            phase = float(line_parts[k+1])
                            # Convert polar to rectangular
                            s_params_block.append(cmath.rect(mag, np.deg2rad(phase)))
                        except ValueError as ve:
                            print(f"Error converting values in line {i+j}: {ve}")
                            break
                
                # Only append if we have the expected number of S-parameters
                if len(s_params_block) == 12:
                    s_parameters.append(s_params_block)
                else:
                    print(f"Incomplete S-parameter block at frequency {freq}")
                
                # Move to next frequency point
                i += 4
            except Exception as e:
                print(f"Error processing line {i}: {e}")
                break

    return np.array(frequencies), np.array(s_parameters)

# Construct the full path to the S-parameter file
s_param_file = r'C:\Users\juesh\OneDrive\Documents\MATLAB\alab\file_browsers\sd_s_param\sd1b_rx0_6in.s4p'

# Verify file exists and parse
if not os.path.exists(s_param_file):
    print(f"Error: S-parameter file not found at {s_param_file}")
    sys.exit(1)

try:
    # Parse the S-parameter file
    print("Attempting to parse S-parameter file...")
    frequencies, s_parameters = parse_s_parameter_file(s_param_file)
    
    print(f"Parsed frequencies: {frequencies}")
    print(f"Parsed S-parameters shape: {s_parameters.shape}")

    # Optional: Plot parsed frequencies and S-parameters
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 2, 1)
    plt.title('Parsed Frequencies')
    plt.plot(frequencies / 1e9, 'bo-')  # Convert to GHz
    plt.xlabel('Data Point')
    plt.ylabel('Frequency (GHz)')
    plt.grid(True)

    plt.subplot(2, 2, 2)
    plt.title('S-Parameters Magnitude')
    magnitudes = np.abs(s_parameters)
    plt.plot(magnitudes)
    plt.xlabel('Data Point')
    plt.ylabel('S-Parameter Magnitude')
    plt.grid(True)

    plt.subplot(2, 2, 3)
    plt.title('S-Parameters Real Part')
    real_parts = np.real(s_parameters)
    plt.plot(real_parts)
    plt.xlabel('Data Point')
    plt.ylabel('S-Parameter Real Part')
    plt.grid(True)

    plt.subplot(2, 2, 4)
    plt.title('S-Parameters Imaginary Part')
    imag_parts = np.imag(s_parameters)
    plt.plot(imag_parts)
    plt.xlabel('Data Point')
    plt.ylabel('S-Parameter Imaginary Part')
    plt.grid(True)

    plt.tight_layout()
    plt.show()

except Exception as e:
    print(f"Error processing S-parameter file: {e}")
    sys.exit(1)
