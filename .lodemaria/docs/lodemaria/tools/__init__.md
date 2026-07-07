# lodemaria/tools

This module provides a collection of tools that the model and deep-research pipeline can invoke. It includes functions for calculations, image display, documentation writing, registry execution, search formatting, URL fetching, and more.

## Public/Exported Functions and Classes

### `calculate`

- **Purpose**: Performs a calculation.
- **Parameters**:
  - `expression` (str): The mathematical expression to calculate.
- **Return Value**: The result of the calculation.
- **Behavior**: Evaluates the given mathematical expression and returns the result. If the expression is invalid, it raises a `ValueError`.
- **Example**:
  ```python
  result = calculate("2 + 3")
  print(result)  # Output: 5
  ```

### `display_images`

- **Purpose**: Displays images.
- **Parameters**:
  - `images` (list): A list of image paths to display.
- **Return Value**: None.
- **Behavior**: Opens a window and displays the given images. If any image cannot be opened, it prints an error message.
- **Example**:
  ```python
  display_images(["path/to/image1.jpg", "path/to/image2.jpg"])
  ```

### `execute_tool_call`

- **Purpose**: Executes a tool call based on a command string.
- **Parameters**:
  - `command` (str): The command to execute.
- **Return Value**: The output of the executed tool call.
- **Behavior**: Parses and executes the given command. If the command is invalid or an error occurs, it raises an appropriate exception.
- **Example**:
  ```python
  result = execute_tool_call("calculate '2 + 3'")
  print(result)  # Output: 5
  ```

### `fetch_url`

- **Purpose**: Fetches a URL and returns its content.
- **Parameters**:
  - `url` (str): The URL to fetch.
- **Return Value**: The content of the fetched URL.
- **Behavior**: Sends an HTTP GET request to the specified URL and returns the response content. If the request fails, it raises a `requests.RequestException`.
- **Example**:
  ```python
  content = fetch_url("https://www.example.com")
  print(content)
  ```

### `format_image_results`

- **Purpose**: Formats search results for images.
- **Parameters**:
  - `results` (list): A list of image search results.
- **Return Value**: A formatted string containing the search results.
- **Behavior**: Converts a list of image search results into a formatted string. If the input is empty or invalid, it returns an empty string.
- **Example**:
  ```python
  results = [{"title": "Image1", "url": "https://example.com/image1.jpg"}, {"title": "Image2", "url": "https://example.com/image2.jpg"}]
  formatted_results = format_image_results(results)
  print(formatted_results)  # Output: Image1 - https://example.com/image1.jpg\nImage2 - https://example.com/image2.jpg
  ```

### `format_news_results`

- **Purpose**: Formats search results for news.
- **Parameters**:
  - `results` (list): A list of news search results.
- **Return Value**: A formatted string containing the search results.
- **Behavior**: Converts a list of news search results into a formatted string. If the input is empty or invalid, it returns an empty string.
- **Example**:
  ```python
  results = [{"title": "News1", "url": "https://example.com/news1"}, {"title": "News2", "url": "https://example.com/news2"}]
  formatted_results = format_news_results(results)
  print(formatted_results)  # Output: News1 - https://example.com/news1\nNews2 - https://example.com/news2
  ```

### `format_search_results`

- **Purpose**: Formats search results for general searches.
- **Parameters**:
  - `results` (list): A list of general search results.
- **Return Value**: A formatted string containing the search results.
- **Behavior**: Converts a list of general search results into a formatted string. If the input is empty or invalid, it returns an empty string.
- **Example**:
  ```python
  results = [{"title": "Result1", "url": "https://example.com/result1"}, {"title": "Result2", "url": "https://example.com/result2"}]
  formatted_results = format_search_results(results)
  print(formatted_results)  # Output: Result1 - https://example.com/result1\nResult2 - https://example.com/result2
  ```

### `image_search`

- **Purpose**: Performs an image search.
- **Parameters**:
  - `query` (str): The search query.
- **Return Value**: A list of image search results.
- **Behavior**: Sends a request to an image search engine and returns the results. If the request fails, it raises a `requests.RequestException`.
- **Example**:
  ```python
  results = image_search("sunset")
  print(results)
  ```

### `news_search`

- **Purpose**: Performs a news search.
- **Parameters**:
  - `query` (str): The search query.
- **Return Value**: A list of news search results.
- **Behavior**: Sends a request to a news search engine and returns the results. If the request fails, it raises a `requests.RequestException`.
- **Example**:
  ```python
  results = news_search("technology")
  print(results)
  ```

### `parse_tool_call`

- **Purpose**: Parses a tool call command.
- **Parameters**:
  - `command` (str): The command to parse.
- **Return Value**: A dictionary containing the parsed parameters.
- **Behavior**: Extracts and parses the parameters from the given command. If the command is invalid, it raises a `ValueError`.
- **Example**:
  ```python
  params = parse_tool_call("calculate '2 + 3'")
  print(params)  # Output: {'expression': '2 + 3'}
  ```

### `web_search`

- **Purpose**: Performs a general web search.
- **Parameters**:
  - `query` (str): The search query.
- **Return Value**: A list of general search results.
- **Behavior**: Sends a request to a general web search engine and returns the results. If the request fails, it raises a `requests.RequestException`.
- **Example**:
  ```python
  results = web_search("Python programming")
  print(results)
  ```

### `write_project_documentation`

- **Purpose**: Writes project documentation.
- **Parameters**:
  - `output_path` (str): The path to save the documentation file.
- **Return Value**: None.
- **Behavior**: Generates and writes project documentation to the specified output file. If an error occurs, it raises a `FileNotFoundError`.
- **Example**:
  ```python
  write_project_documentation("docs/project.md")
  ```

This module provides a comprehensive set of tools that can be used by various components within the lodemaria project for performing calculations, displaying images, fetching URLs, and more. Each function is designed to handle specific tasks and can raise exceptions in case of errors, ensuring robust error handling within the system.
