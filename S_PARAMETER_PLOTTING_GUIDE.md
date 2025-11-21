# S-Parameter Plotting Guide

Complete guide for plotting S-parameter data in pandastable with Touchstone file support.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Touchstone File Support](#touchstone-file-support)
3. [S-Parameter Plot Options](#s-parameter-plot-options)
4. [Step-by-Step Instructions](#step-by-step-instructions)
5. [Common Use Cases](#common-use-cases)
6. [Troubleshooting](#troubleshooting)
7. [File Format Reference](#file-format-reference)

---

## Quick Start

### 3-Step Process

**Step 1: Convert Touchstone to CSV**
```bash
python convert_touchstone.py example_channel.s2p
```

**Step 2: Load in pandastable**
```bash
python examples/csv_browser_v6.x1.2_search_columns.py
```

**Step 3: Plot**
- Load the CSV file
- Click **Plot** button
- Select **'sparam'** plot type
- Configure options
- Click **Apply Options**

---

## Touchstone File Support

### Supported File Types

| Extension | Ports | Parameters | Description |
|-----------|-------|------------|-------------|
| `.s1p` | 1 | S11 | Single-port device |
| `.s2p` | 2 | S11, S21, S12, S22 | Two-port device (most common) |
| `.s4p` | 4 | S11-S44 (16 params) | Four-port device |

### Touchstone File Format

```
! Comment lines start with exclamation mark
# GHZ S MA R 50
! Option line format: # <freq_unit> <parameter> <format> R <impedance>
0.1  0.012  -175   0.995  -2.5   0.995  -2.5   0.012  -175
1.0  0.020  -155   0.970  -15.5  0.970  -15.5  0.020  -155
...
```

**Option Line Parameters:**
- **Frequency Unit:** HZ, KHZ, MHZ, GHZ
- **Parameter Type:** S (S-parameters), Y, Z, H, G
- **Data Format:** 
  - **MA** = Magnitude-Angle (most common)
  - **DB** = dB-Angle
  - **RI** = Real-Imaginary
- **Reference Impedance:** Typically 50Ω or 75Ω

### Converting Touchstone Files

**Basic Conversion:**
```bash
# Auto-generate output filename
python convert_touchstone.py input_file.s2p

# Specify output filename
python convert_touchstone.py input_file.s2p output_file.csv
```

**Batch Conversion:**
```powershell
# Windows PowerShell
Get-ChildItem *.s2p | ForEach-Object { python convert_touchstone.py $_.Name }
```

```bash
# Linux/Mac
for file in *.s2p; do python convert_touchstone.py "$file"; done
```

**Output Format:**
```csv
Frequency_GHz,S11_dB,S21_dB,S12_dB,S22_dB
0.1,-38.4,-0.04,-0.04,-38.4
1.0,-34.0,-0.26,-0.26,-34.0
10.0,-15.0,-14.5,-14.5,-15.0
20.0,-10.8,-38.0,-38.0,-11.0
```

---

## S-Parameter Plot Options

### Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| **log frequency** | Checkbox | ✓ On | Logarithmic frequency axis |
| **show phase** | Checkbox | Off | Show phase on secondary Y-axis (future) |
| **spec limit (dB)** | Entry | "" | Horizontal spec limit line |
| **limit type** | Dropdown | None | None / Horizontal / Vertical |
| **Nyquist marker** | Checkbox | Off | Mark Nyquist frequency |
| **data rate (Gbps)** | Entry | "" | Data rate for Nyquist calculation |
| **freq range (GHz)** | Entry | "" | Custom frequency range (e.g., "0.1-30") |
| **dB range** | Entry | "" | Custom dB range (e.g., "-40-0") |

### Option Details

**log frequency:**
- When enabled: X-axis uses logarithmic scale (good for wide frequency ranges)
- When disabled: X-axis uses linear scale

**spec limit:**
- Enter value in dB (e.g., `-10` for -10 dB)
- Used with `limit_type: Horizontal` to draw spec line

**Nyquist marker:**
- Requires `data_rate` to be specified
- Nyquist frequency = Data Rate / 2
- Example: 16 Gbps → 8 GHz Nyquist

**freq range:**
- Format: `min-max` (e.g., `0.1-30` for 0.1 to 30 GHz)
- Leave blank for auto-range

**dB range:**
- Format: `min-max` (e.g., `-40-0` for -40 to 0 dB)
- Leave blank for auto-range

---

## Step-by-Step Instructions

### Method 1: Using CSV Browser (Recommended)

**1. Start CSV Browser**
```bash
cd c:\Users\juesh\jules\pandastable0
python examples\csv_browser_v6.x1.2_search_columns.py
```

**2. Convert Touchstone File**
```bash
python convert_touchstone.py example_channel.s2p
```
This creates `example_channel.csv`

**3. Load CSV File**
- Navigate to the directory containing your CSV
- Click on the CSV file in the file list
- The data will appear in the right panel

**4. Open Plot Viewer**
- Click the **Plot** button in the toolbar
- A new window will open with plot options

**5. Select S-Parameter Plot**
- In the plot viewer, find the **"kind"** dropdown
- Select **"sparam"** from the list
- The sparam options section will appear

**6. Configure Options**

Scroll down to the **"sparam"** section and set:
- ✓ **log frequency**: Checked (default)
- **spec limit (dB)**: Enter `-10`
- **limit type**: Select `Horizontal`
- **data rate (Gbps)**: Enter `16` (for PCIe Gen4)
- ✓ **Nyquist marker**: Checked
- **freq range**: Leave blank (auto)
- **dB range**: Leave blank (auto)

**7. Generate Plot**
- Click **"Apply Options"** button
- The S-parameter plot will be displayed

### Method 2: Using DataExplore (Standalone)

**1. Start DataExplore**
```bash
python c:\Users\juesh\jules\pandastable0\pandastable\app.py
```

**2. Import CSV**
- Click **File → Import → CSV**
- Navigate to your converted CSV file
- Click **Open**

**3. Open Plot**
- Click **Tools → Plot** (or toolbar Plot button)

**4. Configure and Plot**
- Follow steps 5-7 from Method 1 above

---

## Common Use Cases

### Use Case 1: PCIe Gen4 Channel Validation

**Requirement:** S21 > -10 dB at 8 GHz (Nyquist for 16 GT/s)

**Data:** `example_channel.s2p` or `sparam_example_3_pcie_gen4.csv`

**Settings:**
```
Plot type: sparam
spec limit: -10
limit type: Horizontal
data rate: 16
nyquist marker: On
```

**Expected Result:**
- S21 curve showing insertion loss vs frequency
- Red dashed line at -10 dB
- Orange dotted line at 8 GHz (Nyquist)
- Verify S21 is above -10 dB at 8 GHz

**Pass/Fail:**
- ✓ PASS if S21 > -10 dB at 8 GHz
- ✗ FAIL if S21 < -10 dB at 8 GHz

---

### Use Case 2: USB 3.2 Gen 2 Compliance

**Requirement:** S21 > -12 dB at 5 GHz (Nyquist for 10 Gbps)

**Settings:**
```
Plot type: sparam
spec limit: -12
limit type: Horizontal
data rate: 10
nyquist marker: On
```

**Expected Result:**
- S21 curve
- Red line at -12 dB
- Orange line at 5 GHz
- Check S21 at Nyquist

---

### Use Case 3: 100G Ethernet (25.78 Gbps per lane)

**Requirement:** S21 > -10 dB at 12.89 GHz

**Settings:**
```
Plot type: sparam
spec limit: -10
limit type: Horizontal
data rate: 25.78
nyquist marker: On
```

---

### Use Case 4: Multi-Parameter Analysis

**Objective:** View S11, S21, S12, S22 together

**Data:** `sparam_example_2_multi.csv`

**Settings:**
```
Plot type: sparam
log frequency: On
legend: On
```

**Expected Result:**
- Four curves on same plot:
  - S11 (blue) - Input return loss
  - S21 (orange) - Forward insertion loss
  - S12 (green) - Reverse insertion loss
  - S22 (red) - Output return loss
- Legend identifying each curve

---

### Use Case 5: Return Loss Analysis

**Objective:** Verify S11 < -15 dB across band

**Settings:**
```
Plot type: sparam
spec limit: -15
limit_type: Horizontal
```

**Expected Result:**
- S11 curve (return loss)
- Red line at -15 dB
- S11 should be below (more negative than) -15 dB

**Interpretation:**
- S11 close to 0 dB = Poor impedance match
- S11 very negative (< -20 dB) = Good impedance match

---

## Troubleshooting

### Issue: "Failed to parse Touchstone file"

**Possible Causes:**
1. Invalid file format
2. Unsupported features
3. Corrupted file

**Solutions:**
1. Check option line format: `# GHZ S MA R 50`
2. Verify data has correct number of columns:
   - .s2p needs 9 columns (freq + 8 values)
   - .s4p needs 33 columns (freq + 32 values)
3. Check for special characters in comments
4. Try opening file in text editor to verify format

---

### Issue: "No such file"

**Possible Causes:**
1. Incorrect file path
2. File doesn't exist
3. Case sensitivity (Linux/Mac)

**Solutions:**
1. Use absolute path: `C:\path\to\file.s2p`
2. Verify file exists: `dir file.s2p` (Windows) or `ls file.s2p` (Linux)
3. Check file extension (.s2p not .S2P on Linux)

---

### Issue: Plot doesn't appear

**Possible Causes:**
1. Wrong plot type selected
2. CSV has wrong format
3. Not enough data points

**Solutions:**
1. Verify 'sparam' is selected in plot type dropdown
2. Check CSV has at least 2 columns (Frequency, S-parameter)
3. Click "Apply Options" button
4. Check console for DEBUG messages

---

### Issue: Frequency axis looks wrong

**Possible Causes:**
1. Frequency units not converted properly
2. Data in wrong units

**Solutions:**
1. Check converter output for frequency unit
2. Verify Frequency_GHz column in CSV
3. Check if values are reasonable (0.1-100 GHz typical)
4. Try converting original file again

---

### Issue: Spec limit not showing

**Possible Causes:**
1. limit_type not set
2. spec_limit empty
3. Limit outside plot range

**Solutions:**
1. Set limit_type to "Horizontal"
2. Enter spec_limit value (e.g., `-10`)
3. Adjust dB range to include limit
4. Click "Apply Options" again

---

### Issue: Nyquist marker not showing

**Possible Causes:**
1. data_rate not specified
2. Nyquist outside frequency range
3. nyquist_marker not checked

**Solutions:**
1. Enter data_rate (e.g., `16` for 16 Gbps)
2. Check nyquist_marker checkbox
3. Adjust freq_range to include Nyquist
4. Verify Nyquist = data_rate / 2

---

## File Format Reference

### CSV Format (Converted from Touchstone)

**Required Columns:**
- `Frequency_GHz`: Frequency in GHz (numeric)
- At least one S-parameter column ending in `_dB`

**Example:**
```csv
Frequency_GHz,S11_dB,S21_dB,S12_dB,S22_dB
0.1,-38.4,-0.04,-0.04,-38.4
0.5,-35.5,-0.22,-0.22,-35.5
1.0,-34.0,-0.26,-0.26,-34.0
2.0,-31.0,-0.44,-0.44,-31.0
5.0,-26.0,-1.17,-1.17,-26.0
10.0,-15.0,-14.5,-14.5,-15.0
20.0,-10.8,-38.0,-38.0,-11.0
```

---

### Touchstone .s2p Format

**Structure:**
```
! Comments (optional)
# <freq_unit> <parameter> <format> R <impedance>
<freq> <S11_val1> <S11_val2> <S21_val1> <S21_val2> <S12_val1> <S12_val2> <S22_val1> <S22_val2>
...
```

**Example:**
```
! PCIe Gen4 Channel
# GHZ S MA R 50
0.1  0.012 -175  0.995 -2.5  0.995 -2.5  0.012 -175
1.0  0.020 -155  0.970 -15.5 0.970 -15.5 0.020 -155
10.0 0.105 -108  0.565 -138  0.565 -138  0.105 -108
20.0 0.345 -96   0.055 -275  0.055 -275  0.345 -96
```

**Data Format Conversions:**

**MA (Magnitude-Angle):**
- Value 1: Linear magnitude (0-1)
- Value 2: Angle in degrees (-180 to +180)
- Conversion to dB: `20 * log10(magnitude)`

**DB (dB-Angle):**
- Value 1: Already in dB
- Value 2: Angle in degrees
- No conversion needed

**RI (Real-Imaginary):**
- Value 1: Real part
- Value 2: Imaginary part
- Conversion: `magnitude = sqrt(real² + imag²)`, then `20 * log10(magnitude)`

---

## S-Parameter Interpretation

### Common S-Parameters

| Parameter | Name | Description | Good Value | Bad Value |
|-----------|------|-------------|------------|-----------|
| **S11** | Input Return Loss | Reflection at input port | < -15 dB | > -10 dB |
| **S21** | Insertion Loss | Transmission from port 1 to 2 | > -10 dB at Nyquist | < -15 dB |
| **S12** | Reverse Insertion Loss | Transmission from port 2 to 1 | Same as S21 | Much different from S21 |
| **S22** | Output Return Loss | Reflection at output port | < -15 dB | > -10 dB |

### Reading the Plot

**Insertion Loss (S21):**
- **0 dB:** Perfect transmission (no loss)
- **-3 dB:** Half power transmitted
- **-10 dB:** 10% power transmitted
- **-20 dB:** 1% power transmitted

**Return Loss (S11, S22):**
- **0 dB:** Total reflection (open/short)
- **-10 dB:** 10% power reflected (poor match)
- **-20 dB:** 1% power reflected (good match)
- **-30 dB:** 0.1% power reflected (excellent match)

---

## Advanced Features

### Python API

**Direct Parsing:**
```python
from pandastable.touchstone_parser import parse_touchstone

# Parse Touchstone file
df, metadata = parse_touchstone('example_channel.s2p')

# Access data
print(f"Frequency range: {df['Frequency_GHz'].min()}-{df['Frequency_GHz'].max()} GHz")
print(f"S21 at 10 GHz: {df[df['Frequency_GHz']==10.0]['S21_dB'].values[0]} dB")

# Metadata
print(f"Ports: {metadata['num_ports']}")
print(f"Format: {metadata['format']}")
print(f"Impedance: {metadata['impedance']} Ω")
```

**Conversion:**
```python
from pandastable.touchstone_parser import touchstone_to_csv

# Convert to CSV
csv_file = touchstone_to_csv('input.s2p', 'output.csv')
```

---

## Quick Reference

### Common Data Rates and Nyquist Frequencies

| Standard | Data Rate | Nyquist | Typical S21 Spec |
|----------|-----------|---------|------------------|
| PCIe Gen3 | 8 GT/s | 4 GHz | > -10 dB |
| PCIe Gen4 | 16 GT/s | 8 GHz | > -10 dB |
| PCIe Gen5 | 32 GT/s | 16 GHz | > -10 dB |
| USB 3.2 Gen 1 | 5 Gbps | 2.5 GHz | > -12 dB |
| USB 3.2 Gen 2 | 10 Gbps | 5 GHz | > -12 dB |
| 100G Ethernet | 25.78 Gbps | 12.89 GHz | > -10 dB |

### File Locations

```
pandastable0/
├── convert_touchstone.py          # Converter utility
├── pandastable/
│   └── touchstone_parser.py       # Parser module
├── examples/
│   └── csv_browser_v6.x1.2_search_columns.py  # CSV Browser
├── example_channel.s2p             # Example Touchstone file
├── sparam_example_1_s21.csv        # Example: Single S21
├── sparam_example_2_multi.csv      # Example: Multiple S-params
├── sparam_example_3_pcie_gen4.csv  # Example: PCIe Gen4
├── S_PARAMETER_PLOT_PRD.md         # Feature specification
├── TOUCHSTONE_SUPPORT.md           # Detailed Touchstone guide
└── S_PARAMETER_PLOTTING_GUIDE.md   # This file
```

---

## Summary Checklist

### To Plot S-Parameters:

- [ ] Convert Touchstone file: `python convert_touchstone.py file.s2p`
- [ ] Start CSV Browser or DataExplore
- [ ] Load converted CSV file
- [ ] Click Plot button
- [ ] Select 'sparam' plot type
- [ ] Configure options (spec limit, data rate, etc.)
- [ ] Click "Apply Options"
- [ ] Analyze results

### For Compliance Testing:

- [ ] Know your spec requirements (e.g., S21 > -10 dB at Nyquist)
- [ ] Set spec_limit to required value
- [ ] Set data_rate to calculate Nyquist
- [ ] Enable nyquist_marker
- [ ] Set limit_type to Horizontal
- [ ] Verify S-parameter meets spec at Nyquist frequency

---

## Support and Resources

**Documentation:**
- `S_PARAMETER_PLOT_PRD.md` - Feature specification
- `TOUCHSTONE_SUPPORT.md` - Detailed Touchstone guide
- `BATHTUB_CURVE_PRD.md` - Bathtub plot guide

**Example Files:**
- `example_channel.s2p` - 2-port Touchstone example
- `sparam_example_*.csv` - Pre-converted CSV examples

**Tools:**
- `convert_touchstone.py` - Command-line converter
- `pandastable/touchstone_parser.py` - Python API

---

**Last Updated:** 2025-10-05  
**Version:** 1.0  
**Status:** ✅ Complete and Ready to Use
