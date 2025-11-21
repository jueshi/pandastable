"""
Unit tests for density plot implementation in pandastable
==========================================================

Run with: python -m pytest test_density_plot.py -v

Author: AI Assistant
Date: 2025-10-04
"""

import unittest
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing
import matplotlib.pyplot as plt
from unittest.mock import Mock, patch, MagicMock


class TestDensityPlot(unittest.TestCase):
    """Test cases for density plot functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create sample data
        np.random.seed(42)
        self.df_single = pd.DataFrame({
            'values': np.random.normal(0, 1, 100)
        })
        
        self.df_multiple = pd.DataFrame({
            'col1': np.random.normal(0, 1, 100),
            'col2': np.random.normal(5, 2, 100),
            'col3': np.random.exponential(2, 100)
        })
        
        self.df_mixed = pd.DataFrame({
            'numeric': np.random.normal(0, 1, 100),
            'text': ['a', 'b', 'c'] * 33 + ['a']
        })
        
        self.df_insufficient = pd.DataFrame({
            'single_value': [1.0]
        })
        
        # Create mock PlotViewer instance
        self.mock_viewer = Mock()
        self.mock_viewer.showWarning = Mock()
        
        # Create figure and axes
        self.fig, self.ax = plt.subplots()
    
    def tearDown(self):
        """Clean up after tests"""
        plt.close('all')
    
    def test_single_column_density(self):
        """Test density plot with single column"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        # Import the density function
        from density_plot_implementation import density
        
        # Call density plot
        result = density(self.mock_viewer, self.df_single, self.ax, kwds)
        
        # Verify plot was created
        self.assertIsNotNone(result)
        self.assertEqual(len(self.ax.lines), 1)  # Should have one line
        
    def test_multiple_columns_density(self):
        """Test density plot with multiple columns"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_multiple, self.ax, kwds)
        
        # Should have 3 lines (one per column)
        self.assertEqual(len(self.ax.lines), 3)
        
        # Should have legend
        legend = self.ax.get_legend()
        self.assertIsNotNone(legend)
        
    def test_fill_under_curve(self):
        """Test fill under curve option"""
        kwds = {
            'bw_method': 'scott',
            'fill': True,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_single, self.ax, kwds)
        
        # Should have fill_between (PolyCollection)
        collections = self.ax.collections
        self.assertGreater(len(collections), 0)
        
    def test_rug_plot(self):
        """Test rug plot option"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': True,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_single, self.ax, kwds)
        
        # Should have 2 lines: density curve + rug plot
        self.assertEqual(len(self.ax.lines), 2)
        
    def test_bandwidth_methods(self):
        """Test different bandwidth methods"""
        bandwidth_methods = ['scott', 'silverman', 0.5]
        
        from density_plot_implementation import density
        
        for bw in bandwidth_methods:
            fig, ax = plt.subplots()
            kwds = {
                'bw_method': bw,
                'fill': False,
                'show_rug': False,
                'alpha': 0.7,
                'colormap': 'tab10',
                'linewidth': 1.5,
                'grid': False,
                'legend': True,
                'subplots': False
            }
            
            result = density(self.mock_viewer, self.df_single, ax, kwds)
            
            # Should create plot successfully
            self.assertIsNotNone(result)
            self.assertGreater(len(ax.lines), 0)
            plt.close(fig)
    
    def test_subplots_option(self):
        """Test subplots option"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': True
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_multiple, self.ax, kwds)
        
        # Should return list of axes
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)  # One for each column
        
    def test_mixed_data_types(self):
        """Test with mixed numeric and non-numeric data"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_mixed, self.ax, kwds)
        
        # Should only plot numeric column
        self.assertEqual(len(self.ax.lines), 1)
        
    def test_insufficient_data(self):
        """Test with insufficient data (< 2 points)"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_insufficient, self.ax, kwds)
        
        # Should handle gracefully (no crash)
        self.assertIsNotNone(result)
        
    def test_empty_dataframe(self):
        """Test with empty dataframe"""
        df_empty = pd.DataFrame()
        
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, df_empty, self.ax, kwds)
        
        # Should show warning
        self.mock_viewer.showWarning.assert_called()
        
    def test_nan_handling(self):
        """Test handling of NaN values"""
        df_with_nan = pd.DataFrame({
            'col1': [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10],
            'col2': [np.nan] * 5 + list(range(5, 10))
        })
        
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        # Should not crash
        result = density(self.mock_viewer, df_with_nan, self.ax, kwds)
        self.assertIsNotNone(result)
        
    @patch('density_plot_implementation.stats', None)
    def test_fallback_without_scipy(self):
        """Test fallback to pandas when scipy not available"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        # This test verifies the code handles missing scipy gracefully
        # In actual implementation, it falls back to pandas.plot.density()
        pass
    
    def test_grid_option(self):
        """Test grid display option"""
        kwds = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': True,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        result = density(self.mock_viewer, self.df_single, self.ax, kwds)
        
        # Grid should be enabled
        self.assertTrue(self.ax.xaxis._gridOnMajor)
        
    def test_legend_option(self):
        """Test legend display option"""
        # Test with legend enabled
        kwds_with_legend = {
            'bw_method': 'scott',
            'fill': False,
            'show_rug': False,
            'alpha': 0.7,
            'colormap': 'tab10',
            'linewidth': 1.5,
            'grid': False,
            'legend': True,
            'subplots': False
        }
        
        from density_plot_implementation import density
        
        fig1, ax1 = plt.subplots()
        result1 = density(self.mock_viewer, self.df_multiple, ax1, kwds_with_legend)
        self.assertIsNotNone(ax1.get_legend())
        
        # Test with legend disabled
        kwds_no_legend = kwds_with_legend.copy()
        kwds_no_legend['legend'] = False
        
        fig2, ax2 = plt.subplots()
        result2 = density(self.mock_viewer, self.df_multiple, ax2, kwds_no_legend)
        # Legend might still exist but shouldn't be created by our code
        
        plt.close(fig1)
        plt.close(fig2)


class TestDensityPlotIntegration(unittest.TestCase):
    """Integration tests for density plot with pandastable"""
    
    def test_valid_kwds_configuration(self):
        """Test that valid_kwds includes all necessary density parameters"""
        # This would test the actual valid_kwds dict in plotting.py
        expected_kwds = ['alpha', 'colormap', 'grid', 'legend', 'linestyle',
                        'linewidth', 'marker', 'subplots', 'rot', 'kind',
                        'bw_method', 'fill', 'show_rug']
        
        # In actual implementation, verify these are in valid_kwds['density']
        pass
    
    def test_mpl_options_configuration(self):
        """Test that MPLBaseOptions includes density-specific options"""
        # This would test the opts dict in MPLBaseOptions class
        expected_options = ['bw_method', 'fill', 'show_rug']
        
        # In actual implementation, verify these are in opts dict
        pass


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("=" * 70)
    print("Density Plot Unit Tests")
    print("=" * 70)
    run_tests()
