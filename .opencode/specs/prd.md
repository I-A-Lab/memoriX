# PRD: Quadratic Equation Solver (Python)

## 1. Purpose
Provide a command-line Python program that solves quadratic equations of the form `ax^2 + bx + c = 0`, handling real and complex roots, input validation, and edge cases.

## 2. Functional Requirements

### 2.1 Input
- Accept three coefficients: `a`, `b`, `c` as floating-point numbers.
- Accept input via command-line arguments (argv) OR interactive prompts.
- If exactly 3 CLI args are provided, use them; otherwise prompt interactively.

### 2.2 Computation
- Calculate discriminant `D = b^2 - 4ac`.
- If `D > 0`: two distinct real roots.
- If `D == 0`: one real root (double root).
- If `D < 0`: two complex roots with real and imaginary parts.

### 2.3 Output
- Print the equation in readable form: `ax^2 + bx + c = 0`
- Print the discriminant value.
- Print the root(s) with appropriate formatting.
- Handle special case `a == 0`: reject as not a quadratic equation.

### 2.4 Error Handling
- Non-numeric input -> clear error message and exit.
- Division by zero in a == 0 case -> friendly message.

## 3. Non-Functional Requirements
- Written in Python 3.12+.
- Single file: `main.py` in the repo root.
- Clean, readable code with docstrings.
- Type hints on all functions.
- No external dependencies.

## 4. Design & UI
- CLI application; no GUI needed.
- Clear, concise output formatting using f-strings.
- Display complex roots as `x = -1 + 2i` format.
- Round floats to 2 decimal places for readability.
