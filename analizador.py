import streamlit as st
from google import genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import pandas as pd
import os
import re
import time
from datetime import datetime

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="ReciboZen", page_icon="🧾", layout="centered")

HISTORIAL_CSV = "recibozen_historial.csv"
API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    st.error("Falta configurar GOOGLE_API_KEY en Streamlit Secrets.")
    st.stop()
client = genai.Client(api_key=API_KEY)

# Mantengo tu bloque de CSS intacto ya que es excelente
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@700;800&display=swap');
    :root {
        --surface: rgba(255,255,255,.96);
        --line: rgba(18,48,70,.12);
        --text: #123046;
        --muted: #486171;
        --primary: #0f5fa6;
        --primary-2: #1f7dcb;
        --danger: #b3343b;
        --danger-2: #d94b52;
        --shadow: 0 14px 34px rgba(18,48,70,.08);
    }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: linear-gradient(180deg, #f3f8fc 0%, #eef5fb 100%) !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .block-container { max-width: 840px; padding-top: .6rem; padding-bottom: 3rem; }
    .rz-header, .panel { background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 24px; padding: 1.15rem; margin-bottom: 1rem; }
    .section-title { font-family:'Manrope',sans-serif; font-size:1.12rem; font-weight:800; margin:0 0 .85rem 0; }
    .data-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.85rem; }
    .data-card, .metric-card { background:#fff; border:1px solid var(--line); border-radius:20px; padding:1rem .95rem; box-shadow:0 8px 20px rgba(18,48,70,.05); }
    .metric-value { font-size:2rem; line-height:1.05; font-weight:800; color:var(--text); letter-spacing:-.02em; }
    .metric-delta { margin-top:.45rem; color:var(--muted); font-size:.92rem; font-weight:600; }

    /* Estilos de botones y otros componentes omitidos por brevedad pero mantenidos en ejecución */
    div.stButton > button, .stDownloadButton > button { width:100% !important; min-height:54px !important; border-radius:18px !important; font-weight:800 !important; background:linear-gradient(180deg,var(--primary-2) 0%, var(--primary) 100%) !important; color:white !important; border:none !important; }
    .history-table table { width:100%; border-collapse:collapse; background:#fff; border-radius:16px; overflow:hidden; }
    .history-table thead th { background:#f4f8fc; padding:.8rem; text-align:left; font-weight:800; }
    .history-table tbody td { padding:.78rem; border-bottom:1px solid rgba(18,48,70,.08); }
    </style>
    """, unsafe_allow_html=True
)

# --- FUNCIONES DE LÓGICA ---

def normalizar_periodo_historial(texto):
    """Convierte cualquier formato de fecha a DD/MM/AAAA - DD/MM/AAAA para el historial."""
    fechas = re.findall(r"(\d{1,2})[ /de]*([a-zA-Záéíóú]+|\d{2})[ /de]*(\d{2,4})", texto)
    meses = {"enero":"01","febrero":"02","marzo":"03","abril":"04","mayo":"05","junio":"06","julio":"07","agosto":"08","septiembre":"09","octubre":"10","noviembre":"11","diciembre":"12"}

    if len(fechas) >= 2:
        parts = []
        for f in fechas[:2]:
            dia = f[0].zfill(2)
            mes = f[1].lower()
            mes = meses.get(mes, mes.zfill(2))
            anio = f[2] if len(f[2]) == 4 else f"20{f[2]}"
            parts.append(f"{dia}/{mes}/{anio}")
        return f"{parts[0]} - {parts[1]}"
    return texto

def limpiar_basura_ia(texto):
    """Elimina tooltips o notas que la IA intenta meter en campos de datos."""
    return re.sub(r"\{.*?\}|\(.*?\)", "", texto).strip()

def parsear_bloques(texto):
    # Lógica de extracción mejorada para evitar "basura" en los campos
    resultado = {}
    for line in texto.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip().lower()
            val = limpiar_basura_ia(v)
            resultado[key] = val
    return resultado

def guardar_historial(factura):
    # Usamos el periodo normalizado para el historial
    periodo_norm = normalizar_periodo_historial(factura.get("periodo", ""))

    fila = {
        "fecha_guardado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "periodo": periodo_norm,
        "compania": factura.get("compania", "No detectada"),
        "total_pagar": factura.get("total_pagar"),
        "consumo_kwh": factura.get("consumo_kwh"),
        "potencia_kw": factura.get("potencia_kw"),
        "impuestos": factura.get("impuestos"),
    }

    df_prev = cargar_historial()

    # Verificación de duplicados: Periodo + Total
    if not df_prev.empty:
        es_duplicado = df_prev[
            (df_prev['periodo'] == periodo_norm) &
            (df_prev['total_pagar'].apply(limpiar_numero) == limpiar_numero(fila['total_pagar']))
        ]
        if not es_duplicado.empty:
            return df_prev # No guardamos si ya existe

    df_new = pd.concat([df_prev, pd.DataFrame([fila])], ignore_index=True)
    df_new.to_csv(HISTORIAL_CSV, index=False)
    return df_new

# [Resto de funciones: cargar_historial, limpiar_numero, fmt_euro, render_metric_card se mantienen según tu versión 8.0]

# --- FLUJO PRINCIPAL ---

# ... (Parte de carga de archivo y botón de analizar)

if uploaded_file and analizar:
    # ... (Proceso de cliente.models.generate_content)
    parsed = parsear_bloques(response.text)

    # En la factura actual para la tarjeta, mantenemos el texto original de la IA
    # Pero para el historial, el guardado normaliza automáticamente
    st.session_state["factura_actual"] = parsed
    historial = guardar_historial(parsed)
    # ...
