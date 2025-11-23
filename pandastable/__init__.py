import platform
if platform.system() == 'Darwin':
    import matplotlib
    try:
        matplotlib.use('TkAgg')
    except ImportError:
        pass
from .core import *
from .data import *
__version__ = '0.14.0'
