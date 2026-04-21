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

st.set_page_config(page_title="ReciboZen", page_icon="🧾", layout="centered")

HISTORIAL_CSV = "recibozen_historial.csv"
API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    st.error("Falta configurar GOOGLE_API_KEY en Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODELOS_ANALISIS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

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
  --danger-2: #e45757;
  --shadow: 0 14px 34px rgba(18,48,70,.08);
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background: linear-gradient(180deg, #f3f8fc 0%, #eef5fb 100%) !important;
  color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
}
.block-container { max-width: 840px; padding-top: 2.2rem; padding-bottom: 3rem; }
.rz-header, .panel { background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 24px; padding: 1.15rem; margin-bottom: 1rem; overflow: visible; }
.rz-header { margin-top: .85rem; }
.rz-header img { display:block; width:min(100%,360px); height:auto; }
.section-title { font-family:'Manrope',sans-serif; font-size:1.12rem; font-weight:800; margin:0 0 .85rem 0; }
.hint { margin-top:.6rem; color:var(--muted); font-size:.98rem; }
.data-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.85rem; }
.data-card, .metric-card { background:#fff; border:1px solid var(--line); border-radius:20px; padding:1rem .95rem; box-shadow:0 8px 20px rgba(18,48,70,.05); }
.data-label, .metric-label { font-size:.92rem; color:var(--muted); margin-bottom:.28rem; }
.data-value { font-size:1.05rem; font-weight:700; color:var(--text); }
.metric-head { display:flex; align-items:center; gap:.45rem; margin-bottom:.35rem; }
.metric-value { font-size:2rem; line-height:1.05; font-weight:800; color:var(--text); letter-spacing:-.02em; }
.metric-delta { margin-top:.45rem; color:var(--muted); font-size:.92rem; font-weight:600; }
.tooltip-wrap { position:relative; display:inline-flex; align-items:center; }
.tooltip-icon { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:999px; border:1px solid rgba(15,95,166,.24); background:#eef6ff; color:var(--primary); font-size:.82rem; font-weight:800; cursor:help; box-shadow:0 3px 8px rgba(15,95,166,.08); }
.tooltip-bubble { position:absolute; left:0; top:calc(100% + 8px); width:min(290px,78vw); z-index:60; background:#123046; color:#ffffff !important; padding:.9rem 1rem; border-radius:14px; box-shadow:0 16px 32px rgba(18,48,70,.22); font-size:.93rem; line-height:1.46; opacity:0; visibility:hidden; transform:translateY(4px); transition:all .16s ease; pointer-events:none; }
.tooltip-wrap:hover .tooltip-bubble, .tooltip-wrap:focus-within .tooltip-bubble, .tooltip-wrap:active .tooltip-bubble { opacity:1; visibility:visible; transform:translateY(0); }
.tooltip-bubble::before { content:""; position:absolute; top:-6px; left:12px; width:12px; height:12px; background:#123046; transform:rotate(45deg); }
.spinner-card { display:flex; align-items:center; gap:.85rem; background:linear-gradient(180deg,#f5fbff 0%,#edf6ff 100%); border:1px solid rgba(15,95,166,.16); border-radius:18px; padding:1rem 1.05rem; margin-bottom:1rem; }
.spinner-dot { width:18px; height:18px; border-radius:50%; border:3px solid rgba(15,95,166,.18); border-top-color:var(--primary); animation:rzspin 1s linear infinite; }
@keyframes rzspin { to { transform:rotate(360deg); } }
.stDownloadButton button, .stFileUploader button { width:100% !important; min-height:54px !important; border-radius:18px !important; font-size:1rem !important; font-weight:800 !important; color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; text-shadow:0 1px 1px rgba(0,0,0,.22) !important; background:linear-gradient(180deg,var(--primary-2) 0%,var(--primary) 100%) !important; border:none !important; box-shadow:0 12px 28px rgba(15,95,166,.22) !important; margin-top:0 !important; margin-bottom:0 !important; }
.stButton > button { width:100% !important; min-height:54px !important; border-radius:18px !important; font-size:1rem !important; font-weight:800 !important; color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; text-shadow:0 1px 1px rgba(0,0,0,.22) !important; background:linear-gradient(180deg,var(--primary-2) 0%,var(--primary) 100%) !important; border:none !important; box-shadow:0 12px 28px rgba(15,95,166,.22) !important; margin-top:0 !important; margin-bottom:0 !important; }
button[kind="primary"] { background:linear-gradient(180deg,var(--primary-2) 0%,var(--primary) 100%) !important; box-shadow:0 12px 28px rgba(15,95,166,.22) !important; }
button[data-testid="baseButton-btn_parar"] { background:linear-gradient(180deg,var(--danger-2) 0%,var(--danger) 100%) !important; box-shadow:0 12px 28px rgba(183,28,28,.28) !important; color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; }
.audio-actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; align-items:stretch; margin-top:.25rem; }
.audio-actions div { min-width:0; }
.audio-actions .stButton { height:100%; }
.audio-actions .stButton button { height:54px !important; }
.stFileUploader section { background:#f8fbfe !important; border:2px dashed rgba(31,125,203,.22) !important; border-radius:24px !important; padding:1rem !important; }
.stFileUploader small, .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] div small, .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] div:first-child, .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] svg { display:none !important; }
.audio-panel { background:linear-gradient(180deg,#ffffff 0%,#f7fbff 100%); border:1px solid var(--line); border-radius:22px; padding:1rem; box-shadow:0 12px 22px rgba(18,48,70,.05); }
.audio-title { font-family:'Manrope',sans-serif; font-size:1.05rem; font-weight:800; margin-bottom:.85rem; }
.history-table { overflow-x:auto; margin-top:.4rem; }
.history-table table { width:100%; border-collapse:collapse; font-size:.93rem; background:#fff; overflow:hidden; border-radius:16px; table-layout:fixed; }
.history-table thead th { text-align:left; background:#f4f8fc; color:#123046; padding:.8rem .75rem; border-bottom:1px solid var(--line); font-weight:800; }
.history-table tbody td { padding:.78rem .75rem; border-bottom:1px solid rgba(18,48,70,.08); color:#123046; vertical-align:top; }
.history-table tbody tr:last-child td { border-bottom:none; }
.history-note { margin-top:.55rem; margin-bottom:1rem; color:var(--muted); font-size:.93rem; }
.col-fecha { width:132px; white-space:nowrap; }
.col-periodo { width:180px; }
.col-compania { width:90px; }
.col-total { width:110px; }
.col-consumo { width:110px; }
.col-potencia { width:92px; }
.col-impuestos { width:96px; }
.row-action { display:block; width:100%; min-height:38px; border-radius:12px; border:none; background:linear-gradient(180deg,#35b56a 0%,#1f8f50 100%); color:#ffffff !important; text-align:center; font:inherit; font-weight:700; padding:.45rem .55rem; cursor:pointer; text-decoration:none !important; box-shadow:0 10px 22px rgba(31,143,80,.22); white-space:nowrap; }
.row-action:hover { filter:brightness(1.03); }
.history-danger-wrap { margin-top: 1rem; }
.history-danger-btn { display:block; width:100%; text-align:center; padding: .95rem 1rem; border-radius:18px; font-size:1rem; font-weight:800; color:#ffffff !important; text-decoration:none !important; background:linear-gradient(180deg,var(--danger-2) 0%,var(--danger) 100%); box-shadow:0 12px 28px rgba(183,28,28,.28); }
@media (max-width:700px) { .data-grid { grid-template-columns:1fr; } .audio-actions { grid-template-columns:1fr; } }
</style>
""",
    unsafe_allow_html=True,
)

LOGO_DATA_URI = "data:image/svg+xml;utf8,%3Csvg%20width%3D%22420%22%20height%3D%2296%22%20viewBox%3D%220%200%20420%2096%22%20fill%3D%22none%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20role%3D%22img%22%20aria-label%3D%22Logotipo%20de%20ReciboZen%22%3E%3Cdefs%3E%3ClinearGradient%20id%3D%22rzg%22%20x1%3D%2216%22%20y1%3D%2216%22%20x2%3D%2280%22%20y2%3D%2280%22%20gradientUnits%3D%22userSpaceOnUse%22%3E%3Cstop%20stop-color%3D%22%235BB7FF%22/%3E%3Cstop%20offset%3D%221%22%20stop-color%3D%22%231677C8%22/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect%20x%3D%228%22%20y%3D%228%22%20width%3D%2280%22%20height%3D%2280%22%20rx%3D%2224%22%20fill%3D%22%23EFF7FF%22/%3E%3Cpath%20d%3D%22M31%2032.5C31%2028.3579%2034.3579%2025%2038.5%2025H57.5C61.6421%2025%2065%2028.3579%2065%2032.5V63.5C65%2067.6421%2061.6421%2071%2057.5%2071H38.5C34.3579%2071%2031%2067.6421%2031%2063.5V32.5Z%22%20fill%3D%22url(%23rzg)%22/%3E%3Cpath%20d%3D%22M42.5%2041.5H53.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M42.5%2049.5H54.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.92%22/%3E%3Cpath%20d%3D%22M42.5%2057.5H50.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.86%22/%3E%3Cpath%20d%3D%22M66%2057C71.3333%2053.6667%2076.6667%2053.6667%2082%2057%22%20stroke%3D%22%237CC7FF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M66%2065C71.3333%2061.6667%2076.6667%2061.6667%2082%2065%22%20stroke%3D%22%23A6DBFF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Ctext%20x%3D%22108%22%20y%3D%2249%22%20fill%3D%22%23163042%22%20font-family%3D%22Manrope%2C%20Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2234%22%20font-weight%3D%22800%22%20letter-spacing%3D%22-0.02em%22%3EReciboZen%3C/text%3E%3Ctext%20x%3D%22110%22%20y%3D%2269%22%20fill%3D%22%236B8295%22%20font-family%3D%22Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2214%22%20font-weight%3D%22500%22%3ETu%20factura%20explicada%20con%20calma%3C/text%3E%3C/svg%3E"


def init_state():
    defaults = {
        "audio_b64": None,
        "reproducir": False,
        "factura_actual": None,
        "factura_anterior": None,
        "last_uploaded_name": None,
        "last_file_hash": None,
        "borrar_historial_click": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:  # <- importante que sea "if k not in"
            st.session_state[k] = v


def reset_current_results():
    st.session_state["audio_b64"] = None
    st.session_state["reproducir"] = False
    st.session_state["factura_actual"] = None


def leer_pdf(file):
    reader = PdfReader(file)
    return "\n".join([(page.extract_text() or "") for page in reader.pages])


def obtener_hash_archivo(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        contenido = uploaded_file.getvalue()
    except Exception:
        return None

    nombre = getattr(uploaded_file, "name", "") or ""
    tamano = len(contenido)

    base = nombre.encode("utf-8") + b"||" + str(tamano).encode("utf-8") + b"||" + contenido
    return hashlib.sha256(base).hexdigest()


def preparar_audio(texto):
    tts = gTTS(text=texto, lang="es", slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()


def limpiar_numero(texto):
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    t = t.replace("€", "").replace("EUR", "").replace("kWh", "").replace("kW", "").replace(" ", "")
    m = re.search(r"-?\d+[\.,]?\d*", t)
    if not m:
        return None
    num = m.group(0)
    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return float(num)
    except Exception:
        return None


def normalizar_compania(texto):
    t = (texto or "").strip()
    low = t.lower()
    if any(x in low for x in ["visalia", "domestica gas y electricidad", "doméstica gas y electricidad"]):
        return "Visalia"
    if not t:
        return "No detectada"
    return re.sub(r"\s+", " ", t)


def normalizar_periodo_corto(periodo):
    import calendar
    import re

    if not periodo or str(periodo).strip().lower() == "no detectado":
        return "No detectado"

    t = re.sub(r"\s+", " ", str(periodo)).strip()
    low = t.lower()

    meses = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
        "gen": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "mai": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "set": 9,
        "oct": 10,
        "nov": 11,
        "des": 12,
    }

    def fmt_fecha(dia, mes, anio):
        return f"{int(dia):02d}/{int(mes):02d}/{str(anio)[-2:]}"

    # 1) Caso: 08/01/2026 - 05/02/2026
    fechas = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", t)
    if len(fechas) >= 2:
        d1, m1, y1 = fechas[0]
        d2, m2, y2 = fechas[1]

        if len(y1) == 2:
            y1 = "20" + y1
        if len(y2) == 2:
            y2 = "20" + y2

        return f"{fmt_fecha(d1, m1, y1)} - {fmt_fecha(d2, m2, y2)}"

    # 2) Caso: 01 de marzo al 31 de marzo de 2026
    patron_dia_mes = r"(\d{1,2}) de ([a-záéíóú]+)(?: de (\d{4}))?"
    fechas_texto = re.findall(patron_dia_mes, low)

    if len(fechas_texto) >= 2:
        d1, mes1, y1 = fechas_texto[0]
        d2, mes2, y2 = fechas_texto[1]

        anio_final = y2 or y1
        y1 = y1 or anio_final
        y2 = y2 or anio_final

        m1 = meses.get(mes1)
        m2 = meses.get(mes2)

        if m1 and m2 and y1 and y2:
            return f"{fmt_fecha(d1, m1, y1)} - {fmt_fecha(d2, m2, y2)}"

    # 3) Caso: Marzo 2026
    patron_mes_anio = r"^([a-záéíóú]+)\s+(\d{4})$"
    m = re.match(patron_mes_anio, low)
    if m:
        mes_txt, anio = m.groups()
        mes_num = meses.get(mes_txt)
        if mes_num:
            ultimo_dia = calendar.monthrange(int(anio), mes_num)[1]
            return f"{fmt_fecha(1, mes_num, anio)} - {fmt_fecha(ultimo_dia, mes_num, anio)}"

    # 4) Caso: Noviembre 2025 a Febrero 2026
    patron_mes_a_mes = r"^([a-záéíóú]+)\s+(\d{4})\s+a\s+([a-záéíóú]+)\s+(\d{4})$"
    m = re.match(patron_mes_a_mes, low)
    if m:
        mes_ini_txt, anio_ini, mes_fin_txt, anio_fin = m.groups()
        mes_ini = meses.get(mes_ini_txt)
        mes_fin = meses.get(mes_fin_txt)

        if mes_ini and mes_fin:
            ultimo_dia = calendar.monthrange(int(anio_fin), mes_fin)[1]
            return f"{fmt_fecha(1, mes_ini, anio_ini)} - {fmt_fecha(ultimo_dia, mes_fin, anio_fin)}"

    # 5) Caso: Enero a Marzo de 2026
    patron_mes_a_mes_mismo_anio = r"^([a-záéíóú]+)\s+a\s+([a-záéíóú]+)\s+de\s+(\d{4})$"
    m = re.match(patron_mes_a_mes_mismo_anio, low)
    if m:
        mes_ini_txt, mes_fin_txt, anio = m.groups()
        mes_ini = meses.get(mes_ini_txt)
        mes_fin = meses.get(mes_fin_txt)

        if mes_ini and mes_fin:
            ultimo_dia = calendar.monthrange(int(anio), mes_fin)[1]
            return f"{fmt_fecha(1, mes_ini, anio)} - {fmt_fecha(ultimo_dia, mes_fin, anio)}"

    # 6) Caso catalán abreviado: Gen-Mar/26
    patron_cat_abrev = r"^([a-z]{3})[-/]([a-z]{3})/(\d{2,4})$"
    m = re.match(patron_cat_abrev, low)
    if m:
        mes_ini_txt, mes_fin_txt, anio = m.groups()
        if len(anio) == 2:
            anio = "20" + anio

        mes_ini = meses.get(mes_ini_txt)
        mes_fin = meses.get(mes_fin_txt)

        if mes_ini and mes_fin:
            ultimo_dia = calendar.monthrange(int(anio), mes_fin)[1]
            return f"{fmt_fecha(1, mes_ini, anio)} - {fmt_fecha(ultimo_dia, mes_fin, anio)}"

    return t

def fmt_fecha_corta(valor):
    if not valor:
        return ""
    t = str(valor).strip()
    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    except Exception:
        return t[:10]


def extraer_desde_pdf(texto_raw):
    data = {}

    # 1) Intento general con patrones habituales
    patterns = {
        "periodo": r"Periodo de facturaci[oó]n\s+([0-9]{2}[0-9/\- ]+[0-9]{2,4})",
        "total_pagar": r"Total\s+([0-9]+,[0-9]{2})",
        "consumo_kwh": r"Consumo total\s+([0-9]+,[0-9]{2})\s*kWh",
        "potencia_kw": r"Potencia contratada[\s\S]{0,80}?([0-9]+,[0-9]{2})\s*kW",
        "impuestos": r"IVA\s+([0-9]+,[0-9]{2})",
    }

    for key, pat in patterns.items():
        m = re.search(pat, texto_raw, flags=re.IGNORECASE)
        if m:
            data[key] = m.group(1).strip()

    # 2) Compañía conocida
    if re.search(r"visalia|dom[eé]stica gas y electricidad", texto_raw, flags=re.IGNORECASE):
        data["compania"] = "Visalia"

    # 3) PRIORIDAD: periodo a partir de lecturas reales (muy útil en agua)
    patron_lectura_anterior = r"LECTURA\s+ANTERIOR[\s\S]{0,80}?DATA[:\s]+(\d{1,2}/\d{1,2}/\d{4})"
    patron_lectura_actual = r"LECTURA\s+ACTUAL[\s\S]{0,80}?DATA[:\s]+(\d{1,2}/\d{1,2}/\d{4})"

    m_ant = re.search(patron_lectura_anterior, texto_raw, flags=re.IGNORECASE)
    m_act = re.search(patron_lectura_actual, texto_raw, flags=re.IGNORECASE)

    if m_ant and m_act:
        fecha_ant = m_ant.group(1).strip()
        fecha_act = m_act.group(1).strip()
        data["periodo"] = f"{fecha_ant} - {fecha_act}"
        return data

    # 4) Fallback: si aparecen al menos dos fechas completas cerca de lecturas/dates
    bloque_lecturas = re.search(
        r"(LECTURA\s+ANTERIOR[\s\S]{0,200}LECTURA\s+ACTUAL[\s\S]{0,200})",
        texto_raw,
        flags=re.IGNORECASE
    )
    if bloque_lecturas:
        fechas = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", bloque_lecturas.group(1))
        if len(fechas) >= 2:
            data["periodo"] = f"{fechas[0]} - {fechas[1]}"
            return data

    return data


def parsear_bloques(texto):
    resultado = {
        "periodo": "No detectado",
        "compania": "No detectada",
        "total_pagar": "No detectado",
        "consumo_kwh": "No detectado",
        "potencia_kw": "No detectado",
        "impuestos": "No detectado",
        "explicacion_total": "Es el importe final que pagas este mes. Aquí ya está sumado lo que has consumido, la parte fija y los impuestos.",
        "explicacion_consumo": "Es la energía que has usado durante este periodo. Si sube mucho, normalmente significa que has gastado más electricidad.",
        "explicacion_potencia": "Es la parte fija de la factura. La pagas aunque consumas poco, porque depende de la potencia que tienes contratada en casa.",
        "explicacion_impuestos": "Son los impuestos y cargos añadidos a la factura. No dependen solo de lo que consumes, también influyen normas y peajes.",
        "guion_audio": "Hola. Aquí tienes un resumen sencillo de tu factura.",
    }
    aliases = {
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
        for dest, keys in aliases.items():
            if key in keys and val:
                resultado[dest] = val
                break
    resultado["compania"] = normalizar_compania(resultado.get("compania"))
    return resultado


def combinar_datos(ia, pdf):
    merged = ia.copy()
    for key in ["periodo", "total_pagar", "consumo_kwh", "potencia_kw", "impuestos", "compania"]:
        if pdf.get(key):
            merged[key] = pdf[key]
    merged["compania"] = normalizar_compania(merged.get("compania"))
    return merged


# -------------------------------
# CATEGORÍA DE SUMINISTRO
# -------------------------------

def detectar_categoria_suministro(texto_raw, compania_normalizada):
    t = (texto_raw or "").lower()
    c = (compania_normalizada or "").lower()

    # Luz
    if any(x in c for x in ["visalia"]) or "kwh" in t or "potencia contratada" in t:
        return "Luz"

    # Agua
    if any(x in t for x in [
        "servei municipal d'aigües",
        "aqualia",
        "cicle de l'aigua",
        "clavegueram",
        "canon aigua",
        "tmtr",
        " m3 ",
        "consum d' aigua"
    ]):
        return "Agua"

    # Teléfono
    if any(x in t for x in [
        "pepephone",
        "pepemobile",
        "fibra 1000mb",
        "fibra 1gb",
        "línea móvil",
        "linea movil",
        "llamadas ilimitadas",
        "internet movil"
    ]):
        return "Teléfono"

    return "Otro"


# -------------------------------
# HISTORIAL EN CSV
# -------------------------------

def cargar_historial():
    if os.path.exists(HISTORIAL_CSV):
        try:
            df = pd.read_csv(HISTORIAL_CSV)
            if "compania" in df.columns:
                df["compania"] = df["compania"].apply(normalizar_compania)
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def asegurar_columnas_historial(df):
    columnas = {
        "archivo_hash": "",
        "fecha_guardado": "",
        "periodo": "No detectado",
        "compania": "No detectada",
        "categoria": "Otro",  # NUEVO
        "total_pagar": None,
        "consumo_kwh": None,
        "potencia_kw": None,
        "impuestos": None,
        "explicacion_total": "",
        "explicacion_consumo": "",
        "explicacion_potencia": "",
        "explicacion_impuestos": "",
        "guion_audio": "",
        "modelo_usado": "",
    }
    out = df.copy()
    for col, default in columnas.items():
        if col not in out.columns:
            out[col] = default
    if "compania" in out.columns:
        out["compania"] = out["compania"].apply(normalizar_compania)
    return out


def deduplicar_historial(df):
    if df.empty:
        return df

    tmp = asegurar_columnas_historial(df).copy()

    # Normalizamos campos para poder comparar bien
    tmp["archivo_hash"] = tmp["archivo_hash"].fillna("").astype(str).str.strip()
    tmp["periodo"] = tmp["periodo"].fillna("No detectado").astype(str).str.strip()
    tmp["compania"] = tmp["compania"].fillna("No detectada").apply(normalizar_compania)
    tmp["categoria"] = tmp["categoria"].fillna("Otro").astype(str).str.strip()

    # Fecha a datetime para quedarnos con la fila más reciente
    tmp["_fecha_dt"] = pd.to_datetime(tmp["fecha_guardado"], errors="coerce")

    # Campos auxiliares de comparación
    tmp["_hash_norm"] = tmp["archivo_hash"]
    tmp["_periodo_norm"] = tmp["periodo"].str.lower()
    tmp["_compania_norm"] = tmp["compania"].str.lower()
    tmp["_categoria_norm"] = tmp["categoria"].str.lower()
    tmp["_total_norm"] = pd.to_numeric(tmp["total_pagar"], errors="coerce").round(2)

    # Ordenamos por fecha para que el más reciente quede al final
    tmp = tmp.sort_values("_fecha_dt", ascending=True, na_position="last")

    # Si hay hash, deduplicamos por hash, quedándonos con la ÚLTIMA fila
    has_hash = tmp["_hash_norm"].ne("")
    con_hash = tmp[has_hash].drop_duplicates(subset=["_hash_norm"], keep="last")

    # Si no hay hash, usamos una combinación razonable y nos quedamos con la ÚLTIMA
    sin_hash = tmp[~has_hash].drop_duplicates(
        subset=["_periodo_norm", "_compania_norm", "_categoria_norm", "_total_norm"],
        keep="last"
    )

    tmp = pd.concat([con_hash, sin_hash], ignore_index=True)

    # Orden final del histórico: más reciente arriba
    tmp = tmp.sort_values("_fecha_dt", ascending=False, na_position="last").reset_index(drop=True)

    return tmp.drop(
        columns=[
            "_fecha_dt",
            "_hash_norm",
            "_periodo_norm",
            "_compania_norm",
            "_categoria_norm",
            "_total_norm",
        ],
        errors="ignore",
    )


def buscar_factura_por_hash(file_hash):
    df = deduplicar_historial(cargar_historial())
    if df.empty or "archivo_hash" not in df.columns:
        return None
    rows = df[df["archivo_hash"].astype(str) == str(file_hash)]
    if rows.empty:
        return None
    row = rows.iloc[0].to_dict()
    row["compania"] = normalizar_compania(row.get("compania"))
    return row


def fila_historial_a_factura(row):
    return {
        "periodo": row.get("periodo", "No detectado"),
        "compania": normalizar_compania(row.get("compania", "No detectada")),
        "categoria": row.get("categoria", "Otro"),
        "total_pagar": row.get("total_pagar", "No detectado"),
        "consumo_kwh": row.get("consumo_kwh", "No detectado"),
        "potencia_kw": row.get("potencia_kw", "No detectado"),
        "impuestos": row.get("impuestos", "No detectado"),
        "explicacion_total": row.get("explicacion_total", ""),
        "explicacion_consumo": row.get("explicacion_consumo", ""),
        "explicacion_potencia": row.get("explicacion_potencia", ""),
        "explicacion_impuestos": row.get("explicacion_impuestos", ""),
        "guion_audio": row.get("guion_audio", ""),
        "modelo_usado": row.get("modelo_usado", "historial"),
        "archivo_hash": row.get("archivo_hash", ""),
    }



def guardar_historial(factura, archivo_hash, texto_raw=None):
    compania_norm = normalizar_compania(factura.get("compania", "No detectada"))
    categoria = detectar_categoria_suministro(texto_raw or "", compania_norm)

    fila = {
        "archivo_hash": archivo_hash,
        "fecha_guardado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "periodo": factura.get("periodo", "No detectado"),
        "compania": compania_norm,
        "categoria": categoria,
        "total_pagar": limpiar_numero(factura.get("total_pagar")),
        "consumo_kwh": limpiar_numero(factura.get("consumo_kwh")),
        "potencia_kw": limpiar_numero(factura.get("potencia_kw")),
        "impuestos": limpiar_numero(factura.get("impuestos")),
        "explicacion_total": factura.get("explicacion_total", ""),
        "explicacion_consumo": factura.get("explicacion_consumo", ""),
        "explicacion_potencia": factura.get("explicacion_potencia", ""),
        "explicacion_impuestos": factura.get("explicacion_impuestos", ""),
        "guion_audio": factura.get("guion_audio", ""),
        "modelo_usado": factura.get("modelo_usado", ""),
    }

    df_prev = asegurar_columnas_historial(cargar_historial())
    df_new = pd.concat([df_prev, pd.DataFrame([fila])], ignore_index=True)

    df_new.to_csv(HISTORIAL_CSV, index=False)
    return df_new





def fmt_euro(valor):
    n = limpiar_numero(valor)
    if n is None:
        return "No detectado"
    return f"{n:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_num(valor, sufijo=""):
    n = limpiar_numero(valor)
    if n is None:
        return "No detectado"
    return f"{n:,.2f} {sufijo}".replace(",", "X").replace(".", ",").replace("X", ".").strip()


def calcular_delta(actual, previo, sufijo="€"):
    a = limpiar_numero(actual)
    b = limpiar_numero(previo)
    if a is None or b is None:
        return None
    d = a - b
    sign = "+" if d > 0 else ""
    return f"{sign}{d:,.2f} {sufijo}".replace(",", "X").replace(".", ",").replace("X", ".")


def esc(texto):
    return str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')


def es_error_temporal_modelo(error):
    msg = str(error).upper()
    patrones = ["503", "UNAVAILABLE", "HIGH DEMAND", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED", "SERVICE UNAVAILABLE", "TOO MANY REQUESTS", "429"]
    return any(p in msg for p in patrones)


def construir_prompt(texto_raw):
    return f"""
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
- español de lectura fácil
- frases muy cortas
- sin markdown
- tooltips explicativos pero breves
- si no ves un dato, escribe No detectado

Factura:
{texto_raw[:12000]}
"""


def generar_con_fallback(prompt, modelos=None, reintentos_por_modelo=2):
    modelos = modelos or MODELOS_ANALISIS
    status = st.empty()
    ultimo_error = None
    for modelo in modelos:
        for intento in range(reintentos_por_modelo):
            try:
                status.markdown(f"<div class='hint'>Analizando con IA ({modelo})...</div>", unsafe_allow_html=True)
                response = client.models.generate_content(model=modelo, contents=prompt)
                status.empty()
                return response, modelo
            except Exception as e:
                ultimo_error = e
                if not es_error_temporal_modelo(e):
                    status.empty()
                    raise RuntimeError(f"ERROR_IA: {e}")
                espera = min(2 ** intento, 6)
                status.markdown(f"<div class='hint'>Servicio temporalmente no disponible en {modelo}. Reintentando en {espera} s...</div>", unsafe_allow_html=True)
                time.sleep(espera)
    status.empty()
    if es_error_temporal_modelo(ultimo_error):
        raise RuntimeError(f"ERROR_TEMPORAL_IA: {ultimo_error}")
    raise RuntimeError(f"ERROR_IA: {ultimo_error}")


def render_metric_card(label, value, tooltip, delta=None):
    delta_html = f"<div class='metric-delta'>Frente a la anterior: {esc(delta)}</div>" if delta else ""
    st.markdown(
        f"""
        <div class='metric-card'>
          <div class='metric-head'>
            <div class='metric-label'>{esc(label)}</div>
            <div class='tooltip-wrap' tabindex='0' aria-label='Más información sobre {esc(label)}'>
              <span class='tooltip-icon'>?</span>
              <div class='tooltip-bubble'>{esc(tooltip)}</div>
            </div>
          </div>
          <div class='metric-value'>{esc(value)}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------
# RENDER DEL HISTÓRICO
# -------------------------------

def render_history_table(df, titulo=None, mostrar_tipo=True):
    """
    Pinta una tabla de historial.
    - df: DataFrame ya filtrado.
    - titulo: texto opcional para mostrar encima de la tabla.
    - mostrar_tipo: si True, incluye la columna 'Tipo' (categoria).
    """
    df = asegurar_columnas_historial(df)

    if df.empty:
        if titulo:
            st.markdown(f"#### {titulo}")
        st.markdown("No hay facturas guardadas en esta sección.")
        return

    if titulo:
        st.markdown(f"#### {titulo}")

    # Siempre 6 columnas: Detalle, Periodo, Compañía, Tipo, Total, Consumo
    # Si mostrar_tipo es False, la columna Tipo se deja vacía
    for i, (_, row) in enumerate(df.iterrows()):
        hash_hist = str(row.get("archivo_hash", "") or "").strip()

        with st.container():
            cols = st.columns([1.0, 2.2, 1.8, 1.2, 1.2, 1.2])

            btn_key = f"hist_btn_{(titulo or 'global')}_{i}_{hash_hist}"

            # Columna 0: botón Detalle
            with cols[0]:
                if st.button("Detalle", key=btn_key, use_container_width=True):
                    factura_cargada = None

                    if hash_hist:
                        factura_hist = buscar_factura_por_hash(hash_hist)
                        if factura_hist:
                            factura_cargada = fila_historial_a_factura(factura_hist)

                    if not factura_cargada:
                        factura_cargada = fila_historial_a_factura(row.to_dict())

                    st.session_state["factura_actual"] = factura_cargada
                    st.session_state["last_file_hash"] = (
                        factura_cargada.get("archivo_hash", "") if factura_cargada else ""
                    )
                    st.session_state["audio_b64"] = preparar_audio(
                        (factura_cargada or {}).get("guion_audio", "Resumen de la factura.")
                    )
                    st.session_state["factura_anterior"] = None
                    st.rerun()

            # Columna 1: periodo
            with cols[1]:
                st.markdown(
                    f"**Periodo**<br>{normalizar_periodo_corto(row.get('periodo', ''))}",
                    unsafe_allow_html=True,
                )

            # Columna 2: compañía
            with cols[2]:
                st.markdown(
                    f"**Compañía**<br>{normalizar_compania(row.get('compania', ''))}",
                    unsafe_allow_html=True,
                )

            # Columna 3: tipo (o vacío si mostrar_tipo=False)
            with cols[3]:
                if mostrar_tipo:
                    tipo_txt = row.get("categoria", "Otro") or "Otro"
                    st.markdown(f"**Tipo**<br>{tipo_txt}", unsafe_allow_html=True)
                else:
                    st.markdown(" ", unsafe_allow_html=True)

            # Columna 4: total
            with cols[4]:
                st.markdown(
                    f"**Total**<br>{fmt_euro(row.get('total_pagar'))}",
                    unsafe_allow_html=True,
                )

            # Columna 5: consumo
            with cols[5]:
                st.markdown(
                    f"**Consumo**<br>{fmt_num(row.get('consumo_kwh'), 'kWh')}",
                    unsafe_allow_html=True,
                )

            st.markdown("---")


def render_historial_completo_y_por_secciones():
    """
    Muestra:
    - Una tabla única con todas las facturas (incluye columna Tipo).
    - Luego tablas separadas para Luz, Agua y Teléfono.
    """
    hist = asegurar_columnas_historial(cargar_historial())

    if hist.empty:
        st.markdown("No hay facturas guardadas todavía.")
        return

    hist_sorted = hist.sort_values("fecha_guardado", ascending=False).reset_index(drop=True)

    st.write("DEBUG total filas historial:", len(hist_sorted))
    st.write("DEBUG hashes historial:", hist_sorted["archivo_hash"].astype(str).tolist())

    render_history_table(hist_sorted, titulo="Histórico completo", mostrar_tipo=True)

    secciones = [
        ("Luz", "Facturas de Luz"),
        ("Agua", "Facturas de Agua"),
        ("Teléfono", "Facturas de Teléfono"),
    ]

    for categoria, titulo in secciones:
        sub = hist_sorted[hist_sorted["categoria"] == categoria]
        if sub.empty:
            continue
        st.markdown("---")
        render_history_table(sub, titulo=titulo, mostrar_tipo=False)


init_state()

query_params = st.query_params
if query_params.get("accion") == "borrar_historial":
    if os.path.exists(HISTORIAL_CSV):
        os.remove(HISTORIAL_CSV)
    st.session_state["factura_anterior"] = None
    reset_current_results()
    st.session_state["borrar_historial_click"] = True
    st.query_params.clear()

if query_params.get("accion") == "cargar_historial":
    hash_hist = query_params.get("hash", "")
    if hash_hist:
        factura_hist = buscar_factura_por_hash(hash_hist)
        if factura_hist:
            factura_cargada = fila_historial_a_factura(factura_hist)
            st.session_state["factura_actual"] = factura_cargada
            st.session_state["last_file_hash"] = factura_cargada.get("archivo_hash", "")
            st.session_state["audio_b64"] = preparar_audio(factura_cargada.get("guion_audio", "Resumen de la factura."))
            st.session_state["factura_anterior"] = None
    st.query_params.clear()

st.markdown(f"<div class='rz-header'><img src='{LOGO_DATA_URI}' alt='ReciboZen'></div>", unsafe_allow_html=True)

st.markdown("<div class='panel'><div class='section-title'>Sube tu factura</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Sube tu factura", label_visibility="collapsed", type=["pdf"])

current_file_hash = None

if uploaded_file is not None:
    current_file_hash = obtener_hash_archivo(uploaded_file)

    nombre_actual = getattr(uploaded_file, "name", "") or ""
    firma_actual = f"{nombre_actual}__{current_file_hash}"

    if st.session_state.get("last_uploaded_name") != firma_actual:
        reset_current_results()
        st.session_state["last_uploaded_name"] = firma_actual
        st.session_state["last_file_hash"] = current_file_hash

    st.write("DEBUG uploaded_file:", getattr(uploaded_file, "name", None))
    st.write("DEBUG current_file_hash:", current_file_hash)
else:
    st.write("DEBUG uploaded_file:", None)
    st.write("DEBUG current_file_hash:", None)

st.markdown("<div class='hint'>Sube un PDF de tu factura para analizarlo.</div></div>", unsafe_allow_html=True)

analizar = st.button("Analizar factura", type="primary", use_container_width=True)
spinner_placeholder = st.empty()

if uploaded_file and analizar:
    factura_guardada = buscar_factura_por_hash(current_file_hash)
    if factura_guardada:
        factura_cargada = fila_historial_a_factura(factura_guardada)
        st.session_state["factura_actual"] = factura_cargada
        st.session_state["audio_b64"] = preparar_audio(factura_cargada.get("guion_audio", "Resumen de la factura."))
        st.session_state["factura_anterior"] = None
        st.info("Esta factura ya estaba guardada. Se ha cargado desde el historial sin volver a consultar la IA.")
    else:
        spinner_placeholder.markdown(
            """
            <div class='spinner-card'>
              <div class='spinner-dot'></div>
              <div><strong>Analizando factura</strong><div style='color:#486171;margin-top:.15rem;'>Esto puede tardar unos segundos.</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        try:
            time.sleep(0.35)
            texto_raw = leer_pdf(uploaded_file)
            extraidos_pdf = extraer_desde_pdf(texto_raw)
            prompt = construir_prompt(texto_raw)
            response, modelo_usado = generar_con_fallback(prompt)
            parsed = parsear_bloques(getattr(response, "text", "") or "")
            parsed = combinar_datos(parsed, extraidos_pdf)
            parsed["modelo_usado"] = modelo_usado
            parsed["archivo_hash"] = current_file_hash

            st.session_state["factura_actual"] = parsed
            st.session_state["last_file_hash"] = current_file_hash
            st.session_state["audio_b64"] = preparar_audio(parsed.get("guion_audio", "Resumen de la factura."))
            historial = guardar_historial(parsed, current_file_hash, texto_raw=texto_raw)
            st.session_state["factura_anterior"] = historial.iloc[-2].to_dict() if len(historial) >= 2 else None
        except Exception as e:
            reset_current_results()
            st.session_state["factura_anterior"] = None
            error_txt = str(e)
            if "ERROR_TEMPORAL_IA:" in error_txt:
                st.error("La IA no está disponible en este momento. Revisa tu cuota o vuelve a intentarlo más tarde.")
                st.caption(error_txt)
            elif "ERROR_IA:" in error_txt:
                st.error("La IA no ha podido responder correctamente. Reinténtalo en unos minutos.")
                st.caption(error_txt)
            else:
                st.error("No se pudo analizar la factura por un error inesperado.")
                st.caption(error_txt)
        finally:
            spinner_placeholder.empty()



factura = st.session_state.get("factura_actual")
anterior = st.session_state.get("factura_anterior")

#st.write("DEBUG factura_actual:", factura)

if factura:
    st.markdown("<div class='panel'><div class='section-title'>Datos de esta factura</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='data-grid'>
          <div class='data-card'><div class='data-label'>Periodo</div><div class='data-value'>{esc(factura.get('periodo', 'No detectado'))}</div></div>
          <div class='data-card'><div class='data-label'>Compañía</div><div class='data-value'>{esc(normalizar_compania(factura.get('compania', 'No detectada')))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if factura.get("modelo_usado"):
        st.caption(f"Origen de los datos: {factura.get('modelo_usado')}")

    c1, c2 = st.columns(2)
    with c1:
        render_metric_card(
            "Total a pagar",
            fmt_euro(factura.get("total_pagar")),
            factura.get("explicacion_total"),
            calcular_delta(factura.get("total_pagar"), anterior.get("total_pagar") if anterior else None, "€") if anterior else None,
        )
        render_metric_card(
            "Consumo",
            fmt_num(factura.get("consumo_kwh"), "kWh"),
            factura.get("explicacion_consumo"),
            calcular_delta(factura.get("consumo_kwh"), anterior.get("consumo_kwh") if anterior else None, "kWh") if anterior else None,
        )
    with c2:
        render_metric_card(
            "Potencia contratada",
            fmt_num(factura.get("potencia_kw"), "kW"),
            factura.get("explicacion_potencia"),
            calcular_delta(factura.get("potencia_kw"), anterior.get("potencia_kw") if anterior else None, "kW") if anterior else None,
        )
        render_metric_card(
            "Impuestos",
            fmt_euro(factura.get("impuestos")),
            factura.get("explicacion_impuestos"),
            calcular_delta(factura.get("impuestos"), anterior.get("impuestos") if anterior else None, "€") if anterior else None,
        )

    st.markdown("<div class='audio-panel'><div class='audio-title'>Escuchar resumen</div><div class='audio-actions'>", unsafe_allow_html=True)
    cola, colb = st.columns(2, gap="medium")
    with cola:
        if st.button("Escuchar", key="btn_escuchar", use_container_width=True):
            st.session_state["reproducir"] = True
    with colb:
        if st.button("Parar", key="btn_parar", use_container_width=True):
            st.session_state["reproducir"] = False
    st.markdown("</div></div>", unsafe_allow_html=True)

    if st.session_state.get("reproducir") and st.session_state.get("audio_b64"):
        st.components.v1.html(
            f"<audio autoplay><source src='data:audio/mp3;base64,{st.session_state['audio_b64']}' type='audio/mp3'></audio>",
            height=0,
        )

hist = deduplicar_historial(asegurar_columnas_historial(cargar_historial()))
if not hist.empty:
    if os.path.exists(HISTORIAL_CSV):
        hist.to_csv(HISTORIAL_CSV, index=False)

    st.markdown(
        "<div class='panel'><div class='section-title'>Historial de facturas guardadas</div>",
        unsafe_allow_html=True,
    )

    # NUEVO: histórico completo + secciones Luz / Agua / Teléfono
    render_historial_completo_y_por_secciones()

    st.markdown(
        "<div class='history-note'>Al analizar una factura, se guarda toda su información para poder recuperarla desde el historial sin volver a consumir la API.</div>",
        unsafe_allow_html=True,
    )

    # Descarga del CSV sigue igual
    st.download_button(
        "Descargar historial facturas",
        data=hist.to_csv(index=False).encode("utf-8"),
        file_name="recibozen_historial.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown(
        "<div class='history-danger-wrap'><a class='history-danger-btn' href='?accion=borrar_historial'>Borrar historial</a></div></div>",
        unsafe_allow_html=True,
    )

if st.session_state.get("borrar_historial_click"):
    st.success("Historial borrado correctamente.")
    st.session_state["borrar_historial_click"] = False
