"""
Density Plot Implementation for Pandastable
============================================

This file contains the implementation of the density plot feature.
To integrate into plotting.py:

1. Add the density() method to the PlotViewer class (around line 1080)
2. Add the density plot case to _doplot() method (around line 838)
3. Update MPLBaseOptions to include density-specific options

Author: AI Assistant
Date: 2025-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors

def density(self, df, ax, kwds):
    """
    Create kernel density estimation plot.
    
    This method creates smooth density curves for numeric data using
    kernel density estimation (KDE). Supports multiple columns with
    overlaid densities.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Data to plot. All numeric columns will be used.
    ax : matplotlib.axes.Axes
        Axes object to plot on
    kwds : dict
        Plotting keywords including:
        - bw_method: str or float, bandwidth method ('scott', 'silverman', or numeric)
        - fill: bool, whether to fill under the curve
        - show_rug: bool, whether to show rug plot
        - alpha: float, transparency (0-1)
        - colormap: str, colormap name
        - linewidth: float, line width
        - grid: bool, show grid
        - legend: bool, show legend
        - subplots: bool, create separate subplots
        
    Returns:
    --------
    ax or list of axes
    """
    
    # Get parameters
    bw_method = kwds.get('bw_method', 'scott')
    fill = kwds.get('fill', False)
    show_rug = kwds.get('show_rug', False)
    alpha = kwds.get('alpha', 0.7)
    cmap = plt.cm.get_cmap(kwds.get('colormap', 'tab10'))
    lw = kwds.get('linewidth', 1.5)
    grid = kwds.get('grid', False)
    legend = kwds.get('legend', True)
    subplots = kwds.get('subplots', False)
    
    # Get numeric data only
    data = df._get_numeric_data()
    
    if len(data.columns) == 0:
        self.showWarning('No numeric data to plot')
        return ax
    
    # Check if scipy is available for KDE
    try:
        from scipy import stats
        use_scipy = True
    except ImportError:
        use_scipy = False
        # Fall back to pandas built-in density plot
        if not subplots:
            for i, col in enumerate(data.columns):
                color = cmap(float(i) / len(data.columns))
                data[col].plot.density(ax=ax, color=color, linewidth=lw, 
                                      alpha=alpha, label=col)
            if legend:
                ax.legend()
            if grid:
                ax.grid(True, alpha=0.3)
            ax.set_ylabel('Density')
            return ax
    
    # Create subplots if requested
    if subplots:
        n_cols = len(data.columns)
        n_rows = int(np.ceil(np.sqrt(n_cols)))
        n_cols_grid = int(np.ceil(n_cols / n_rows))
        
        fig = ax.get_figure()
        fig.clear()
        axes = []
        
        for i, col in enumerate(data.columns):
            ax_sub = fig.add_subplot(n_rows, n_cols_grid, i + 1)
            axes.append(ax_sub)
            
            # Get data for this column, remove NaN
            col_data = data[col].dropna()
            
            if len(col_data) < 2:
                ax_sub.text(0.5, 0.5, 'Insufficient data', 
                           ha='center', va='center', transform=ax_sub.transAxes)
                ax_sub.set_title(col)
                continue
            
            # Compute KDE
            if use_scipy:
                try:
                    kde = stats.gaussian_kde(col_data, bw_method=bw_method)
                    x_range = np.linspace(col_data.min(), col_data.max(), 200)
                    density_vals = kde(x_range)
                    
                    # Plot
                    color = cmap(float(i) / n_cols)
                    ax_sub.plot(x_range, density_vals, color=color, linewidth=lw, alpha=alpha)
                    
                    if fill:
                        ax_sub.fill_between(x_range, density_vals, alpha=alpha*0.5, color=color)
                    
                    if show_rug:
                        # Add rug plot at bottom
                        y_min = ax_sub.get_ylim()[0]
                        ax_sub.plot(col_data, [y_min] * len(col_data), '|', 
                                   color=color, alpha=0.5, markersize=10)
                    
                except Exception as e:
                    ax_sub.text(0.5, 0.5, f'Error: {str(e)}', 
                               ha='center', va='center', transform=ax_sub.transAxes)
            
            ax_sub.set_title(col)
            ax_sub.set_ylabel('Density')
            if grid:
                ax_sub.grid(True, alpha=0.3)
        
        # Remove empty subplots
        for i in range(len(data.columns), len(axes)):
            fig.delaxes(axes[i])
        
        plt.tight_layout()
        return axes
    
    else:
        # Single plot with multiple densities
        for i, col in enumerate(data.columns):
            # Get data for this column, remove NaN
            col_data = data[col].dropna()
            
            if len(col_data) < 2:
                continue
            
            color = cmap(float(i) / len(data.columns))
            
            if use_scipy:
                try:
                    # Compute KDE
                    kde = stats.gaussian_kde(col_data, bw_method=bw_method)
                    x_range = np.linspace(col_data.min(), col_data.max(), 200)
                    density_vals = kde(x_range)
                    
                    # Plot
                    ax.plot(x_range, density_vals, color=color, linewidth=lw, 
                           alpha=alpha, label=col)
                    
                    if fill:
                        ax.fill_between(x_range, density_vals, alpha=alpha*0.3, color=color)
                    
                    if show_rug:
                        # Add rug plot at bottom
                        y_min = ax.get_ylim()[0]
                        ax.plot(col_data, [y_min] * len(col_data), '|', 
                               color=color, alpha=0.3, markersize=8)
                
                except Exception as e:
                    print(f"Error plotting density for {col}: {e}")
                    continue
        
        if legend and len(data.columns) > 1:
            ax.legend()
        
        ax.set_ylabel('Density')
        ax.set_xlabel('Value')
        
        if grid:
            ax.grid(True, alpha=0.3)
        
        return ax


# Integration instructions for plotting.py
# ==========================================

INTEGRATION_INSTRUCTIONS = """
STEP 1: Add density plot case to _doplot() method
--------------------------------------------------
Location: Around line 838, after the 'radviz' case and before the 'else' clause

Add this code:

        elif kind == 'density':
            axs = self.density(data, ax, kwargs)

STEP 2: Add density() method to PlotViewer class
-------------------------------------------------
Location: Around line 1080, after the venn() method

Copy the density() method from this file (lines 20-180)

STEP 3: Update MPLBaseOptions configuration
--------------------------------------------
Location: Around line 1490, in the opts dictionary

Add these options:

                'bw_method':{'type':'combobox','default':'scott',
                            'items':['scott','silverman','0.1','0.2','0.5','1.0'],
                            'label':'bandwidth method'},
                'fill':{'type':'checkbutton','default':0,'label':'fill under curve'},
                'show_rug':{'type':'checkbutton','default':0,'label':'show rug plot'},

STEP 4: Update valid_kwds dictionary
-------------------------------------
Location: Around line 72, the 'density' entry already exists, verify it includes:

            'density': ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                       'linewidth', 'marker', 'subplots', 'rot', 'kind',
                       'bw_method', 'fill', 'show_rug'],

STEP 5: Test the implementation
--------------------------------
1. Load pandastable with a numeric dataset
2. Select one or more numeric columns
3. Choose 'density' from plot type dropdown
4. Verify the density plot appears
5. Test with different bandwidth methods
6. Test fill and rug plot options
7. Test with subplots option
8. Test with grouped data (by parameter)

STEP 6: Add unit tests
-----------------------
Create test_density.py with tests for:
- Single column density
- Multiple column density
- Different bandwidth methods
- Fill option
- Rug plot option
- Subplots
- Error handling (insufficient data, non-numeric data)
"""

if __name__ == '__main__':
    print(INTEGRATION_INSTRUCTIONS)
