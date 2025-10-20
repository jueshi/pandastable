"""
Touchstone File Parser for S-Parameter Data

Supports .s2p (2-port) and .s4p (4-port) Touchstone files.
Converts to pandas DataFrame for easy plotting.

Author: Pandastable Team
Date: 2025-10-05
"""

import pandas as pd
import numpy as np
import re

def parse_touchstone(filename):
    """
    Parse Touchstone file (.s2p, .s4p) and convert to DataFrame.
    
    Parameters:
    -----------
    filename : str
        Path to Touchstone file
        
    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with frequency and S-parameter data
    metadata : dict
        File metadata (format, units, etc.)
    """
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Parse header and options
    metadata = {
        'format': 'MA',  # Default: Magnitude-Angle
        'freq_unit': 'GHz',
        'parameter': 'S',
        'impedance': 50.0,
        'num_ports': 2
    }
    
    data_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Parse option line (starts with #)
        if line.startswith('#'):
            parts = line[1:].strip().upper().split()
            if len(parts) >= 1:
                # Frequency unit
                if parts[0] in ['HZ', 'KHZ', 'MHZ', 'GHZ']:
                    metadata['freq_unit'] = parts[0]
                    
            if len(parts) >= 2:
                # Parameter type
                if parts[1] in ['S', 'Y', 'Z', 'H', 'G']:
                    metadata['parameter'] = parts[1]
                    
            if len(parts) >= 3:
                # Data format
                if parts[2] in ['MA', 'DB', 'RI']:
                    metadata['format'] = parts[2]
                    
            if len(parts) >= 5:
                # Reference impedance
                if parts[4] == 'R':
                    try:
                        metadata['impedance'] = float(parts[5]) if len(parts) > 5 else 50.0
                    except:
                        metadata['impedance'] = 50.0
            continue
            
        # Skip comment lines
        if line.startswith('!'):
            continue
            
        # Data line
        data_lines.append(line)
    
    # Determine number of ports from filename
    if '.s2p' in filename.lower():
        metadata['num_ports'] = 2
        num_params = 4  # S11, S21, S12, S22
    elif '.s4p' in filename.lower():
        metadata['num_ports'] = 4
        num_params = 16  # S11-S44
    else:
        # Try to detect from data
        if data_lines:
            first_data = data_lines[0].split()
            # Each S-parameter has 2 values (mag/phase or real/imag)
            num_values = len(first_data) - 1  # Subtract frequency
            num_params = num_values // 2
            metadata['num_ports'] = int(np.sqrt(num_params))
    
    # Parse data
    freq_data = []
    sparam_data = {f'S{i+1}{j+1}': [] for i in range(metadata['num_ports']) 
                   for j in range(metadata['num_ports'])}
    
    for line in data_lines:
        values = line.split()
        if len(values) < 3:  # Need at least freq + one S-param (2 values)
            continue
            
        try:
            freq = float(values[0])
            freq_data.append(freq)
            
            # Parse S-parameters
            param_idx = 0
            for i in range(metadata['num_ports']):
                for j in range(metadata['num_ports']):
                    param_name = f'S{i+1}{j+1}'
                    
                    # Get magnitude and phase/angle values
                    val_idx = 1 + param_idx * 2
                    if val_idx + 1 < len(values):
                        val1 = float(values[val_idx])
                        val2 = float(values[val_idx + 1])
                        
                        # Convert to dB magnitude based on format
                        if metadata['format'] == 'MA':
                            # Magnitude-Angle: val1 is magnitude, val2 is angle
                            mag_db = 20 * np.log10(val1) if val1 > 0 else -100
                        elif metadata['format'] == 'DB':
                            # Already in dB
                            mag_db = val1
                        elif metadata['format'] == 'RI':
                            # Real-Imaginary: convert to magnitude
                            mag = np.sqrt(val1**2 + val2**2)
                            mag_db = 20 * np.log10(mag) if mag > 0 else -100
                        else:
                            mag_db = val1
                        
                        sparam_data[param_name].append(mag_db)
                    else:
                        sparam_data[param_name].append(np.nan)
                    
                    param_idx += 1
                    
        except (ValueError, IndexError) as e:
            print(f"Warning: Could not parse line: {line}")
            continue
    
    # Convert frequency to GHz
    freq_array = np.array(freq_data)
    if metadata['freq_unit'] == 'HZ':
        freq_ghz = freq_array / 1e9
    elif metadata['freq_unit'] == 'KHZ':
        freq_ghz = freq_array / 1e6
    elif metadata['freq_unit'] == 'MHZ':
        freq_ghz = freq_array / 1e3
    else:  # GHZ
        freq_ghz = freq_array
    
    # Create DataFrame
    df_dict = {'Frequency_GHz': freq_ghz}
    
    # Add S-parameters with _dB suffix
    for param_name, values in sparam_data.items():
        if len(values) == len(freq_ghz):
            df_dict[f'{param_name}_dB'] = values
    
    df = pd.DataFrame(df_dict)
    
    return df, metadata


def touchstone_to_csv(touchstone_file, csv_file=None):
    """
    Convert Touchstone file to CSV format.
    
    Parameters:
    -----------
    touchstone_file : str
        Path to input Touchstone file
    csv_file : str, optional
        Path to output CSV file. If None, uses same name with .csv extension
        
    Returns:
    --------
    csv_file : str
        Path to created CSV file
    """
    
    if csv_file is None:
        csv_file = touchstone_file.rsplit('.', 1)[0] + '.csv'
    
    df, metadata = parse_touchstone(touchstone_file)
    df.to_csv(csv_file, index=False)
    
    print(f"Converted {touchstone_file} to {csv_file}")
    print(f"  Ports: {metadata['num_ports']}")
    print(f"  Format: {metadata['format']}")
    print(f"  Frequency points: {len(df)}")
    
    return csv_file


if __name__ == '__main__':
    # Test the parser
    import sys
    
    if len(sys.argv) > 1:
        touchstone_file = sys.argv[1]
        df, metadata = parse_touchstone(touchstone_file)
        
        print(f"\nParsed Touchstone file: {touchstone_file}")
        print(f"Metadata: {metadata}")
        print(f"\nDataFrame shape: {df.shape}")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst few rows:")
        print(df.head())
        
        # Save to CSV
        csv_file = touchstone_to_csv(touchstone_file)
        print(f"\nSaved to: {csv_file}")
    else:
        print("Usage: python touchstone_parser.py <touchstone_file>")
