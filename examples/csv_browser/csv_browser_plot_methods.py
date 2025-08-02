"""
CSV Browser - Plot Methods
"""

class PlotMethodsMixin:
    """Mixin class for plot-related methods in CSVBrowser"""
    
    def restore_plot_settings(self):
        """Wrapper method to call PlotUtils restore_plot_settings"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils.restore_plot_settings()
    
    def save_plot_settings(self):
        """Wrapper method to call PlotUtils save_plot_settings"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils.save_plot_settings()
    
    def _safe_replot_with_index_preservation(self, pf):
        """Wrapper method to call PlotUtils _safe_replot_with_index_preservation"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils._safe_replot_with_index_preservation(pf)
    
    def save_plot_settings_to_file(self):
        """Wrapper method to call PlotUtils save_plot_settings_to_file"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils.save_plot_settings_to_file()
    
    def load_plot_settings_from_file(self):
        """Wrapper method to call PlotUtils load_plot_settings_from_file"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils.load_plot_settings_from_file()
    
    def save_current_plot_columns(self):
        """Wrapper method to call PlotUtils save_current_plot_columns"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils.save_current_plot_columns()
    
    def restore_plot_columns(self):
        """Wrapper method to call PlotUtils restore_plot_columns"""
        if hasattr(self, 'plot_utils'):
            self.plot_utils.restore_plot_columns()
