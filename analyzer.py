# analyzer.py
import os
import re
import requests
# Import para NLI (cargar de forma perezosa, puede no estar disponible en entornos ligeros)
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
except Exception:
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    torch = None
# Import spaCy (carga perezosa del modelo de idioma)
try:
    import spacy
except Exception:
    spacy = None
from urllib.parse import urlparse
from textblob import TextBlob
from langdetect import detect
import wikipedia


class NewsAnalyzer:
    """
    NewsAnalyzer orientado a verificación por fuentes confiables.

    Estrategia:
    - Extraer una/s frase/s afirmativas (reclamaciones) desde el texto.
    - Si existe NEWSAPI_KEY en el entorno, consultar NewsAPI.org y filtrar
      resultados por dominios confiables.
    - Si no hay API key, usar búsqueda en Wikipedia como fallback.
    - Devolver un dict con claves esperadas por `api.py`:
      language, label, confidence, explanation, text, polaridad, keywords
    """

    TRUSTED_DOMAINS = [
        "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com", "nytimes.com",
        "elpais.com", "eltiempo.com", "cnn.com", "washingtonpost.com", "theguardian.com"
    ]

    CONTRADICTION_TERMS = [
        "falso", "desmiente", "no es cierto", "falso", "desmentido", "incorrecto", "erróneo", "negado"
    ]

    def __init__(self, newsapi_key: str = None):
        # Permite inyectar la API key en tiempo de ejecución (útil para pruebas)
        self.newsapi_key = newsapi_key or os.getenv("NEWSAPI_KEY")
        # for Wikipedia fallback
        wikipedia.set_lang("es")
        # NLI model (cargado bajo demanda)
        self.nli_model = None
        self.nli_tokenizer = None
        # spaCy NLP (cargado bajo demanda)
        self.nlp = None

    def analyze_news(self, text: str) -> dict:
        """Interface usada por `api.py`.

        Devuelve: {
            language: str,
            label: "REAL"|"FALSO"|"DESCONOCIDO",
            confidence: float (0..1),
            explanation: str,
            text: str (truncate),
            polaridad: float,
            keywords: list
        }
        """
        text = text.strip()
        if not text:
            raise ValueError("Texto vacío")

        # Detectar idioma y polaridad (no se usa para la decisión principal)
        try:
            lang = detect(text)
        except Exception:
            lang = "desconocido"

        polarity = round(TextBlob(text).sentiment.polarity, 3)

        # Extraer la(s) claim(s) principales (heurística simple: primeras 1-2 oraciones)
        claims = self.extract_claims(text)
        keywords = self.extract_keywords(text)

        # Intentar verificación por fuentes confiables
        sources_checked = []
        supporting = 0
        contradicting = 0
        supporting_sources = []
        contradicting_sources = []

        for claim in claims:
            articles = self.search_newsapi(claim) if self.newsapi_key else []

            if articles:
                for a in articles:
                    domain = self._get_domain(a.get("url", ""))
                    title = (a.get("title") or "").lower()
                    desc = (a.get("description") or "").lower()
                    combined = title + " " + desc

                    # Si el artículo de fuente confiable menciona la afirmación -> soporte heurístico
                    if any(td in domain for td in self.TRUSTED_DOMAINS):
                        if self._claim_mentioned(claim.lower(), combined):
                            supporting += 1
                            supporting_sources.append(domain)
                        if any(term in combined for term in self.CONTRADICTION_TERMS):
                            contradicting += 1
                            contradicting_sources.append(domain)

                    # Intentar usar NLI entre la evidencia del artículo y la claim
                    evidence = (a.get("content") or a.get("description") or a.get("title") or "")
                    if evidence:
                        nli_label_a, nli_score_a = self._nli_check(evidence, claim)
                        if nli_label_a == "entailment" and nli_score_a >= 0.65:
                            supporting += 1
                            supporting_sources.append(domain)
                        elif nli_label_a == "contradiction" and nli_score_a >= 0.65:
                            contradicting += 1
                            contradicting_sources.append(domain)

                    sources_checked.append(domain)

            # Si no hay NewsAPI o no se encontraron artículos, usar Wikipedia como fallback
            if not articles:
                # Intentar extraer PERSON del claim y buscar la página de esa persona primero
                person = self._extract_person_from_claim(claim)
                if person:
                    wiki_summary, wiki_label, wiki_source = self._wiki_check_person(person, claim)
                else:
                    wiki_summary, wiki_label, wiki_source = self._wiki_check(claim)
                sources_checked.append(wiki_source)
                # Usar NLI para evaluar la relación entre claim y resumen de Wikipedia si está disponible
                nli_label, nli_score = self._nli_check(wiki_summary, claim)
                if nli_label == "entailment" and nli_score >= 0.65:
                    supporting += 1
                    supporting_sources.append(wiki_source)
                elif nli_label == "contradiction" and nli_score >= 0.65:
                    contradicting += 1
                    contradicting_sources.append(wiki_source)
                else:
                    # fallback a heurística simple
                    if wiki_label == "REAL":
                        supporting += 1
                        supporting_sources.append(wiki_source)
                    elif wiki_label == "FALSO":
                        contradicting += 1
                        contradicting_sources.append(wiki_source)

        # Decidir etiqueta
        label = "DESCONOCIDO"
        confidence = 0.0
        explanation_parts = []

        if supporting > 0 and contradicting == 0:
            label = "REAL"
            confidence = min(0.95, 0.4 + 0.15 * supporting)
            explanation_parts.append(f"Encontradas fuentes confiables: {len(set(supporting_sources))}")
        elif contradicting > supporting:
            label = "FALSO"
            confidence = min(0.95, 0.4 + 0.15 * contradicting)
            explanation_parts.append(f"Fuentes informan contradicción: {len(set(contradicting_sources))}")
        elif supporting == 0 and contradicting == 0:
            label = "DESCONOCIDO"
            confidence = 0.15
            explanation_parts.append("No se encontraron fuentes confiables que confirmen o desmientan la afirmación.")
        else:
            # caso mixto
            label = "DESCONOCIDO"
            confidence = min(0.8, 0.35 + 0.1 * abs(supporting - contradicting))
            explanation_parts.append("Resultados mixtos entre fuentes confiables.")

        # Detallar fuentes comprobadas (pequeño resumen)
        if supporting_sources:
            explanation_parts.append("Soporta: " + ", ".join(list(set(supporting_sources))[:5]))
        if contradicting_sources:
            explanation_parts.append("Contradicciones en: " + ", ".join(list(set(contradicting_sources))[:5]))

        explanation = ". ".join(explanation_parts)

        return {
            "language": lang,
            "label": label,
            "confidence": round(confidence, 3),
            "explanation": explanation,
            "text": text[:2000] + ("..." if len(text) > 2000 else ""),
            "polaridad": polarity,
            "keywords": keywords,
        }

    def extract_claims(self, text):
        # Heurística simple: tomar las primeras 1-2 oraciones que suelen contener la afirmación
        sentences = re.split(r'[\.!?]\s+', text)
        claims = [s.strip() for s in sentences if len(s.strip()) > 20]
        return claims[:2] if claims else [text[:200]]

    def extract_keywords(self, text):
        # Palabras clave simples: palabras largas y únicas
        words = [re.sub(r'\W+', '', w).lower() for w in text.split()]
        words = [w for w in words if len(w) > 4]
        seen = []
        for w in words:
            if w and w not in seen:
                seen.append(w)
            if len(seen) >= 7:
                break
        return seen

    def search_newsapi(self, query):
        """Consulta NewsAPI.org y devuelve lista de artículos (dicts). Requiere NEWSAPI_KEY en el entorno."""
        if not self.newsapi_key:
            return []
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "pageSize": 20,
                "language": "es",
                # ordenar por relevancia
            }
            headers = {"Authorization": self.newsapi_key}
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data.get("articles", [])
        except Exception:
            return []

    def _get_domain(self, url):
        try:
            p = urlparse(url)
            return p.netloc.lower()
        except Exception:
            return ""

    def _init_nli(self):
        """Carga el modelo NLI de forma perezosa. Devuelve True si quedó disponible."""
        if self.nli_model is not None:
            return True
        if AutoTokenizer is None or AutoModelForSequenceClassification is None or torch is None:
            return False
        try:
            self.nli_tokenizer = AutoTokenizer.from_pretrained("roberta-large-mnli")
            self.nli_model = AutoModelForSequenceClassification.from_pretrained("roberta-large-mnli")
            self.nli_model.eval()
            return True
        except Exception:
            self.nli_model = None
            self.nli_tokenizer = None
            return False

    def _nli_check(self, premise, hypothesis):
        """
        Realiza una comprobación NLI entre premise (evidencia) y hypothesis (claim).
        Devuelve (label, score) donde label ∈ {"entailment","contradiction","neutral","unknown"}.
        """
        if not premise or not hypothesis:
            return "unknown", 0.0

        if self.nli_model is None:
            ok = self._init_nli()
            if not ok:
                return "unknown", 0.0

        try:
            # Tokenizar y truncar a 512 tokens
            inputs = self.nli_tokenizer.encode_plus(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                logits = self.nli_model(**inputs).logits
                probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
            # roberta-large-mnli labels: 0 -> contradiction, 1 -> neutral, 2 -> entailment
            labels = ["contradiction", "neutral", "entailment"]
            idx = int(probs.argmax())
            return labels[idx], float(probs[idx])
        except Exception:
            return "unknown", 0.0

    def _init_spacy(self):
        """Carga el modelo spaCy de español de forma perezosa."""
        if self.nlp is not None:
            return True
        if spacy is None:
            return False
        try:
            # intenta cargar el modelo entrenado de español
            self.nlp = spacy.load("es_core_news_sm")
            return True
        except Exception:
            try:
                # fallback a un pipeline en blanco en español
                self.nlp = spacy.blank("es")
                return True
            except Exception:
                self.nlp = None
                return False

    def _extract_person_from_claim(self, claim):
        """Extrae el nombre de PERSON (si existe) desde la claim usando spaCy; fallback por regex."""
        if not claim:
            return None
        ok = self._init_spacy()
        if not ok or self.nlp is None:
            # fallback simple: buscar dos palabras capitalizadas seguidas
            m = re.search(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2}))\b", claim)
            if m:
                return m.group(1)
            return None

        doc = self.nlp(claim)
        # spaCy español suele usar etiquetas 'PER' para personas; para compatibilidad chequeamos varias
        for ent in doc.ents:
            if ent.label_ in ("PER", "PERSON"):
                return ent.text
        # fallback: juntar las primeras dos PROPN
        propns = [token.text for token in doc if token.pos_ == "PROPN"]
        if propns:
            return " ".join(propns[:2])
        return None

    def _wiki_check_person(self, person, claim):
        """Buscar específicamente la página de la persona en Wikipedia y evaluar.
        Retorna (summary, label, source) similar a _wiki_check.
        """
        try:
            results = wikipedia.search(person)
            if not results:
                return "No se encontraron fuentes relevantes.", "DESCONOCIDO", f"Wikipedia: {person}"
            # Preferir resultado que contenga el nombre exacto o sea una página biográfica
            chosen = None
            for r in results:
                if person.lower() in r.lower():
                    chosen = r
                    break
            if not chosen:
                chosen = results[0]

            summary = wikipedia.summary(chosen, sentences=4)
            lower = summary.lower()

            # Si la claim habla de 'actual' y el summary indica pasado -> FALSO
            claim_low = claim.lower()
            asserts_current = "presidente" in claim_low and "actual" in claim_low or "actualmente es" in claim_low
            years_in_summary = re.search(r"\b(19|20)\d{2}\b", lower)
            desde_match = re.search(r"presidente desde (\d{4})", lower)
            if asserts_current:
                if any(p in lower for p in ["fue presidente", "fue el presidente"]) or (years_in_summary and not desde_match):
                    return summary, "FALSO", f"Wikipedia: {chosen}"
                if desde_match and "fue" not in lower:
                    return summary, "REAL", f"Wikipedia: {chosen}"

            if any(term in lower for term in self.CONTRADICTION_TERMS):
                return summary, "FALSO", f"Wikipedia: {chosen}"

            return summary, "REAL", f"Wikipedia: {chosen}"
        except Exception as e:
            return f"Error Wikipedia: {str(e)[:120]}", "DESCONOCIDO", "Wikipedia"

    def _claim_mentioned(self, claim, text):
        # Heurística simple: todas las palabras claves del claim aparecen en el texto
        tokens = [t for t in re.findall(r"\w+", claim) if len(t) > 3]
        if not tokens:
            return False
        present = sum(1 for t in tokens if t in text)
        return present >= max(1, int(len(tokens) * 0.4))

    def _wiki_check(self, claim):
        try:
            terms = " ".join(claim.split()[:6])
            results = wikipedia.search(terms)
            if not results:
                return "No se encontraron fuentes relevantes.", "DESCONOCIDO", "Wikipedia: sin resultados"
            summary = wikipedia.summary(results[0], sentences=3)
            lower = summary.lower()

            # Mejor heurística para detectar afirmaciones de cargo "actual"
            claim_low = claim.lower()
            asserts_current = any(k in claim_low for k in [
                "presidente actual", "actualmente es presidente", "es presidente actual",
                "es el presidente", "presidente de colombia actual", "presidente actual de"
            ])

            # Si la afirmación dice 'actual' pero el resumen usa pasado => contradicción
            past_indicators = ["fue presidente", "fue el presidente", "presidente entre", "presidente desde", "hasta", "hasta el"]

            # Detectar rangos o años en el resumen que indiquen mandato pasado
            years_in_summary = re.search(r"\b(19|20)\d{2}\b", lower)

            # Caso especial: si summary indica 'presidente desde <año>' y ese año es reciente, puede apoyar
            desde_match = re.search(r"presidente desde (\d{4})", lower)
            if asserts_current:
                # Si el texto de Wikipedia contiene 'fue presidente' o años que parecen indicar mandato pasado -> FALSO
                if any(p in lower for p in ["fue presidente", "fue el presidente"]) or (years_in_summary and not desde_match):
                    return summary, "FALSO", f"Wikipedia: {results[0]}"
                # Si summary explícitamente dice 'presidente desde <año>' -> REAL (asumiendo no aparece 'fue')
                if desde_match and "fue" not in lower:
                    return summary, "REAL", f"Wikipedia: {results[0]}"

            # Heurística general: buscar términos de contradicción en el resumen
            if any(term in lower for term in self.CONTRADICTION_TERMS):
                return summary, "FALSO", f"Wikipedia: {results[0]}"

            return summary, "REAL", f"Wikipedia: {results[0]}"
        except Exception as e:
            return f"Error Wikipedia: {str(e)[:120]}", "DESCONOCIDO", "Wikipedia"


if __name__ == "__main__":
    # Ejecución interactiva: pedir al usuario su API key y la consulta
    print("Ejecución interactiva de NewsAnalyzer")
    user_key = input("Introduce tu NewsAPI key (ENTER para usar Wikipedia): ").strip()
    user_query = input("Introduce el texto/afirmación a comprobar: ").strip()
    if not user_query:
        print("No se proporcionó consulta. Saliendo.")
    else:
        a = NewsAnalyzer(newsapi_key=user_key if user_key else None)
        try:
            result = a.analyze_news(user_query)
            print("Resultado:\n", result)
        except Exception as e:
            print("Error durante el análisis:", e)
