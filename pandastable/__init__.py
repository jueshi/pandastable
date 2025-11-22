"""
pandastable
===========

A Python library for embedding tables in Tkinter applications using pandas DataFrames.
Provides excel-like functionality including filtering, sorting, plotting, and data manipulation.

Main components:
- Table: The main widget class for displaying and interacting with data.
- TableModel: Data model wrapper around the pandas DataFrame.
- DataExplore: A standalone application wrapper around the Table widget.

Usage:
    from pandastable import Table, TableModel
    ...
    table = Table(frame, dataframe=df)
    table.show()
"""

import platform
if platform.system() == 'Darwin':
    import matplotlib
    matplotlib.use('TkAgg')
from .core import *
from .data import *
__version__ = '0.14.0'
