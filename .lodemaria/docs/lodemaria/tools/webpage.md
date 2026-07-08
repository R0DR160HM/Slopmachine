# lodemaria/tools/webpage.py

This module provides functions to fetch web pages and extract their readable text. It handles various HTML tags by stripping them, unescapes HTML entities, and collapses whitespace to ensure the extracted text is clean and concise.

## Public Functions

1. **`extract_text(html_text: str) -> str`:**
   - **Parameters:**
     - `html_text (str): The input HTML content from which to extract readable text.**
   - **Returns:**
     - `str`: The extracted readable text.
   - **Behavior:**
     - If BeautifulSoup is available, it uses it to parse the HTML and extract the text. If not, it uses regular expressions to strip tags like `<script>`, `<style>`, etc., and then unescapes the HTML entities.
     - It collapses blank lines and surrounding whitespace to ensure the text is clean and readable.

2. **`fetch_url(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str`:**
   - **Parameters:**
     - `url (str): The URL of the web page to fetch.**
     - `max_chars (int): The maximum number of characters to return from the fetched text. Default is 4000.**
   - **Returns:**
     - `str`: The visible text from the web page, truncated to `max_chars` if necessary.
   - **Behavior:**
     - It validates that the URL starts with "http://" or "https://".
     - It creates a request with the specified user agent and timeout.
     - It reads up to `MAX_DOWNLOAD_BYTES` bytes from the server.
     - It uses `extract_text` to extract readable text from the raw HTML content.
     - If the extracted text is empty, it returns an error message indicating that no readable text was found at the URL.
     - If the extracted text exceeds `max_chars`, it truncates it and appends "…[conteúdo truncado]" to indicate the truncation.

This module is useful for parsing web pages in applications that require clean and concise text content.
