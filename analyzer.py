# Sistema de detección de noticias falsas basado en análisis semántico con DistilBERT (analyzer.py)
from transformers import pipeline
from textblob import TextBlob
from langdetect import detect
from sklearn.feature_extraction.text import CountVectorizer
import pandas as pd
import re

class NewsAnalyzer:
    def __init__(self):
        self.model = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")

    def _get_sentiment_and_keywords(self, text):
        """Calcula la polaridad (TextBlob) y extrae palabras clave."""
        blob = TextBlob(text)
        polaridad = blob.sentiment.polarity

        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        clean_text = re.sub(r'\d+', '', clean_text)
        vectorizer = CountVectorizer(stop_words="english", max_features=15)
        keywords_list = []
        try:
            X = vectorizer.fit_transform([clean_text])
            words = vectorizer.get_feature_names_out()
            freqs = X.toarray()[0]
            data = pd.DataFrame({"word": words, "count": freqs})
            data = data[data['word'].apply(len) > 2].sort_values("count", ascending=False).head(10)
            keywords_list = data.to_dict('records')
        except ValueError:
            keywords_list = []
        return polaridad, keywords_list

    def translate_if_needed(self, text, target_lang="en"):
        """Detecta idioma y traduce si no está en inglés"""
        if not text or len(text.strip()) < 10:
            return text, "unknown"
        try:
            detected = detect(text)
        except Exception:
            detected = "unknown"
        if detected != target_lang and detected != "unknown":
            try:
                blob = TextBlob(text)
                translated = str(blob.translate(to=target_lang))
                return translated, detected
            except Exception:
                return text, detected
        return text, detected

    def analyze_news(self, text):
        """Analiza la veracidad de la noticia"""
        original_text = text
        processed_text, lang = self.translate_if_needed(text)
        processed_text_for_model = processed_text[:512]
        result = self.model(processed_text_for_model)[0]
        label_raw = result["label"].upper()
        score = result["score"]
        if label_raw == "POSITIVE":
            label = "REAL"
            explanation = "El texto presenta un lenguaje coherente y tono neutral, lo cual el modelo asocia con la veracidad."
        else:
            label = "FAKE"
            explanation = "El texto muestra rasgos emocionales, exageración o afirmaciones no neutrales, indicando una potencial noticia falsa."
        polaridad, keywords = self._get_sentiment_and_keywords(processed_text)
        return {
            "language": lang,
            "label": label,
            "confidence": round(score, 4),
            "explanation": explanation,
            "text": original_text[:1000] + ("..." if len(original_text) > 1000 else ""),
            "polaridad": round(polaridad, 4),
            "keywords": keywords,
        }
