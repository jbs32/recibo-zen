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
import hashlib
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS (UI/UX)
# =============================================================================
st.set_page_config(page_title="ReciboZen", page_icon="🧾", layout="centered")

# Definición de constantes para persistencia
HISTORIAL_CSV = "recibozen_historial.csv"

# Recuperación de la API KEY desde los secretos de Streamlit
API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    st.error("Falta configurar GOOGLE_API_KEY en Streamlit Secrets.")
    st.stop()

# Configuración del cliente de Google GenAI (Gemini)
client = genai.Client(api_key=API_KEY)
MODELOS_ANALISIS = ["gemini-2.0-flash", "gemini-1.5-flash"] # Modelos más rápidos y capaces

# Estilos CSS personalizados para una interfaz didáctica y accesible
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
  --danger: #b71c1c;
}

/* Diseño general y tipografía */
.main { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: var(--text); }
h1, h2, h3 { font-family: 'Manrope', sans-serif; font-weight: 800; color: var(--text); }

/* Contenedores visuales (Paneles) */
.panel {
    background: white;
    padding: 24px;
    border-radius: 20px;
    border: 1px solid var(--line);
    margin-bottom: 24px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}

/* Etiquetas de categoría (Badges) */
.badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 10px;
}
.badge-luz { background: #fff9c4; color: #fbc02d; }
.badge-agua { background: #e3f2fd; color: #1976d2; }
.badge-gas { background: #fbe9e7; color: #d84315; }

/* Títulos de sección */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# LÓGICA DE DETECCIÓN Y CATEGORIZACIÓN
# =============================================================================

def detectar_categoria(texto_raw):
    """
    Analiza el texto bruto de la factura para clasificarla.
    Es vital para la organización del historial.
    """
    t = texto_raw.lower()
    # Prioridad Agua: Términos específicos encontrados en factura-agua-febrero.pdf
    if any(x in t for x in ["m3", "aigua", "agua", "canon", "clavegueram", "aqualia"]):
        return "Agua"
    # Prioridad Luz: Términos en factura-enero.pdf
    if any(x in t for x in ["kwh", "potencia contratada", "eléctrico", "luz", "electricidad"]):
        return "Luz"
    # Gas: Términos habituales de gas natural
    if any(x in t for x in ["gas natural", "término de energía gas", "hace referencia al gas"]):
        return "Gas"
    return "Otros"

# =============================================================================
# GESTIÓN DEL HISTORIAL (CSV Y PANDAS)
# =============================================================================

def cargar_historial():
    """Carga el historial desde CSV de forma segura."""
    if os.path.exists(HISTORIAL_CSV):
        try:
            return pd.read_csv(HISTORIAL_CSV)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def asegurar_columnas_historial(df):
    """
    IMPORTANTE: Esta función garantiza que el CSV siempre tenga las columnas necesarias.
    Si se añade una nueva funcionalidad (como 'categoria'), esta función evita que la app falle.
    """
    columnas_requeridas = {
        "archivo_hash": "",
        "fecha_guardado": "",
        "categoria": "Otros",        # Nueva columna para la separación
        "periodo": "No detectado",
        "compania": "No detectada",
        "total_pagar": 0.0,
        "consumo_principal": 0.0,    # Genérico para kwh o m3
        "unidad": "",                # 'kWh' o 'm3'
        "resumen_didactico": "",
        "audio_b64": ""
    }
    
    if df.empty:
        return pd.DataFrame(columns=columnas_requeridas.keys())
    
    for col, default in columnas_requeridas.items():
        if col not in df.columns:
            df[col] = default
    return df

def deduplicar_historial(df):
    """Evita guardar dos veces la misma factura basándose en el contenido único."""
    if df.empty: return df
    return df.drop_duplicates(subset=["archivo_hash"], keep="first")

# =============================================================================
# PROCESAMIENTO DE DOCUMENTOS (PDF + IA)
# =============================================================================

def extraer_texto_pdf(file):
    """Extrae todo el texto de un PDF para dárselo a la IA."""
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            texto += content + "\n"
    return texto

def analizar_con_ia(texto):
    """
    Utiliza Gemini para interpretar la factura de forma humana y didáctica.
    He mejorado el prompt para que extraiga específicamente la categoría y unidades.
    """
    prompt = f"""
    Actúa como un experto en facturas del hogar. Analiza este texto de una factura:
    {texto}
    
    Extrae la siguiente información en formato JSON puro (sin markdown):
    {{
        "compania": "nombre de la empresa",
        "total": 0.00,
        "periodo": "rango de fechas",
        "consumo_valor": 0.00,
        "unidad_medida": "kWh o m3",
        "explicacion_sencilla": "Un resumen de 3 frases explicando qué ha pasado este mes sin usar tecnicismos complejos.",
        "audio_script": "Un guión para leer en voz alta para una persona con discapacidad visual."
    }}
    """
    
    for modelo in MODELOS_ANALISIS:
        try:
            response = client.models.generate_content(model=modelo, contents=prompt)
            # Limpieza básica para asegurar que solo procesamos JSON
            clean_json = re.sub(r"```json|```", "", response.text).strip()
            return pd.read_json(io.StringIO(clean_json), typ="series")
        except Exception as e:
            continue
    return None

# =============================================================================
# INTERFAZ DE USUARIO (LOGOTIPO Y CARGA)
# =============================================================================

# Header con Logo y Eslogan
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    if os.path.exists("recibozen-logo.svg"):
        st.image("recibozen-logo.svg", width=100)
    else:
        st.title("🧾")
with col_tit:
    st.markdown("<h1 style='margin-bottom:0;'>ReciboZen</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:var(--muted); font-size:1.1rem;'>Tus facturas, ahora claras como el agua.</p>", unsafe_allow_html=True)

# Sección de Carga de Archivos
with st.container():
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Sube tu factura (PDF)", type=["pdf"])
    st.markdown("</div>", unsafe_allow_html=True)

# Lógica principal de ejecución al subir un archivo
if uploaded_file:
    # Generamos un hash único para evitar duplicados en el historial
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    
    # Comprobar si ya existe en el historial para no gastar API innecesariamente
    hist_actual = asegurar_columnas_historial(cargar_historial())
    existe = hist_actual[hist_actual["archivo_hash"] == file_hash]
    
    if not existe.empty:
        # Recuperar datos del historial si ya existe
        data = existe.iloc[0]
        st.info("Esta factura ya estaba en tu historial. Recuperando datos...")
    else:
        with st.spinner("Analizando tu factura con IA..."):
            texto_extraido = extraer_texto_pdf(uploaded_file)
            res = analizar_con_ia(texto_extraido)
            
            if res is not None:
                categoria = detectar_categoria(texto_extraido)
                
                # Generar Audio con gTTS
                tts = gTTS(text=res['audio_script'], lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                audio_b64 = base64.b64encode(fp.getvalue()).decode()
                
                # Crear nueva fila para el historial
                nueva_fila = {
                    "archivo_hash": file_hash,
                    "fecha_guardado": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "categoria": categoria,
                    "periodo": res['periodo'],
                    "compania": res['compania'],
                    "total_pagar": res['total'],
                    "consumo_principal": res['consumo_valor'],
                    "unidad": res['unidad_medida'],
                    "resumen_didactico": res['explicacion_sencilla'],
                    "audio_b64": audio_b64
                }
                
                # Guardar en CSV de forma segura
                hist_actual = pd.concat([hist_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
                hist_actual.to_csv(HISTORIAL_CSV, index=False)
                data = nueva_fila
            else:
                st.error("No hemos podido interpretar esta factura. Inténtalo de nuevo.")
                st.stop()

    # MOSTRAR RESULTADO DEL ANÁLISIS ACTUAL
    st.markdown(f"""
    <div class='panel'>
        <div class='badge badge-{data['categoria'].lower()}'>{data['categoria']}</div>
        <h2>{data['total_pagar']} €</h2>
        <p><b>Compañía:</b> {data['compania']}<br>
        <b>Periodo:</b> {data['periodo']}<br>
        <b>Consumo:</b> {data['consumo_principal']} {data['unidad']}</p>
        <hr style='border: 0; border-top: 1px solid var(--line); margin: 20px 0;'>
        <p style='font-size: 1.1rem; line-height: 1.5;'>{data['resumen_didactico']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Reproductor de Audio accesible
    st.audio(base64.b64decode(data['audio_b64']), format="audio/mp3")

# =============================================================================
# VISUALIZACIÓN DEL HISTORIAL POR CATEGORÍAS
# =============================================================================

st.markdown("<hr style='margin: 40px 0;'>", unsafe_allow_html=True)
st.subheader("Tu Histórico")

hist_disp = asegurar_columnas_historial(cargar_historial())

if not hist_disp.empty:
    # Ordenar por fecha más reciente
    hist_disp = hist_disp.sort_values("fecha_guardado", ascending=False)
    
    # Creación de pestañas para organizar por tipo de suministro
    tab_luz, tab_agua, tab_gas, tab_otros = st.tabs(["💡 Luz", "💧 Agua", "🔥 Gas", "📂 Otros"])
    
    def renderizar_lista_categoria(df_cat):
        """Renderiza una lista simplificada para cada categoría."""
        if df_cat.empty:
            st.write("No hay facturas en esta categoría.")
        else:
            for _, fila in df_cat.iterrows():
                with st.expander(f"{fila['fecha_guardado']} - {fila['compania']} ({fila['total_pagar']} €)"):
                    st.write(f"**Periodo:** {fila['periodo']}")
                    st.write(f"**Consumo:** {fila['consumo_principal']} {fila['unidad']}")
                    st.write(fila['resumen_didactico'])
                    st.audio(base64.b64decode(fila['audio_b64']), format="audio/mp3")

    with tab_luz:
        renderizar_lista_categoria(hist_disp[hist_disp['categoria'] == 'Luz'])
    
    with tab_agua:
        renderizar_lista_categoria(hist_disp[hist_disp['categoria'] == 'Agua'])
        
    with tab_gas:
        renderizar_lista_categoria(hist_disp[hist_disp['categoria'] == 'Gas'])
        
    with tab_otros:
        renderizar_lista_categoria(hist_disp[hist_disp['categoria'] == 'Otros'])
else:
    st.info("Aún no tienes facturas guardadas. Sube la primera para empezar tu histórico.")

# =============================================================================
# BOTONES DE ACCIÓN FINAL
# =============================================================================
if not hist_disp.empty:
    st.download_button(
        label="Exportar datos a Excel/CSV",
        data=hist_disp.to_csv(index=False).encode('utf-8'),
        file_name="historial_recibozen.csv",
        mime="text/csv",
    )
