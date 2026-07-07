# lodemaria/tools/webpage.py

This Python module provides utilities for fetching and extracting readable text from web pages.

## Constants

- **FETCH_TIMEOUT**: The maximum number of seconds to wait for a response when fetching a URL (default is 15 seconds).
- **MAX_DOWNLOAD_BYTES**: The maximum number of bytes to download per request (default is 2MB).
- **DEFAULT_MAX_CHARS**: The default maximum number of characters to return from the fetched text (default is 4000 characters).
- **USER_AGENT**: The user agent string used for HTTP requests.

## Functions

### `extract_text(html_text: str) -> str`

Extracts readable text from HTML content. If BeautifulSoup is available, it uses that library; otherwise, it falls back to using regex.

**Parameters:**

- **html_text** (str): The HTML content from which to extract text.

**Returns:**

- **str**: The extracted and cleaned text.

### `fetch_url(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str`

Downloads a web page and returns its visible text, truncated to the specified maximum number of characters.

**Parameters:**

- **url** (str): The URL of the web page to fetch.
- **max_chars** (int, optional): The maximum number of characters to return from the fetched text (default is 4000 characters).

**Returns:**

- **str**: The extracted and cleaned text, possibly truncated.

**Behavior:**

- If the URL does not start with "http" or "https", it prepends "https://" to it.
- It sets a user agent string for HTTP requests.
- It attempts to download the page content within the specified timeout.
- If successful, it decodes the response using the detected character set (default is UTF-8) and extracts visible text using `extract_text`.
- If an error occurs during the fetch or extraction process, it returns a failure message.

**Error Handling:**

- Errors in fetching the URL result in a failure message indicating what went wrong.
- If no readable text can be found at the URL, it returns a message indicating that.
- If the extracted text exceeds the specified maximum number of characters, it truncates the text and appends "…[conteúdo truncado]".
