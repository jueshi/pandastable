"""
Bathtub Plot Examples for SerDes BER Analysis

This script demonstrates how to use the bathtub plot feature
for visualizing Bit Error Rate (BER) vs sampling point position.

Examples:
1. Basic single bathtub curve
2. Dual bathtub (left/right edges)
3. Voltage bathtub
4. Multiple channel comparison

Author: Pandastable Team
Date: 2025-10-05
"""

import os
import sys
import pandas as pd
import numpy as np

# Add pandastable to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_bathtub_data(center_ber=1e-16, margin_ui=0.4, num_points=21):
    """
    Generate synthetic bathtub curve data.
    
    Parameters:
    -----------
    center_ber : float
        BER at optimal sampling point (center)
    margin_ui : float
        Timing margin in UI at 1e-12 BER
    num_points : int
        Number of data points
        
    Returns:
    --------
    pd.DataFrame with Sample_UI and BER columns
    """
    # Sample points from -0.5 to +0.5 UI
    sample_ui = np.linspace(-0.5, 0.5, num_points)
    
    # Generate bathtub shape using Gaussian-like function
    # BER increases exponentially away from center
    ber = []
    for s in sample_ui:
        # Calculate BER based on distance from center
        # Adjust shape to match desired margin
        distance = abs(s)
        if distance < margin_ui / 2:
            # Inside margin - very low BER
            ber_val = center_ber * 10**(distance / (margin_ui/2) * 4)
        else:
            # Outside margin - BER increases rapidly
            ber_val = 1e-12 * 10**((distance - margin_ui/2) / 0.1 * 3)
        ber.append(min(ber_val, 1e-2))  # Cap at 1e-2
    
    df = pd.DataFrame({
        'Sample_UI': sample_ui,
        'BER': ber
    })
    
    return df


def generate_dual_bathtub_data(center_ber_left=1e-16, center_ber_right=1.5e-16,
                                margin_left=0.38, margin_right=0.42, num_points=21):
    """
    Generate asymmetric dual bathtub curve data.
    
    Parameters:
    -----------
    center_ber_left : float
        BER at center for left edge
    center_ber_right : float
        BER at center for right edge
    margin_left : float
        Left edge margin in UI
    margin_right : float
        Right edge margin in UI
    num_points : int
        Number of data points
        
    Returns:
    --------
    pd.DataFrame with Sample_UI, BER_Left, BER_Right columns
    """
    sample_ui = np.linspace(-0.5, 0.5, num_points)
    
    ber_left = []
    ber_right = []
    
    for s in sample_ui:
        distance = abs(s)
        
        # Left edge BER
        if distance < margin_left / 2:
            ber_l = center_ber_left * 10**(distance / (margin_left/2) * 4)
        else:
            ber_l = 1e-12 * 10**((distance - margin_left/2) / 0.1 * 3)
        ber_left.append(min(ber_l, 1e-2))
        
        # Right edge BER (slightly different)
        if distance < margin_right / 2:
            ber_r = center_ber_right * 10**(distance / (margin_right/2) * 4)
        else:
            ber_r = 1e-12 * 10**((distance - margin_right/2) / 0.1 * 3)
        ber_right.append(min(ber_r, 1e-2))
    
    df = pd.DataFrame({
        'Sample_UI': sample_ui,
        'BER_Left': ber_left,
        'BER_Right': ber_right
    })
    
    return df


def generate_voltage_bathtub_data(center_ber=1e-16, margin_mv=100, num_points=15):
    """
    Generate voltage bathtub curve data.
    
    Parameters:
    -----------
    center_ber : float
        BER at optimal voltage (center)
    margin_mv : float
        Voltage margin in mV at 1e-12 BER
    num_points : int
        Number of data points
        
    Returns:
    --------
    pd.DataFrame with Voltage_mV and BER columns
    """
    voltage_mv = np.linspace(-250, 250, num_points)
    
    ber = []
    for v in voltage_mv:
        distance = abs(v)
        if distance < margin_mv:
            ber_val = center_ber * 10**(distance / margin_mv * 4)
        else:
            ber_val = 1e-12 * 10**((distance - margin_mv) / 50 * 3)
        ber.append(min(ber_val, 1e-1))
    
    df = pd.DataFrame({
        'Voltage_mV': voltage_mv,
        'BER': ber
    })
    
    return df


def example_1_basic_bathtub():
    """Example 1: Basic single bathtub curve"""
    print("\n" + "="*60)
    print("Example 1: Basic Single Bathtub Curve")
    print("="*60)
    
    # Generate data
    df = generate_bathtub_data(center_ber=1e-16, margin_ui=0.40, num_points=21)
    
    # Save to CSV
    output_file = os.path.join(os.path.dirname(__file__), '..', 'bathtub_test_1_basic.csv')
    df.to_csv(output_file, index=False)
    print(f"✓ Generated: {output_file}")
    print(f"  - Data points: {len(df)}")
    print(f"  - BER range: {df['BER'].min():.2e} to {df['BER'].max():.2e}")
    print(f"  - Expected margin: ~0.40 UI at 1e-12 BER")
    
    return df


def example_2_dual_bathtub():
    """Example 2: Dual bathtub (left/right edges)"""
    print("\n" + "="*60)
    print("Example 2: Dual Bathtub (Asymmetric)")
    print("="*60)
    
    # Generate asymmetric data
    df = generate_dual_bathtub_data(
        center_ber_left=1e-16,
        center_ber_right=1.5e-16,
        margin_left=0.38,
        margin_right=0.42,
        num_points=21
    )
    
    # Save to CSV
    output_file = os.path.join(os.path.dirname(__file__), '..', 'bathtub_test_2_dual.csv')
    df.to_csv(output_file, index=False)
    print(f"✓ Generated: {output_file}")
    print(f"  - Data points: {len(df)}")
    print(f"  - Left BER range: {df['BER_Left'].min():.2e} to {df['BER_Left'].max():.2e}")
    print(f"  - Right BER range: {df['BER_Right'].min():.2e} to {df['BER_Right'].max():.2e}")
    print(f"  - Shows asymmetric eye (left vs right edge)")
    
    return df


def example_3_voltage_bathtub():
    """Example 3: Voltage bathtub"""
    print("\n" + "="*60)
    print("Example 3: Voltage Bathtub")
    print("="*60)
    
    # Generate voltage data
    df = generate_voltage_bathtub_data(center_ber=1e-16, margin_mv=100, num_points=15)
    
    # Save to CSV
    output_file = os.path.join(os.path.dirname(__file__), '..', 'bathtub_test_3_voltage.csv')
    df.to_csv(output_file, index=False)
    print(f"✓ Generated: {output_file}")
    print(f"  - Data points: {len(df)}")
    print(f"  - Voltage range: {df['Voltage_mV'].min():.0f} to {df['Voltage_mV'].max():.0f} mV")
    print(f"  - BER range: {df['BER'].min():.2e} to {df['BER'].max():.2e}")
    print(f"  - Expected margin: ~200 mV at 1e-12 BER")
    
    return df


def example_4_multi_channel():
    """Example 4: Multiple channel comparison"""
    print("\n" + "="*60)
    print("Example 4: Multi-Channel Comparison")
    print("="*60)
    
    sample_ui = np.linspace(-0.5, 0.5, 21)
    
    # Generate data for 3 channels with different margins
    df = pd.DataFrame({'Sample_UI': sample_ui})
    
    for ch, margin in enumerate([0.45, 0.38, 0.35]):
        ber = []
        for s in sample_ui:
            distance = abs(s)
            if distance < margin / 2:
                ber_val = 1e-16 * 10**(distance / (margin/2) * 4)
            else:
                ber_val = 1e-12 * 10**((distance - margin/2) / 0.1 * 3)
            ber.append(min(ber_val, 1e-2))
        df[f'Ch{ch}_BER'] = ber
    
    # Save to CSV
    output_file = os.path.join(os.path.dirname(__file__), '..', 'bathtub_test_4_multichannel.csv')
    df.to_csv(output_file, index=False)
    print(f"✓ Generated: {output_file}")
    print(f"  - Channels: 3")
    print(f"  - Ch0 margin: ~0.45 UI (best)")
    print(f"  - Ch1 margin: ~0.38 UI (good)")
    print(f"  - Ch2 margin: ~0.35 UI (marginal)")
    
    return df


def print_usage_instructions():
    """Print instructions for using the generated data"""
    print("\n" + "="*60)
    print("How to Use These Examples")
    print("="*60)
    print("""
1. Open DataExplore or CSV Browser:
   python pandastable/app.py
   
2. Load one of the generated CSV files:
   - bathtub_test_1_basic.csv
   - bathtub_test_2_dual.csv
   - bathtub_test_3_voltage.csv
   - bathtub_test_4_multichannel.csv

3. Click the "Plot" button in the toolbar

4. Select "bathtub" from the plot type dropdown

5. Configure options:
   - BER target: 1e-12 (default)
   - show margins: On
   - margin style: arrows
   - For dual curve: Enable "dual curve (L/R)"
   - For voltage: Set X-axis type to "Voltage (mV)"

6. Click "Apply Options" to generate the plot

Expected Results:
- Example 1: Classic U-shaped bathtub with ~0.40 UI margin
- Example 2: Two curves showing asymmetric eye
- Example 3: Voltage bathtub with ~200 mV margin
- Example 4: Three overlaid curves for channel comparison
""")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Bathtub Plot Examples - Data Generator")
    print("="*60)
    print("Generating synthetic bathtub curve data for testing...")
    
    # Generate all examples
    example_1_basic_bathtub()
    example_2_dual_bathtub()
    example_3_voltage_bathtub()
    example_4_multi_channel()
    
    # Print usage instructions
    print_usage_instructions()
    
    print("\n" + "="*60)
    print("✓ All example files generated successfully!")
    print("="*60)
