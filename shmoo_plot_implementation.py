"""
2D Shmoo Plot Implementation for Pandastable
=============================================

This file contains the implementation of the 2D shmoo plot feature for
parameter sweep visualization, commonly used in semiconductor and hardware testing.

Author: AI Assistant
Date: 2025-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors

def shmoo(self, df, ax, kwds):
    """
    Create 2D shmoo plot for parameter sweep visualization.
    
    A shmoo plot visualizes the results of a 2D parameter sweep, typically
    showing pass/fail regions or measurement values across a grid of test conditions.
    Common in semiconductor testing, hardware validation, and system characterization.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Data to plot. Must contain at least 3 columns for X, Y, and Z values.
    ax : matplotlib.axes.Axes
        Axes object to plot on
    kwds : dict
        Plotting keywords including:
        - x_param: str, X-axis parameter column name (default: first column)
        - y_param: str, Y-axis parameter column name (default: second column)
        - z_param: str, Z-value parameter column name (default: third column)
        - threshold_min: float, minimum passing threshold (optional)
        - threshold_max: float, maximum passing threshold (optional)
        - colormap: str, colormap name (default: 'RdYlGn')
        - show_contours: bool, overlay contour lines (default: False)
        - contour_levels: int, number of contour levels (default: 10)
        - interpolation: str, interpolation method ('none', 'nearest', 'bilinear', 'cubic')
        - show_stats: bool, display pass/fail statistics (default: False)
        - grid: bool, show grid (default: True)
        - colorbar: bool, show colorbar (default: True)
        - marker_size: float, size of data point markers (default: 50)
        - show_markers: bool, show data point markers (default: False)
        
    Returns:
    --------
    ax : matplotlib.axes.Axes
    """
    
    # Get parameters
    x_param = kwds.get('x_param', None)
    y_param = kwds.get('y_param', None)
    z_param = kwds.get('z_param', None)
    threshold_min = kwds.get('threshold_min', None)
    threshold_max = kwds.get('threshold_max', None)
    cmap_name = kwds.get('colormap', 'RdYlGn')
    show_contours = kwds.get('show_contours', False)
    contour_levels = kwds.get('contour_levels', 10)
    interpolation = kwds.get('interpolation', 'nearest')
    show_stats = kwds.get('show_stats', False)
    grid = kwds.get('grid', True)
    show_colorbar = kwds.get('colorbar', True)
    marker_size = kwds.get('marker_size', 50)
    show_markers = kwds.get('show_markers', False)
    
    # Get numeric data only
    data = df._get_numeric_data()
    
    if len(data.columns) < 3:
        self.showWarning('Shmoo plot requires at least 3 numeric columns (X, Y, Z)')
        return ax
    
    # Auto-select columns if not specified
    if x_param is None or x_param not in data.columns:
        x_param = data.columns[0]
    if y_param is None or y_param not in data.columns:
        y_param = data.columns[1]
    if z_param is None or z_param not in data.columns:
        z_param = data.columns[2]
    
    # Extract data
    x_data = data[x_param].values
    y_data = data[y_param].values
    z_data = data[z_param].values
    
    # Remove NaN values
    mask = ~(np.isnan(x_data) | np.isnan(y_data) | np.isnan(z_data))
    x_data = x_data[mask]
    y_data = y_data[mask]
    z_data = z_data[mask]
    
    if len(x_data) == 0:
        self.showWarning('No valid data points after removing NaN values')
        return ax
    
    # Check if data is on a regular grid
    x_unique = np.unique(x_data)
    y_unique = np.unique(y_data)
    
    is_regular_grid = (len(x_data) == len(x_unique) * len(y_unique))
    
    if is_regular_grid:
        # Data is on a regular grid - reshape for pcolormesh
        try:
            # Create meshgrid
            X, Y = np.meshgrid(x_unique, y_unique)
            
            # Reshape Z data to match grid
            Z = np.full((len(y_unique), len(x_unique)), np.nan)
            for i, (x, y, z) in enumerate(zip(x_data, y_data, z_data)):
                xi = np.where(x_unique == x)[0][0]
                yi = np.where(y_unique == y)[0][0]
                Z[yi, xi] = z
            
            # Create the plot using pcolormesh for regular grids
            if threshold_min is not None and threshold_max is not None:
                # Create pass/fail colormap
                norm = mcolors.BoundaryNorm([z_data.min(), threshold_min, threshold_max, z_data.max()], 
                                           ncolors=256)
                cmap = plt.cm.get_cmap(cmap_name)
            else:
                norm = None
                cmap = plt.cm.get_cmap(cmap_name)
            
            mesh = ax.pcolormesh(X, Y, Z, cmap=cmap, norm=norm, shading='auto')
            
            # Add contour lines if requested
            if show_contours:
                contours = ax.contour(X, Y, Z, levels=contour_levels, colors='black', 
                                     linewidths=0.5, alpha=0.5)
                ax.clabel(contours, inline=True, fontsize=8)
            
        except Exception as e:
            self.showWarning(f'Error creating regular grid plot: {str(e)}')
            return ax
    
    else:
        # Irregular grid - use scatter plot or interpolation
        try:
            from scipy.interpolate import griddata
            
            # Create regular grid for interpolation
            xi = np.linspace(x_data.min(), x_data.max(), 100)
            yi = np.linspace(y_data.min(), y_data.max(), 100)
            Xi, Yi = np.meshgrid(xi, yi)
            
            # Interpolate Z values
            if interpolation == 'none':
                # Just use scatter plot
                if threshold_min is not None and threshold_max is not None:
                    # Color by pass/fail
                    colors_array = np.where((z_data >= threshold_min) & (z_data <= threshold_max), 
                                          'green', 'red')
                    scatter = ax.scatter(x_data, y_data, c=colors_array, s=marker_size, 
                                       edgecolors='black', linewidth=0.5)
                else:
                    scatter = ax.scatter(x_data, y_data, c=z_data, cmap=cmap_name, 
                                       s=marker_size, edgecolors='black', linewidth=0.5)
                    if show_colorbar:
                        plt.colorbar(scatter, ax=ax, label=z_param)
            else:
                # Interpolate
                method = 'cubic' if interpolation == 'cubic' else 'linear'
                Zi = griddata((x_data, y_data), z_data, (Xi, Yi), method=method)
                
                if threshold_min is not None and threshold_max is not None:
                    norm = mcolors.BoundaryNorm([z_data.min(), threshold_min, threshold_max, z_data.max()], 
                                               ncolors=256)
                    cmap = plt.cm.get_cmap(cmap_name)
                else:
                    norm = None
                    cmap = plt.cm.get_cmap(cmap_name)
                
                mesh = ax.pcolormesh(Xi, Yi, Zi, cmap=cmap, norm=norm, shading='auto')
                
                if show_contours:
                    contours = ax.contour(Xi, Yi, Zi, levels=contour_levels, colors='black', 
                                         linewidths=0.5, alpha=0.5)
                    ax.clabel(contours, inline=True, fontsize=8)
                
                if show_colorbar:
                    plt.colorbar(mesh, ax=ax, label=z_param)
                
                # Optionally show original data points
                if show_markers:
                    ax.scatter(x_data, y_data, c='black', s=10, marker='o', alpha=0.5)
                    
        except ImportError:
            # Scipy not available, fall back to scatter plot
            if threshold_min is not None and threshold_max is not None:
                colors_array = np.where((z_data >= threshold_min) & (z_data <= threshold_max), 
                                      'green', 'red')
                scatter = ax.scatter(x_data, y_data, c=colors_array, s=marker_size, 
                                   edgecolors='black', linewidth=0.5)
            else:
                scatter = ax.scatter(x_data, y_data, c=z_data, cmap=cmap_name, 
                                   s=marker_size, edgecolors='black', linewidth=0.5)
                if show_colorbar:
                    plt.colorbar(scatter, ax=ax, label=z_param)
        
        except Exception as e:
            self.showWarning(f'Error creating irregular grid plot: {str(e)}')
            return ax
    
    # Set labels
    ax.set_xlabel(x_param, fontsize=12, fontweight='bold')
    ax.set_ylabel(y_param, fontsize=12, fontweight='bold')
    ax.set_title(f'Shmoo Plot: {z_param}', fontsize=14, pad=15)
    
    # Add grid
    if grid:
        ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add statistics if requested
    if show_stats:
        if threshold_min is not None and threshold_max is not None:
            pass_mask = (z_data >= threshold_min) & (z_data <= threshold_max)
            pass_count = np.sum(pass_mask)
            total_count = len(z_data)
            pass_rate = 100.0 * pass_count / total_count if total_count > 0 else 0
            
            # Calculate margins
            if pass_count > 0:
                margin_min = np.min(z_data[pass_mask] - threshold_min)
                margin_max = np.min(threshold_max - z_data[pass_mask])
            else:
                margin_min = margin_max = 0
            
            stats_text = f'Pass: {pass_count}/{total_count} ({pass_rate:.1f}%)\n'
            stats_text += f'Min Margin: {margin_min:.3f}\n'
            stats_text += f'Max Margin: {margin_max:.3f}'
            
            # Add text box with statistics
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', bbox=props)
        else:
            stats_text = f'Points: {len(z_data)}\n'
            stats_text += f'Min: {z_data.min():.3f}\n'
            stats_text += f'Max: {z_data.max():.3f}\n'
            stats_text += f'Mean: {z_data.mean():.3f}'
            
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', bbox=props)
    
    return ax


# Integration instructions for plotting.py
# ==========================================

INTEGRATION_INSTRUCTIONS = """
STEP 1: Add shmoo to valid_kwds dictionary
-------------------------------------------
Location: Around line 72-84

Add this entry:

            'shmoo': ['alpha', 'colormap', 'grid', 'colorbar',
                     'x_param', 'y_param', 'z_param', 'threshold_min', 'threshold_max',
                     'show_contours', 'contour_levels', 'interpolation', 'show_stats',
                     'marker_size', 'show_markers'],

STEP 2: Add shmoo case to _doplot() method
-------------------------------------------
Location: Around line 845, after the 'density' case

Add this code:

        elif kind == 'shmoo':
            axs = self.shmoo(data, ax, kwargs)

STEP 3: Add shmoo() method to PlotViewer class
-----------------------------------------------
Location: Around line 1310, after the density() method

Copy the shmoo() method from this file (lines 17-260)

STEP 4: Update MPLBaseOptions kinds list
-----------------------------------------
Location: Around line 1639

Add 'shmoo' to the kinds list:

    kinds = ['line', 'scatter', 'bar', 'barh', 'pie', 'histogram', 'boxplot', 'violinplot', 'dotplot',
             'heatmap', 'area', 'hexbin', 'contour', 'imshow', 'scatter_matrix', 'density', 'radviz', 'venn', 'shmoo']

STEP 5: Add shmoo options to MPLBaseOptions
--------------------------------------------
Location: Around line 1700, in the opts dictionary

Add these options:

                'x_param':{'type':'combobox','items':datacols,'label':'X parameter','default':''},
                'y_param':{'type':'combobox','items':datacols,'label':'Y parameter','default':''},
                'z_param':{'type':'combobox','items':datacols,'label':'Z value','default':''},
                'threshold_min':{'type':'entry','default':'','width':10,'label':'min threshold'},
                'threshold_max':{'type':'entry','default':'','width':10,'label':'max threshold'},
                'show_contours':{'type':'checkbutton','default':0,'label':'show contours'},
                'contour_levels':{'type':'entry','default':10,'width':10,'label':'contour levels'},
                'interpolation':{'type':'combobox','default':'nearest',
                               'items':['none','nearest','bilinear','cubic'],
                               'label':'interpolation'},
                'show_stats':{'type':'checkbutton','default':0,'label':'show statistics'},
                'marker_size':{'type':'scale','default':50,'range':(10,200),'interval':10,'label':'marker size'},
                'show_markers':{'type':'checkbutton','default':0,'label':'show markers'},

STEP 6: Test the implementation
--------------------------------
1. Load pandastable with a dataset containing X, Y, Z columns
2. Select three numeric columns
3. Choose 'shmoo' from plot type dropdown
4. Verify the shmoo plot appears
5. Test with different interpolation methods
6. Test threshold settings for pass/fail visualization
7. Test contour overlay
8. Test statistics display

"""

if __name__ == '__main__':
    print(INTEGRATION_INSTRUCTIONS)
