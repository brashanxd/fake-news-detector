# webscraper.py
import requests
from bs4 import BeautifulSoup

def extract_article_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        text = " ".join(paragraphs).strip()
        return text
    except Exception as e:
        return f"Error al extraer texto: {e}"
