"""
VanderVeg Menu Scraper

This module scrapes the VanderVeg restaurant website to extract the daily menu
and prices. It uses OCR to extract text from menu images.
"""

import logging
import re
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import easyocr
import requests
from bs4 import BeautifulSoup
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
HOMEPAGE_URL = "https://vanderveg.si"

# Pre-compile regexes at module level for efficiency
DAY_PATTERN = re.compile(r"^(\w+),\s*(\d{1,2})\.(\d{1,2})")
ALLERGEN_PATTERN = re.compile(r"\s*\d+(?:,\d+)*\s*$")
JUNK_LINES = {"vanderveg", "vanderueg", "uanderueg", "uanderveg"}
SOUP_PRICE_PATTERN = re.compile(r'Dnevna juha:\s*(\d+[,\.]\d+€)')
MAIN_DISH_PRICE_PATTERN = re.compile(r'Dnevna glavna jed:\s*(\d+[,\.]\d+€)')


def get_latest_menu_image_url() -> str:
    """
    Scrape the vanderveg.si homepage for the latest menu image URL.
    
    Returns:
        str: The absolute URL to the menu image.
        
    Raises:
        requests.RequestException: If there's an error fetching the website.
        ValueError: If the menu image is not found on the homepage.
    """
    try:
        resp = requests.get(HOMEPAGE_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find all image tags
        imgs = soup.find_all("img")
        
        # Look for an image with 'meni' in the src and ending with .jpg or .jpeg
        for img in imgs:
            src = img.get("src", "")
            if "meni" in src.lower() and src.lower().endswith((".jpg", ".jpeg")):
                if src.startswith("http"):
                    return src
                else:
                    return HOMEPAGE_URL + (src if src.startswith("/") else f"/{src}")
                    
        raise ValueError("Menu image not found on homepage.")
    except requests.RequestException as e:
        logger.error(f"Error fetching website: {e}")
        raise


def scrape_menu_image(
    image_url: str, 
    reader: Optional[easyocr.Reader] = None, 
    lang: str = 'sl'
) -> str:
    """
    Download image from URL and extract text using EasyOCR.
    
    Args:
        image_url: URL of the menu image.
        reader: Optional EasyOCR reader instance. If None, a new one will be created.
        lang: Language code for OCR (default: 'sl' for Slovenian).
        
    Returns:
        str: Extracted text from the image.
        
    Raises:
        requests.RequestException: If there's an error downloading the image.
        ValueError: If there's an error processing the image.
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        
        if reader is None:
            logger.info("Creating new EasyOCR reader")
            reader = easyocr.Reader([lang], gpu=False, verbose=False)
            
        results = reader.readtext(image, detail=0)
        return '\n'.join(results)
    except requests.RequestException as e:
        logger.error(f"Error downloading image: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise ValueError(f"Failed to process menu image: {e}")


def clean_menu_text(raw_text: str) -> Dict[str, List[str]]:
    """
    Cleans OCR text from the menu image.
    
    Args:
        raw_text: Raw text extracted from the menu image.
        
    Returns:
        Dict[str, List[str]]: A dictionary mapping days to menu items.
        The format is {day: [soup, main dish]}.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    menu = {}
    current_day = None
    buffer = []

    def process_buffer():
        """Process the current buffer and add it to the menu."""
        nonlocal buffer, current_day
        if current_day and buffer:
            soup = buffer[0] if buffer else ''
            main = " ".join(buffer[1:]).strip().replace(" ,", ",") if len(buffer) > 1 else ''
            menu[current_day] = [soup, main]
        buffer.clear()

    for line in lines:
        line_lower = line.lower()
        
        # Skip junk lines
        if any(junk in line_lower for junk in JUNK_LINES) or line.startswith("ALERGENI"):
            continue
            
        day_match = DAY_PATTERN.match(line)
        if day_match:
            # Process previous day's buffer before starting new day
            process_buffer()
            
            # Set up new day
            day_name, day, month = day_match.groups()
            current_day = f"{day_name}, {day}. {month}."
        else:
            clean_line = ALLERGEN_PATTERN.sub("", line)
            if clean_line:
                buffer.append(clean_line)
                
    # Process the last day's buffer
    process_buffer()
    return menu


def get_prices() -> Tuple[Optional[str], Optional[str]]:
    """
    Scrape prices for main dish and soup from vanderveg.si
    
    Returns:
        Tuple[Optional[str], Optional[str]]: (soup_price, main_dish_price) as strings,
        or (None, None) if not found.
    """
    try:
        resp = requests.get(HOMEPAGE_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        
        soup_match = SOUP_PRICE_PATTERN.search(text)
        soup_price = soup_match.group(1) if soup_match else None
        
        main_dish_match = MAIN_DISH_PRICE_PATTERN.search(text)
        main_dish_price = main_dish_match.group(1) if main_dish_match else None
        
        return soup_price, main_dish_price
    except requests.RequestException as e:
        logger.error(f"Error fetching website: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error parsing prices: {e}")
        return None, None


def format_menu_output(menu: Dict[str, List[str]], prices: Tuple[Optional[str], Optional[str]]) -> str:
    """
    Format the menu and prices into a readable string.
    
    Args:
        menu: Dictionary of menu items by day.
        prices: Tuple of (soup_price, main_dish_price).
        
    Returns:
        str: Formatted menu text.
    """
    soup_price, main_dish_price = prices
    output_lines = ["--- VanderVeg Menu ---\n"]
    
    for day, dishes in menu.items():
        output_lines.append(day)
        output_lines.append(f"Juha: {dishes[0]}{f' ({soup_price})' if soup_price else ''}")
        output_lines.append(f"Glavna jed: {dishes[1]}{f' ({main_dish_price})' if main_dish_price else ''}")
        output_lines.append("")
    
    return "\n".join(output_lines)


def get_menu() -> Dict[str, List[str]]:
    """
    Main function to get the complete menu.
    
    Returns:
        Dict[str, List[str]]: A dictionary mapping days to menu items.
    """
    try:
        menu_image_url = get_latest_menu_image_url()
        logger.info(f"Menu image URL: {menu_image_url}")
        
        # Create reader once and reuse
        reader = easyocr.Reader(['sl'], gpu=False, verbose=False)
        
        menu_text = scrape_menu_image(menu_image_url, reader)
        logger.debug(f"Extracted menu text:\n{menu_text}")
        
        return clean_menu_text(menu_text)
    except Exception as e:
        logger.error(f"Error getting menu: {e}")
        raise


if __name__ == "__main__":
    try:
        # Get menu and prices
        menu = get_menu()
        prices = get_prices()
        
        # Format and print the menu
        formatted_menu = format_menu_output(menu, prices)
        print(formatted_menu)
    except Exception as e:
        logger.error(f"Error: {e}")
