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

st.set_page_config(page_title="ReciboZen", page_icon="🧾", layout="centered")

HISTORIAL_CSV = "recibozen_historial.csv"

API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    st.error("Falta configurar GOOGLE_API_KEY en Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@700;800&display=swap');

    :root {
        --bg: #eef5fb;
        --surface: rgba(255,255,255,.96);
        --surface-2: #ffffff;
        --line: rgba(18,48,70,.12);
        --text: #123046;
        --muted: #486171;
        --primary: #0f5fa6;
        --primary-2: #1f7dcb;
        --primary-soft: #eaf4ff;
        --danger: #9b2c2c;
        --shadow: 0 14px 34px rgba(18,48,70,.08);
        --radius: 22px;
    }

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: linear-gradient(180deg, #f3f8fc 0%, #eef5fb 100%) !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        padding-top: 1.2rem;
    }

    .block-container {
        max-width: 840px;
        padding-top: 0.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4, p, span, label, div {
        color: var(--text);
    }

    .rz-header {
        background: var(--surface);
        border: 1px solid var(--line);
        box-shadow: var(--shadow);
        border-radius: 26px;
        padding: 1.25rem 1.25rem 1rem 1.25rem;
        margin-bottom: 1rem;
    }

    .rz-header img {
        display: block;
        width: min(100%, 360px);
        height: auto;
        filter: none !important;
        opacity: 1 !important;
    }

    .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 24px;
        box-shadow: var(--shadow);
        padding: 1.15rem;
        margin: 0 0 1rem 0;
    }

    .section-title {
        font-family: 'Manrope', sans-serif;
        font-size: 1.12rem;
        font-weight: 800;
        margin: 0 0 .85rem 0;
        color: var(--text);
    }

    .hint {
        margin-top: .6rem;
        color: var(--muted);
        font-size: .98rem;
    }

    .data-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .8rem;
    }

    .data-card {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: .95rem 1rem;
    }

    .data-label {
        font-size: .85rem;
        color: var(--muted);
        margin-bottom: .22rem;
    }

    .data-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text);
    }

    .spinner-card {
        display:flex;
        align-items:center;
        gap:.85rem;
        background: linear-gradient(180deg, #f5fbff 0%, #edf6ff 100%);
        border:1px solid rgba(15,95,166,.16);
        border-radius:18px;
        padding:1rem 1.05rem;
        box-shadow:0 8px 18px rgba(15,95,166,.08);
        margin-top:.25rem;
        margin-bottom:1rem;
    }

    .spinner-dot {
        width:18px;
        height:18px;
        border-radius:50%;
        border:3px solid rgba(15,95,166,.18);
        border-top-color: var(--primary);
        animation: rzspin 1s linear infinite;
        flex:0 0 auto;
    }

    @keyframes rzspin { to { transform: rotate(360deg);} }

    .spinner-copy strong {
        display:block;
        font-size:1rem;
        color:var(--text);
    }

    .spinner-copy span {
        display:block;
        font-size:.95rem;
        color:var(--muted);
        margin-top:.15rem;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFileUploader button,
    [data-testid="stBaseButton-primary"],
    .stButton > button[kind="primary"] {
        width: 100% !important;
        min-height: 54px !important;
        border-radius: 18px !important;
        font-size: 1rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        text-shadow: 0 1px 1px rgba(0,0,0,.22) !important;
        background: linear-gradient(180deg, var(--primary-2) 0%, var(--primary) 100%) !important;
        border: none !important;
        box-shadow: 0 12px 28px rgba(15,95,166,.22) !important;
    }

    .stButton > button *,
    .stDownloadButton > button *,
    .stFileUploader button *,
    [data-testid="stBaseButton-primary"] *,
    .stButton > button[kind="primary"] * {
        color:#ffffff !important;
        fill:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFileUploader button:hover,
    [data-testid="stBaseButton-primary"]:hover,
    .stButton > button[kind="primary"]:hover {
        filter: brightness(1.03);
        transform: translateY(-1px);
    }

    .stButton > button:focus,
    .stDownloadButton > button:focus,
    .stFileUploader button:focus {
        outline: 3px solid rgba(31,125,203,.22) !important;
        outline-offset: 2px !important;
    }

    .stFileUploader section {
        background: #f8fbfe !important;
        border: 2px dashed rgba(31,125,203,.22) !important;
        border-radius: 24px !important;
        padding: 1rem !important;
    }

    .stFileUploader small,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div > small {
        display: none !important;
    }

    [data-testid="stFileUploaderDropzoneInstructions"] div {
        color: var(--muted) !important;
    }

    [data-testid="stMetric"] {
        background: var(--surface-2);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: .8rem .95rem;
        box-shadow: 0 8px 20px rgba(18,48,70,.05);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--text) !important;
        font-weight: 800 !important;
    }

    .audio-panel {
        background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1rem;
        box-shadow: 0 12px 22px rgba(18,48,70,.05);
    }

    .audio-title {
        font-family: 'Manrope', sans-serif;
        font-size: 1.05rem;
        font-weight: 800;
        margin-bottom: .85rem;
    }

    .history-note {
        color: var(--muted);
        font-size: .95rem;
        margin-top: .55rem;
    }

    @media (max-width: 700px) {
        .data-grid { grid-template-columns: 1fr; }
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .rz-header { padding: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

LOGO_DATA_URI = "data:image/svg+xml;utf8,%3Csvg%20width%3D%22420%22%20height%3D%2296%22%20viewBox%3D%220%200%20420%2096%22%20fill%3D%22none%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20role%3D%22img%22%20aria-label%3D%22Logotipo%20de%20ReciboZen%22%3E%3Cdefs%3E%3ClinearGradient%20id%3D%22rzg%22%20x1%3D%2216%22%20y1%3D%2216%22%20x2%3D%2280%22%20y2%3D%2280%22%20gradientUnits%3D%22userSpaceOnUse%22%3E%3Cstop%20stop-color%3D%22%235BB7FF%22/%3E%3Cstop%20offset%3D%221%22%20stop-color%3D%22%231677C8%22/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect%20x%3D%228%22%20y%3D%228%22%20width%3D%2280%22%20height%3D%2280%22%20rx%3D%2224%22%20fill%3D%22%23EFF7FF%22/%3E%3Cpath%20d%3D%22M31%2032.5C31%2028.3579%2034.3579%2025%2038.5%2025H57.5C61.6421%2025%2065%2028.3579%2065%2032.5V63.5C65%2067.6421%2061.6421%2071%2057.5%2071H38.5C34.3579%2071%2031%2067.6421%2031%2063.5V32.5Z%22%20fill%3D%22url(%23rzg)%22/%3E%3Cpath%20d%3D%22M42.5%2041.5H53.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M42.5%2049.5H54.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.92%22/%3E%3Cpath%20d%3D%22M42.5%2057.5H50.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.86%22/%3E%3Cpath%20d%3D%22M66%2057C71.3333%2053.6667%2076.6667%2053.6667%2082%2057%22%20stroke%3D%22%237CC7FF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M66%2065C71.3333%2061.6667%2076.6667%2061.6667%2082%2065%22%20stroke%3D%22%23A6DBFF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Ctext%20x%3D%22108%22%20y%3D%2249%22%20fill%3D%22%23163042%22%20font-family%3D%22Manrope%2C%20Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2234%22%20font-weight%3D%22800%22%20letter-spacing%3D%22-0.02em%22%3EReciboZen%3C/text%3E%3Ctext%20x%3D%22110%22%20y%3D%2269%22%20fill%3D%22%236B8295%22%20font-family%3D%22Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2214%22%20font-weight%3D%22500%22%3ETu%20factura%20explicada%20con%20calma%3C/text%3E%3C/svg%3E"


def init_state():
    defaults = {
        "analisis_texto": None,
        "audio_b64": None,
        "reproducir": False,
        "factura_actual": None,
        "factura_anterior": None,
        "spinner_visible": False,
        "last_uploaded_name": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_current_results():
    st.session_state["analisis_texto"] = None
    st.session_state["audio_b64"] = None
    st.session_state["reproducir"] = False
    st.session_state["factura_actual"] = None
    st.session_state["spinner_visible"] = False


def leer_pdf(file):
    reader = PdfReader(file)
    textos = []
    for page in reader.pages:
        textos.append(page.extract_text() or "")
    return "\n".join(textos)


def preparar_audio(texto):
    tts = gTTS(text=texto, lang="es", slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()


def limpiar_numero(texto):
    if texto is None:
        return None
    t = str(texto).strip().replace("€", "").replace("EUR", "")
    t = t.replace("kWh", "").replace("kW", "")
    t = t.replace(".", "").replace(",", ".")
    nums = re.findall(r"-?\d+(?:\.\d+)?", t)
    if not nums:
        return None
    try:
        return float(nums[0])
    except Exception:
        return None


def parsear_bloques(texto):
    resultado = {
        "periodo": "No detectado",
        "compania": "No detectada",
        "total_pagar": "No detectado",
        "consumo_kwh": "No detectado",
        "potencia_kw": "No detectado",
        "impuestos": "No detectado",
        "explicacion_total": "Importe final de la factura.",
        "explicacion_consumo": "Energía usada durante el periodo.",
        "explicacion_potencia": "Parte fija por la potencia que tienes contratada.",
        "explicacion_impuestos": "Cargos e impuestos aplicados en la factura.",
        "resumen_visual": texto.strip(),
        "guion_audio": "Hola. Aquí tienes un resumen sencillo de tu factura.",
    }
    claves = {
        "periodo": ["periodo", "periodo_factura"],
        "compania": ["compania", "compañia", "empresa", "comercializadora"],
        "total_pagar": ["total", "total_pagar", "importe_total"],
        "consumo_kwh": ["consumo", "consumo_kwh"],
        "potencia_kw": ["potencia", "potencia_kw"],
        "impuestos": ["impuestos"],
        "explicacion_total": ["explicacion_total"],
        "explicacion_consumo": ["explicacion_consumo"],
        "explicacion_potencia": ["explicacion_potencia"],
        "explicacion_impuestos": ["explicacion_impuestos"],
        "guion_audio": ["guion_audio", "audio"],
    }
    for line in texto.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().lower().replace(" ", "_")
        val = v.strip()
        for destino, aliases in claves.items():
            if key in aliases and val:
                resultado[destino] = val
                break
    return resultado


def cargar_historial():
    if os.path.exists(HISTORIAL_CSV):
        try:
            return pd.read_csv(HISTORIAL_CSV)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def guardar_historial(factura):
    fila = {
        "fecha_guardado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "periodo": factura.get("periodo", "No detectado"),
        "compania": factura.get("compania", "No detectada"),
        "total_pagar": limpiar_numero(factura.get("total_pagar")),
        "consumo_kwh": limpiar_numero(factura.get("consumo_kwh")),
        "potencia_kw": limpiar_numero(factura.get("potencia_kw")),
        "impuestos": limpiar_numero(factura.get("impuestos")),
    }
    df_prev = cargar_historial()
    df_new = pd.concat([df_prev, pd.DataFrame([fila])], ignore_index=True)
    df_new.to_csv(HISTORIAL_CSV, index=False)
    return df_new


def fmt_euro(valor):
    if valor is None or valor == "No detectado":
        return "No detectado"
    n = limpiar_numero(valor)
    if n is None:
        return str(valor)
    return f"{n:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_num(valor, sufijo=""):
    if valor is None or valor == "No detectado":
        return "No detectado"
    n = limpiar_numero(valor)
    if n is None:
        return str(valor)
    return f"{n:,.2f} {sufijo}".replace(",", "X").replace(".", ",").replace("X", ".").strip()


def calcular_delta(actual, previo, sufijo="€"):
    a = limpiar_numero(actual)
    b = limpiar_numero(previo)
    if a is None or b is None:
        return None
    diff = a - b
    signo = "+" if diff > 0 else ""
    return f"{signo}{diff:,.2f} {sufijo}".replace(",", "X").replace(".", ",").replace("X", ".")


init_state()

st.markdown(f'<div class="rz-header"><img src="{LOGO_DATA_URI}" alt="ReciboZen"></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Sube tu factura", type=["pdf"], help="Sube un PDF de tu factura para analizarlo")

if uploaded_file is not None:
    if st.session_state.get("last_uploaded_name") != uploaded_file.name:
        reset_current_results()
        st.session_state["last_uploaded_name"] = uploaded_file.name

st.markdown('<div class="hint">Sube un PDF de tu factura para analizarlo.</div>', unsafe_allow_html=True)

analizar = st.button("Analizar factura", type="primary", use_container_width=True)

spinner_placeholder = st.empty()
if st.session_state.get("spinner_visible"):
    spinner_placeholder.markdown(
        '''<div class="spinner-card"><div class="spinner-dot"></div><div class="spinner-copy"><strong>Analizando factura…</strong><span>Esto puede tardar unos segundos.</span></div></div>''',
        unsafe_allow_html=True,
    )
else:
    spinner_placeholder.empty()

if uploaded_file and analizar:
    st.session_state["spinner_visible"] = True
    spinner_placeholder.markdown(
        '''<div class="spinner-card"><div class="spinner-dot"></div><div class="spinner-copy"><strong>Analizando factura…</strong><span>Esto puede tardar unos segundos.</span></div></div>''',
        unsafe_allow_html=True,
    )
    try:
        time.sleep(0.4)
        texto_raw = leer_pdf(uploaded_file)
        prompt = f"""
Eres ReciboZen. Analiza una factura para personas mayores o con poca familiaridad con términos energéticos.
Responde SOLO con líneas clave: valor.

periodo:
compania:
total_pagar:
consumo_kwh:
potencia_kw:
impuestos:
explicacion_total:
explicacion_consumo:
explicacion_potencia:
explicacion_impuestos:
guion_audio:

Reglas:
- Español de lectura fácil.
- Frases muy cortas.
- Sin markdown.
- guion_audio máximo 70 palabras y tono amable.

Factura:
{texto_raw[:12000]}
        """
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        parsed = parsear_bloques(response.text)
        st.session_state["factura_actual"] = parsed
        st.session_state["analisis_texto"] = response.text
        st.session_state["audio_b64"] = preparar_audio(parsed.get("guion_audio", "Resumen de la factura."))
        historial = guardar_historial(parsed)
        if len(historial) >= 2:
            prev = historial.iloc[-2].to_dict()
            st.session_state["factura_anterior"] = prev
        else:
            st.session_state["factura_anterior"] = None
    except Exception as e:
        st.error(f"No se pudo analizar la factura: {e}")
    finally:
        st.session_state["spinner_visible"] = False
        spinner_placeholder.empty()

factura = st.session_state.get("factura_actual")
anterior = st.session_state.get("factura_anterior")

if factura:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Datos de esta factura</div>', unsafe_allow_html=True)
    st.markdown(
        f'''
        <div class="data-grid">
            <div class="data-card"><div class="data-label">Periodo</div><div class="data-value">{factura.get("periodo", "No detectado")}</div></div>
            <div class="data-card"><div class="data-label">Compañía</div><div class="data-value">{factura.get("compania", "No detectada")}</div></div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "Total a pagar",
            fmt_euro(factura.get("total_pagar")),
            delta=calcular_delta(factura.get("total_pagar"), anterior.get("total_pagar") if anterior else None, "€") if anterior else None,
            help=factura.get("explicacion_total", "Importe final de la factura."),
            border=True,
        )
        st.metric(
            "Consumo",
            fmt_num(factura.get("consumo_kwh"), "kWh"),
            delta=calcular_delta(factura.get("consumo_kwh"), anterior.get("consumo_kwh") if anterior else None, "kWh") if anterior else None,
            help=factura.get("explicacion_consumo", "Energía usada durante el periodo."),
            border=True,
        )
    with c2:
        st.metric(
            "Potencia contratada",
            fmt_num(factura.get("potencia_kw"), "kW"),
            delta=calcular_delta(factura.get("potencia_kw"), anterior.get("potencia_kw") if anterior else None, "kW") if anterior else None,
            help=factura.get("explicacion_potencia", "Parte fija por la potencia contratada."),
            border=True,
        )
        st.metric(
            "Impuestos",
            fmt_euro(factura.get("impuestos")),
            delta=calcular_delta(factura.get("impuestos"), anterior.get("impuestos") if anterior else None, "€") if anterior else None,
            help=factura.get("explicacion_impuestos", "Cargos e impuestos aplicados."),
            border=True,
        )

    st.markdown('<div class="audio-panel">', unsafe_allow_html=True)
    st.markdown('<div class="audio-title">Escuchar resumen</div>', unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        if st.button("Escuchar", use_container_width=True):
            st.session_state["reproducir"] = True
    with a2:
        if st.button("Parar", use_container_width=True):
            st.session_state["reproducir"] = False
    if st.session_state.get("reproducir") and st.session_state.get("audio_b64"):
        st.components.v1.html(
            f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>',
            height=0,
        )
    st.markdown('</div>', unsafe_allow_html=True)

hist = cargar_historial()
if not hist.empty:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Historial</div>', unsafe_allow_html=True)
    show = hist.copy()
    st.dataframe(show.sort_index(ascending=False), use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar historial facturas",
        data=hist.to_csv(index=False).encode("utf-8"),
        file_name="recibozen_historial.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if st.button("Borrar historial", use_container_width=True):
        if os.path.exists(HISTORIAL_CSV):
            os.remove(HISTORIAL_CSV)
        st.session_state["factura_anterior"] = None
        st.success("Historial borrado correctamente.")
        st.rerun()
    st.markdown('<div class="history-note">Aquí puedes comparar tus facturas guardadas y descargar el historial.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
