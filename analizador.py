import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64

# --- CONEXIÓN DIRECTA ---
# Ponemos la clave aquí directamente para asegurar que llega
API_KEY = "AIzaSyAiuURS2QzBLgEyjBj_ihaSDMN2h_Uwr88"
genai.configure(api_key=API_KEY)

# Usamos el modelo que SABEMOS que tienes (el 2.5 flash que viste en tu lista)
# pero lo llamamos de la forma más sencilla posible
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="ReciboZen", page_icon="🧘")

# --- CSS ZEN ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f4f8 !important; }
    h1, h2, h3, p, div, label { color: #2c3e50 !important; }
    .report-card { 
        background-color: white !important; 
        padding: 25px; 
        border-radius: 20px; 
        border-top: 10px solid #27ae60; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .stButton>button { height: 60px; border-radius: 15px; font-weight: bold; color: white !important; }
    .stButton > button[kind="primary"] { background-color: #27ae60 !important; }
    .stButton > button[kind="secondary"] { background-color: #3498db !important; }
    div.row-widget.stButton.stop-btn > button { background-color: #e67e22 !important; }
    [data-testid="stFileUploader"] section { background-color: white !important; border: 2px dashed #27ae60 !important; }
    </style>
    """, unsafe_allow_html=True)

def leer_pdf(file):
    reader = PdfReader(file)
    return "".join([page.extract_text() for page in reader.pages])

st.title("🧘 ReciboZen")
st.write("### Explicaciones claras para tus facturas")

uploaded_file = st.file_uploader("Cargue su PDF", type="pdf")

if uploaded_file:
    if st.button("🚀 ANALIZAR MI FACTURA", type="primary"):
        with st.spinner('Analizando...'):
            try:
                texto = leer_pdf(uploaded_file)
                # Intento de generación directo
                response = model.generate_content(f"Resume esta factura para una persona mayor. Indica Total, Consumo y Potencia. Sé amable. Texto: {texto[:3000]}")
                st.session_state['analisis'] = response.text
                
                # Generar audio
                tts = gTTS(text=response.text.replace('*', '').replace('#', ''), lang='es')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.session_state['audio_b64'] = base64.b64encode(audio_io.getvalue()).decode()
            except Exception as e:
                st.error(f"Error de conexión: {e}")

if 'analisis' in st.session_state:
    st.markdown(f"<div class='report-card'><h3>📋 Informe ReciboZen</h3>{st.session_state['analisis']}</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔊 ESCUCHAR", type="secondary", use_container_width=True):
            st.session_state['play'] = True
    with col2:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("⏹️ PARAR", type="secondary", use_container_width=True):
            st.session_state['play'] = False
        st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.get('play'):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=0)

st.markdown("<br><hr><center><small>ReciboZen · 2026</small></center>", unsafe_allow_html=True)
