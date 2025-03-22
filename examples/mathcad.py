import sys
import re
import numpy as np
from sympy import symbols, sympify, lambdify, latex
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLineEdit, QLabel, QPushButton,
                           QScrollArea, QFrame, QSplitter, QTextEdit)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QPainter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from io import BytesIO

class MathWidget(QWidget):
    """Widget for displaying and evaluating a mathematical expression"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Arial", 12))
        self.input_edit.setPlaceholderText("Enter mathematical expression (e.g., x^2 + 5*x + 2)")
        self.input_edit.textChanged.connect(self.update_expression)
        input_layout.addWidget(QLabel("Expression:"))
        input_layout.addWidget(self.input_edit)
        
        # LaTeX display area
        self.latex_label = QLabel()
        self.latex_label.setAlignment(Qt.AlignCenter)
        self.latex_label.setMinimumHeight(60)
        self.latex_label.setStyleSheet("background-color: white; border: 1px solid lightgray;")
        
        # Result area
        result_layout = QHBoxLayout()
        result_layout.addWidget(QLabel("Result:"))
        self.result_label = QLabel()
        self.result_label.setFont(QFont("Arial", 12))
        result_layout.addWidget(self.result_label)
        
        # Add all components to main layout
        layout.addLayout(input_layout)
        layout.addWidget(self.latex_label)
        layout.addLayout(result_layout)
        
        self.setLayout(layout)
    
    def update_expression(self):
        expression = self.input_edit.text()
        if not expression:
            self.latex_label.clear()
            self.result_label.setText("")
            return
        
        try:
            # Convert to sympy expression
            sympy_expr = sympify(expression)
            
            # Create LaTeX representation
            latex_str = latex(sympy_expr)
            
            # Display LaTeX using matplotlib
            self.display_latex(latex_str)
            
            # Evaluate the expression
            try:
                result = float(sympy_expr)
                self.result_label.setText(str(result))
            except:
                self.result_label.setText("Expression contains variables")
        except Exception as e:
            self.latex_label.clear()
            self.result_label.setText(f"Error: {str(e)}")
    
    def display_latex(self, latex_str):
        """Render LaTeX using matplotlib and display it"""
        fig = Figure(figsize=(5, 1), dpi=100)
        fig.patch.set_facecolor('white')
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.axis('off')
        ax.text(0.5, 0.5, f"${latex_str}$", fontsize=14, ha='center', va='center')
        
        # Convert the figure to an image
        buf = BytesIO()
        canvas.print_figure(buf)
        buf.seek(0)
        
        # Create pixmap from the buffer
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        
        self.latex_label.setPixmap(pixmap)
        self.latex_label.setAlignment(Qt.AlignCenter)


class MathcadWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Python Mathcad-like Application")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create a scrollable area for math widgets
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Container for math widgets
        self.math_container = QWidget()
        self.math_layout = QVBoxLayout(self.math_container)
        
        # Add an initial math widget
        math_widget = MathWidget()
        self.math_layout.addWidget(math_widget)
        
        # Add spacer at the bottom to push widgets to the top
        self.math_layout.addStretch()
        
        # Add button to add more math widgets
        add_button = QPushButton("Add Expression")
        add_button.clicked.connect(self.add_math_widget)
        
        # Set up scroll area
        scroll_area.setWidget(self.math_container)
        
        # Add components to main layout
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(add_button)
        
        self.setCentralWidget(central_widget)
    
    def add_math_widget(self):
        """Add a new math widget to the container"""
        math_widget = MathWidget()
        # Insert before the last item (which is a spacer)
        self.math_layout.insertWidget(self.math_layout.count() - 1, math_widget)


class AdvancedMathcadWindow(QMainWindow):
    """More advanced version with variable definitions and plotting"""
    def __init__(self):
        super().__init__()
        self.variables = {}
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Advanced Python Mathcad-like Application")
        self.setGeometry(100, 100, 1000, 800)
        
        # Create central widget with splitter
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - workspace with math expressions
        self.workspace = QWidget()
        workspace_layout = QVBoxLayout(self.workspace)
        
        # Scrollable area for math expressions
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.math_container = QWidget()
        self.math_layout = QVBoxLayout(self.math_container)
        
        # Add one math expression widget to start
        self.add_variable_widget()
        
        # Add spacer
        self.math_layout.addStretch()
        
        scroll_area.setWidget(self.math_container)
        workspace_layout.addWidget(scroll_area)
        
        # Buttons for adding content
        button_layout = QHBoxLayout()
        add_var_button = QPushButton("Add Variable/Expression")
        add_var_button.clicked.connect(self.add_variable_widget)
        add_plot_button = QPushButton("Add Plot")
        add_plot_button.clicked.connect(self.add_plot_widget)
        
        button_layout.addWidget(add_var_button)
        button_layout.addWidget(add_plot_button)
        workspace_layout.addLayout(button_layout)
        
        # Right side - variables and documentation
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Variables:"))
        self.variables_display = QTextEdit()
        self.variables_display.setReadOnly(True)
        right_layout.addWidget(self.variables_display)
        
        # Add panels to splitter
        splitter.addWidget(self.workspace)
        splitter.addWidget(right_panel)
        splitter.setSizes([700, 300])
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)
    
    def add_variable_widget(self):
        """Add a widget for variable definition or expression"""
        widget = VariableWidget(self)
        # Insert before the last item (spacer)
        self.math_layout.insertWidget(self.math_layout.count() - 1, widget)
    
    def add_plot_widget(self):
        """Add a plotting widget"""
        widget = PlotWidget(self)
        self.math_layout.insertWidget(self.math_layout.count() - 1, widget)
    
    def update_variables_display(self):
        """Update the variables panel with current variables"""
        text = ""
        for name, value in self.variables.items():
            text += f"{name} = {value}\n"
        self.variables_display.setText(text)
    
    def set_variable(self, name, value):
        """Set a variable value and update display"""
        self.variables[name] = value
        self.update_variables_display()
    
    def get_variable(self, name):
        """Get a variable value"""
        return self.variables.get(name, None)


class VariableWidget(QFrame):
    """Widget for defining variables or evaluating expressions"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        
    def initUI(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout()
        
        # Input area with variable name and expression
        input_layout = QHBoxLayout()
        self.var_name = QLineEdit()
        self.var_name.setPlaceholderText("Variable name (optional)")
        self.var_name.setFixedWidth(150)
        
        self.equals_label = QLabel(" = ")
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Enter expression (e.g., x^2 + 5)")
        self.input_edit.textChanged.connect(self.update_expression)
        
        input_layout.addWidget(self.var_name)
        input_layout.addWidget(self.equals_label)
        input_layout.addWidget(self.input_edit)
        
        # LaTeX display
        self.latex_label = QLabel()
        self.latex_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.latex_label.setMinimumHeight(60)
        self.latex_label.setStyleSheet("background-color: white; border: 1px solid lightgray;")
        
        # Result display
        result_layout = QHBoxLayout()
        result_layout.addWidget(QLabel("Result:"))
        self.result_label = QLabel()
        result_layout.addWidget(self.result_label)
        result_layout.addStretch()
        
        layout.addLayout(input_layout)
        layout.addWidget(self.latex_label)
        layout.addLayout(result_layout)
        
        self.setLayout(layout)
    
    def update_expression(self):
        expression = self.input_edit.text()
        var_name = self.var_name.text()
        
        if not expression:
            self.latex_label.clear()
            self.result_label.setText("")
            return
        
        try:
            # Replace known variables with their values
            expr_with_vars = expression
            for name, value in self.parent.variables.items():
                if name in expression and name != var_name:  # Avoid self-reference
                    expr_with_vars = expr_with_vars.replace(name, str(value))
            
            # Convert to sympy expression
            sympy_expr = sympify(expr_with_vars)
            
            # Create LaTeX
            if var_name:
                latex_str = f"{var_name} = {latex(sympy_expr)}"
            else:
                latex_str = latex(sympy_expr)
            
            # Display LaTeX
            self.display_latex(latex_str)
            
            # Evaluate and store if it's a variable
            try:
                result = float(sympy_expr)
                self.result_label.setText(str(result))
                
                if var_name:
                    self.parent.set_variable(var_name, result)
            except:
                self.result_label.setText("Expression contains undefined variables")
        except Exception as e:
            self.latex_label.clear()
            self.result_label.setText(f"Error: {str(e)}")
    
    def display_latex(self, latex_str):
        """Render LaTeX using matplotlib and display it"""
        fig = Figure(figsize=(5, 1), dpi=100)
        fig.patch.set_facecolor('white')
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.axis('off')
        ax.text(0.1, 0.5, f"${latex_str}$", fontsize=14, ha='left', va='center')
        
        buf = BytesIO()
        canvas.print_figure(buf)
        buf.seek(0)
        
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        
        self.latex_label.setPixmap(pixmap)


class PlotWidget(QFrame):
    """Widget for creating plots of expressions"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        
    def initUI(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        layout = QVBoxLayout()
        
        # Function input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Function:"))
        self.function_edit = QLineEdit()
        self.function_edit.setPlaceholderText("Function to plot (e.g., sin(x))")
        input_layout.addWidget(self.function_edit)
        
        # Range inputs
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("x from:"))
        self.x_min = QLineEdit("-10")
        self.x_min.setFixedWidth(60)
        range_layout.addWidget(self.x_min)
        
        range_layout.addWidget(QLabel("to:"))
        self.x_max = QLineEdit("10")
        self.x_max.setFixedWidth(60)
        range_layout.addWidget(self.x_max)
        
        range_layout.addStretch()
        
        plot_button = QPushButton("Plot")
        plot_button.clicked.connect(self.create_plot)
        range_layout.addWidget(plot_button)
        
        # Plot area
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(300)
        
        layout.addLayout(input_layout)
        layout.addLayout(range_layout)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
    
    def create_plot(self):
        function_str = self.function_edit.text()
        if not function_str:
            return
        
        try:
            x_min = float(self.x_min.text())
            x_max = float(self.x_max.text())
            
            # Create a symbolic variable and expression
            x = symbols('x')
            expr = sympify(function_str)
            
            # Convert to a numpy function
            f = lambdify(x, expr, "numpy")
            
            # Generate x values
            x_vals = np.linspace(x_min, x_max, 1000)
            
            # Calculate y values
            try:
                y_vals = f(x_vals)
                
                # Clear the figure and create the plot
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                ax.plot(x_vals, y_vals)
                ax.set_xlabel('x')
                ax.set_ylabel('y')
                ax.set_title(f'Plot of {function_str}')
                ax.grid(True)
                
                self.canvas.draw()
            except Exception as e:
                print(f"Error evaluating function: {e}")
        except Exception as e:
            print(f"Error creating plot: {e}")


def main():
    app = QApplication(sys.argv)
    # For a simpler version: window = MathcadWindow()
    window = AdvancedMathcadWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()