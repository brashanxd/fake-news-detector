

# ===============================================
# API Backend para el Analizador de Noticias Falsas
# ===============================================

from fastapi import FastAPI, HTTPException
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyzer import NewsAnalyzer
from webscraper import extract_article_text
import sys

# -----------------------------------------------
# 1. Inicialización de la aplicación
# -----------------------------------------------
app = FastAPI(
    title="Fake News Analyzer API",
    description="API que usa DistilBERT, TextBlob y Web Scraping para análisis semántico de noticias.",
    version="1.1.0"
)

# -----------------------------------------------
# 2. Configurar CORS (para que el frontend se conecte sin problema)
# -----------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Acepta peticiones desde cualquier origen (útil para localhost)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------
# 3. Modelos Pydantic para solicitudes y respuestas
# -----------------------------------------------
class TextRequest(BaseModel):
    text: str

class URLRequest(BaseModel):
    url: str

class AnalysisResult(BaseModel):
    language: str
    label: str
    confidence: float
    explanation: str
    text: str
    polaridad: float
    keywords: list

# -----------------------------------------------
# 4. Cargar el modelo IA al iniciar
# -----------------------------------------------
analyzer = None
try:
    print("🧠 Cargando modelo de NewsAnalyzer...")
    # Pasar la clave desde la variable de entorno si está presente
    analyzer = NewsAnalyzer(os.getenv("NEWSAPI_KEY"))
    print("✅ Modelo cargado correctamente.")
except Exception as e:
    print(f"❌ ERROR al inicializar NewsAnalyzer: {e}", file=sys.stderr)

# -----------------------------------------------
# 5. Endpoint para analizar texto manual
# -----------------------------------------------
@app.post("/analyze_text", response_model=AnalysisResult)
def analyze_text_endpoint(request: TextRequest):
    """Analiza un texto proporcionado manualmente por el usuario."""
    if not analyzer:
        raise HTTPException(status_code=500, detail="El modelo de IA no está disponible.")
    if len(request.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="El texto debe tener al menos 20 caracteres.")
    try:
        result = analyzer.analyze_news(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante el análisis: {str(e)}")

# -----------------------------------------------
# 6. Endpoint para analizar una URL (noticia online)
# -----------------------------------------------
@app.post("/analyze_url", response_model=AnalysisResult)
def analyze_url_endpoint(request: URLRequest):
    """Extrae texto de una URL y luego lo analiza."""
    if not analyzer:
        raise HTTPException(status_code=500, detail="El modelo de IA no está disponible.")
    print(f"🌐 Extrayendo texto de: {request.url}")

    scraped_text = extract_article_text(request.url)
    if scraped_text.startswith("Error"):
        raise HTTPException(status_code=400, detail=scraped_text)
    if len(scraped_text) < 50:
        raise HTTPException(status_code=400, detail="No se pudo extraer suficiente texto del artículo (menos de 50 caracteres).")

    try:
        result = analyzer.analyze_news(scraped_text)
        result["text"] = scraped_text[:1000] + ("..." if len(scraped_text) > 1000 else "")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante el análisis de URL: {str(e)}")

# -----------------------------------------------
# 7. Mensaje base (para pruebas rápidas)
# -----------------------------------------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "API de Análisis Semántico de Noticias en funcionamiento ✅",
        "endpoints": ["/analyze_text", "/analyze_url"]
    }
