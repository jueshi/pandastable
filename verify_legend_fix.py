import pandas as pd
from pandastable.core import Table, TableModel
from pandastable.plotting_subplots_n_legend import PlotViewer
try:
    from tkinter import *
except ImportError:
    from Tkinter import *

class TestApp(Frame):
    def __init__(self, parent=None):
        self.parent = parent
        Frame.__init__(self)
        self.main = self.master
        self.main.geometry('800x600+200+100')
        self.main.title('Verification')
        f = Frame(self.main)
        f.pack(fill=BOTH, expand=1)

        # Load data and create table
        df = pd.read_csv('sample_data.csv')
        self.table = Table(f, dataframe=df, showtoolbar=True, showstatusbar=True)
        self.table.show()

        # Create plot viewer
        self.plot_viewer = PlotViewer(self.table, parent=self)
        self.plot_viewer.pack(fill=BOTH, expand=1)

        # Configure and generate plot
        self.create_grouped_plot()

    def create_grouped_plot(self):
        # Set plot options for a grouped bar plot
        self.plot_viewer.mplopts.kwds['kind'] = 'bar'
        self.plot_viewer.mplopts.kwds['by'] = 'category'
        self.plot_viewer.mplopts.kwds['subplots'] = False
        self.plot_viewer.mplopts.kwds['legend'] = True

        # Replot and save
        self.plot_viewer.replot()
        self.plot_viewer.savePlot('grouped_plot.png')
        print("Plot saved to grouped_plot.png")
        self.parent.destroy()

if __name__ == '__main__':
    root = Tk()
    app = TestApp(parent=root)
    root.mainloop()