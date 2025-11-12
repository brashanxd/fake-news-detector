# scraper_simple.py
import requests
from bs4 import BeautifulSoup
import re
import time
from config import CONFIG

class ExtractorSimple:
    def __init__(self):
        self.sesion = requests.Session()
        self.sesion.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': 'https://www.google.com/'
        })

    def extraer_de_url(self, url):
        """Extrae contenido con mejores estrategias para diferentes sitios"""
        try:
            print(f"Conectando con: {url}")
            
            response = self.sesion.get(url, timeout=15, verify=False)
            
            if response.status_code != 200:
                print(f"Error HTTP {response.status_code}")
                return None
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Estrategia por tipo de sitio
            dominio = self._extraer_dominio(url)
            contenido = None
            
            if 'wikipedia.org' in dominio:
                contenido = self._extraer_wikipedia(soup)
            elif 'bbc.com' in dominio:
                contenido = self._extraer_bbc(soup)
            elif 'eltiempo.com' in dominio:
                contenido = self._extraer_eltiempo(soup)
            elif 'reuters.com' in dominio:
                contenido = self._extraer_reuters(soup)
            else:
                contenido = self._extraer_generico(soup)
            
            if contenido and len(contenido) > 100:
                return self._limpiar_texto(contenido)
            else:
                return None
                
        except Exception as e:
            print(f"Error extrayendo {url}: {str(e)[:80]}")
            return None

    def _extraer_wikipedia(self, soup):
        """Extrae contenido de Wikipedia"""
        # Wikipedia es facil de extraer
        content = soup.find('div', {'id': 'mw-content-text'})
        if content:
            # Tomar solo los primeros parrafos
            parrafos = content.find_all('p', limit=10)
            texto = ' '.join([p.get_text() for p in parrafos if p.get_text()])
            return texto
        return None

    def _extraer_bbc(self, soup):
        """Extrae contenido de BBC"""
        # Buscar el articulo principal
        articulo = soup.find('article')
        if articulo:
            parrafos = articulo.find_all('p')
            texto = ' '.join([p.get_text() for p in parrafos if len(p.get_text()) > 50])
            return texto
        
        # Fallback: buscar por datos de componente
        componentes = soup.find_all('div', {'data-component': 'text-block'})
        if componentes:
            texto = ' '.join([comp.get_text() for comp in componentes])
            return texto
            
        return self._extraer_generico(soup)

    def _extraer_eltiempo(self, soup):
        """Extrae contenido de El Tiempo"""
        contenido = soup.find('div', class_='contenido')
        if contenido:
            parrafos = contenido.find_all('p')
            texto = ' '.join([p.get_text() for p in parrafos if len(p.get_text()) > 30])
            return texto
        return self._extraer_generico(soup)

    def _extraer_reuters(self, soup):
        """Extrae contenido de Reuters"""
        articulo = soup.find('article')
        if articulo:
            parrafos = articulo.find_all('p')
            texto = ' '.join([p.get_text() for p in parrafos if len(p.get_text()) > 40])
            return texto
        return self._extraer_generico(soup)

    def _extraer_generico(self, soup):
        """Extraccion generica para cualquier sitio"""
        # Eliminar elementos no deseados
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Buscar el contenido mas largo (probablemente el articulo)
        parrafos = soup.find_all('p')
        textos_largos = []
        
        for p in parrafos:
            texto = p.get_text().strip()
            if len(texto) > 100 and not self._es_publicidad(texto):
                textos_largos.append(texto)
        
        if textos_largos:
            return ' '.join(textos_largos[:15])  # Limitar a 15 parrafos
        
        # Ultimo recurso: todo el texto
        return soup.get_text()

    def _es_publicidad(self, texto):
        """Detecta texto de publicidad"""
        palabras_publicidad = [
            'publicidad', 'sponsored', 'anuncio', 'suscrib', 'newsletter',
            'patrocinado', 'advertisement', 'promocionado', 'marketing'
        ]
        texto_lower = texto.lower()
        return any(palabra in texto_lower for palabra in palabras_publicidad)

    def _extraer_dominio(self, url):
        """Extrae dominio de URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.lower()
        except:
            return ""

    def _limpiar_texto(self, texto):
        """Limpia el texto extraido"""
        if not texto:
            return None
        # Eliminar espacios multiples
        texto = re.sub(r'\s+', ' ', texto)
        # Eliminar caracteres problematicos
        texto = re.sub(r'[^\w\s.,!?;:()\-]', '', texto)
        return texto.strip()

    def buscar_noticias_google(self, consulta, limite=5):
        """Busca noticias usando Google News"""
        try:
            consulta_codificada = requests.utils.quote(consulta)
            url = f"https://news.google.com/search?q={consulta_codificada}&hl=es-419&gl=CO&ceid=CO:es-419"
            
            response = self.sesion.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            noticias = []
            articulos = soup.find_all('article')[:limite]
            
            for articulo in articulos:
                try:
                    enlace = articulo.find('a')
                    if enlace and enlace.get('href'):
                        titulo = enlace.get_text().strip()
                        url_relativa = enlace.get('href')
                        url_completa = f"https://news.google.com{url_relativa}"
                        
                        noticias.append({
                            'titulo': titulo,
                            'url': url_completa,
                            'fuente': 'Google News'
                        })
                except:
                    continue
            
            return noticias
            
        except Exception as e:
            print(f"Error buscando en Google News: {e}")
            return []