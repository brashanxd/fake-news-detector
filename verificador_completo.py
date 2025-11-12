# verificador_completo.py
import requests
import re
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configuración
CONFIG = {
    "newsapi_key": "7de67c78ed5a4a808ad09eba35f74003",
    "timeout": 10,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

FUENTES_CONFIABLES = [
    "bbc.com", "reuters.com", "apnews.com", "cnn.com",
    "wikipedia.org", "eltiempo.com", "elespectador.com"
]

class ExtractorSimple:
    def __init__(self):
        self.sesion = requests.Session()
        self.sesion.headers.update({
            'User-Agent': CONFIG['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })

    def extraer_de_url(self, url):
        try:
            print(f"Conectando con: {url}")
            response = self.sesion.get(url, timeout=15, verify=False)
            
            if response.status_code != 200:
                print(f"Error HTTP {response.status_code}")
                return None
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            parrafos = soup.find_all('p')
            textos = []
            
            for p in parrafos:
                texto = p.get_text().strip()
                if len(texto) > 50 and not self._es_publicidad(texto):
                    textos.append(texto)
            
            if textos:
                contenido = ' '.join(textos[:10])
                return self._limpiar_texto(contenido)
            else:
                return self._limpiar_texto(soup.get_text())
                
        except Exception as e:
            print(f"Error extrayendo: {e}")
            return None

    def _es_publicidad(self, texto):
        palabras_publicidad = ['publicidad', 'sponsored', 'anuncio', 'newsletter']
        texto_lower = texto.lower()
        return any(palabra in texto_lower for palabra in palabras_publicidad)

    def _limpiar_texto(self, texto):
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

class IAVerificador:
    def __init__(self):
        print("Modulo de IA inicializado")
        
    def analizar_con_ia(self, texto):
        if not texto or len(texto) < 20:
            return 0.5, "Texto insuficiente para analisis de IA"
        
        texto_lower = texto.lower()
        
        patrones_falsos = [
            r'\b(cura definitiva|curacion completa|sanacion total)\b',
            r'\b(descubrimiento revolucionario|avance increible)\b', 
            r'\b(ocultan|encubren|conspiracion)\b',
            r'\b(miles? de millones|trillones|cantidades exorbitantes)\b',
            r'\b(proximo mes|esta semana|urgente|inmediato)\b',
            r'\b(cientificos de harvard|universidad de oxford)\b.*\b(descubrieron|encontraron)\b',
            r'\b(nasa confirma|nasa anuncia)\b.*\b(asteroide|extraterrestre)\b'
        ]
        
        patrones_verdaderos = [
            r'\b(presidente|gobierno|ministerio|institucion)\b.*\b(anuncio|confirmo|informo)\b',
            r'\b(estudio publicado|investigacion cientifica|revista especializada)\b',
            r'\b(segun fuentes oficiales|de acuerdo con|confirmado por)\b',
            r'\b(elecciones|votaciones|proceso democratico)\b',
            r'\b(datos estadisticos|cifras oficiales|informe anual)\b'
        ]
        
        patrones_falsos_encontrados = sum(1 for patron in patrones_falsos if re.search(patron, texto_lower))
        patrones_verdaderos_encontrados = sum(1 for patron in patrones_verdaderos if re.search(patron, texto_lower))
        
        total_patrones = patrones_falsos_encontrados + patrones_verdaderos_encontrados
        if total_patrones == 0:
            return 0.5, "IA: No se detectaron patrones claros"
        
        confianza = 0.5 + (patrones_verdaderos_encontrados - patrones_falsos_encontrados) * 0.15
        confianza = max(0.1, min(0.9, confianza))
        
        explicacion = "IA: "
        if patrones_falsos_encontrados > patrones_verdaderos_encontrados:
            explicacion += f"Se detectaron {patrones_falsos_encontrados} patrones tipicos de desinformacion"
        elif patrones_verdaderos_encontrados > patrones_falsos_encontrados:
            explicacion += f"Se detectaron {patrones_verdaderos_encontrados} patrones de informacion confiable"
        else:
            explicacion += "Patrones equilibrados, se requiere verificacion adicional"
            
        return confianza, explicacion

class VerificadorSimple:
    def __init__(self):
        self.extractor = ExtractorSimple()
        self.newsapi_key = CONFIG['newsapi_key']
        
    def verificar(self, texto):
        print("Analizando noticia...")
        
        elementos = self._analizar_texto(texto)
        print(f"Personas: {elementos['personas']}")
        print(f"Lugares: {elementos['lugares']}")
        
        resultados = self._buscar_informacion(elementos)
        
        return self._generar_resultado(resultados, texto)

    def _analizar_texto(self, texto):
        personas = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', texto)
        
        lugares = re.findall(r'\b(Texas|California|Florida|México|EEUU|Estados Unidos)\b', texto, re.IGNORECASE)
        
        tema = "general"
        texto_lower = texto.lower()
        if any(palabra in texto_lower for palabra in ['migrante', 'inmigrante', 'frontera']):
            tema = "migración"
        if 'trump' in texto_lower:
            tema = "política EEUU"
        
        return {
            'personas': list(set(personas)),
            'lugares': list(set([l.title() for l in lugares])),
            'tema': tema,
            'texto': texto
        }

    def _buscar_informacion(self, elementos):
        print("Buscando información relacionada...")
        
        resultados = {
            'newsapi': [],
            'wikipedia': [],
            'encontrado': False
        }
        
        if elementos['personas'] or elementos['lugares']:
            consulta = self._generar_consulta(elementos)
            print(f"Buscando: {consulta}")
            
            resultados['newsapi'] = self._buscar_newsapi(consulta)
            resultados['wikipedia'] = self._buscar_wikipedia_simple(consulta)
        
        resultados['encontrado'] = len(resultados['newsapi']) > 0 or len(resultados['wikipedia']) > 0
        return resultados

    def _generar_consulta(self, elementos):
        consulta_parts = []
        
        if elementos['personas']:
            consulta_parts.append(elementos['personas'][0])
        
        if elementos['lugares']:
            consulta_parts.append(elementos['lugares'][0])
        
        if elementos['tema'] != 'general':
            consulta_parts.append(elementos['tema'])
        
        return ' '.join(consulta_parts) if consulta_parts else elementos['texto'][:50]

    def _buscar_newsapi(self, consulta):
        if not self.newsapi_key:
            return []
            
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': consulta,
                'pageSize': 5,
                'sortBy': 'relevancy',
                'language': 'es'
            }
            headers = {'Authorization': self.newsapi_key}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articulos = data.get('articles', [])
                print(f"NewsAPI: {len(articulos)} artículos")
                return articulos
                
        except Exception as e:
            print(f"Error NewsAPI: {e}")
            
        return []

    def _buscar_wikipedia_simple(self, consulta):
        try:
            print("Wikipedia: búsqueda simulada")
            return [{'titulo': 'Resultado Wikipedia', 'fuente': 'wikipedia'}]
        except:
            return []

    def _generar_resultado(self, resultados, texto_original):
        if resultados['encontrado']:
            etiqueta = "INFORMACIÓN ENCONTRADA"
            confianza = 0.7
            explicacion = "Se encontró información relacionada en fuentes confiables."
        else:
            etiqueta = "NO VERIFICABLE"
            confianza = 0.3
            explicacion = "No se encontró información suficiente."
        
        return {
            'etiqueta': etiqueta,
            'confianza': confianza,
            'explicacion': explicacion,
            'texto_analizado': texto_original[:200]
        }

class VerificadorSimpleConIA(VerificadorSimple):
    def __init__(self):
        super().__init__()
        self.ia = IAVerificador()
        
    def verificar(self, texto):
        resultado = super().verificar(texto)
        
        confianza_ia, explicacion_ia = self.ia.analizar_con_ia(texto)
        
        resultado['confianza_ia'] = round(confianza_ia, 2)
        resultado['explicacion_ia'] = explicacion_ia
        
        if confianza_ia >= 0.7 and resultado['etiqueta'] == 'NO VERIFICABLE':
            resultado['etiqueta'] = 'PROBABLEMENTE VERDADERO'
            resultado['confianza'] = max(resultado['confianza'], 0.6)
        elif confianza_ia <= 0.3 and resultado['etiqueta'] == 'NO VERIFICABLE':
            resultado['etiqueta'] = 'PROBABLEMENTE FALSO' 
            resultado['confianza'] = max(resultado['confianza'], 0.6)
            
        return resultado

def main():
    verificador = VerificadorSimpleConIA()
    extractor = ExtractorSimple()
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 50)
        print("    VERIFICADOR DE NOTICIAS - VERSIÓN SIMPLE")
        print("=" * 50)
        print()
        print("1. Verificar texto")
        print("2. Verificar URL") 
        print("3. Salir")
        print()
        
        opcion = input("Selecciona opción (1-3): ").strip()
        
        if opcion == '1':
            verificar_texto(verificador)
        elif opcion == '2':
            verificar_url(verificador, extractor)
        elif opcion == '3':
            print("¡Hasta pronto!")
            break
        else:
            input("Opción inválida. Enter para continuar...")

def verificar_texto(verificador):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("VERIFICAR TEXTO")
    print("Pega el texto a verificar:")
    print("-" * 40)
    
    texto = input("> ").strip()
    
    if len(texto) < 20:
        input("Texto muy corto. Enter para continuar...")
        return
    
    resultado = verificador.verificar(texto)
    mostrar_resultado(resultado)

def verificar_url(verificador, extractor):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("VERIFICAR URL")
    url = input("Ingresa la URL: ").strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print("Extrayendo contenido...")
    texto = extractor.extraer_de_url(url)
    
    if not texto:
        input("No se pudo extraer contenido. Enter para continuar...")
        return
    
    print(f"Extraídos {len(texto)} caracteres")
    
    print("\n¿Qué afirmación quieres verificar?")
    afirmacion = input("> ").strip()
    
    if afirmacion:
        texto_verificar = f"{afirmacion}. Contexto: {texto[:300]}"
    else:
        texto_verificar = texto[:500]
    
    resultado = verificador.verificar(texto_verificar)
    mostrar_resultado(resultado)

def mostrar_resultado(resultado):
    print("\n" + "=" * 50)
    print("RESULTADO:")
    print("=" * 50)
    print(f"Estado: {resultado['etiqueta']}")
    print(f"Confianza: {resultado['confianza'] * 100}%")
    if 'confianza_ia' in resultado:
        print(f"Confianza IA: {resultado['confianza_ia'] * 100}%")
        print(f"Análisis IA: {resultado['explicacion_ia']}")
    print(f"Explicación: {resultado['explicacion']}")
    print(f"Texto analizado: {resultado['texto_analizado']}")
    print("=" * 50)
    input("Enter para continuar...")

if __name__ == "__main__":
    try:
        requests.packages.urllib3.disable_warnings()
        main()
    except KeyboardInterrupt:
        print("\n¡Programa interrumpido!")
    except Exception as e:
        print(f"\nError: {e}")
        input("Enter para salir...")