import requests
from io import BytesIO
from PIL import Image
import easyocr
import re
from bs4 import BeautifulSoup

def scrape_menu_image(image_url):
    """Download image from URL and extract text using EasyOCR."""
    response = requests.get(image_url)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    reader = easyocr.Reader(['sl'], gpu=False, verbose=False)
    results = reader.readtext(image, detail=0)
    return '\n'.join(results)

def clean_menu_text(raw_text):
    """
    Cleans OCR text from the menu image.
    Returns a dict: {day: [soup, main dish]}
    """
    # Single regex pattern that both matches and captures day information
    day_pattern = re.compile(r"^(\w+),\s*(\d{1,2})\.(\d{1,2})")
    allergen_pattern = re.compile(r"\s*\d+(?:,\d+)*\s*$")
    # Remove logo and it's OCR errors
    junk_lines = {"vanderveg", "vanderueg", "uanderueg", "uanderveg"}
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    menu = {}
    current_day = None
    buffer = []
    
    def process_buffer():
        if current_day and buffer:
            soup = buffer[0]
            main = " ".join(buffer[1:]).strip().replace(" ,", ",")
            menu[current_day] = [soup, main]
    
    for line in lines:
        # Skip junk lines
        if line in junk_lines or line.startswith("ALERGENI"):
            continue
            
        # Check if this is a day header
        day_match = day_pattern.match(line)
        if day_match:
            # Process previous day's buffer before starting new day
            process_buffer()
            
            # Set up new day
            day_name, d, m = day_match.groups()
            current_day = f"{day_name}, {d}. {m}."
            buffer = []
        else:
            # Remove allergens chars and add to current day's buffer
            clean_line = allergen_pattern.sub("", line)
            buffer.append(clean_line)
    
    # Process the last day
    process_buffer()
    
    return menu

def get_latest_menu_image_url():
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
        if "meni" in src and src.endswith(('.jpg', '.jpeg')):
            # Make absolute URL if needed
            if src.startswith("http"):
                return src
            else:
                return homepage + src if src.startswith("/") else homepage + "/" + src
    raise Exception("Menu image not found on homepage.")

if __name__ == "__main__":
    menu_image_url = get_latest_menu_image_url()
    print(f"Menu image URL: {menu_image_url}")
    menu_text = scrape_menu_image(menu_image_url)
    print("Extracted menu text:")
    print(menu_text)
    print("\n--- Cleaned Menu ---\n")
    menu = clean_menu_text(menu_text)
    for day, dishes in menu.items():
        print(day)
        print("Juha:", dishes[0])
        print("Glavna jed:", dishes[1])
        print()
