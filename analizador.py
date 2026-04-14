import streamlit as st
from google import genai
from pypdf import PdfReader
from gtts import gTTS
import io
import base64
import csv
import os
import re
import json
import time
import hashlib
from datetime import datetime
from html import escape

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import requests
except Exception:
    requests = None

st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="wide")

HISTORY_FILE = "recibozen_historial.csv"
CACHE_FILE = "recibozen_cache.json"
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
OPENROUTER_MODEL = "openrouter/auto"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    GOOGLE_API_KEY = ""

try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    OPENROUTER_API_KEY = ""

client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
    --bg: #f4f8fc;
    --surface: #ffffff;
    --surface-2: #f7fbff;
    --text: #163042;
    --muted: #647a8d;
    --line: #d9e5f0;
    --primary: #1677c8;
    --primary-dark: #0d5fa2;
    --primary-soft: #e8f2fb;
    --accent: #4bb4ff;
    --accent-soft: #eaf6ff;
    --warn: #ffb703;
    --warn-soft: #fff4cd;
    --success: #2f8f79;
    --shadow: 0 12px 34px rgba(15, 48, 76, 0.08);
    --radius-lg: 22px;
    --radius-md: 18px;
}
html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top right, #e9f4ff 0%, #f4f8fc 44%, #ffffff 100%) !important;
}
body, p, div, label, li, span, small, h1, h2, h3 {
    color: var(--text) !important;
    font-family: 'Inter', system-ui, sans-serif !important;
}
.block-container { max-width: 1180px; padding-top: 1.2rem; padding-bottom: 3rem; }
.hero {
    background: linear-gradient(140deg, rgba(255,255,255,.98), rgba(244,249,255,.94));
    border: 1px solid rgba(22,119,200,.12);
    border-radius: 30px;
    padding: 1.5rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
}
.hero::after {
    content: "";
    position: absolute;
    right: -60px;
    bottom: -70px;
    width: 240px;
    height: 240px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(75,180,255,.22) 0%, rgba(75,180,255,0) 70%);
    pointer-events: none;
}
.hero-title {
    margin: 0 0 .4rem 0;
    font-family: 'Manrope', system-ui, sans-serif !important;
    font-size: clamp(2rem, 3vw, 3.2rem);
    line-height: 1.02;
    letter-spacing: -0.03em;
    font-weight: 800;
}
.hero-sub { color: var(--muted) !important; font-size: 1.04rem; max-width: 62ch; line-height: 1.55; }
.feature-list { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: .85rem 1rem; margin-top: 1.15rem; }
.feature-item { display: flex; align-items: flex-start; gap: .75rem; background: rgba(255,255,255,.68); border: 1px solid rgba(22,119,200,.08); border-radius: 18px; padding: .9rem 1rem; backdrop-filter: blur(6px); }
.feature-dot { width: 12px; height: 12px; margin-top: .36rem; border-radius: 999px; flex: 0 0 12px; background: linear-gradient(180deg, var(--accent), var(--primary)); box-shadow: 0 0 0 4px rgba(75,180,255,.13); }
.feature-copy { font-size: .96rem; line-height: 1.4; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: 1rem; box-shadow: var(--shadow); margin-bottom: 1rem; }
.soft-card { background: var(--surface-2); border: 1px solid #e4edf6; border-radius: 16px; padding: .95rem; }
.metric-card { background: linear-gradient(180deg, #ffffff 0%, #f9fcff 100%); border: 1px solid var(--line); border-radius: 20px; padding: 1rem; box-shadow: var(--shadow); min-height: 132px; }
.metric-label { font-size: .92rem; color: var(--muted) !important; margin-bottom: .35rem; font-weight: 800; }
.metric-value { font-family: 'Manrope', system-ui, sans-serif !important; font-size: clamp(1.55rem, 2.5vw, 2.3rem); line-height: 1.03; font-weight: 800; letter-spacing: -0.03em; }
.metric-help { margin-top: .45rem; color: var(--muted) !important; font-size: .95rem; }
.section-title { font-family: 'Manrope', system-ui, sans-serif !important; font-size: 1.18rem; margin-bottom: .8rem; font-weight: 800; }
.summary-box { background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%); border: 1px solid var(--line); border-radius: 22px; padding: 1rem; box-shadow: var(--shadow); }
.big-text { font-size: 1.06rem; line-height: 1.7; }
.helper-list { margin: 0; padding-left: 1.15rem; }
.helper-list li { margin-bottom: .55rem; }
.small-note { color: var(--muted) !important; font-size: .95rem; }
.history-table-wrap { overflow-x: auto; border-radius: 16px; border: 1px solid var(--line); }
.history-table { width: 100%; border-collapse: collapse; background: var(--surface); }
.history-table th, .history-table td { text-align: left; padding: .82rem .8rem; border-bottom: 1px solid #ebf1f7; font-size: .95rem; }
.history-table th { background: #f8fbff; color: var(--muted) !important; font-weight: 800; }
.audio-box { background: linear-gradient(180deg, #f7fbff 0%, #eef7ff 100%); border: 1px solid var(--line); border-radius: 20px; padding: 1rem; }
.audio-grid { display:grid; grid-template-columns: 1fr 1fr; gap:.85rem; margin-top:.25rem; }
.badge-ok { display: inline-block; padding: .38rem .74rem; border-radius: 999px; background: #e8f2fb; color: #155f9f !important; font-weight: 800; font-size: .88rem; }
.advice-box { position: relative; background: linear-gradient(135deg, #fff9e8 0%, #fff2c8 100%); border: 1px solid rgba(255,183,3,.25); border-radius: 18px; padding: 1rem 1rem 1rem 1.1rem; box-shadow: 0 10px 24px rgba(255,183,3,.12); }
.advice-box::before { content: '⚡'; position: absolute; top: -12px; right: 14px; font-size: 1.45rem; }
.panel-stack { display: grid; gap: .95rem; }
.info-panel { background: linear-gradient(135deg, #f8fbff 0%, #eef7ff 100%); border: 1px solid rgba(22,119,200,.1); border-radius: 18px; padding: .98rem 1rem; }
.info-panel h3, .advice-box h3 { margin: 0 0 .6rem 0; font-family: 'Manrope', system-ui, sans-serif !important; font-size: 1.06rem; color: var(--primary-dark) !important; }
.info-panel ul { margin: 0; padding-left: 1.15rem; }
.info-panel li { margin-bottom: .45rem; }
.footer-note { text-align: center; color: var(--muted) !important; margin-top: 1rem; font-size: .9rem; }
div[data-testid="stFileUploader"] section { background: rgba(255,255,255,.92) !important; border: 2px dashed rgba(22,119,200,.26) !important; border-radius: 18px !important; }
div[data-testid="stFileUploader"] small { display:none !important; }
.stButton > button { border-radius: 16px !important; min-height: 58px !important; font-weight: 800 !important; border: none !important; white-space: nowrap !important; font-family: 'Inter', system-ui, sans-serif !important; }
.stButton > button[kind="primary"] { background: linear-gradient(180deg, var(--primary), var(--primary-dark)) !important; color: white !important; box-shadow: 0 10px 24px rgba(22,119,200,.22) !important; }
div[data-testid="column"] .stButton > button { width: 100% !important; min-width: 100% !important; }
.spinner-shell { display:flex; align-items:center; gap:.8rem; padding:.9rem 1rem; margin-bottom:1rem; background:linear-gradient(180deg,#ffffff 0%,#f4f9ff 100%); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow); }
.spinner-dot { width:16px; height:16px; border-radius:999px; border:3px solid #d8eaf8; border-top-color: var(--primary); animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 768px) {
    .hero { padding: 1rem; border-radius: 22px; }
    .metric-card { min-height: unset; }
    .feature-list { grid-template-columns: 1fr; }
    .audio-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)

MONTHS = {1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"}


def init_history_file():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "periodo", "empresa", "total_eur", "consumo_kwh", "potencia_kw", "impuestos_eur", "consejo", "resumen", "modelo", "proveedor"])


def read_history():
    init_history_file()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_history_item(item):
    init_history_file()
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([item.get("timestamp", ""), item.get("periodo", ""), item.get("empresa", ""), item.get("total_eur", ""), item.get("consumo_kwh", ""), item.get("potencia_kw", ""), item.get("impuestos_eur", ""), item.get("consejo", ""), item.get("resumen", ""), item.get("modelo", ""), item.get("proveedor", "")])


def init_cache():
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def read_cache():
    init_cache()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pdf_hash(uploaded_file):
    return hashlib.sha256(uploaded_file.getvalue()).hexdigest()


def clear_current_result():
    for key in ["analisis_meta", "analisis_html", "audio_txt", "audio_b64", "origen_resultado", "reproducir", "current_file_hash"]:
        if key in st.session_state:
            del st.session_state[key]


def leer_pdf(file):
    reader = PdfReader(io.BytesIO(file.getvalue()))
    textos = []
    for page in reader.pages:
        textos.append(page.extract_text() or "")
    return "\n".join(textos).strip()


def preparar_audio(texto):
    tts = gTTS(text=texto, lang="es", slow=False)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    return base64.b64encode(audio_io.getvalue()).decode()


def extraer_texto_respuesta(response):
    texto = getattr(response, "text", None)
    if texto:
        return texto.strip()
    try:
        candidates = getattr(response, "candidates", []) or []
        trozos = []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for part in parts:
                part_text = getattr(part, "text", None)
                if part_text:
                    trozos.append(part_text)
        return "\n".join(trozos).strip()
    except Exception:
        return ""


def parsear_bloques(texto):
    partes = texto.split("---")
    meta_txt = partes[0].strip() if len(partes) > 0 else ""
    html_txt = partes[1].strip() if len(partes) > 1 else "<p>No se pudo generar el informe visual.</p>"
    audio_txt = partes[2].strip() if len(partes) > 2 else "¡Hola, hola! Aquí tienes un resumen sencillo de tu factura."
    meta = {}
    for line in meta_txt.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip().strip('"').strip("',")
    return meta, html_txt, audio_txt


def build_prompt(texto_raw):
    return f'''
Eres ReciboZen, una app para explicar facturas de forma MUY CLARA a personas mayores, personas con cierta dificultad cognitiva o personas que no entienden conceptos de suministros.

Normas obligatorias:
- Usa frases muy cortas.
- Usa palabras sencillas.
- Evita tecnicismos o explícalos con lenguaje simple.
- Sé tranquilizador, claro y amable.
- Si un dato no aparece claro, dilo sin inventar.

Devuelve exactamente estas 2 partes separadas por ---

PRIMERA PARTE:
Un bloque simple con estas claves exactas:
periodo:
empresa:
total_eur:
consumo_kwh:
potencia_kw:
impuestos_eur:
mensaje_claro:
consejo:
resumen_1_linea:

SEGUNDA PARTE:
Un texto en HTML muy simple con este formato:
<h3>Qué estás pagando</h3>
<ul><li>...</li></ul>
<h3>Qué significa</h3>
<ul><li>...</li></ul>
<h3>Consejo útil</h3>
<p>...</p>

Y termina con una TERCERA PARTE separada también por ---:
Un guion de voz en español, alegre y cercano, máximo 80 palabras, que empiece exactamente por ¡Hola, hola!

Factura:
{texto_raw[:4200]}
'''


def call_gemini(prompt):
    if not client:
        raise RuntimeError("No hay GOOGLE_API_KEY configurada.")
    last_error = None
    for model in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            text = extraer_texto_respuesta(response)
            if not text:
                raise RuntimeError("Respuesta vacía.")
            return text, model, "interno"
        except Exception as e:
            last_error = e
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", msg, re.IGNORECASE)
                wait_s = 0
                if m:
                    try:
                        wait_s = min(float(m.group(1)), 45)
                    except Exception:
                        wait_s = 0
                if wait_s > 0:
                    time.sleep(wait_s)
                    try:
                        response = client.models.generate_content(model=model, contents=prompt)
                        text = extraer_texto_respuesta(response)
                        if text:
                            return text, model, "interno"
                    except Exception as e2:
                        last_error = e2
                continue
    raise RuntimeError(f"Servicio principal no disponible: {last_error}")


def call_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("No hay OPENROUTER_API_KEY configurada.")
    if requests is None:
        raise RuntimeError("Falta instalar requests.")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://streamlit.io", "X-Title": "ReciboZen"}
    payload = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": "Responde siempre en español claro."}, {"role": "user", "content": prompt}]}
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
    if r.status_code >= 400:
        raise RuntimeError(f"Servicio alternativo no disponible: {r.status_code}")
    data = r.json()
    text = data["choices"][0]["message"]["content"].strip()
    used_model = data.get("model", OPENROUTER_MODEL)
    return text, used_model, "alternativo"


def analizar_con_fallback(texto_raw):
    prompt = build_prompt(texto_raw)
    errores = []
    try:
        return call_gemini(prompt)
    except Exception as e:
        errores.append(str(e))
    try:
        return call_openrouter(prompt)
    except Exception as e:
        errores.append(str(e))
    raise RuntimeError(" | ".join(errores))


def limpiar_numero(texto):
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    t = t.replace("€", "").replace("EUR", "").replace("eur", "").replace("kWh", "").replace("kw", "").replace("kW", "").replace(" ", "")
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group())
    except Exception:
        return None


def format_eur(v):
    if v is None:
        return "No disponible"
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def format_num(v, unit=""):
    if v is None:
        return "No disponible"
    txt = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{txt} {unit}".strip()


def diff_label(current, previous, suffix=""):
    if current is None or previous is None:
        return "Sin comparación todavía"
    diff = current - previous
    if abs(diff) < 0.005:
        return f"Igual que la factura anterior{suffix}"
    sign = "más" if diff > 0 else "menos"
    return f"{abs(diff):.2f} {sign} que la factura anterior{suffix}"


def latest_previous(rows):
    return rows[-2] if len(rows) >= 2 else None


def short_period_label(periodo, timestamp):
    if not periodo:
        try:
            dt = datetime.fromisoformat(timestamp)
            return f"{MONTHS.get(dt.month, str(dt.month))} {str(dt.year)[2:]}"
        except Exception:
            return "Sin fecha"
    nums = re.findall(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", str(periodo))
    if len(nums) >= 2:
        def parse_date(txt):
            txt = txt.replace('-', '/')
            d, m, y = txt.split('/')
            if len(y) == 2:
                y = '20' + y
            return int(d), int(m), int(y)
        try:
            d1, m1, _ = parse_date(nums[0])
            d2, m2, _ = parse_date(nums[1])
            return f"{d1}/{MONTHS.get(m1, m1)} a {d2}/{MONTHS.get(m2, m2)}"
        except Exception:
            pass
    nums2 = re.findall(r"\d{1,2}/\d{1,2}", str(periodo))
    if len(nums2) >= 2:
        try:
            d1, m1 = nums2[0].split('/')
            d2, m2 = nums2[1].split('/')
            return f"{int(d1)}/{MONTHS.get(int(m1), m1)} a {int(d2)}/{MONTHS.get(int(m2), m2)}"
        except Exception:
            pass
    return str(periodo)[:18]


def render_history_table(rows):
    if not rows:
        st.info("Todavía no hay historial guardado.")
        return
    html = ['<div class="history-table-wrap"><table class="history-table"><thead><tr>']
    for c in ["Fecha", "Periodo", "Empresa", "Total", "Consumo"]:
        html.append(f"<th>{escape(c)}</th>")
    html.append("</tr></thead><tbody>")
    for r in reversed(rows[-24:]):
        html.append("<tr>")
        html.append(f"<td>{escape(str(r.get('timestamp',''))[:16].replace('T',' '))}</td>")
        html.append(f"<td>{escape(short_period_label(r.get('periodo',''), r.get('timestamp','')))}</td>")
        html.append(f"<td>{escape(r.get('empresa','') or '—')}</td>")
        html.append(f"<td>{escape(format_eur(limpiar_numero(r.get('total_eur'))))}</td>")
        html.append(f"<td>{escape(format_num(limpiar_numero(r.get('consumo_kwh')), 'kWh'))}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def decorate_analysis_html(html_text):
    html_mejorado = html_text
    html_mejorado = html_mejorado.replace('<h3>Qué estás pagando</h3>', '<div class="panel-stack"><div class="info-panel"><h3>Qué estás pagando</h3>')
    html_mejorado = html_mejorado.replace('<h3>Qué significa</h3>', '</div><div class="info-panel"><h3>Qué significa</h3>')
    html_mejorado = html_mejorado.replace('<h3>Consejo útil</h3>', '</div><div class="advice-box"><h3>Consejo útil</h3>')
    html_mejorado += '</div></div>'
    return html_mejorado


rows = read_history()
prev = latest_previous(rows)
cache = read_cache()

st.markdown('''
<div class="hero">
  <div class="logo-wrap"><img src="data:image/svg+xml;utf8,%3Csvg%20width%3D%22420%22%20height%3D%2296%22%20viewBox%3D%220%200%20420%2096%22%20fill%3D%22none%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20role%3D%22img%22%20aria-label%3D%22Logotipo%20de%20ReciboZen%22%3E%3Cdefs%3E%3ClinearGradient%20id%3D%22rzg%22%20x1%3D%2216%22%20y1%3D%2216%22%20x2%3D%2280%22%20y2%3D%2280%22%20gradientUnits%3D%22userSpaceOnUse%22%3E%3Cstop%20stop-color%3D%22%235BB7FF%22/%3E%3Cstop%20offset%3D%221%22%20stop-color%3D%22%231677C8%22/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect%20x%3D%228%22%20y%3D%228%22%20width%3D%2280%22%20height%3D%2280%22%20rx%3D%2224%22%20fill%3D%22%23EFF7FF%22/%3E%3Cpath%20d%3D%22M31%2032.5C31%2028.3579%2034.3579%2025%2038.5%2025H57.5C61.6421%2025%2065%2028.3579%2065%2032.5V63.5C65%2067.6421%2061.6421%2071%2057.5%2071H38.5C34.3579%2071%2031%2067.6421%2031%2063.5V32.5Z%22%20fill%3D%22url(%23rzg)%22/%3E%3Cpath%20d%3D%22M42.5%2041.5H53.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M42.5%2049.5H54.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.92%22/%3E%3Cpath%20d%3D%22M42.5%2057.5H50.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.86%22/%3E%3Cpath%20d%3D%22M66%2057C71.3333%2053.6667%2076.6667%2053.6667%2082%2057%22%20stroke%3D%22%237CC7FF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M66%2065C71.3333%2061.6667%2076.6667%2061.6667%2082%2065%22%20stroke%3D%22%23A6DBFF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Ctext%20x%3D%22108%22%20y%3D%2249%22%20fill%3D%22%23163042%22%20font-family%3D%22Manrope%2C%20Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2234%22%20font-weight%3D%22800%22%20letter-spacing%3D%22-0.02em%22%3EReciboZen%3C/text%3E%3Ctext%20x%3D%22110%22%20y%3D%2269%22%20fill%3D%22%236B8295%22%20font-family%3D%22Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2214%22%20font-weight%3D%22500%22%3ETu%20factura%20explicada%20con%20calma%3C/text%3E%3C/svg%3E" alt="ReciboZen" style="width:min(100%, 420px); height:auto; margin-bottom: .7rem;"/>
  <p class="hero-sub">Entiende tu factura sin tecnicismos. Mira cuánto pagas, compara meses y escucha un resumen sencillo.</p>
  <div class="feature-list">
    <div class="feature-item"><span class="feature-dot"></span><div class="feature-copy"><strong>Lectura fácil</strong><br>Textos breves y claros para entender mejor cada concepto</div></div>
    <div class="feature-item"><span class="feature-dot"></span><div class="feature-copy"><strong>Comparación mensual</strong><br>Visualiza si subes o bajas de una factura a otra</div></div>
    <div class="feature-item"><span class="feature-dot"></span><div class="feature-copy"><strong>Resumen en audio</strong><br>Escucha una explicación rápida sin leer toda la pantalla</div></div>
    <div class="feature-item"><span class="feature-dot"></span><div class="feature-copy"><strong>Diseño claro</strong><br>Interfaz moderna, limpia y adaptada a móvil y escritorio</div></div>
  </div>
</div>
''', unsafe_allow_html=True)

left, right = st.columns([1.45, 1], gap="large")

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Sube tu factura</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Subir fichero PDF", type="pdf", label_visibility="collapsed", key="pdf_uploader")
    st.caption("Sube un PDF de tu factura para analizarlo.")
    analizar = st.button("Analizar factura", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Ayuda rápida</div>', unsafe_allow_html=True)
    st.markdown('''
    <ul class="helper-list">
      <li><strong>Total:</strong> lo que pagas al final.</li>
      <li><strong>Consumo:</strong> la energía usada.</li>
      <li><strong>Potencia:</strong> una parte fija de la factura.</li>
      <li><strong>Impuestos:</strong> cargos añadidos por ley.</li>
    </ul>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Historial</div>', unsafe_allow_html=True)
    st.markdown(f"<p class='small-note'>Facturas guardadas: <strong>{len(rows)}</strong></p>", unsafe_allow_html=True)
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "rb") as f:
            st.download_button("Descargar historial CSV", f, file_name=HISTORY_FILE, mime="text/csv", use_container_width=True)
    if st.button("Borrar historial y caché", use_container_width=True):
        for file in [HISTORY_FILE, CACHE_FILE]:
            if os.path.exists(file):
                os.remove(file)
        st.session_state.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file is not None:
    current_hash = pdf_hash(uploaded_file)
    previous_hash = st.session_state.get("current_file_hash")
    if previous_hash and previous_hash != current_hash:
        clear_current_result()
    st.session_state["current_file_hash"] = current_hash

with left:
    if analizar:
        try:
            if not uploaded_file:
                raise RuntimeError("Primero tienes que subir un PDF.")

            st.markdown('<div class="spinner-shell"><div class="spinner-dot"></div><div><strong>Analizando factura…</strong><br><span class="small-note">Esto puede tardar unos segundos.</span></div></div>', unsafe_allow_html=True)
            factura_hash = pdf_hash(uploaded_file)
            texto_raw = leer_pdf(uploaded_file)
            if not texto_raw:
                raise RuntimeError("No se pudo extraer texto del PDF.")

            if factura_hash in cache:
                cached = cache[factura_hash]
                meta = cached["meta"]
                html_txt = cached["html_txt"]
                audio_txt = cached["audio_txt"]
                origen = "guardado"
            else:
                with st.spinner(""):
                    raw_text, modelo, proveedor = analizar_con_fallback(texto_raw)
                    meta, html_txt, audio_txt = parsear_bloques(raw_text)
                    cache[factura_hash] = {"meta": meta, "html_txt": html_txt, "audio_txt": audio_txt, "modelo": modelo, "proveedor": proveedor}
                    write_cache(cache)
                    origen = "nuevo"

            st.session_state["analisis_meta"] = meta
            st.session_state["analisis_html"] = html_txt
            st.session_state["audio_txt"] = audio_txt
            st.session_state["audio_b64"] = preparar_audio(audio_txt)
            st.session_state["origen_resultado"] = origen
            st.session_state["reproducir"] = False

            if origen != "guardado":
                save_history_item({
                    "timestamp": datetime.now().isoformat(timespec="minutes"),
                    "periodo": meta.get("periodo", ""),
                    "empresa": meta.get("empresa", ""),
                    "total_eur": meta.get("total_eur", ""),
                    "consumo_kwh": meta.get("consumo_kwh", ""),
                    "potencia_kw": meta.get("potencia_kw", ""),
                    "impuestos_eur": meta.get("impuestos_eur", ""),
                    "consejo": meta.get("consejo", ""),
                    "resumen": meta.get("resumen_1_linea", ""),
                    "modelo": "",
                    "proveedor": ""
                })
                rows = read_history()
                prev = latest_previous(rows)

            st.success("Factura lista.")

        except Exception as e:
            st.error(f"No se pudo analizar la factura: {e}")

    if "analisis_meta" in st.session_state:
        meta = st.session_state["analisis_meta"]
        total_now = limpiar_numero(meta.get("total_eur"))
        consumo_now = limpiar_numero(meta.get("consumo_kwh"))
        potencia_now = limpiar_numero(meta.get("potencia_kw"))
        impuestos_now = limpiar_numero(meta.get("impuestos_eur"))
        total_prev = limpiar_numero(prev.get("total_eur")) if prev else None
        consumo_prev = limpiar_numero(prev.get("consumo_kwh")) if prev else None

        if st.session_state.get("origen_resultado") == "guardado":
            st.markdown("<span class='badge-ok'>Resultado recuperado sin volver a analizar</span>", unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown(f'''<div class="metric-card"><div class="metric-label">Total a pagar</div><div class="metric-value">{escape(format_eur(total_now))}</div><div class="metric-help">{escape(diff_label(total_now, total_prev, ' en total'))}</div></div>''', unsafe_allow_html=True)
        with c2:
            st.markdown(f'''<div class="metric-card"><div class="metric-label">Consumo</div><div class="metric-value">{escape(format_num(consumo_now, 'kWh'))}</div><div class="metric-help">{escape(diff_label(consumo_now, consumo_prev, ' de consumo'))}</div></div>''', unsafe_allow_html=True)

        c3, c4 = st.columns(2, gap="medium")
        with c3:
            st.markdown(f'''<div class="metric-card"><div class="metric-label">Potencia contratada</div><div class="metric-value">{escape(format_num(potencia_now, 'kW'))}</div><div class="metric-help">Parte fija de la factura.</div></div>''', unsafe_allow_html=True)
        with c4:
            st.markdown(f'''<div class="metric-card"><div class="metric-label">Impuestos</div><div class="metric-value">{escape(format_eur(impuestos_now))}</div><div class="metric-help">Cargos añadidos por ley.</div></div>''', unsafe_allow_html=True)

        a, b = st.columns([1.2, .8], gap="large")
        with a:
            st.markdown('<div class="summary-box">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Resumen fácil de entender</div>', unsafe_allow_html=True)
            if meta.get("mensaje_claro"):
                st.markdown(f"<p class='big-text'><strong>{escape(meta.get('mensaje_claro'))}</strong></p>", unsafe_allow_html=True)
            st.markdown(decorate_analysis_html(st.session_state["analisis_html"]), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with b:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Datos de esta factura</div>', unsafe_allow_html=True)
            st.markdown(f"<div class='soft-card'><strong>Periodo:</strong><br>{escape(meta.get('periodo') or 'No indicado')}</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='soft-card'><strong>Empresa:</strong><br>{escape(meta.get('empresa') or 'No indicada')}</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='advice-box'><strong>Consejo útil</strong><br>{escape(meta.get('consejo') or 'Sin consejo disponible')}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Escuchar resumen</div>', unsafe_allow_html=True)
            st.markdown('<div class="audio-box"><div class="audio-grid">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Reproducir audio", use_container_width=True):
                    st.session_state["reproducir"] = True
            with col2:
                if st.button("⏹️ Parar audio", use_container_width=True):
                    st.session_state["reproducir"] = False
            if st.session_state.get("reproducir"):
                st.components.v1.html(f'<audio autoplay controls style="width:100%; margin-top:12px;"><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=60)
            st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Comparación mensual</div>', unsafe_allow_html=True)
    st.markdown("<p class='small-note'>Cada punto representa una factura. La etiqueta resume el periodo de facturación.</p>", unsafe_allow_html=True)
    if rows:
        if pd is not None and len(rows) >= 2:
            try:
                df = pd.DataFrame(rows)
                df["total_num"] = df["total_eur"].apply(limpiar_numero)
                df["periodo_view"] = df.apply(lambda r: short_period_label(r.get("periodo", ""), r.get("timestamp", "")), axis=1)
                chart_df = df[["periodo_view", "total_num"]].dropna().tail(12)
                if not chart_df.empty:
                    st.line_chart(chart_df.set_index("periodo_view"), color="#4bb4ff")
            except Exception:
                pass
        render_history_table(rows)
    else:
        st.info("Cuando analices la primera factura, aquí verás la comparación entre meses.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="footer-note">ReciboZen · 2026 · Interfaz clara y moderna</div>', unsafe_allow_html=True)
