#!/usr/bin/env python3
"""
TDR Analysis Tool
Basic implementation for Time Domain Reflectometry analysis
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import skrf as rf

def read_sparam(filepath):
    """Read S-parameter file using scikit-rf or manual parser"""
    try:
        network = rf.Network(str(filepath))
        return network.f, network.s[:, 0, 0]
    except Exception as e:
        print(f"scikit-rf failed ({e}), using manual parser...")
        return _read_manual(filepath)

def _read_manual(filepath):
    """Read S-parameter file manually"""
    freq = []
    s11_real = []
    s11_imag = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith(('!', '#')): continue
            values = line.strip().split()
            if len(values) >= 9:
                try:
                    f_val = float(values[0])
                    if f_val > 0:
                        freq.append(f_val)
                        s11_real.append(float(values[1]))
                        s11_imag.append(float(values[2]))
                except ValueError: continue
    if not freq:
        raise ValueError("No valid data found")
    return np.array(freq), np.array(s11_real) + 1j * np.array(s11_imag)

def calculate_tdr(freq, s11, window='hamming'):
    """Calculate TDR response"""
    w = np.kaiser(len(s11), 6) if window == 'kaiser' else np.hamming(len(s11))
    s11_w = s11 * w
    tdr = np.fft.ifft(s11_w)
    dt = 1 / (2 * freq[-1])
    t = np.arange(len(tdr)) * dt * 1e9  # ns
    return t, np.abs(tdr)  # Return magnitude in volts

def plot_tdr(t, tdr, title=None):
    """Create TDR plot"""
    plt.figure(figsize=(10, 6))
    plt.plot(t, tdr, linewidth=1.5)
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Magnitude (V)')  # Change y-axis label to volts
    plt.title(title or 'TDR Response')
    t_max = min(10, max(t)/4)
    plt.xlim(0, t_max)
    plt.ylim(0, max(tdr) * 1.1)  # Adjust y-axis limits for voltage display

if __name__ == "__main__":
    # Path to the S-parameter file
    s_param_file = Path(r"C:\Users\juesh\OneDrive\Documents\MATLAB\alab\file_browsers\sd_s_param\sd1b_rx0_6in.s4p")

    # Read the S-parameter file
    freq, s11 = read_sparam(s_param_file)
    
    # Visualize the S11 data in frequency domain
    plt.figure(figsize=(12, 10))
    
    # Plot 1: S11 Magnitude
    plt.subplot(221)
    plt.plot(freq/1e9, np.abs(s11), 'b-')
    plt.grid(True)
    plt.xlabel('Frequency (GHz)')
    plt.ylabel('|S11| Magnitude')
    plt.title('S11 Magnitude vs Frequency')
    
    # Plot 2: S11 Phase
    plt.subplot(222)
    plt.plot(freq/1e9, np.angle(s11, deg=True), 'r-')
    plt.grid(True)
    plt.xlabel('Frequency (GHz)')
    plt.ylabel('Phase (degrees)')
    plt.title('S11 Phase vs Frequency')
    
    # Compute windowed S11 and compare
    window = np.hamming(len(s11))
    s11_windowed = s11 * window
    
    # Plot 3: Original vs Windowed S11
    plt.subplot(223)
    plt.plot(freq/1e9, np.abs(s11), 'b-', label='Original')
    plt.plot(freq/1e9, np.abs(s11_windowed), 'g-', label='Windowed')
    plt.grid(True)
    plt.xlabel('Frequency (GHz)')
    plt.ylabel('|S11| Magnitude')
    plt.title('Effect of Windowing on S11')
    plt.legend()
    
    # Plot 4: Time domain impulse response (using both methods)
    plt.subplot(224)
    
    # Original TDR calculation
    t, tdr_magnitude = calculate_tdr(freq, s11)
    plt.plot(t, tdr_magnitude, 'b-', label='TDR Response')
    
    # Calculate with different window for comparison
    t_kaiser, tdr_kaiser = calculate_tdr(freq, s11, window='kaiser')
    plt.plot(t_kaiser, tdr_kaiser, 'r--', label='TDR (Kaiser window)')
    
    plt.grid(True)
    plt.xlabel('Time (ns)')
    plt.ylabel('Magnitude (V)')
    plt.title('TDR Response: Hamming vs Kaiser Window')
    plt.legend()
    
    plt.tight_layout()
    plt.show()
    
    # Now continue with the original TDR analysis in a separate figure
    t, tdr_magnitude = calculate_tdr(freq, s11)
    
    # Plot the TDR response
    plot_tdr(t, tdr_magnitude, title="TDR Analysis for sd1b_rx0_6in.s4p")

    # Show the plot
    plt.show()