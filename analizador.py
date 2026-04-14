import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import time

# --- CONEXIÓN ---
API_KEY = "AIzaSyAiuURS2QzBLgEyjBj_ihaSDMN2h_Uwr88"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

# --- CSS MEJORADO (Botones Alineados y Colores Blindados) ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    
    .report-card { 
        background-color: white !important; 
        padding: 30px; 
        border-radius: 20px; 
        border-top: 10px solid #27ae60; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 25px;
        line-height: 1.6;
    }

    /* Alineación perfecta de botones */
    .stButton > button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 15px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        color: white !important;
        border: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    /* Estilo específico para el botón de parar */
    div.stop-btn > div.stButton > button { background-color: #e67e22 !important; }

    [data-testid="stFileUploader"] section { background-color: white !important; border: 2px dashed #27ae60 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

def preparar_audio(texto_para_leer):
    # gTTS no permite cambiar velocidad directamente de forma fina, 
    # pero al quitar puntuación pesada suena más fluido.
    tts = gTTS(text=texto_para_leer, lang='es', slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con cariño y alegría")

uploaded_file = st.file_uploader("Carga tu factura (PDF)", type="pdf")

if uploaded_file:
    if st.button("🚀 ¡DAME LUZ SOBRE MI FACTURA!", type="primary"):
        with st.spinner('ReciboZen está dándole vueltas a los números...'):
            try:
                texto_raw = leer_pdf(uploaded_file)
                
                # PROMPT 1: El Informe Visual (Detallado y Zen)
                prompt_informe = f"""
                Analiza esta factura de energía. Usa un lenguaje muy cercano, como un nieto experto explicando a su abuelo.
                Estructura el informe con estos puntos:
                1. El susto o la alegría (Total en €).
                2. ¿En qué se nos va el dinero? (Desglose sencillo de Potencia vs Consumo).
                3. El rincón de los impuestos (Explicado de forma que no duela).
                4. Un consejo Zen para ahorrar el mes que viene.
                Texto: {texto_raw[:3500]}
                """
                res_informe = model.generate_content(prompt_informe).text
                
                # PROMPT 2: El Guion de Voz (Divertido y Alegre)
                prompt_voz = f"""
                Basándote en este informe: {res_informe}, escribe un guion para ser leído. 
                Debe ser muy alegre, desenfadado, con energía. 
                Usa expresiones como "¡Hola, hola!", "¡Vamos a ver qué tenemos aquí!", "¡No te preocupes por esos impuestos!".
                Que sea una charla animada, no una lectura aburrida. Máximo 100 palabras.
                """
                res_voz = model.generate_content(prompt_voz).text
                
                st.session_state['analisis'] = res_informe
                st.session_state['audio_b64'] = preparar_audio(res_voz)
                st.session_state['reproducir'] = False
            except Exception as e:
                st.error(f"¡Ups! Algo ha fallado: {e}")

if 'analisis' in st.session_state:
    st.markdown(f"<div class='report-card'><h3>📋 Tu Informe ReciboZen</h3>{st.session_state['analisis']}</div>", unsafe_allow_html=True)
    
    st.write("### 🔊 Escucha tu versión animada")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ INICIAR AUDIO", type="secondary"):
            st.session_state['reproducir'] = True
    with col2:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("⏹️ PARAR AUDIO", type="secondary"):
            st.session_state['reproducir'] = False
        st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.get('reproducir'):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=0)

st.markdown("<br><hr><center><small>ReciboZen · 2026 · Hecho con alegría ✨</small></center>", unsafe_allow_html=True)
