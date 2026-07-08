### lodemaria/tools/display.py

**Purpose:** Render image search results as Unicode half-block art (24-bit ANSI).

**Description:**

This function `display_images` takes a list of dictionaries containing image search results, each with an optional "image" URL. It downloads all images into memory and renders them side-by-side in the terminal using ASCII art.

**Parameters:**

- `results`: A list of dictionaries where each dictionary contains at least the key `"thumbnail"` (an optional URL for the image) and `"title"` (the title of the search result).
- `max_display`: The maximum number of images to display (default is 3).

**Behavior:**

1. **Image Downloading:** Each image is downloaded using `urllib.request` with a timeout of 15 seconds.
2. **PIL Image Conversion:** The downloaded images are converted into PIL RGB format and loaded.
3. **Resizing and Pixel Extraction:** The images are resized to fit side by side in the terminal, preserving their aspect ratio. Each pixel is represented as three bytes (RGB).
4. **Titles Line:** A title line is printed at the top of the terminal, showing titles of up to `max_display` results.
5. **Rendering Rows:** Each row of pixels is rendered across all images simultaneously using ASCII art, where each character cell shows two pixel rows (top → foreground, bottom → background of "▀").

**Error Handling:**

- If PIL is not installed, a message "[dim]  (pillow não encontrado — pip install pillow)[/dim]" is printed.
- If any image download fails, the corresponding title is skipped.

**Side Effects:**

- The function outputs the rendered images in ASCII art format to the terminal.

**Example Usage:**

```python
results = [
    {"thumbnail": "https://example.com/image1.jpg", "title": "Image 1"},
    {"image": "https://example.com/image2.jpg", "title": "Image 2"}
]
display_images(results)
```

This will display the top two image results side-by-side in the terminal using Unicode half-block art.
