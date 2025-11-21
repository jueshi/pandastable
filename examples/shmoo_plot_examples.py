"""
2D Shmoo Plot Examples for Pandastable
=======================================

This script demonstrates the 2D shmoo plot functionality with various
use cases common in semiconductor testing and hardware validation.

Author: AI Assistant
Date: 2025-10-05
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Example 1: Voltage-Current Sweep (Regular Grid)
# ================================================
print("Example 1: Voltage-Current Sweep (Regular Grid)")
print("-" * 60)

# Generate regular grid data
voltages = np.linspace(0.8, 1.2, 20)
currents = np.linspace(0.1, 0.5, 15)

data = []
for v in voltages:
    for i in currents:
        # Simulate a measurement that passes in the middle region
        measurement = 1.0 - 0.5 * ((v - 1.0)**2 + (i - 0.3)**2)
        # Add some noise
        measurement += np.random.normal(0, 0.02)
        data.append([v, i, measurement])

df1 = pd.DataFrame(data, columns=['Voltage', 'Current', 'Measurement'])

print(f"Data shape: {df1.shape}")
print(f"Voltage range: {df1['Voltage'].min():.2f} - {df1['Voltage'].max():.2f}")
print(f"Current range: {df1['Current'].min():.2f} - {df1['Current'].max():.2f}")
print(f"Measurement range: {df1['Measurement'].min():.3f} - {df1['Measurement'].max():.3f}")
print("\nTo use in pandastable:")
print("  1. Load this CSV")
print("  2. Choose 'shmoo' plot type")
print("  3. Set threshold_min=0.8, threshold_max=1.0")
print("  4. Enable 'show statistics'\n")

# Example 2: Temperature-Frequency Characterization
# ==================================================
print("\nExample 2: Temperature-Frequency Characterization")
print("-" * 60)

temperatures = np.arange(-40, 125, 5)  # -40°C to 125°C
frequencies = np.arange(100, 1100, 25)  # 100 MHz to 1 GHz

data = []
for temp in temperatures:
    for freq in frequencies:
        # Simulate timing margin that degrades with temp and frequency
        margin = 100 - 0.3 * abs(temp - 25) - 0.05 * freq
        margin += np.random.normal(0, 2)
        data.append([temp, freq, margin])

df2 = pd.DataFrame(data, columns=['Temperature_C', 'Frequency_MHz', 'Timing_Margin_ps'])

print(f"Data shape: {df2.shape}")
print(f"Temperature range: {df2['Temperature_C'].min():.0f}°C - {df2['Temperature_C'].max():.0f}°C")
print(f"Frequency range: {df2['Frequency_MHz'].min():.0f} - {df2['Frequency_MHz'].max():.0f} MHz")
print(f"Margin range: {df2['Timing_Margin_ps'].min():.1f} - {df2['Timing_Margin_ps'].max():.1f} ps")
print("\nRecommended settings:")
print("  - threshold_min=20 (minimum acceptable margin)")
print("  - interpolation='bilinear'")
print("  - show_contours=True\n")

# Example 3: Power Supply Characterization (Irregular Grid)
# ==========================================================
print("\nExample 3: Power Supply Characterization (Irregular Grid)")
print("-" * 60)

# Generate irregular grid data (random sampling)
np.random.seed(42)
n_points = 200

vdd = np.random.uniform(1.0, 1.3, n_points)
vss = np.random.uniform(-0.2, 0.2, n_points)

# Simulate power consumption
power = 50 + 30 * vdd - 20 * vss + np.random.normal(0, 2, n_points)

df3 = pd.DataFrame({
    'VDD': vdd,
    'VSS': vss,
    'Power_mW': power
})

print(f"Data shape: {df3.shape}")
print(f"VDD range: {df3['VDD'].min():.2f} - {df3['VDD'].max():.2f} V")
print(f"VSS range: {df3['VSS'].min():.2f} - {df3['VSS'].max():.2f} V")
print(f"Power range: {df3['Power_mW'].min():.1f} - {df3['Power_mW'].max():.1f} mW")
print("\nRecommended settings:")
print("  - interpolation='cubic' (for smooth irregular grid)")
print("  - show_markers=True (to see actual test points)")
print("  - colormap='plasma'\n")

# Example 4: Signal Integrity Sweep
# ==================================
print("\nExample 4: Signal Integrity Sweep")
print("-" * 60)

rise_times = np.linspace(50, 500, 25)  # ps
slew_rates = np.linspace(0.5, 5.0, 20)  # V/ns

data = []
for rt in rise_times:
    for sr in slew_rates:
        # Simulate eye opening (better with faster rise time and moderate slew)
        eye_opening = 200 - 0.2 * rt - 10 * abs(sr - 2.5)
        eye_opening += np.random.normal(0, 5)
        eye_opening = max(0, eye_opening)  # Can't be negative
        data.append([rt, sr, eye_opening])

df4 = pd.DataFrame(data, columns=['Rise_Time_ps', 'Slew_Rate_V_ns', 'Eye_Opening_mV'])

print(f"Data shape: {df4.shape}")
print(f"Rise time range: {df4['Rise_Time_ps'].min():.0f} - {df4['Rise_Time_ps'].max():.0f} ps")
print(f"Slew rate range: {df4['Slew_Rate_V_ns'].min():.1f} - {df4['Slew_Rate_V_ns'].max():.1f} V/ns")
print(f"Eye opening range: {df4['Eye_Opening_mV'].min():.1f} - {df4['Eye_Opening_mV'].max():.1f} mV")
print("\nRecommended settings:")
print("  - threshold_min=100 (minimum acceptable eye opening)")
print("  - show_contours=True, contour_levels=15\n")

# Example 5: Process Corner Validation
# =====================================
print("\nExample 5: Process Corner Validation")
print("-" * 60)

# NMOS and PMOS threshold voltage variations
vth_n = np.linspace(-0.05, 0.05, 15)  # Variation from nominal
vth_p = np.linspace(-0.05, 0.05, 15)

data = []
for vn in vth_n:
    for vp in vth_p:
        # Simulate delay (increases with higher thresholds)
        delay = 100 + 500 * vn + 300 * vp
        delay += np.random.normal(0, 5)
        data.append([vn, vp, delay])

df5 = pd.DataFrame(data, columns=['VTH_N_variation', 'VTH_P_variation', 'Delay_ps'])

print(f"Data shape: {df5.shape}")
print(f"VTH_N variation: {df5['VTH_N_variation'].min():.3f} - {df5['VTH_N_variation'].max():.3f} V")
print(f"VTH_P variation: {df5['VTH_P_variation'].min():.3f} - {df5['VTH_P_variation'].max():.3f} V")
print(f"Delay range: {df5['Delay_ps'].min():.1f} - {df5['Delay_ps'].max():.1f} ps")
print("\nRecommended settings:")
print("  - threshold_max=150 (maximum acceptable delay)")
print("  - colormap='RdYlGn_r' (reversed for delay)")
print("  - show_stats=True\n")

# Example 6: Yield Analysis
# ==========================
print("\nExample 6: Yield Analysis (Pass/Fail Data)")
print("-" * 60)

x_positions = np.arange(0, 10, 0.5)
y_positions = np.arange(0, 10, 0.5)

data = []
for x in x_positions:
    for y in y_positions:
        # Simulate pass/fail based on distance from center
        distance = np.sqrt((x - 5)**2 + (y - 5)**2)
        # Higher probability of pass near center
        pass_prob = 1.0 - 0.15 * distance
        passed = 1 if np.random.random() < pass_prob else 0
        data.append([x, y, passed])

df6 = pd.DataFrame(data, columns=['X_Position_mm', 'Y_Position_mm', 'Pass'])

print(f"Data shape: {df6.shape}")
print(f"X range: {df6['X_Position_mm'].min():.1f} - {df6['X_Position_mm'].max():.1f} mm")
print(f"Y range: {df6['Y_Position_mm'].min():.1f} - {df6['Y_Position_mm'].max():.1f} mm")
print(f"Pass rate: {df6['Pass'].mean() * 100:.1f}%")
print("\nRecommended settings:")
print("  - threshold_min=0.5, threshold_max=1.5 (to highlight pass=1)")
print("  - interpolation='nearest' (for discrete pass/fail)")
print("  - show_stats=True\n")

# Example 7: Multi-Parameter Optimization
# ========================================
print("\nExample 7: Multi-Parameter Optimization")
print("-" * 60)

# Optimize two design parameters
param1 = np.linspace(0, 10, 30)
param2 = np.linspace(0, 10, 30)

data = []
for p1 in param1:
    for p2 in param2:
        # Simulate a performance metric with optimal region
        performance = 100 * np.exp(-((p1-6)**2 + (p2-4)**2) / 10)
        performance += np.random.normal(0, 2)
        data.append([p1, p2, performance])

df7 = pd.DataFrame(data, columns=['Parameter_1', 'Parameter_2', 'Performance_Score'])

print(f"Data shape: {df7.shape}")
print(f"Parameter 1 range: {df7['Parameter_1'].min():.1f} - {df7['Parameter_1'].max():.1f}")
print(f"Parameter 2 range: {df7['Parameter_2'].min():.1f} - {df7['Parameter_2'].max():.1f}")
print(f"Performance range: {df7['Performance_Score'].min():.1f} - {df7['Performance_Score'].max():.1f}")
print("\nRecommended settings:")
print("  - threshold_min=80 (target performance)")
print("  - show_contours=True")
print("  - colormap='viridis'\n")

# Example 8: Jitter Analysis
# ===========================
print("\nExample 8: Jitter Analysis")
print("-" * 60)

data_rates = np.arange(1, 11, 0.5)  # Gbps
cable_lengths = np.arange(0, 21, 1)  # meters

data = []
for rate in data_rates:
    for length in cable_lengths:
        # Simulate jitter (increases with rate and length)
        jitter = 10 + 5 * rate + 2 * length
        jitter += np.random.normal(0, 1)
        data.append([rate, length, jitter])

df8 = pd.DataFrame(data, columns=['Data_Rate_Gbps', 'Cable_Length_m', 'Jitter_ps'])

print(f"Data shape: {df8.shape}")
print(f"Data rate range: {df8['Data_Rate_Gbps'].min():.1f} - {df8['Data_Rate_Gbps'].max():.1f} Gbps")
print(f"Cable length range: {df8['Cable_Length_m'].min():.0f} - {df8['Cable_Length_m'].max():.0f} m")
print(f"Jitter range: {df8['Jitter_ps'].min():.1f} - {df8['Jitter_ps'].max():.1f} ps")
print("\nRecommended settings:")
print("  - threshold_max=50 (maximum acceptable jitter)")
print("  - show_contours=True")
print("  - interpolation='bilinear'\n")

# Example 9: Thermal Characterization
# ====================================
print("\nExample 9: Thermal Characterization")
print("-" * 60)

ambient_temps = np.arange(0, 71, 5)  # °C
power_levels = np.arange(0, 101, 5)  # W

data = []
for amb in ambient_temps:
    for pwr in power_levels:
        # Simulate junction temperature
        tj = amb + 0.8 * pwr + np.random.normal(0, 2)
        data.append([amb, pwr, tj])

df9 = pd.DataFrame(data, columns=['Ambient_Temp_C', 'Power_W', 'Junction_Temp_C'])

print(f"Data shape: {df9.shape}")
print(f"Ambient temp range: {df9['Ambient_Temp_C'].min():.0f} - {df9['Ambient_Temp_C'].max():.0f} °C")
print(f"Power range: {df9['Power_W'].min():.0f} - {df9['Power_W'].max():.0f} W")
print(f"Junction temp range: {df9['Junction_Temp_C'].min():.1f} - {df9['Junction_Temp_C'].max():.1f} °C")
print("\nRecommended settings:")
print("  - threshold_max=125 (maximum junction temperature)")
print("  - colormap='hot'")
print("  - show_stats=True\n")

# Example 10: Bit Error Rate Testing
# ===================================
print("\nExample 10: Bit Error Rate Testing")
print("-" * 60)

signal_levels = np.linspace(-10, 10, 25)  # dBm
noise_levels = np.linspace(-80, -40, 20)  # dBm

data = []
for sig in signal_levels:
    for noise in noise_levels:
        # Simulate BER (log scale)
        snr = sig - noise
        ber = max(-15, -0.5 * snr + np.random.normal(0, 0.5))
        data.append([sig, noise, ber])

df10 = pd.DataFrame(data, columns=['Signal_dBm', 'Noise_dBm', 'Log_BER'])

print(f"Data shape: {df10.shape}")
print(f"Signal range: {df10['Signal_dBm'].min():.1f} - {df10['Signal_dBm'].max():.1f} dBm")
print(f"Noise range: {df10['Noise_dBm'].min():.1f} - {df10['Noise_dBm'].max():.1f} dBm")
print(f"Log BER range: {df10['Log_BER'].min():.1f} - {df10['Log_BER'].max():.1f}")
print("\nRecommended settings:")
print("  - threshold_min=-12 (BER < 1e-12)")
print("  - colormap='RdYlGn'")
print("  - show_contours=True\n")

# Save all example datasets
# ==========================
print("\n" + "=" * 60)
print("Saving example datasets...")
print("=" * 60)

try:
    df1.to_csv('shmoo_example_1_voltage_current.csv', index=False)
    df2.to_csv('shmoo_example_2_temp_freq.csv', index=False)
    df3.to_csv('shmoo_example_3_power_supply.csv', index=False)
    df4.to_csv('shmoo_example_4_signal_integrity.csv', index=False)
    df5.to_csv('shmoo_example_5_process_corner.csv', index=False)
    df6.to_csv('shmoo_example_6_yield_analysis.csv', index=False)
    df7.to_csv('shmoo_example_7_optimization.csv', index=False)
    df8.to_csv('shmoo_example_8_jitter.csv', index=False)
    df9.to_csv('shmoo_example_9_thermal.csv', index=False)
    df10.to_csv('shmoo_example_10_ber.csv', index=False)
    
    print("✓ All example datasets saved successfully!")
    print("\nYou can now:")
    print("1. Open pandastable")
    print("2. Load any of the example CSV files")
    print("3. Choose 'shmoo' from plot type dropdown")
    print("4. Adjust parameters as recommended above")
    print("5. Experiment with different options")
    
except Exception as e:
    print(f"Error saving files: {e}")

print("\n" + "=" * 60)
print("2D Shmoo Plot Feature Summary")
print("=" * 60)
print("""
Key Features:
-------------
1. Regular and irregular grid support
2. Pass/fail threshold visualization
3. Contour line overlay
4. Multiple interpolation methods
5. Statistics display (pass rate, margins)
6. Flexible parameter selection
7. Colorbar and grid options
8. Marker display for data points

Best Practices:
---------------
- Use regular grids when possible (faster rendering)
- Set thresholds for pass/fail visualization
- Enable contours for level visualization
- Use 'nearest' interpolation for discrete data
- Use 'cubic' interpolation for smooth irregular grids
- Enable statistics for pass/fail analysis
- Choose appropriate colormap (RdYlGn for pass/fail)

Common Use Cases:
-----------------
- Semiconductor device characterization
- Power supply validation
- Signal integrity analysis
- Thermal characterization
- Yield analysis
- Process corner validation
- Multi-parameter optimization
- Environmental testing

Interpolation Guide:
--------------------
- 'none': Scatter plot (fastest, shows actual points)
- 'nearest': Nearest neighbor (good for discrete data)
- 'bilinear': Linear interpolation (smooth, moderate speed)
- 'cubic': Cubic interpolation (smoothest, slower)

Colormap Recommendations:
-------------------------
- 'RdYlGn': Pass/fail (red=fail, green=pass)
- 'RdYlGn_r': Reversed (for delay/jitter)
- 'viridis': General purpose
- 'plasma': High contrast
- 'hot': Temperature data
- 'coolwarm': Diverging data
""")

print("\nFor more information, see:")
print("- PLOTTING_FEATURES_PRD.md (Section 2)")
print("- shmoo_plot_implementation.py")
print("- SHMOO_PLOT_INTEGRATION_COMPLETE.md")
print("=" * 60)
