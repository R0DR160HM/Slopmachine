# lodemaria/tools/forge.py: Tool Forge

This script utilizes a coder model to dynamically generate and execute new tools at runtime. The coder receives an agent's description of the desired tool, which the model must produce as a Python module defining `TOOL_NAME`, `TOOL_DESCRIPTION`, and `run(input: str) -> str`. Upon generation, the code is presented to the user for syntax highlighting and execution with full local privileges.

The generated code is verified to meet specified contract requirements, ensuring that the tool's behavior matches the expected specifications. The Forge system ensures that each forged tool is thoroughly tested and validated before being used in the agent's operations.
