import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time

# --- CONFIGURACIÓN DE SEGURIDAD ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_AQUI"

genai.configure(api_key=GOOGLE_API_KEY)

@st.cache_resource
def obtener_modelo_seguro():
    # Probamos los nombres que tu lista confirmó como válidos
    nombres = ['models/gemini-2.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-flash']
    for n in nombres:
        try:
            return genai.GenerativeModel(n)
        except:
            continue
    return None

model = obtener_modelo_seguro()

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS RADICAL PARA ELIMINAR EL NEGRO ---
st.markdown("""
    <style>
    /* 1. Fondo general */
    .stApp { background-color: #f0f4f8 !important; }
    
    /* 2. Textos generales */
    h1, h2, h3, p, span, div, label, .stMarkdown { color: #2c3e50 !important; }

    /* 3. ARREGLO RADICAL DEL UPLOAD (Adiós al negro) */
    /* Contenedor principal del uploader */
    [data-testid="stFileUploader"] {
        background-color: transparent !important;
    }
    
    /* El área de arrastre y el archivo ya subido */
    [data-testid="stFileUploader"] section, 
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploaderSmallFileDropzone"],
    div[data-testid="stFileUploaderDropzone"] {
        background-color: #ffffff !important;
        color: #2c3e50 !important;
        border: 2px dashed #27ae60 !important;
        border-radius: 15px !important;
    }

    /* Iconos y textos de archivos subidos */
