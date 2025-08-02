"""
CSV Browser - Plot Utilities
"""
import os
import sys
import copy
import types
import traceback
import warnings
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PlotUtils:
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.saved_plot_settings = None
        # Store the current plot columns by name
        self.current_plot_columns = []
        # Store whether plot viewer was open
        self.plot_viewer_was_open = False

    def get_top_correlated_columns(self, data, target_column, top_n=10):
        """
        Get the top N most correlated columns to a specified target column in a DataFrame.
        Excludes constant columns (columns with zero variance).

        Parameters:
        - data (pd.DataFrame): The input DataFrame.
        - target_column (str): The name of the target column.
        - top_n (int): The number of top correlated columns to return.

        Returns:
        - tuple: (correlation_df, data_df) where:
            - correlation_df: DataFrame with correlation information
            - data_df: DataFrame with all columns, but correlated columns moved to the front
        """
        # Store original column order for non-correlated columns
        original_columns = list(data.columns)
        
        # Ensure the target column exists in the dataset
        if target_column not in data.columns:
            raise ValueError(f"The specified target column '{target_column}' does not exist in the dataset.")
        
        # Convert all possible columns to numeric
        numeric_data = data.apply(pd.to_numeric, errors='coerce')
        
        # Remove columns with all NaN values (non-numeric columns)
        numeric_data = numeric_data.dropna(axis=1, how='all')
        
        # Ensure the target column is still in the dataset
        if target_column not in numeric_data.columns:
            raise ValueError(f"The target column '{target_column}' could not be converted to numeric type.")
        
        # Remove constant columns (columns with zero variance)
        non_constant_data = numeric_data.loc[:, numeric_data.nunique() > 1]
        
        # Check if the target column still exists after filtering
        if target_column not in non_constant_data.columns:
            raise ValueError(f"The target column '{target_column}' is constant (has zero variance).")
        
        # Calculate the correlation matrix
        cor_matrix = non_constant_data.corr()
        
        # Extract correlations for the target column
        cor_target = cor_matrix[target_column]
        
        # Create a DataFrame for sorting
        cor_target_df = pd.DataFrame({
            'Column': cor_target.index,
            'Correlation': cor_target.values
        })
        
        # Sort by absolute correlation and get the top N (excluding the target column itself)
        top_correlated = cor_target_df[cor_target_df['Column'] != target_column] \
            .sort_values(by='Correlation', key=abs, ascending=False) \
            .head(top_n)
        
        # Get the column names for the top correlated columns
        selected_columns = list(top_correlated['Column'])
        
        # Create the final column order:
        # 1. Target column
        # 2. Top correlated columns
        # 3. Remaining columns (in original order)
        final_columns = [target_column] + selected_columns
        remaining_columns = [col for col in original_columns if col not in final_columns]
        final_columns.extend(remaining_columns)
        
        # Create a DataFrame with all data in the new column order
        data_df = data[final_columns].copy()
        
        return top_correlated, data_df

    def plot_correlation_heatmap(self, data, columns=None):
        """Create a correlation heatmap for the specified columns"""
        try:
            # Use specified columns or all numeric columns
            if columns is None:
                # Get numeric columns
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                columns = [col for col in numeric_cols if data[col].nunique() > 1]
            
            # Calculate correlation matrix
            corr_matrix = data[columns].corr()
            
            # Create figure and axes
            plt.figure(figsize=(12, 10))
            
            # Create heatmap
            sns.heatmap(corr_matrix, 
                       annot=True,  # Show correlation values
                       cmap='coolwarm',  # Color scheme
                       center=0,  # Center the colormap at 0
                       square=True,  # Make cells square
                       fmt='.2f',  # Format for correlation values
                       linewidths=0.5,  # Width of cell borders
                       cbar_kws={"shrink": .5})  # Colorbar size
            
            plt.title('Correlation Heatmap')
            plt.tight_layout()
            
            return plt.gcf()
            
        except Exception as e:
            print(f"Error creating correlation heatmap: {e}")
            traceback.print_exc()
            return None

    def plot_scatter_matrix(self, data, columns=None, figsize=(12, 12)):
        """Create a scatter plot matrix for the specified columns"""
        try:
            # Use specified columns or all numeric columns
            if columns is None:
                # Get numeric columns
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                columns = [col for col in numeric_cols if data[col].nunique() > 1]
            
            # Limit to first 6 columns to avoid overcrowding
            if len(columns) > 6:
                print("Warning: Limiting scatter matrix to first 6 columns")
                columns = columns[:6]
            
            # Create scatter matrix
            fig = plt.figure(figsize=figsize)
            axs = pd.plotting.scatter_matrix(data[columns],
                                           figsize=figsize,
                                           diagonal='kde',  # Show distribution on diagonal
                                           alpha=0.5,  # Point transparency
                                           grid=True)  # Show grid
            
            # Rotate x-axis labels
            for ax in axs.flatten():
                ax.xaxis.label.set_rotation(45)
                ax.yaxis.label.set_rotation(0)
                ax.tick_params(axis='both', labelsize=8)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            print(f"Error creating scatter matrix: {e}")
            traceback.print_exc()
            return None

    def create_correlation_plots(self, data_df, target_column, corr_df, base_path):
        """
        Create scatter plots for each correlated column vs target column.
        
        Parameters:
        - data_df: DataFrame containing the data
        - target_column: Name of the target column
        - corr_df: DataFrame containing correlation information
        - base_path: Base path for saving plots
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(base_path, exist_ok=True)
            
            # Create a plot for each correlated column
            for _, row in corr_df.iterrows():
                col = row['Column']
                corr = row['Correlation']
                
                # Create figure
                plt.figure(figsize=(10, 6))
                
                # Create scatter plot
                plt.scatter(data_df[col], data_df[target_column], alpha=0.5)
                
                # Add trend line
                z = np.polyfit(data_df[col], data_df[target_column], 1)
                p = np.poly1d(z)
                plt.plot(data_df[col], p(data_df[col]), "r--", alpha=0.8)
                
                # Add labels and title
                plt.xlabel(col)
                plt.ylabel(target_column)
                plt.title(f'{col} vs {target_column}\nCorrelation: {corr:.3f}')
                
                # Add grid
                plt.grid(True, alpha=0.3)
                
                # Save plot
                plot_file = os.path.join(base_path, f'correlation_{col}_{target_column}.png')
                plt.savefig(plot_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                print(f"Saved correlation plot to: {plot_file}")
                
        except Exception as e:
            print(f"Error creating correlation plots: {e}")
            traceback.print_exc()

    def get_numeric_varying_columns(self, data):
        """
        Get list of columns that are numeric and have more than one unique value.
        
        Parameters:
        - data (pd.DataFrame): Input DataFrame
        
        Returns:
        - list: List of column names that are numeric and non-constant
        """
        try:
            # Get numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            
            # Filter for columns with more than one unique value
            varying_cols = [col for col in numeric_cols if data[col].nunique() > 1]
            
            return varying_cols
            
        except Exception as e:
            print(f"Error getting numeric varying columns: {e}")
            traceback.print_exc()
            return []

    def save_plot_settings(self):
        """Save the current plot settings from the pandastable PlotViewer"""
        try:
            # Check if the plot frame exists and has been initialized
            if not hasattr(self, 'csv_table') or not hasattr(self.csv_table, 'pf'):
                return
            
            # Get the PlotViewer instance
            pf = self.csv_table.pf
            
            # Create a dictionary to store plot settings
            settings = {}
            
            # Save global options
            if hasattr(pf, 'globalopts'):
                settings['globalopts'] = copy.deepcopy(pf.globalopts)
            
            # Save matplotlib options
            if hasattr(pf, 'mplopts') and hasattr(pf.mplopts, 'kwds'):
                # Create a copy to avoid modifying the original
                mpl_options = copy.deepcopy(pf.mplopts.kwds)
                
                # Fix for 'color' and 'colormap' conflict - only save one of them
                if 'color' in mpl_options and 'colormap' in mpl_options:
                    # Prioritize 'color' over 'colormap'
                    del mpl_options['colormap']
                
                settings['mplopts'] = mpl_options
            
            # Save layout options
            if hasattr(pf, 'layoutopts'):
                settings['layout'] = {
                    'rows': pf.layoutopts.rows,
                    'cols': pf.layoutopts.cols
                }
                # Save mode if available
                if hasattr(pf.layoutopts, 'modevar'):
                    settings['layout']['mode'] = pf.layoutopts.modevar.get()
            
            # Save 3D options
            if hasattr(pf, 'mplopts3d') and hasattr(pf.mplopts3d, 'kwds'):
                # Create a copy to avoid modifying the original
                mpl_3d_options = copy.deepcopy(pf.mplopts3d.kwds)
                
                # Fix for 'color' and 'colormap' conflict in 3D options
                if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                    del mpl_3d_options['colormap']
                
                settings['mplopts3d'] = mpl_3d_options
            
            # Save label options
            if hasattr(pf, 'labelopts') and hasattr(pf.labelopts, 'kwds'):
                settings['labelopts'] = copy.deepcopy(pf.labelopts.kwds)
            
            # Store the settings
            self.saved_plot_settings = settings
            
            # Save settings to file
            self.save_settings()
            
            print("Plot settings saved successfully")
            
        except Exception as e:
            print(f"Error saving plot settings: {e}")
            traceback.print_exc()
            
    def restore_plot_settings(self):
        """Restore previously saved plot settings to the pandastable PlotViewer"""
        try:
            # Check if plot settings exist
            if not hasattr(self, 'saved_plot_settings') or not self.saved_plot_settings:
                print("No plot settings to restore")
                return False
                
            # Check if csv_table exists
            if not hasattr(self, 'csv_table'):
                print("No table to apply plot settings to")
                return False
                
            # IMPORTANT: Check if plot viewer exists before proceeding
            if not hasattr(self.csv_table, 'pf') or self.csv_table.pf is None:
                print("Plot viewer not open, skipping plot settings restoration")
                return False            

            # The PlotViewer is created on demand when showPlot is called
            # We'll add a custom method to the csv_table that will apply our settings when the plot is shown
            self.csv_table.custom_plot_settings = self.saved_plot_settings
            
            # Check if plot viewer is already open
            if hasattr(self.csv_table, 'pf') and self.csv_table.pf is not None:
                pf = self.csv_table.pf
                settings = self.saved_plot_settings
                
                # Apply settings to the open plot viewer
                if not self._apply_plot_settings_to_viewer(pf, settings):
                    print("Warning: Failed to apply plot settings to viewer")
                    return False
                
                # Automatically replot with the selected columns
                if hasattr(self.csv_table, 'multiplecollist') and self.csv_table.multiplecollist:
                    try:
                        # Draw the selected columns in the UI
                        self.csv_table.drawSelectedCol()
                        
                        # Use our safe replot method that ensures index preservation
                        if self._safe_replot_with_index_preservation(pf):
                            print("Automatically replotted with the selected columns")
                        else:
                            print("Warning: Could not automatically replot")
                    except Exception as e:
                        print(f"Warning: Error during automatic replot: {e}")
                        traceback.print_exc()
                
                return True
            else:
                # Monkey patch the showPlot method to apply our settings
                try:
                    original_showPlot = self.csv_table.showPlot
                    
                    def patched_showPlot(self, *args, **kwargs):
                        # Call the original method first
                        result = original_showPlot(*args, **kwargs)
                        
                        # Now apply our saved settings
                        if hasattr(self, 'custom_plot_settings') and hasattr(self, 'pf') and self.pf is not None:
                            pf = self.pf
                            settings = self.custom_plot_settings
                            
                            # Apply settings to the newly opened plot viewer
                            app = self.table.app if hasattr(self.table, 'app') else None
                            if app and hasattr(app, '_apply_plot_settings_to_viewer'):
                                app._apply_plot_settings_to_viewer(pf, settings)
                        
                        return result
                    
                    # Replace the original method with our patched version
                    self.csv_table.showPlot = types.MethodType(patched_showPlot, self.csv_table)
                    return True
                except Exception as e:
                    print(f"Warning: Error patching showPlot method: {e}")
                    traceback.print_exc()
                    return False
            
        except Exception as e:
            print(f"Error restoring plot settings: {e}")
            traceback.print_exc()
            return False    

    def _apply_plot_settings_to_viewer(self, pf, settings):
        """Apply the given settings to a plot viewer instance"""
        try:
            # Validate inputs first
            if pf is None or settings is None:
                print("Warning: Cannot apply plot settings - plot viewer or settings are None")
                return False
                
            # Apply global options
            if 'globalopts' in settings and hasattr(pf, 'globalopts'):
                for k, v in settings['globalopts'].items():
                    pf.globalopts[k] = v
                    if hasattr(pf, 'globalvars') and k in pf.globalvars:
                        pf.globalvars[k].set(v)
            
            # Apply matplotlib options with conflict resolution
            if 'mplopts' in settings and hasattr(pf, 'mplopts'):
                # Create a copy to avoid modifying the original
                mpl_options = settings['mplopts'].copy()
                
                # Fix for 'color' and 'colormap' conflict
                if 'color' in mpl_options and 'colormap' in mpl_options:
                    # Prioritize 'color' over 'colormap'
                    del mpl_options['colormap']
                
                pf.mplopts.kwds.update(mpl_options)
                if hasattr(pf.mplopts, 'updateFromDict'):
                    pf.mplopts.updateFromDict(mpl_options)
            
            # Apply layout options
            if 'layout' in settings and hasattr(pf, 'layoutopts'):
                if 'rows' in settings['layout']:
                    pf.layoutopts.rows = settings['layout']['rows']
                if 'cols' in settings['layout']:
                    pf.layoutopts.cols = settings['layout']['cols']
                if 'mode' in settings['layout'] and hasattr(pf.layoutopts, 'modevar'):
                    pf.layoutopts.modevar.set(settings['layout']['mode'])
            
            # Apply 3D options with conflict resolution
            if 'mplopts3d' in settings and hasattr(pf, 'mplopts3d'):
                # Create a copy to avoid modifying the original
                mpl_3d_options = settings['mplopts3d'].copy()
                
                # Fix for 'color' and 'colormap' conflict in 3D options
                if 'color' in mpl_3d_options and 'colormap' in mpl_3d_options:
                    del mpl_3d_options['colormap']
                
                pf.mplopts3d.kwds.update(mpl_3d_options)
                if hasattr(pf.mplopts3d, 'updateFromDict'):
                    pf.mplopts3d.updateFromDict(mpl_3d_options)
            
            # Apply label options - Add extra validation here
            if 'labelopts' in settings and hasattr(pf, 'labelopts') and hasattr(pf.labelopts, 'kwds'):
                try:
                    pf.labelopts.kwds.update(settings['labelopts'])
                    if hasattr(pf.labelopts, 'updateFromDict'):
                        pf.labelopts.updateFromDict(settings['labelopts'])
                except Exception as e:
                    print(f"Warning: Error applying label options: {e}")
            
            # Suppress warnings globally for this session
            import warnings
            warnings.filterwarnings('ignore', message='.*color.*and.*colormap.*cannot be used simultaneously.*')
            warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
            
            return True
            
        except Exception as e:
            print(f"Error applying plot settings: {e}")
            traceback.print_exc()
            return False

    def save_current_plot_columns(self):
        """Save the currently selected plot columns by name"""
        try:
            if not hasattr(self.parent_app, 'csv_table'):
                return
            
            table = self.parent_app.csv_table
            if not hasattr(table, 'multiplecollist') or not table.multiplecollist:
                return
            
            # Get column names from indices
            df = table.model.df
            self.current_plot_columns = [df.columns[i] for i in table.multiplecollist]
            
            # Check if plot viewer is open
            self.plot_viewer_was_open = hasattr(table, 'pf') and table.pf is not None
            
            print(f"Saved plot columns: {self.current_plot_columns}")
            print(f"Plot viewer was open: {self.plot_viewer_was_open}")
            
        except Exception as e:
            print(f"Error saving plot columns: {e}")
            traceback.print_exc()

    def restore_plot_columns(self):
        """Restore previously saved plot columns"""
        try:
            if not self.current_plot_columns or not hasattr(self.parent_app, 'csv_table'):
                return False
            
            table = self.parent_app.csv_table
            df = table.model.df
            
            # Convert column names to indices in the new DataFrame
            indices = []
            for col in self.current_plot_columns:
                if col in df.columns:
                    indices.append(df.columns.get_loc(col))
            
            if indices:
                # Set the multiplecollist property
                table.multiplecollist = indices
                
                # Update the UI to show selected columns
                table.drawSelectedCol()
                
                # If plot viewer was open, reopen it
                if self.plot_viewer_was_open and not hasattr(table, 'pf'):
                    table.showPlot()
                # If plot viewer is already open, just replot
                elif hasattr(table, 'pf') and table.pf is not None:
                    self._safe_replot_with_index_preservation(table.pf)
                
                print(f"Restored plot columns: {[df.columns[i] for i in indices]}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error restoring plot columns: {e}")
            traceback.print_exc()
            return False

    def _safe_replot_with_index_preservation(self, pf):
        """Safely replot with proper index preservation when column filtering is active"""
        try:
            if not hasattr(self.parent_app, 'csv_table'):
                return False
                
            table = self.parent_app.csv_table
            
            # Store the current index
            current_index = None
            if hasattr(table.model, 'df'):
                current_index = table.model.df.index
            
            # Perform the replot
            pf.replot()
            
            # Restore the index if needed
            if current_index is not None and hasattr(table.model, 'df'):
                table.model.df.index = current_index
            
            return True
            
        except Exception as e:
            print(f"Error during safe replot: {e}")
            traceback.print_exc()
            return False
