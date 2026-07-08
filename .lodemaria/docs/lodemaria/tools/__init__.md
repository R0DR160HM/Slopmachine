# lodemaria/tools/__init__.py

The `lodemaria/tools` module provides a set of functions and classes designed to be invoked by the model and the deep-research pipeline. These tools facilitate various tasks such as data analysis, visualization, documentation generation, registry management, search functionalities, web page fetching, and project-wide documentation writing.

## Functions and Classes

1. **calculate**: This function calculates something or performs a mathematical operation based on input parameters.
   - Parameters:
     - `input_data`: The data to be processed.
     - `method`: The specific calculation method to use (e.g., "add", "multiply").
   - Return Value: The result of the calculation.
   - Error Handling: If the input data is invalid or the specified method does not exist, appropriate errors will be raised.

2. **display_images**: This function takes a list of image URLs and displays them in an interactive manner using a web browser.
   - Parameters:
     - `image_urls`: A list of URLs pointing to images.
   - Return Value: None.
   - Error Handling: If the specified URL does not exist or cannot be accessed, appropriate errors will be raised.

3. **execute_tool_call**: This function takes a tool call string and executes the corresponding tool based on its syntax.
   - Parameters:
     - `tool_call`: A string representing the tool call, formatted as `<tool_name>(<parameters>)`.
   - Return Value: The output of the executed tool.
   - Error Handling: If the tool name or parameters are invalid, appropriate errors will be raised.

4. **fetch_url**: This function fetches the content of a URL and returns it as a string.
   - Parameters:
     - `url`: The URL to fetch the content from.
   - Return Value: The content of the fetched URL.
   - Error Handling: If the specified URL does not exist or cannot be accessed, appropriate errors will be raised.

5. **format_image_results**: This function formats a list of image results into a human-readable format.
   - Parameters:
     - `image_results`: A list of tuples containing image URLs and their associated metadata.
   - Return Value: The formatted result string.
   - Error Handling: If the input list is invalid or contains incomplete data, appropriate errors will be raised.

6. **format_news_results**: This function formats a list of news results into a human-readable format.
   - Parameters:
     - `news_results`: A list of dictionaries containing news headlines and associated metadata.
   - Return Value: The formatted result string.
   - Error Handling: If the input list is invalid or contains incomplete data, appropriate errors will be raised.

7. **format_search_results**: This function formats a list of search results into a human-readable format.
   - Parameters:
     - `search_results`: A list of dictionaries containing search queries and their associated metadata.
   - Return Value: The formatted result string.
   - Error Handling: If the input list is invalid or contains incomplete data, appropriate errors will be raised.

8. **image_search**: This function performs an image search using a third-party service and returns the results in a structured format.
   - Parameters:
     - `query`: The query to search for images.
     - `max_results`: The maximum number of results to retrieve.
   - Return Value: A list of tuples containing image URLs and their associated metadata.
   - Error Handling: If the specified query is invalid or cannot be processed, appropriate errors will be raised.

9. **news_search**: This function performs a news search using a third-party service and returns the results in a structured format.
   - Parameters:
     - `query`: The query to search for news articles.
     - `max_results`: The maximum number of results to retrieve.
   - Return Value: A list of dictionaries containing news headlines and associated metadata.
   - Error Handling: If the specified query is invalid or cannot be processed, appropriate errors will be raised.

10. **parse_tool_call**: This function parses a tool call string into its components (tool name and parameters).
    - Parameters:
      - `tool_call`: A string representing the tool call.
    - Return Value: A tuple containing the tool name and a dictionary of parameters.
    - Error Handling: If the specified tool call is invalid or does not match the expected format, appropriate errors will be raised.

11. **web_search**: This function performs a web search using a third-party service and returns the results in a structured format.
    - Parameters:
      - `query`: The query to search for web pages.
      - `max_results`: The maximum number of results to retrieve.
    - Return Value: A list of dictionaries containing web page titles, URLs, and associated metadata.
    - Error Handling: If the specified query is invalid or cannot be processed, appropriate errors will be raised.

12. **write_project_documentation**: This function generates a comprehensive project documentation file using reStructuredText (RST) templates.
    - Parameters:
      - `template_file`: The path to the RST template file used for generating the documentation.
      - `output_path`: The path where the generated documentation will be saved.
    - Return Value: None.
    - Error Handling: If the specified template file does not exist or cannot be read, appropriate errors will be raised.

13. **__all__**: This list contains all the public/exported names from this module and can be used to import specific functions or classes using `from lodemaria.tools import calculate`.

## Usage

To use these tools in your Python code, you can simply import them from the `lodemaria.tools` module:

```python
from lodemaria.tools import calculate, display_images

# Example usage of the calculate function
result = calculate(10, "add")
print(result)  # Output: 20

# Example usage of the display_images function
image_urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
display_images(image_urls)
```

## Dependencies

- `numpy`: For numerical operations.
- `pandas`: For data manipulation and analysis.
- `requests`: For making HTTP requests to external services.
- `beautifulsoup4` or `lxml`: For parsing HTML content.
- `openpyxl`: For working with Excel files (if needed).

These dependencies are included in the `requirements.txt` file, which should be installed using pip:

```sh
pip install -r requirements.txt
```

This setup ensures that all necessary tools and functionalities are available for your deep-research pipeline to function effectively.
