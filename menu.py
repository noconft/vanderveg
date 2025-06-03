import requests
from io import BytesIO
from PIL import Image
import easyocr

def scrape_menu_image(image_url):
    # Download image
    response = requests.get(image_url)
    response.raise_for_status()
    
    # Load image into PIL
    image = Image.open(BytesIO(response.content))
    
    # Initialize EasyOCR reader (include Slovenian language code 'sl', no GPU here, hence `gpu=False`)
    reader = easyocr.Reader(['sl'], gpu=False)
    
    # Perform OCR on the image
    results = reader.readtext(image, detail=0)  # detail=0 to get only text strings
    
    # Join extracted lines into one string
    extracted_text = '\n'.join(results)
    return extracted_text

if __name__ == "__main__":
    url = "https://vanderveg.si/wp-content/uploads/2025/06/meni0206.jpg"
    menu_text = scrape_menu_image(url)
    print("Extracted menu text:")
    print(menu_text)
