import altair as alt
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from textblob import TextBlob
import streamlit as st

def visualize_word_frequencies(result):
    text = result["text"]
    label = result["label"]
    confidence = result["confidence"]

    vectorizer = CountVectorizer(stop_words="english")
    X = vectorizer.fit_transform([text])
    words = vectorizer.get_feature_names_out()
    freqs = X.toarray()[0]
    data = pd.DataFrame({"word": words, "count": freqs}).sort_values("count", ascending=False)[:15]

    chart = (
        alt.Chart(data)
        .mark_bar(color="#4a90e2")
        .encode(
            x=alt.X("count", title="Frecuencia"),
            y=alt.Y("word", sort="-x", title="Palabras"),
        )
        .properties(title=f"Palabras más frecuentes — {label} ({confidence*100:.2f}%)")
    )
    st.altair_chart(chart, use_container_width=True)

def visualize_sentiment(result):
    blob = TextBlob(result["text"])
    sentiment = blob.sentiment.polarity
    sentiment_text = (
        "Negativo 😟" if sentiment < 0 else "Positivo 🙂" if sentiment > 0 else "Neutral 😐"
    )
    st.write(f"**Análisis de sentimiento:** {sentiment_text} ({sentiment:.2f})")

    sentiment_data = pd.DataFrame({"Tipo": ["Positivo", "Negativo"], "Valor": [max(sentiment, 0), max(-sentiment, 0)]})
    chart = alt.Chart(sentiment_data).mark_bar().encode(
        x="Tipo",
        y="Valor",
        color="Tipo"
    ).properties(title="Distribución del sentimiento")
    st.altair_chart(chart, use_container_width=True)
