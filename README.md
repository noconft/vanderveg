# Vanderveg Menu Scraper

This Python script dynamically fetches and extracts the daily menu from the Vanderveg restaurant website (https://vanderveg.si) using OCR.

## Features
- Automatically finds the latest menu image from the homepage
- Uses EasyOCR to extract text from the menu image
- Cleans and parses the menu into a readable format

## Requirements
- Python 3.7+
- See `requirements.txt` for dependencies

## Installation
Clone this repository and install required Python modules listed in requirements.txt.

## Usage
Run the script to print the extracted and cleaned menu:
```sh
python menu.py
```

## Notes
- The script uses OCR and may not be 100% accurate depending on image quality.
