# display.py

This module provides functionality to render image search results as Unicode half-block art (24-bit ANSI) in a terminal.

## Constants

- **DOWNLOAD_TIMEOUT**: `15` - The timeout for downloading images.
- **IMAGE_ROWS**: `30` - The number of character rows each covering 2 pixel rows for the images.
- **GAP**: `2` - The number of blank columns between side-by-side images.
- **FALLBACK_TERM_WIDTH**: `118` - The fallback terminal width if the current terminal size cannot be determined.

## Functions

### `_download_image(url: str) -> PIL.Image or None`

Downloads and decodes one image into a PIL RGB image. Returns `None` on failure.

#### Parameters
- **url** (`str`): The URL of the image to download.

#### Returns
- **PIL.Image or None**: A PIL RGB image if successful, otherwise `None`.

### `display_images(results: list[dict], max_display: int = 3) -> None`

Renders top image results side-by-side in the terminal.

#### Parameters
- **results** (`list[dict]`): The search results containing image information.
- **max_display** (`int`, optional): The maximum number of images to display. Default is `3`.

#### Returns
- **None**

## Internal Logic and Algorithms

1. **Downloading Images**: It iterates through the search results, downloading images from the provided URLs using `_download_image` and storing them in memory if successful.

2. **Image Layout Calculation**: It calculates the width for each image to fit side-by-side based on the terminal width and the number of images to display.

3. **Image Resizing and Pixel Extraction**: Each downloaded image is resized to a uniform height of `IMAGE_ROWS * 2` pixel rows. The pixel data is then extracted into a list of RGB tuples.

4. **Rendering**: It constructs the ANSI escape sequences for each character cell, where each cell represents two pixel rows (top and bottom). The top pixel row determines the foreground color, while the bottom pixel row determines the background color of the "▀" half-block character.

5. **Error Handling**: If PIL is not installed, it prints a message indicating that Pillow needs to be installed using `pip install pillow`.

This function aims to provide a visually appealing way to display image search results in a terminal environment by leveraging Unicode half-block characters to represent images.
