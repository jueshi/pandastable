# pandastable

[![PyPI version shields.io](https://img.shields.io/pypi/v/pandastable.svg)](https://pypi.python.org/pypi/pandastable/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Build: status](https://img.shields.io/travis/dmnfarrell/pandastable.svg)](https://travis-ci.org/dmnfarrell/pandastable)

## Introduction

<img align="right" src=https://raw.githubusercontent.com/dmnfarrell/pandastable/master/img/logo.png width=150px>

The pandastable library provides a table widget for Tkinter with plotting and data manipulation functionality.
It uses the pandas DataFrame class to store table data. Pandas is an open source Python library providing high-performance data structures and data analysis tools. Tkinter is the standard GUI toolkit for python.

**Purpose:**
* For Python/Tkinter GUI developers who want to include a table in their application that can store and process large amounts of data.
* For non-programmers who are not familiar with Python or the pandas API and want to use the included DataExplore application to manipulate/view their data.
* For data analysts and programmers who want to get an initial interactive look at their tabular data without coding.

The DataExplore application using these classes is included in the distribution and is a self-contained application for educational and research use. Currently this focuses on providing a spreadsheet-like interface for table manipulation with configurable 2D/3D plotting.

**Documentation** is at http://pandastable.readthedocs.io/

**Note:** dataexplore has now been re-implemented in the Qt toolkit in a new app called [Tablexplore](https://github.com/dmnfarrell/tablexplore). If you're only interested in the application and not the Tkinter widget, the new app is recommended.

**Note 2:** pandas 1.0 no longer supports msgpack format so the project files now use pickle. You will not be able to open your old project files in pandastable versions >0.12.1.

## Installation

Requires python>=3.6 or 2.7 and numpy, matplotlib and pandas.

### Using pip

```bash
pip install pandastable
```

### From Source

```bash
pip install -e git+https://github.com/dmnfarrell/pandastable.git#egg=pandastable
```

### Snap Package (Linux)

You can also install the dataexplore snap package on any linux distribution that supports snaps. This installs everything you need as one app:

```bash
sudo snap install dataexplore
```

See the [docs](https://pandastable.readthedocs.io/en/latest/description.html#installation) for more details on installing.

## Usage

### Basic Usage

To use the table in your own application:

```python
from tkinter import *
from pandastable import Table, TableModel

class TestApp(Frame):
    def __init__(self, parent=None):
        self.parent = parent
        Frame.__init__(self)
        self.main = self.master
        self.main.geometry('600x400+200+100')
        self.main.title('Table app')
        f = Frame(self.main)
        f.pack(fill=BOTH,expand=1)
        df = TableModel.getSampleData()
        self.table = pt = Table(f, dataframe=df,
                                showtoolbar=True, showstatusbar=True)
        pt.show()
        return

app = TestApp()
app.mainloop()
```

### DataExplore Application

Installing the package creates a command `dataexplore` in your path. Just run this to open the program.
This is a standalone application for data manipulation and plotting meant for education and basic data analysis.

```bash
dataexplore
```

## Current features
* add, remove rows and columns
* spreadsheet-like drag, shift-click, ctrl-click selection
* edit individual cells
* sort by column, rename columns
* reorder columns dynamically by mouse drags
* set some basic formatting such as font, text size and column width
* save the DataFrame to supported pandas formats
* import/export of supported text files
* rendering of very large tables is only memory limited
* interactive plots with matplotlib, mostly using the pandas plot functions
* basic table manipulations like aggregate and pivot
* filter table using built in dataframe functionality
* graphical way to perform split-apply-combine operations

## FAQ

* **What version of Python?**
  Python versions >=2.7 and >=3.6 are compatible. Python 3 is recommended if possible.

* **Why use Tkinter?**
  Tkinter is the standard GUI toolkit for python. It is lightweight and included with most Python installations.

* **Is this just a half-baked spreadsheet?**
  Hopefully not. Some of the basic functions are naturally present since it's a table. But there is no point in trying to mimic a proper spreadsheet app. Pandas can do lots of stuff that would be nice for a non-programmer to utilize and that might not be available in a spreadsheet application.

* **Are there other better tools for dataframe visualization?**
  This depends as always on what is required. The ipython notebook is good for interactive use. Bokeh is an advanced interactive plotting tool using modern generation web technologies for in browser rendering. The goal of this project is to use DataFrames as the back end for a table widget that can be used in a desktop application.

## Links

* http://openresearchsoftware.metajnl.com/articles/10.5334/jors.94/
* http://dmnfarrell.github.io/pandastable/
* https://youtu.be/Ss0QIFywt74
* [Interview about dataexplore](http://decisionstats.com/2015/12/25/interview-damien-farrell-python-gui-dataexplore-python-rstats-pydata/)

## Citation

If you use this software in your work please cite the following article:

Farrell, D 2016 DataExplore: An Application for General Data Analysis in Research and Education.
Journal of Open Research Software, 4: e9, DOI: http://dx.doi.org/10.5334/jors.94
