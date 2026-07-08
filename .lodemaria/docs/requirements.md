# Requirements.txt - Project Dependencies

This file lists the required packages and dependencies for the project, specifying the versions of each package used.

## ollama
- **Description**: A large language model developed by Meta.
- **Parameters**:
  - `model_name`: Name of the model to use.
- **Return Values**:
  - `response`: The output of the model in natural language.
- **Error Handling**:
  - Raised if the model name is invalid.

## ddgs
- **Description**: A dynamic database search engine for web pages.
- **Parameters**:
  - `url`: URL of the webpage to search on.
- **Return Values**:
  - `results`: List of search results from the webpage.
- **Error Handling**:
  - Raised if the URL is invalid or the webpage cannot be accessed.

## rich
- **Description**: A rich text generator for Python that allows you to format and display text in various ways.
- **Parameters**:
  - `text`: The text to be formatted.
- **Return Values**:
  - `formatted_text`: The formatted text.
- **Error Handling**:
  - Raised if the input is not a valid string.

## pillow
- **Description**: A fork of PIL that adds support for more formats and improved performance.
- **Parameters**:
  - `image_path`: Path to the image file.
- **Return Values**:
  - `image`: The loaded image object.
- **Error Handling**:
  - Raised if the image file cannot be found or opened.

## beautifulsoup4
- **Description**: A library for web scraping purposes to extract data from HTML and XML files.
- **Parameters**:
  - `url`: URL of the webpage to scrape on.
- **Return Values**:
  - `parsed_data`: The parsed data in a structured format (e.g., dictionary or list).
- **Error Handling**:
  - Raised if the URL is invalid or the webpage cannot be accessed.
