```markdown
# tool_forge: have a coder model write a brand-new tool at runtime.

## Purpose and Role in the Project

The coder model (config.FORGE_MODEL) receives the agent's description of the desired tool and must answer with a Python module defining TOOL_NAME, TOOL_DESCRIPTION, run(input: str) -> str. The module is loaded here and handed back to the tool registry, which makes it callable by the agent.

The generated code is shown to the user (syntax-highlighted) before it is loaded, and it executes with full local privileges — same trust level as the rest of this app.

## Internal Logic

- **Forking**: The code is forked from a module provided by `llm`.
- **Imports**: We import necessary components and setup for execution.
- **Error Handling**: We handle potential errors such as missing blocks or invalid functions, ensuring robustness.
- **Code Generation**: The generated code is executed in the terminal, allowing local debugging and testing.

## Related Files

- `lodemaria/tools/forge.py`
  - Contains the main logic and classes for the forge tool. Each file includes a comprehensive docstring explaining its purpose and responsibilities.
  
## User Interface

The user can interact with the generated code by navigating through the terminal's command-line interface or using graphical tools.

```bash
python lodemaria/tools/forge.py --description "Example tool description"
```

This approach leverages Python's dynamic typing and the ability to run code directly from the terminal, making it easy for developers to experiment with the tool without the need for extensive setup.
