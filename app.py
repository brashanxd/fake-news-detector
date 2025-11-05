# app.py
# Aplicación web para detección de noticias falsas
# Ejecutar con: streamlit run app.py

import streamlit as st
from analyzer import NewsAnalyzer
from webscraper import extract_article_text
from visualization import visualize_word_frequencies, visualize_sentiment

st.set_page_config(
    page_title="Detector de Noticias Falsas",
    page_icon="📰",
    layout="centered",
)

st.title("Detector Inteligente de Noticias Falsas")
st.markdown(
    """
    Esta herramienta usa **Inteligencia Artificial (BERT)** para analizar noticias en inglés o español.  
    Puedes escribir un texto o pegar un enlace a una noticia y el sistema te dirá si parece **real o falsa**, con explicación y análisis visual.
    """
)

# Campo de entrada
option = st.radio("¿Qué deseas analizar?", ["Texto manual", "Enlace de noticia"])

if option == "Texto manual":
    texto = st.text_area("Escribe o pega una noticia:", height=200)
else:
    url = st.text_input("Pega la URL de la noticia:")
    texto = ""
    if url:
        with st.spinner("Extrayendo contenido de la página..."):
            texto = extract_article_text(url)

if texto:
    st.write("### 🧾 Texto detectado:")
    st.write(texto[:1000] + ("..." if len(texto) > 1000 else ""))

    if st.button("🔍 Analizar noticia"):
        analyzer = NewsAnalyzer()
        with st.spinner("Analizando con modelo IA..."):
            resultado = analyzer.analyze_news(texto)

        st.success("Análisis completado")
        st.subheader("Resultado del modelo")
        st.write(f"**Idioma detectado:** {resultado['language']}")
        st.write(f"**Clasificación:** {resultado['label']}")
        st.write(f"**Confianza:** {resultado['confidence']*100:.2f}%")
        st.info(resultado['explanation'])

        # Mostrar visualizaciones
        st.subheader("Análisis visual del texto")
        visualize_word_frequencies(resultado)
        visualize_sentiment(resultado)
else:
    st.warning("Por favor, ingresa un texto o una URL válida para analizar.")
