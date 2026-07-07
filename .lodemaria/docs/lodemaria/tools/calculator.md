# Calculator.py

Calculator.py is a Python module that provides a safe arithmetic evaluation functionality. It uses an Abstract Syntax Tree (AST) walker to parse and evaluate arithmetic expressions, ensuring that only predefined operators are allowed.

## Public Functions

### `calculate(expression: str) -> str`

#### Parameters:
- `expression` (`str`): The arithmetic expression to be evaluated.

#### Return Value:
- `str`: A string describing the result of the evaluation or an error message if calculation fails.

#### Behavior:
The function takes a string representing an arithmetic expression and attempts to evaluate it safely. If successful, it returns a formatted string with the expression and its result. If any error occurs during parsing or evaluation (such as division by zero or use of disallowed operators), it catches the exception and returns an error message.

#### Error Handling:
- Returns an error message if an unsupported operator is used in the expression.
- Catches any other exceptions that may occur during parsing or evaluation, providing a generic error message.

### `_eval_node(node: ast.AST) -> float`

This is an internal function used by `calculate()` to recursively evaluate an AST node. It restricts the evaluation to only arithmetic operations (addition, subtraction, multiplication, division, modulus, and exponentiation). It does not support variable names or function calls.

#### Parameters:
- `node` (`ast.AST`): The AST node to be evaluated.

#### Return Value:
- `float`: The result of evaluating the AST node.

#### Behavior:
The function checks if the node is a constant (either an integer or a float) and returns its value. If it's a binary operation, it recursively evaluates the left and right operands and applies the corresponding arithmetic operator. For unary operations, it similarly evaluates the operand and applies the operator. If any disallowed type of node is encountered, it raises a `ValueError`.

#### Error Handling:
- Raises a `ValueError` if the node type is not supported (i.e., if it's a name or function call).
