# Touchstone File Support for S-Parameter Plotting

## Overview

Touchstone files (.s2p, .s4p) are industry-standard formats for S-parameter data used in RF and high-speed digital design. This guide shows how to use Touchstone files with pandastable's S-parameter plotting feature.

---

## Quick Start

### Method 1: Convert to CSV (Recommended)

**Step 1: Convert Touchstone to CSV**
```bash
python convert_touchstone.py example_channel.s2p
```

This creates `example_channel.csv` with frequency and S-parameter data.

**Step 2: Load in pandastable**
```bash
python pandastable/app.py
# Or
python examples/csv_browser_v6.x1.2_search_columns.py
```

**Step 3: Plot**
- Load the CSV file
- Click Plot
- Select 'sparam' plot type
- Configure options
- Click Apply Options

### Method 2: Manual Integration (Advanced)

Add Touchstone support directly to your CSV Browser by modifying the `load_csv_file` method:

```python
# In load_csv_file method, after line 1142:
# Check if it's a Touchstone file
if file_path.lower().endswith(('.s2p', '.s4p', '.s1p', '.s3p')):
    print("Detected Touchstone file, parsing...")
    try:
        from pandastable.touchstone_parser import parse_touchstone
        df, metadata = parse_touchstone(file_path)
        print(f"Parsed: {metadata['num_ports']}-port, {len(df)} points")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to parse:\n{str(e)}")
        return
else:
    df = self._advanced_file_read(file_path)
```

---

## Touchstone File Format

### .s2p File Structure

```
! Comment lines start with !
# GHZ S MA R 50
! Freq  S11mag S11ang S21mag S21ang S12mag S12ang S22mag S22ang
0.1     0.012  -175   0.995  -2.5   0.995  -2.5   0.012  -175
1.0     0.020  -155   0.970  -15.5  0.970  -15.5  0.020  -155
...
```

### Option Line Format

`# <freq_unit> <parameter> <format> R <impedance>`

- **freq_unit**: HZ, KHZ, MHZ, GHZ
- **parameter**: S, Y, Z, H, G (S-parameters most common)
- **format**: 
  - MA = Magnitude-Angle
  - DB = dB-Angle
  - RI = Real-Imaginary
- **impedance**: Reference impedance (typically 50Ω)

### Supported Formats

| File Type | Ports | Parameters | Columns |
|-----------|-------|------------|---------|
| .s1p | 1 | S11 | 3 (freq, mag, angle) |
| .s2p | 2 | S11, S21, S12, S22 | 9 (freq + 8 values) |
| .s4p | 4 | S11-S44 | 33 (freq + 32 values) |

---

## Converter Tool Usage

### Basic Conversion

```bash
# Convert with auto-generated output name
python convert_touchstone.py example_channel.s2p
# Creates: example_channel.csv

# Specify output filename
python convert_touchstone.py example_channel.s2p my_channel.csv
```

### Batch Conversion

```bash
# Windows PowerShell
Get-ChildItem *.s2p | ForEach-Object { python convert_touchstone.py $_.Name }

# Linux/Mac
for file in *.s2p; do python convert_touchstone.py "$file"; done
```

### Output Format

The converter creates a CSV with:
- **Frequency_GHz**: Frequency in GHz (auto-converted from any unit)
- **S11_dB, S21_dB, etc.**: S-parameters in dB magnitude

Example output:
```csv
Frequency_GHz,S11_dB,S21_dB,S12_dB,S22_dB
0.1,-38.4,-0.04,-0.04,-38.4
1.0,-34.0,-0.26,-0.26,-34.0
...
```

---

## Plotting S-Parameters

### Step-by-Step

1. **Convert Touchstone file:**
   ```bash
   python convert_touchstone.py example_channel.s2p
   ```

2. **Load CSV in pandastable:**
   - Open DataExplore or CSV Browser
   - Load `example_channel.csv`

3. **Create S-parameter plot:**
   - Click Plot button
   - Select plot type: **sparam**
   - Scroll to "sparam" options section

4. **Configure options:**
   - ✅ log frequency: On (default)
   - spec limit (dB): `-10` (for PCIe Gen4)
   - limit type: `Horizontal`
   - data rate (Gbps): `16` (for PCIe Gen4)
   - ✅ Nyquist marker: On
   - freq range: Leave blank (auto)
   - dB range: Leave blank (auto)

5. **Apply and view:**
   - Click "Apply Options"
   - View S-parameter plot with spec limits

### Common Configurations

#### PCIe Gen4 (16 GT/s)
```
Plot type: sparam
spec limit: -10
limit type: Horizontal
data rate: 16
nyquist marker: On
```

#### USB 3.2 Gen 2 (10 Gbps)
```
Plot type: sparam
spec limit: -12
limit type: Horizontal
data rate: 10
nyquist marker: On
```

#### 100G Ethernet (25.78 Gbps per lane)
```
Plot type: sparam
spec limit: -10
limit type: Horizontal
data rate: 25.78
nyquist marker: On
```

---

## Parser API

### Python API

```python
from pandastable.touchstone_parser import parse_touchstone, touchstone_to_csv

# Parse Touchstone file
df, metadata = parse_touchstone('example_channel.s2p')

# Access data
print(f"Frequency range: {df['Frequency_GHz'].min()} - {df['Frequency_GHz'].max()} GHz")
print(f"S21 at 10 GHz: {df[df['Frequency_GHz']==10.0]['S21_dB'].values[0]} dB")

# Metadata
print(f"Ports: {metadata['num_ports']}")
print(f"Format: {metadata['format']}")
print(f"Impedance: {metadata['impedance']} Ω")

# Convert to CSV
csv_file = touchstone_to_csv('example_channel.s2p', 'output.csv')
```

### Metadata Dictionary

```python
metadata = {
    'format': 'MA',        # MA, DB, or RI
    'freq_unit': 'GHZ',    # HZ, KHZ, MHZ, GHZ
    'parameter': 'S',      # S, Y, Z, H, G
    'impedance': 50.0,     # Reference impedance
    'num_ports': 2         # Number of ports
}
```

---

## Examples

### Example 1: PCIe Gen4 Channel

**File**: `example_channel.s2p` (provided)

**Convert:**
```bash
python convert_touchstone.py example_channel.s2p
```

**Plot Settings:**
- spec_limit: -10
- data_rate: 16
- Shows: S11, S21, S12, S22 with Nyquist at 8 GHz

### Example 2: Create Custom .s2p File

```
! My custom channel
# GHZ S MA R 50
0.1  0.01 -180  0.99 -1   0.99 -1   0.01 -180
1.0  0.02 -170  0.95 -10  0.95 -10  0.02 -170
10.0 0.10 -140  0.70 -90  0.70 -90  0.10 -140
20.0 0.20 -120  0.40 -180 0.40 -180 0.20 -120
```

Save as `my_channel.s2p`, then convert and plot.

---

## Troubleshooting

### "Failed to parse Touchstone file"

**Cause**: Invalid file format or unsupported features

**Solutions:**
- Check option line format: `# GHZ S MA R 50`
- Ensure data has correct number of columns
- Verify frequency values are numeric
- Check for special characters in comments

### "No such file"

**Cause**: File path incorrect

**Solutions:**
- Use absolute path: `C:\path\to\file.s2p`
- Check file extension (.s2p not .S2P on Linux)
- Verify file exists: `dir file.s2p` (Windows) or `ls file.s2p` (Linux)

### "Wrong number of columns"

**Cause**: Data format doesn't match port count

**Solutions:**
- .s2p needs 9 columns (freq + 8 S-param values)
- .s4p needs 33 columns (freq + 32 S-param values)
- Check for missing or extra data

### Conversion works but plot is wrong

**Cause**: Frequency unit conversion issue

**Solutions:**
- Check metadata: `python convert_touchstone.py file.s2p` shows units
- Verify Frequency_GHz column in CSV is in GHz
- Check if values are reasonable (0.1-100 GHz typical)

---

## File Format Reference

### Magnitude-Angle (MA)

```
# GHZ S MA R 50
freq  S11_mag  S11_ang  S21_mag  S21_ang  ...
0.1   0.012    -175     0.995    -2.5     ...
```

- Magnitude: Linear (0-1 for S21, 0-0.5 for S11)
- Angle: Degrees (-180 to +180)
- Converted to dB: `20*log10(magnitude)`

### dB-Angle (DB)

```
# GHZ S DB R 50
freq  S11_dB  S11_ang  S21_dB  S21_ang  ...
0.1   -38.4   -175     -0.04   -2.5     ...
```

- Already in dB (no conversion needed)
- Angle: Degrees

### Real-Imaginary (RI)

```
# GHZ S RI R 50
freq  S11_re  S11_im  S21_re  S21_im  ...
0.1   -0.01   0.005   0.99    -0.04   ...
```

- Real and imaginary parts
- Converted to magnitude: `sqrt(re² + im²)`
- Then to dB: `20*log10(magnitude)`

---

## Integration Checklist

To fully integrate Touchstone support into CSV Browser:

- [ ] Import touchstone_parser in CSV Browser
- [ ] Add file type check in load_csv_file method
- [ ] Update file filters to include .s2p, .s4p
- [ ] Add Touchstone to supported formats in UI
- [ ] Test with example files
- [ ] Update user documentation

**Quick Integration Code:**
```python
# Add to imports at top of file
from pandastable.touchstone_parser import parse_touchstone

# Add to load_csv_file method (around line 1144)
if file_path.lower().endswith(('.s2p', '.s4p')):
    df, metadata = parse_touchstone(file_path)
else:
    df = self._advanced_file_read(file_path)
```

---

## Summary

✅ **Touchstone parser implemented** - Supports .s2p and .s4p files  
✅ **Converter tool created** - Easy command-line conversion  
✅ **S-parameter plotting ready** - Use 'sparam' plot type  
✅ **Example files provided** - Ready to test  

**Next Steps:**
1. Convert your .s2p files: `python convert_touchstone.py your_file.s2p`
2. Load CSV in pandastable
3. Plot with 'sparam' type
4. Analyze channel performance!

---

**Happy Plotting!** 📊🔬
