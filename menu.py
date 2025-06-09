import requests
from io import BytesIO
from PIL import Image
import easyocr
import re
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)

# Pre-compile regexes at module level for efficiency
DAY_PATTERN = re.compile(r"^(\w+),\s*(\d{1,2})\.(\d{1,2})")
ALLERGEN_PATTERN = re.compile(r"\s*\d+(?:,\d+)*\s*$")
JUNK_LINES = {"vanderveg", "vanderueg", "uanderueg", "uanderveg"}


def get_latest_menu_image_url() -> str:
    """
    Scrape the vanderveg.si homepage for the latest menu image URL.
    Returns the absolute URL to the menu image.
    """
    homepage = "https://vanderveg.si"
    resp = requests.get(homepage)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Find all image tags
    imgs = soup.find_all("img")
    # Look for an image with 'meni' in the src and ending with .jpg or .jpeg
    for img in imgs:
        src = img.get("src", "")
        if "meni" in src and src.endswith((".jpg", ".jpeg")):
            if src.startswith("http"):
                return src
            else:
                return homepage + src if src.startswith("/") else homepage + "/" + src
    raise Exception("Menu image not found on homepage.")


def scrape_menu_image(image_url: str, reader: Optional[easyocr.Reader] = None, lang: str = 'sl') -> str:
    """Download image from URL and extract text using EasyOCR."""
    response = requests.get(image_url)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    if reader is None:
        reader = easyocr.Reader([lang], gpu=False, verbose=False)
    results = reader.readtext(image, detail=0)
    return '\n'.join(results)


def clean_menu_text(raw_text: str) -> Dict[str, List[str]]:
    """
    Cleans OCR text from the menu image.
    Returns a dict: {day: [soup, main dish]}
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    menu = {}
    current_day = None
    buffer = []

    def process_buffer():
        nonlocal buffer, current_day
        if current_day and buffer:
            soup = buffer[0] if buffer else ''
            main = " ".join(buffer[1:]).strip().replace(" ,", ",") if len(buffer) > 1 else ''
            menu[current_day] = [soup, main]
        buffer.clear()

    for line in lines:
        line_lower = line.lower()
        if any(junk in line_lower for junk in JUNK_LINES) or line.startswith("ALERGENI"):
            continue
        day_match = DAY_PATTERN.match(line)
        if day_match:
            # Process previous day's buffer before starting new day
            process_buffer()
            
            # Set up new day
            day_name, d, m = day_match.groups()
            current_day = f"{day_name}, {d}. {m}."
        else:
            clean_line = ALLERGEN_PATTERN.sub("", line)
            if clean_line:
                buffer.append(clean_line)
    process_buffer()
    return menu


if __name__ == "__main__":
    try:
        menu_image_url = get_latest_menu_image_url()
        logging.info(f"Menu image URL: {menu_image_url}")
        reader = easyocr.Reader(['sl'], gpu=False, verbose=False)
        menu_text = scrape_menu_image(menu_image_url, reader)
        print("Extracted menu text:")
        print(menu_text)
        print("\n--- Cleaned Menu ---\n")
        menu = clean_menu_text(menu_text)
        for day, dishes in menu.items():
            print(day)
            print("Juha:", dishes[0])
            print("Glavna jed:", dishes[1])
            print()
    except Exception as e:
        logging.error(f"Error: {e}")
