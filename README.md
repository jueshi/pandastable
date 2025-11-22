# pandastable

[![PyPI version shields.io](https://img.shields.io/pypi/v/pandastable.svg)](https://pypi.python.org/pypi/pandastable/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Build: status](https://img.shields.io/travis/dmnfarrell/pandastable.svg)](https://travis-ci.org/dmnfarrell/pandastable)

## Introduction

The pandastable library provides a table widget for Tkinter with plotting and data manipulation functionality. It uses the pandas DataFrame class to store table data. Pandas is an open source Python library providing high-performance data structures and data analysis tools. Tkinter is the standard GUI toolkit for python. It is intended for the following uses:

* For Python/Tkinter GUI developers who want to include a table in their application that can store and process large amounts of data.
* For non-programmers who are not familiar with Python or the pandas API and want to use the included DataExplore application to manipulate/view their data.
* It may also be useful for data analysts and programmers who want to get an initial interactive look at their tabular data without coding.

The DataExplore application using these classes is included in the distribution and is a self-contained application for educational and research use. Currently this focuses on providing a spreadsheet-like interface for table manipulation with configurable 2D/3D plotting.

**Documentation** is available at http://pandastable.readthedocs.io/.

**Note:** The dataexplore application has been re-implemented in the Qt toolkit as [Tablexplore](https://github.com/dmnfarrell/tablexplore). If you're only interested in the application and not the Tkinter widget, the new app is recommended.

## Installation

### Requirements
* Python >= 3.6
* numpy
* matplotlib
* pandas

### Install via pip

```bash
pip install pandastable
```

### Install from Source

```bash
pip install -e git+https://github.com/dmnfarrell/pandastable.git#egg=pandastable
```

### Linux Snap

You can also install the dataexplore snap package on any linux distribution that supports snaps:

```bash
sudo snap install dataexplore
```

See the [installation docs](https://pandastable.readthedocs.io/en/latest/description.html#installation) for more details.

## Usage

### As a Library

To use `pandastable` in your own Tkinter application:

```python
from tkinter import *
from pandastable import Table, TableModel
import pandas as pd

# Create a frame
root = Tk()
frame = Frame(root)
frame.pack(fill='both', expand=True)

# Create a DataFrame
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})

# Create and show the table
pt = Table(frame, dataframe=df, showtoolbar=True, showstatusbar=True)
pt.show()

root.mainloop()
```

### As an Application

Installing the package creates a command `dataexplore` in your path. Just run this to open the program.

```bash
dataexplore
```

This is a standalone application for data manipulation and plotting meant for education and basic data analysis.

## Features

* **Data Manipulation**: Add/remove rows and columns, edit cells, sort, and rename columns.
* **Selection**: Spreadsheet-like drag, shift-click, and ctrl-click selection.
* **Formatting**: Basic formatting including font, text size, and column width.
* **I/O**: Import/export supported text files and save DataFrames to pandas formats.
* **Performance**: Rendering of very large tables is generally memory-limited.
* **Plotting**: Interactive plots with matplotlib (2D/3D), including scatter, line, bar, histogram, boxplot, density, and more.
* **Analysis**: Basic manipulations like aggregate, pivot, melt, merge/concat, and filtering.
* **Split-Apply-Combine**: Graphical interface for split-apply-combine operations.

## FAQ

**What version of Python?**
Python 3.6+ is recommended.

**Why use Tkinter?**
Tkinter is the standard GUI toolkit for Python. While sometimes considered outdated, it is stable and part of the standard library. This project builds upon previous work (`tkintertable`) using Tkinter.

**Is this a spreadsheet replacement?**
No. While it shares some basic functionality, the goal is to leverage pandas for data analysis tasks that go beyond typical spreadsheet capabilities, accessible to non-programmers.

**Are there alternatives?**
Yes. Jupyter Notebooks are excellent for interactive analysis. Tools like Bokeh provide advanced web-based plotting. `pandastable` specifically targets desktop applications using Tkinter.

## Links

* [Documentation](https://pandastable.readthedocs.io/en/latest/)
* [Journal Article](http://openresearchsoftware.metajnl.com/articles/10.5334/jors.94/)
* [Video Demo](https://youtu.be/Ss0QIFywt74)

## Citation

If you use this software in your work, please cite:

Farrell, D. (2016). DataExplore: An Application for General Data Analysis in Research and Education. *Journal of Open Research Software*, 4: e9. DOI: http://dx.doi.org/10.5334/jors.94
