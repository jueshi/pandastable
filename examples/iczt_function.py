"""
ICZT-based TDR calculation module for S-parameter analysis
This module provides functions for calculating Time Domain Reflectometry (TDR)
responses using the Inverse Chirp Z-Transform (ICZT) method.
"""

import numpy as np
from scipy import signal

def calculate_tdr_iczt(freq, s_params, t_start, t_stop, num_points):
    """Calculate TDR using ICZT approach
    
    This provides higher resolution and more control over the time domain
    compared to standard IFFT methods.
    
    Args:
        freq: Frequency points in Hz
        s_params: S-parameters (complex values)
        t_start: Start time in seconds
        t_stop: Stop time in seconds
        num_points: Number of time points to calculate
        
    Returns:
        time: Time array in seconds
        tdr: TDR response (complex values)
    """
    # Apply window to reduce ringing
    window = signal.windows.hann(len(freq))
    s_params_windowed = s_params * window
    
    # Define time points
    time = np.linspace(t_start, t_stop, num_points)
    
    # Calculate ICZT directly
    tdr = np.zeros(num_points, dtype=complex)
    for i, t in enumerate(time):
        # For each time point, calculate sum of frequency components
        tdr[i] = np.sum(s_params_windowed * np.exp(1j * 2 * np.pi * freq * t)) / len(freq)
    
    return time, tdr

# Example of how to use this function with the S-parameter browser:
"""
# Within the SParamBrowser class:
def calculate_pulse_response_iczt(self, network=None):
    # Get frequency points and S-parameters
    if network is None:
        network = self.data[0]  # Use first network if none specified
    
    f = network.f
    s21 = network.s[:, 1, 0]  # Get S21 parameter
    
    # Define time range - adjust as needed
    t_max = 1 / (f[1] - f[0])  # Maximum time from frequency spacing
    
    # Calculate with ICZT
    t_start = 0
    t_stop = t_max / 2  # Use half of the maximum time range
    num_points = len(f) * 8  # Increase resolution with more points
    
    time, pulse = calculate_tdr_iczt(f, s21, t_start, t_stop, num_points)
    
    # Continue with pulse processing...
    return time, pulse
"""
