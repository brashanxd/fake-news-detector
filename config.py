#config.py
CONFIG = {
    "newsapi_key": "7de67c78ed5a4a808ad09eba35f74003",
    "timeout": 10,
    "max_results": 10,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

FUENTES_CONFIABLES = [
    "bbc.com", "reuters.com", "apnews.com", "efe.com", 
    "eltiempo.com", "elespectador.com", "semana.com",
    "wikipedia.org", "bbc.co.uk", "cnn.com", "afp.com",
    "bloomberg.com", "wsj.com", "nytimes.com"
]

PATRONES_CONTRADICCION = [
    r"desmient[ae]", r"falso", r"noticia falsa", r"fake news", 
    r"neg[óo]", r"incorrecto", r"erroneo", r"sin fundamento",
    r"desinformacion", r"bulo", r"mentira", r"engaño"
]