"""Render image search results as Unicode half-block art (24-bit ANSI)."""

import io
import os
import urllib.request

from pythia.terminal import console, prompt_area

DOWNLOAD_TIMEOUT = 15
IMAGE_ROWS = 30  # character rows (each covers 2 pixel rows)
GAP = 2  # blank columns between side-by-side images
FALLBACK_TERM_WIDTH = 118


def _download_image(url: str):
    """Download and decode one image into a PIL RGB image; None on failure."""
    from PIL import Image as PilImage

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            data = resp.read()
        img = PilImage.open(io.BytesIO(data)).convert("RGB")
        img.load()
        return img
    except Exception:
        return None


def display_images(results: list[dict], max_display: int = 3) -> None:
    """Render top image results side-by-side in the terminal."""
    try:
        from PIL import Image as PilImage
    except ImportError:
        console.print("[dim]  (pillow não encontrado — pip install pillow)[/dim]")
        return

    # Download all images into memory before rendering
    panels = []
    for r in results:
        if len(panels) >= max_display:
            break
        url = r.get("thumbnail") or r.get("image")
        if not url:
            continue
        img = _download_image(url)
        if img is not None:
            panels.append((img, r.get("title", "")))

    if not panels:
        return

    # Compute per-image width so all images fit side by side
    n = len(panels)
    try:
        term_w = os.get_terminal_size().columns - 2
    except OSError:
        term_w = FALLBACK_TERM_WIDTH
    img_w = (term_w - GAP * (n - 1)) // n

    # Resize all images to the same dimensions and extract pixels
    resized = []
    for img, title in panels:
        raw = img.resize((img_w, IMAGE_ROWS * 2), PilImage.LANCZOS).tobytes()
        px = [raw[i:i + 3] for i in range(0, len(raw), 3)]
        resized.append((px, title))

    # Titles line
    title_line = (" " * GAP).join(t[:img_w].ljust(img_w) for _, t in resized)
    console.print(f"[dim]  {title_line}[/dim]")

    # Render row by row across all images simultaneously; each character cell
    # shows two pixel rows (top → foreground, bottom → background of "▀").
    gap_str = "\x1b[0m" + " " * GAP
    for row in range(0, IMAGE_ROWS * 2 - 1, 2):
        line = ""
        for i, (px, _) in enumerate(resized):
            if i:
                line += gap_str
            for col in range(img_w):
                top = px[row * img_w + col]
                bottom = px[(row + 1) * img_w + col]
                line += (
                    f"\x1b[38;2;{top[0]};{top[1]};{top[2]}m"
                    f"\x1b[48;2;{bottom[0]};{bottom[1]};{bottom[2]}m▀"
                )
        prompt_area.write(line + "\x1b[0m\n")
    prompt_area.write("\n")
