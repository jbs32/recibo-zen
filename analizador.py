import streamlit as st
from google import genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import hashlib
import re
import os
import pandas as pd
from datetime import datetime
import requests

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    GOOGLE_API_KEY = ""

try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    OPENROUTER_API_KEY = ""

CANDIDATE_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
HISTORIAL_CSV = "recibozen_historial.csv"
COLUMNAS_HISTORIAL = ["factura_id", "fecha_analisis", "compania", "periodo",
                      "total", "consumo", "potencia", "impuestos", "proveedor"]

# ─────────────────────────────────────────────
# MESES EN ESPAÑOL
# ─────────────────────────────────────────────
MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Manrope', sans-serif !important;
    background-color: #f0f5fb !important;
}

/* Ocultar elementos innecesarios */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* Cabecera */
.zen-header {
    display: flex;
    align-items: center;
    padding: 18px 0 24px 0;
    margin-bottom: 8px;
}

/* Secciones */
.zen-section {
    background: white;
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(30,80,160,0.07);
    border: 1px solid #e3ecf7;
}

.zen-section-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b8cba !important;
    margin-bottom: 16px;
}

/* Tarjetas de métricas */
.zen-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-bottom: 8px;
}

.zen-metric-card {
    background: linear-gradient(135deg, #f0f5fb 0%, #e8f0fa 100%);
    border-radius: 16px;
    padding: 18px 16px 14px 16px;
    border: 1px solid #d0e0f5;
    position: relative;
}

.zen-metric-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6b8cba;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
}

.zen-metric-value {
    font-size: 26px;
    font-weight: 800;
    color: #1a3a6b;
    line-height: 1.1;
}

.zen-metric-sub {
    font-size: 12px;
    color: #8aa4c8;
    margin-top: 2px;
}

/* Tooltip */
.zen-tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
}

.zen-tooltip .zen-tip-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 17px;
    height: 17px;
    border-radius: 50%;
    background: #d0e0f5;
    color: #3a6abf;
    font-size: 10px;
    font-weight: 800;
    line-height: 1;
}

.zen-tooltip .zen-tip-text {
    visibility: hidden;
    opacity: 0;
    background: #1a3a6b;
    color: white;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.5;
    border-radius: 10px;
    padding: 10px 14px;
    position: absolute;
    z-index: 999;
    bottom: 130%;
    left: 50%;
    transform: translateX(-50%);
    width: 220px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.18);
    transition: opacity 0.2s;
    pointer-events: none;
}

.zen-tooltip:hover .zen-tip-text {
    visibility: visible;
    opacity: 1;
}

/* Datos de factura */
.zen-data-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 4px;
}

.zen-data-item {
    background: #f7faff;
    border-radius: 12px;
    padding: 12px 14px;
    border: 1px solid #e3ecf7;
}

.zen-data-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #8aa4c8;
    margin-bottom: 4px;
}

.zen-data-value {
    font-size: 14px;
    font-weight: 700;
    color: #1a3a6b;
}

/* Sección del informe */
.zen-report-block {
    background: linear-gradient(135deg, #eaf1fb 0%, #f0f7ff 100%);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 12px;
    border-left: 4px solid #3a6abf;
}

.zen-report-block-title {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #3a6abf;
    margin-bottom: 10px;
}

.zen-report-text {
    font-size: 15px;
    color: #2c3e6b;
    line-height: 1.65;
}

/* Consejo */
.zen-consejo {
    background: linear-gradient(135deg, #fffbe6 0%, #fff8d6 100%);
    border-radius: 14px;
    padding: 16px 20px;
    border-left: 4px solid #f0b429;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-top: 4px;
}

.zen-consejo-icon {
    font-size: 22px;
    line-height: 1;
    flex-shrink: 0;
}

.zen-consejo-text {
    font-size: 14px;
    color: #7a5c00;
    font-weight: 600;
    line-height: 1.5;
}

/* Botones principales */
.stButton > button {
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    border-radius: 12px !important;
    border: none !important;
    height: 48px !important;
    white-space: nowrap !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}

/* Botón primario (Analizar) */
button[kind="primary"], .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1a3a6b 100%) !important;
    color: white !important;
}

/* Todos los botones secundarios en azul por defecto */
.stButton > button:not([kind="primary"]) {
    background: linear-gradient(135deg, #2563eb 0%, #3a7bd5 100%) !important;
    color: white !important;
}

/* Botones destructivos: Parar y Borrar historial */
div[data-testid="column"].btn-rojo .stButton > button,
.btn-destructivo .stButton > button {
    background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%) !important;
    color: white !important;
}

/* Uploader limpio */
[data-testid="stFileUploader"] {
    background: white !important;
}
[data-testid="stFileUploader"] section {
    background: white !important;
    border: 2px dashed #3a6abf !important;
    border-radius: 14px !important;
    padding: 16px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] div span {
    display: none !important;
}
[data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "Arrastra tu factura aquí o haz clic para buscarla";
    font-family: 'Manrope', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #3a6abf;
}
[data-testid="stFileUploaderDropzone"] small {
    display: none !important;
}

/* Spinner */
[data-testid="stSpinner"] {
    background: white !important;
    border-radius: 16px !important;
    padding: 20px !important;
}

/* Historial tabla */
.zen-historial-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 8px;
}
.zen-historial-table th {
    background: #eaf1fb;
    color: #3a6abf;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid #d0e0f5;
}
.zen-historial-table td {
    padding: 10px 12px;
    color: #1a3a6b;
    border-bottom: 1px solid #f0f5fb;
    background: white;
}
.zen-historial-table tr:last-child td {
    border-bottom: none;
}
.zen-historial-table tr:hover td {
    background: #f7faff;
}

/* Aviso duplicado */
.zen-aviso {
    background: #eaf4ff;
    border-radius: 12px;
    padding: 12px 16px;
    border-left: 4px solid #3a6abf;
    font-size: 13px;
    color: #1a3a6b;
    font-weight: 600;
    margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGOTIPO SVG
# ─────────────────────────────────────────────
LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 60" width="220" height="50">
  <defs>
    earGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2563eb;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1a3a6b;stop-opacity:1" />
    </linearGradient>
  </defs>
  <!-- Icono -->
  <rect x="0" y="6" width="44" height="48" rx="8" fill="url(#logoGrad)" />
  <rect x="7" y="15" width="20" height="3" rx="1.5" fill="white" opacity="0.9"/>
  <rect x="7" y="22" width="30" height="3" rx="1.5" fill="white" opacity="0.9"/>
  <rect x="7" y="29" width="25" height="3" rx="1.5" fill="white" opacity="0.7"/>
  <rect x="7" y="36" width="18" height="3" rx="1.5" fill="white" opacity="0.5"/>
  <!-- Onda zen -->
  <path d="M10 46 Q17 40 24 46 Q31 52 38 46" stroke="white" stroke-width="2.5"
        fill="none" stroke-linecap="round" opacity="0.9"/>
  <!-- Texto -->
  <text x="54" y="42" font-family="Manrope, sans-serif" font-weight="800"
        font-size="28" fill="#1a3a6b">Recibo</text>
  <text x="163" y="42" font-family="Manrope, sans-serif" font-weight="300"
        font-size="28" fill="#2563eb">Zen</text>
  <!-- Punto decorativo -->
  ircle cx="273" cy="14" r="5" fill="#f0b429"/>
</svg>
"""

# ─────────────────────────────────────────────
# FUNCIONES DE FECHA Y PERIODO
# ─────────────────────────────────────────────
def parsear_fecha_es(texto):
    texto = texto.strip().lower()
    # DD/MM/AAAA o DD-MM-AAAA
    m = re.match(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", texto)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.
