# Safe Arithmetic Evaluation via a Restricted AST Walker

This file provides a safe way to evaluate arithmetic expressions, ensuring that only allowed operations and types are used. The `calculate` function parses the input string into an abstract syntax tree (AST) using `ast.parse`, then recursively evaluates it by calling `_eval_node`.

## Usage

1. **Input**:
   - A valid arithmetic expression (e.g., "3 + 5").

2. **Output**:
   - The result of the arithmetic calculation.
   - If an error occurs during evaluation, a descriptive message will be returned.

## Public Functions and Classes

### `_eval_node(node: ast.AST) -> float`

- **Parameters**:
  - `node (ast.AST)`: A parsed AST node representing a single operation or constant.

- **Return Value**:
  - The result of evaluating the AST node, which can be an integer, float, or boolean.
  
- **Behavior**:
  - If the node is a constant, it returns the value.
  - If the node is a binary operation (Add, Sub, Mult, Div, FloorDiv, Mod, Pow), it applies the corresponding operator to the two sub-nodes and recursively evaluates them.
  - If the node is an unary operation (USub, UAdd), it applies the operator to the single sub-node and recursively evaluates it.

### `calculate(expression: str) -> str`

- **Parameters**:
  - `expression (str)`: The arithmetic expression to be evaluated.

- **Return Value**:
  - A string containing the input expression along with its evaluation result.
  
- **Behavior**:
  - Parses the input string into an AST using `ast.parse`.
  - Calls `_eval_node` to recursively evaluate the AST.
  - If successful, formats and returns the expression along with the result in a human-readable format.
  - If an error occurs during parsing or evaluation, it catches the exception, constructs an error message, and returns it.

## Example

```python
from lodemaria.tools.calculator import calculate

result = calculate("3 + 5")
print(result)  # Output: "3 + 5 = 8"
```

This example demonstrates how to use the `calculate` function safely evaluate a simple arithmetic expression.
