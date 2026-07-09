## lodemaria/tools/registry.py

### Detection and Execution of Tool Calls emitted by the Model

The `registry.py` module is designed to parse and execute tool calls from the model, providing a flexible interface for different tools and their inputs.

#### Purpose and Role in the Project

- **Tool Management**: It helps maintain a list of available and used tools, allowing users to choose which tool to use based on their requirements or preferences.
- **Command Execution**: It supports calling any of the forged tools from the module, making it easy to execute any command without needing to understand its internal logic.

#### Public Exported Classes, Functions, Constants, and Entrypoint

- **parse_tool_call**: Parses a given tool call response and returns a parsed dictionary. This includes checking for required keys and ensuring that inputs are valid.
  
- **_run_web_search**, `_run_image_search`, `_run_news_search`, `_run_fetch_url`, and `_run_calculate`: These helper functions handle the execution of web, image, news, fetch, and calculate tools respectively. They validate inputs and provide feedback to the model.

- **_run_tool_forge**: Processes forged tools by running them with a user-provided input argument. It checks for valid tool names, ensures appropriate syntax, and handles any potential errors.

#### Notable Internal Logic

1. **JSON Object Parsing**: The module uses `json` to parse responses containing JSON objects. This allows for flexible handling of different types of data.
   
2. **Validation**: The parsing process includes checking if required keys are present in the response and ensuring that inputs are valid according to their descriptions.

3. **Error Handling**: The module handles errors such as invalid input, missing fields, or logic errors in forged tools.

#### When Several Companion Files Are Given

- The `registry.py` module allows for a unified interface among tool managers by using one "unit" (a single companion file). This separation makes it easier to manage and reuse code across different models.
  
- **Companion Files**: Each companion file should be named similarly to the tool it provides, such as `web_search.js`, `image_search.js`, etc., and share a common prefix or root path.

#### Documentation

- **Summary**: The documentation describes the purpose and functionality of the module along with its public APIs.
  
- **Public Classes**: Lists the classes that provide access to the parser and execution logic.
  
- **Functions**: Describes the functions that handle parsing, validation, and command execution.

- **Constants**: Includes common constants related to tool names and their descriptions.

- **Entrypoint**: Provides a mechanism for calling tools by passing an argument (e.g., input string) or specifying only the required keys.

- **Notable Internal Logic**: Explains the internal logic of parsing and validation, including handling errors in forged tools.

#### When Several Companion Files Are Given

- **Common Prefix**: The `registry.py` module uses a common prefix for companion files to make it easier to manage and reuse code across different models.
  
- **Separation**: Each companion file should be named similarly to the tool it provides, such as `web_search.js`, `image_search.js`, etc., and share a common root path.

```markdown
## Lodemaria/tools/registry.py

### Detection and Execution of Tool Calls emitted by the Model

The `registry.py` module is designed to parse and execute tool calls from the model, providing a flexible interface for different tools and their inputs.

#### Purpose and Role in the Project

- **Tool Management**: It helps maintain a list of available and used tools, allowing users to choose which tool to use based on their requirements or preferences.
- **Command Execution**: It supports calling any of the forged tools from the module, making it easy to execute any command without needing to understand its internal logic.

#### Public Exported Classes, Functions, Constants, and Entrypoint

- **parse_tool_call**: Parses a given tool call response and returns a parsed dictionary. This includes checking for required keys and ensuring that inputs are valid.
  
- **_run_web_search**, `_run_image_search`, `_run_news_search`, `_run_fetch_url`, and `_run_calculate`: These helper functions handle the execution of web, image, news, fetch, and calculate tools respectively. They validate inputs and provide feedback to the model.

- **_run_tool_forge**: Processes forged tools by running them with a user-provided input argument. It checks for valid tool names, ensures appropriate syntax, and handles any potential errors.

#### Notable Internal Logic

1. **JSON Object Parsing**: The module uses `json` to parse responses containing JSON objects. This allows for flexible handling of different types of data.
   
2. **Validation**: The parsing process includes checking if required keys are present in the response and ensuring that inputs are valid according to their descriptions.

3. **Error Handling**: The module handles errors such as invalid input, missing fields, or logic errors in forged tools.

#### When Several Companion Files Are Given

- The `registry.py` module allows for a unified interface among tool managers by using one "unit" (a single companion file). This separation makes it easier to manage and reuse code across different models.
  
- **Companion Files**: Each companion file should be named similarly to the tool it provides, such as `web_search.js`, `image_search.js`, etc., and share a common root path.

#### Documentation

- **Summary**: The documentation describes the purpose and functionality of the module along with its public APIs.
  
- **Public Classes**: Lists the classes that provide access to the parser and execution logic.
  
- **Functions**: Describes the functions that handle parsing, validation, and command execution.

- **Constants**: Includes common constants related to tool names and their descriptions.

- **Entrypoint**: Provides a mechanism for calling tools by passing an argument (e.g., input string) or specifying only the required keys.

- **Notable Internal Logic**: Explains the internal logic of parsing and validation, including handling errors in forged tools.
