import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64

# --- CONEXIÓN DIRECTA ---
try:
    # Intentamos leer de Secrets, si no, usamos el texto directo (por si acaso)
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # SI NADA FUNCIONA, PEGA TU CLAVE AQUÍ ENTRE COMILLAS SOLO PARA PROBAR
    API_KEY = "TU_CLAVE_AQUI" 

genai.configure(api_key=API_KEY)

# Usamos el nombre más básico de todos
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="ReciboZen", page_icon="🧘")

# --- ESTILO ZEN ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f4f8 !important; }
    .report-card { background-color: white; padding: 25px; border-radius: 15px; border-top: 10px solid #27ae60; color: #2c3e50; }
    .stButton > button { width: 100%; height: 60px; border-radius: 12px; font-weight: bold; color: white !important; }
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    [data-testid="column"]:nth-of-type(1) button { background-color: #3498db !important; }
    [data-testid="column"]:nth-of-type(2) button { background-color: #e67e22 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

st.title("🧘 ReciboZen")
st.write("### Tu factura explicada con alegría")

uploaded_file = st.file_uploader("Carga tu PDF", type="pdf")

if uploaded_file:
    if st.button("🚀 ANALIZAR FACTURA", type="primary"):
        with st.spinner('Analizando...'):
            try:
                texto = leer_pdf(uploaded_file)
                prompt = f"Eres ReciboZen. Analiza esta factura. Da el Total (€), Consumo (kWh) y un consejo. Luego añade '---' y un saludo alegre para audio. Factura: {texto[:3000]}"
                response = model.generate_content(prompt)
                
                # Guardamos en sesión
                partes = response.text.split('---')
                st.session_state['txt'] = partes[0]
                voz = partes[1] if len(partes)>1 else partes[0]
                
                tts = gTTS(text=voz, lang='es')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.session_state['aud'] = base64.b64encode(audio_io.getvalue()).decode()
            except Exception as e:
                st.error(f"Error de Google: {e}")

if 'txt' in st.session_state:
    st.markdown(f"<div class='report-card'>{st.session_state['txt']}</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ INICIAR"): st.session_state['play'] = True
    with col2:
        if st.button("⏹️ PARAR"): st.session_state['play'] = False
    
    if st.session_state.get('play'):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["aud"]}" type="audio/mp3"></audio>', height=0)
