#!/usr/bin/env python
"""
Touchstone to CSV Converter Utility

Converts .s2p and .s4p Touchstone files to CSV format for use with pandastable.

Usage:
    python convert_touchstone.py <touchstone_file>
    python convert_touchstone.py <touchstone_file> <output_csv>
    
Examples:
    python convert_touchstone.py example_channel.s2p
    python convert_touchstone.py example_channel.s2p channel_data.csv
"""

import sys
import os
from pandastable.touchstone_parser import parse_touchstone, touchstone_to_csv

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    touchstone_file = sys.argv[1]
    
    if not os.path.exists(touchstone_file):
        print(f"Error: File not found: {touchstone_file}")
        sys.exit(1)
    
    # Output CSV file
    if len(sys.argv) >= 3:
        csv_file = sys.argv[2]
    else:
        csv_file = None  # Will auto-generate name
    
    try:
        # Convert to CSV
        output_file = touchstone_to_csv(touchstone_file, csv_file)
        
        # Parse and display info
        df, metadata = parse_touchstone(touchstone_file)
        
        print(f"\n✓ Successfully converted Touchstone file!")
        print(f"  Input:  {touchstone_file}")
        print(f"  Output: {output_file}")
        print(f"\nFile Info:")
        print(f"  Ports:      {metadata['num_ports']}")
        print(f"  Format:     {metadata['format']}")
        print(f"  Freq Unit:  {metadata['freq_unit']}")
        print(f"  Impedance:  {metadata['impedance']} Ω")
        print(f"  Data Points: {len(df)}")
        print(f"\nColumns in CSV:")
        for col in df.columns:
            print(f"  - {col}")
        
        print(f"\nYou can now load '{output_file}' in pandastable and plot with 'sparam' plot type!")
        
    except Exception as e:
        print(f"Error converting file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
