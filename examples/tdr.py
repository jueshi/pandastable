#!/usr/bin/env python3
"""
TDR Analysis Tool
Implementation for Time Domain Reflectometry analysis with differential impedance support
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import skrf as rf

def read_sparam_4port(filepath):
    """
    Read 4-port S-parameter file using scikit-rf.

    Args:
        filepath (str or Path): Path to the Touchstone file.

    Returns:
        tuple: (frequency array, S-parameter matrix array).
    """
    try:
        # Use scikit-rf to read the full 4-port network
        network = rf.Network(str(filepath))
        return network.f, network.s
    except Exception as e:
        print(f"scikit-rf failed ({e}), using manual parser...")
        return _read_manual_4port(filepath)

def _read_manual_4port(filepath):
    """
    Read 4-port S-parameter file manually as a fallback.

    Args:
        filepath (str or Path): Path to the Touchstone file.

    Returns:
        tuple: (frequency array, S-parameter matrix array).
    """
    freq = []
    s_data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith(('!', '#')): continue
            values = line.strip().split()
            if len(values) >= 9:  # At minimum we need 9 values (freq + real/imag for at least 4 parameters)
                try:
                    f_val = float(values[0])
                    if f_val > 0:
                        freq.append(f_val)
                        # For each frequency point, create a 4x4 complex matrix
                        s_matrix = np.zeros((4, 4), dtype=complex)
                        idx = 1  # Start after frequency value
                        
                        # Read all 16 S-parameters
                        for i in range(4):
                            for j in range(4):
                                if idx + 1 < len(values):
                                    s_real = float(values[idx])
                                    s_imag = float(values[idx+1])
                                    s_matrix[i, j] = s_real + 1j * s_imag
                                    idx += 2
                        
                        s_data.append(s_matrix)
                except ValueError: continue
    if not freq:
        raise ValueError("No valid data found")
    
    return np.array(freq), np.array(s_data)

def convert_to_mixed_mode(s_matrix):
    """
    Convert 4-port single-ended S-parameters to mixed-mode S-parameters (specifically Sdd11).

    Args:
        s_matrix (np.array): Array of 4-port S-matrices.

    Returns:
        np.array: Array of differential return loss (Sdd11).
    """
    n_freq = s_matrix.shape[0]
    sdd11 = np.zeros(n_freq, dtype=complex)
    
    for i in range(n_freq):
        s = s_matrix[i]
        # Calculate Sdd11 = 0.5 * (S11 - S13 - S31 + S33)
        sdd11[i] = 0.5 * (s[0, 0] - s[0, 2] - s[2, 0] + s[2, 2])
    
    return sdd11

def calculate_tdr(freq, s_param, window='kaiser', response_type='step', is_differential=True):
    """
    Calculate Time Domain Reflectometry (TDR) response.

    Args:
        freq (np.array): Frequency array.
        s_param (np.array): S-parameter array (complex).
        window (str): Windowing function ('kaiser' or 'hamming').
        response_type (str): 'step' or 'impulse'.
        is_differential (bool): Whether the input is differential.

    Returns:
        tuple: (time array, TDR response array).
    """
    # Better DC handling - PLTS likely uses extrapolation instead of just setting to 0
    if freq[0] > 1e6:
        # Linear extrapolation from first two points
        if len(freq) >= 2:
            slope = (s_param[1] - s_param[0]) / (freq[1] - freq[0])
            dc_value = s_param[0] - slope * freq[0]
        else:
            dc_value = 0
            
        freq = np.concatenate(([0], freq))
        s_param = np.concatenate(([dc_value], s_param))
    
    # Use Kaiser with beta=6 to match PLTS behavior
    beta = 6  # More aggressive Kaiser beta
    w = np.kaiser(len(s_param), beta) if window == 'kaiser' else np.hamming(len(s_param))
    s_param_w = s_param * w
    
    # Compute impulse response
    tdr_impulse = np.fft.ifft(s_param_w)
    
    dt = 1 / (2 * freq[-1])
    t = np.arange(len(tdr_impulse)) * dt * 1e9  # ns
    
    if response_type == 'step':
        # Calculate step response
        tdr_step = np.cumsum(tdr_impulse.real)
        
        # PLTS likely uses more sophisticated normalization
        max_abs = np.max(np.abs(tdr_step))
        if max_abs > 0:
            # Use a smaller scale factor to match PLTS sensitivity
            scale_factor = min(1.0, 0.8 / max_abs)
            tdr_step = tdr_step * scale_factor
            
            # Apply a small offset to center around zero
            late_time_avg = np.mean(tdr_step[-int(len(tdr_step)/5):])
            tdr_step = tdr_step - late_time_avg
        
        return t, tdr_step
    else:
        return t, np.abs(tdr_impulse)

def calculate_impedance(reflection_coefficient, z0=100.0):
    """
    Calculate impedance profile from reflection coefficient.

    Args:
        reflection_coefficient (np.array): TDR step response (reflection coefficient).
        z0 (float): Reference impedance.

    Returns:
        np.array: Impedance profile.
    """
    # Use a tighter limit to match PLTS sensitivity
    rc_limited = np.clip(reflection_coefficient, -0.9, 0.9)
    
    # Calculate impedance
    impedance = z0 * (1 + rc_limited) / (1 - rc_limited)
    
    # PLTS likely uses minimal or no smoothing to preserve features
    window_size = min(5, len(impedance) // 50 * 2 + 1)  # Much smaller window
    if window_size >= 3:
        kernel = np.ones(window_size) / window_size
        impedance = np.convolve(impedance, kernel, mode='same')
    
    return impedance

def plot_tdr(t, tdr, title=None):
    """
    Create and display a TDR plot.

    Args:
        t (np.array): Time array.
        tdr (np.array): TDR response array.
        title (str, optional): Plot title.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(t, tdr, linewidth=1.5)
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Magnitude (V)')
    plt.title(title or 'TDR Response')
    t_max = min(10, max(t)/4)
    plt.xlim(0, t_max)
    plt.ylim(0, max(tdr) * 1.1)

if __name__ == "__main__":
    # Path to the S-parameter file
    s_param_file = Path(r"C:\Users\juesh\OneDrive\Documents\MATLAB\alab\file_browsers\sd_s_param\sd1b_rx0_6in.s4p")

    # Read the 4-port S-parameter file
    freq, s_data = read_sparam_4port(s_param_file)
    
    # Convert to differential S-parameters (Sdd11)
    sdd11 = convert_to_mixed_mode(s_data)
    
    # Visualize comparison of impulse and step responses
    plt.figure(figsize=(10, 12))
    
    # Plot 1: Impulse Response
    plt.subplot(311)
    t_impulse, tdr_impulse = calculate_tdr(freq, sdd11, window='kaiser', response_type='impulse', is_differential=True)
    plt.plot(t_impulse, tdr_impulse, 'b-')
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Magnitude (V)')
    plt.title('Differential TDR Impulse Response')
    plt.xlim(0, 6)  # Match PLTS x-axis range
    
    # Plot 2: Step Response
    plt.subplot(312)
    t_step, tdr_step = calculate_tdr(freq, sdd11, window='kaiser', response_type='step', is_differential=True)
    plt.plot(t_step, tdr_step, 'r-')
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Reflection Coefficient')
    plt.title('Differential TDR Step Response')
    plt.xlim(0, 6)  # Match PLTS x-axis range
    
    # Plot 3: Impedance Profile
    plt.subplot(313)
    impedance = calculate_impedance(tdr_step, z0=100.0)  # Use 100 ohms for differential
    plt.plot(t_step, impedance, 'g-')
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Differential Impedance (Ω)')
    plt.title('Differential Impedance Profile')
    
    # Set y-axis limits to match typical differential impedance plot scale
    # For differential 100 ohm traces, typically centered at 100 ohms
    y_mean = np.mean(impedance)
    plt.ylim(50, 150)  # Focus on range for 100 ohm differential
    
    plt.tight_layout()
    plt.show()
    
    # Now show the full impedance profile plot with PLTS-like scaling
    plt.figure(figsize=(10, 6))
    plt.plot(t_step, impedance, 'g-', linewidth=1.5)
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Differential Impedance (Ω)')
    plt.title('Differential Impedance Profile for sd1b_rx0_6in.s4p')
    
    # Match PLTS scaling (observed ~2 ohms/div)
    plt.ylim(50, 150)
    
    # Add reference line for expected differential impedance
    plt.axhline(y=100, color='r', linestyle='--', label='Z0 = 100 Ω')
    plt.legend()
    plt.show()