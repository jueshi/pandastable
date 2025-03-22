# Python MATHCAD-like Application

A Python implementation of a MATHCAD-like application featuring live mathematical notation, expression evaluation, and function plotting.

![MATHCAD-like Application](mathcad_screenshot.png)

## Features

- **Live Mathematical Notation**: Enter mathematical expressions that render in real-time using LaTeX notation
- **Variable Definition and Usage**: Define variables and use them across multiple expressions
- **Real-time Calculation**: Expressions are evaluated as you type
- **Function Plotting**: Create plots of mathematical functions with adjustable ranges
- **Worksheet Interface**: Document-focused approach with multiple expressions and plots in one view

## Installation

### Prerequisites

- Python 3.x
- Git (for cloning the repository)

### Using the Virtual Environment (Recommended)

1. Clone the repository:
   ```
   git clone [repository-url]
   cd pandastable/pandastable/examples
   ```

2. Activate the existing virtual environment:
   ```
   .\mathcad_env\Scripts\activate
   ```

3. Run the application:
   ```
   python mathcad.py
   ```

### Manual Installation

If you prefer to install the dependencies manually:

1. Install the required dependencies:
   ```
   pip install numpy sympy PyQt5 matplotlib
   ```

2. Run the application:
   ```
   python mathcad.py
   ```

## How to Use

### Basic Operations

1. **Entering Expressions**: Type mathematical expressions in the input fields
   - Examples: `x^2 + 5*x + 2`, `sin(x)`, `sqrt(x+1)`

2. **Defining Variables**: Enter a variable name in the left field and an expression in the right field
   - Example: `a = 5`, `b = a*2`

3. **Creating Plots**: 
   - Click "Add Plot"
   - Enter a function expression (in terms of x)
   - Set the x-axis range
   - Click "Plot"

4. **Adding More Content**: Use the "Add Variable/Expression" and "Add Plot" buttons to add more elements to your worksheet

### Tips

- Variables defined in one cell can be used in later expressions
- Use standard mathematical notation (e.g., `sin(x)`, `x^2`, `sqrt(x)`)
- The Variables panel on the right side shows all defined variables and their values

## Architecture

The application is built using:

- **PyQt5**: For the GUI components
- **SymPy**: For symbolic mathematics and expression parsing
- **Matplotlib**: For rendering LaTeX expressions and plotting functions
- **NumPy**: For numerical computations

## Limitations

- The application currently supports basic mathematical operations and functions
- More advanced features like differential equations, matrices, and units are not yet implemented
- The application does not currently support saving and loading worksheets

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the same license as the parent pandastable project.
