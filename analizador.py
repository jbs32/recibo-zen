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


MODELOS_ANALISIS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def es_error_temporal_modelo(error):
    msg = str(error).upper()
    patrones = [
        "503",
        "UNAVAILABLE",
        "HIGH DEMAND",
        "RESOURCE_EXHAUSTED",
        "DEADLINE_EXCEEDED",
        "SERVICE UNAVAILABLE",
        "TOO MANY REQUESTS",
        "429",
    ]
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
                status.markdown(
                    f"<div class='hint'>Analizando con IA ({modelo})...</div>",
                    unsafe_allow_html=True,
                )
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                status.empty()
                return response, modelo
            except Exception as e:
                ultimo_error = e
                if not es_error_temporal_modelo(e):
                    status.empty()
                    raise
                espera = min(2 ** intento, 6)
                status.markdown(
                    f"<div class='hint'>Servicio saturado en {modelo}. Reintentando en {espera} s...</div>",
                    unsafe_allow_html=True,
                )
                time.sleep(espera)

    status.empty()
    raise RuntimeError(f"No fue posible analizar con IA en este momento. {ultimo_error}")


def construir_respuesta_local(extraidos_pdf):
    periodo = extraidos_pdf.get("periodo", "No detectado")
    compania = normalizar_compania(extraidos_pdf.get("compania", "No detectada"))
    total_pagar = extraidos_pdf.get("total_pagar", "No detectado")
    consumo_kwh = extraidos_pdf.get("consumo_kwh", "No detectado")
    potencia_kw = extraidos_pdf.get("potencia_kw", "No detectado")
    impuestos = extraidos_pdf.get("impuestos", "No detectado")

    lineas = [
        f"periodo: {periodo}",
        f"compania: {compania}",
        f"total_pagar: {total_pagar}",
        f"consumo_kwh: {consumo_kwh}",
        f"potencia_kw: {potencia_kw}",
        f"impuestos: {impuestos}",
        "explicacion_total: Es el importe final que pagas este mes. Incluye consumo, parte fija e impuestos.",
        "explicacion_consumo: Es la energía que has usado en este periodo. Si sube, normalmente has consumido más.",
        "explicacion_potencia: Es la parte fija de la factura. La pagas aunque consumas poco.",
        "explicacion_impuestos: Son impuestos y cargos añadidos al importe final.",
        f"guion_audio: Hola. Esta factura es de {compania}. El periodo es {periodo}. El total a pagar es {total_pagar} euros. El consumo es {consumo_kwh} kilovatios hora. La potencia contratada es {potencia_kw} kilovatios. Los impuestos son {impuestos} euros.",
    ]
    return "\n".join(lineas)


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
    .rz-header, .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        box-shadow: var(--shadow);
        border-radius: 24px;
        padding: 1.15rem;
        margin-bottom: 1rem;
    }
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
    .tooltip-icon {
        display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:999px;
        border:1px solid rgba(15,95,166,.24); background:#eef6ff; color:var(--primary); font-size:.82rem; font-weight:800; cursor:help;
        box-shadow:0 3px 8px rgba(15,95,166,.08);
    }
    .tooltip-bubble {
        position:absolute; left:0; top:calc(100% + 8px); width:min(290px, 78vw); z-index:60;
        background:#123046; color:#ffffff !important; padding:.9rem 1rem; border-radius:14px; box-shadow:0 16px 32px rgba(18,48,70,.22);
        font-size:.93rem; line-height:1.46; opacity:0; visibility:hidden; transform:translateY(4px); transition:all .16s ease; pointer-events:none;
    }
    .tooltip-wrap:hover .tooltip-bubble, .tooltip-wrap:focus-within .tooltip-bubble, .tooltip-wrap:active .tooltip-bubble { opacity:1; visibility:visible; transform:translateY(0); }
    .tooltip-bubble::before { content:""; position:absolute; top:-6px; left:12px; width:12px; height:12px; background:#123046; transform:rotate(45deg); }
    .spinner-card { display:flex; align-items:center; gap:.85rem; background:linear-gradient(180deg,#f5fbff 0%,#edf6ff 100%); border:1px solid rgba(15,95,166,.16); border-radius:18px; padding:1rem 1.05rem; margin-bottom:1rem; }
    .spinner-dot { width:18px; height:18px; border-radius:50%; border:3px solid rgba(15,95,166,.18); border-top-color:var(--primary); animation:rzspin 1s linear infinite; }
    @keyframes rzspin { to { transform: rotate(360deg);} }

    div.stButton > button, .stDownloadButton > button, .stFileUploader button, [data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {
        width:100% !important; min-height:54px !important; border-radius:18px !important; font-size:1rem !important; font-weight:800 !important;
        color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; text-shadow:0 1px 1px rgba(0,0,0,.22) !important;
        background:linear-gradient(180deg,var(--primary-2) 0%, var(--primary) 100%) !important; border:none !important; box-shadow:0 12px 28px rgba(15,95,166,.22) !important;
        margin-top:0 !important; margin-bottom:0 !important;
    }
    div.stButton > button *, .stDownloadButton > button *, .stFileUploader button *, [data-testid="stBaseButton-primary"] *, .stButton > button[kind="primary"] * { color:#ffffff !important; fill:#ffffff !important; -webkit-text-fill-color:#ffffff !important; }

    .listen-btn div.stButton > button {
        background:linear-gradient(180deg,var(--primary-2) 0%, var(--primary) 100%) !important;
        box-shadow:0 12px 28px rgba(15,95,166,.22) !important;
    }
    .stop-btn div.stButton > button,
    .danger-btn div.stButton > button {
        background:linear-gradient(180deg,var(--danger-2) 0%, var(--danger) 100%) !important;
        box-shadow:0 12px 28px rgba(179,52,59,.22) !important;
    }

    .audio-actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; align-items:stretch; margin-top:.25rem; }
    .audio-actions > div { min-width:0; }
    .audio-actions .stButton { height:100%; }
    .audio-actions .stButton > button { height:54px !important; }

    .stFileUploader section { background:#f8fbfe !important; border:2px dashed rgba(31,125,203,.22) !important; border-radius:24px !important; padding:1rem !important; }
    .stFileUploader small, .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div > small { display:none !important; }
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child, .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] svg { display:none !important; }

    .audio-panel { background:linear-gradient(180deg,#ffffff 0%, #f7fbff 100%); border:1px solid var(--line); border-radius:22px; padding:1rem; box-shadow:0 12px 22px rgba(18,48,70,.05); }
    .audio-title { font-family:'Manrope',sans-serif; font-size:1.05rem; font-weight:800; margin-bottom:.85rem; }

    .history-table { overflow-x:auto; margin-top:.4rem; }
    .history-table table { width:100%; border-collapse:collapse; font-size:.93rem; background:#fff; overflow:hidden; border-radius:16px; }
    .history-table thead th { text-align:left; background:#f4f8fc; color:#123046; padding:.8rem .75rem; border-bottom:1px solid var(--line); font-weight:800; }
    .history-table tbody td { padding:.78rem .75rem; border-bottom:1px solid rgba(18,48,70,.08); color:#123046; }
    .history-table tbody tr:last-child td { border-bottom:none; }
    .history-note { margin-top:.55rem; color:var(--muted); font-size:.93rem; }

    @media (max-width:700px){ .data-grid { grid-template-columns:1fr; } .audio-actions { grid-template-columns:1fr; } }
    </style>
    """,
    unsafe_allow_html=True,
)

LOGO_DATA_URI = "data:image/svg+xml;utf8,%3Csvg%20width%3D%22420%22%20height%3D%2296%22%20viewBox%3D%220%200%20420%2096%22%20fill%3D%22none%22%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20role%3D%22img%22%20aria-label%3D%22Logotipo%20de%20ReciboZen%22%3E%3Cdefs%3E%3ClinearGradient%20id%3D%22rzg%22%20x1%3D%2216%22%20y1%3D%2216%22%20x2%3D%2280%22%20y2%3D%2280%22%20gradientUnits%3D%22userSpaceOnUse%22%3E%3Cstop%20stop-color%3D%22%235BB7FF%22/%3E%3Cstop%20offset%3D%221%22%20stop-color%3D%22%231677C8%22/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect%20x%3D%228%22%20y%3D%228%22%20width%3D%2280%22%20height%3D%2280%22%20rx%3D%2224%22%20fill%3D%22%23EFF7FF%22/%3E%3Cpath%20d%3D%22M31%2032.5C31%2028.3579%2034.3579%2025%2038.5%2025H57.5C61.6421%2025%2065%2028.3579%2065%2032.5V63.5C65%2067.6421%2061.6421%2071%2057.5%2071H38.5C34.3579%2071%2031%2067.6421%2031%2063.5V32.5Z%22%20fill%3D%22url(%23rzg)%22/%3E%3Cpath%20d%3D%22M42.5%2041.5H53.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M42.5%2049.5H54.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.92%22/%3E%3Cpath%20d%3D%22M42.5%2057.5H50.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20opacity%3D%220.86%22/%3E%3Cpath%20d%3D%22M66%2057C71.3333%2053.6667%2076.6667%2053.6667%2082%2057%22%20stroke%3D%22%237CC7FF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Cpath%20d%3D%22M66%2065C71.3333%2061.6667%2076.6667%2061.6667%2082%2065%22%20stroke%3D%22%23A6DBFF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22/%3E%3Ctext%20x%3D%22108%22%20y%3D%2249%22%20fill%3D%22%23163042%22%20font-family%3D%22Manrope%2C%20Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2234%22%20font-weight%3D%22800%22%20letter-spacing%3D%22-0.02em%22%3EReciboZen%3C/text%3E%3Ctext%20x%3D%22110%22%20y%3D%2269%22%20fill%3D%22%236B8295%22%20font-family%3D%22Inter%2C%20Arial%2C%20sans-serif%22%20font-size%3D%2214%22%20font-weight%3D%22500%22%3ETu%20factura%20explicada%20con%20calma%3C/text%3E%3C/svg%3E"


def init_state():
    defaults = {"audio_b64": None, "reproducir": False, "factura_actual": None, "factura_anterior": None, "last_uploaded_name": None}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_current_results():
    st.session_state["audio_b64"] = None
    st.session_state["reproducir"] = False
    st.session_state["factura_actual"] = None


def leer_pdf(file):
    reader = PdfReader(file)
    return "\n".join([(page.extract_text() or "") for page in reader.pages])


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
    t = t.replace("€", "").replace("EUR", "").replace("kWh", "").replace("kW", "")
    t = t.replace(" ", "")
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


def extraer_desde_pdf(texto_raw):
    data = {}
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
            data[key] = m.group(1)
    if re.search(r"visalia|dom[eé]stica gas y electricidad", texto_raw, flags=re.IGNORECASE):
        data["compania"] = "Visalia"
    return data


def parsear_bloques(texto):
    resultado = {
        "periodo": "No detectado", "compania": "No detectada", "total_pagar": "No detectado",
        "consumo_kwh": "No detectado", "potencia_kw": "No detectado", "impuestos": "No detectado",
        "explicacion_total": "Es el importe final que pagas este mes. Aquí ya está sumado lo que has consumido, la parte fija y los impuestos.",
        "explicacion_consumo": "Es la energía que has usado durante este periodo. Si sube mucho, normalmente significa que has gastado más electricidad.",
        "explicacion_potencia": "Es la parte fija de la factura. La pagas aunque consumas poco, porque depende de la potencia que tienes contratada en casa.",
        "explicacion_impuestos": "Son los impuestos y cargos añadidos a la factura. No dependen solo de lo que consumes, también influyen normas y peajes.",
        "guion_audio": "Hola. Aquí tienes un resumen sencillo de tu factura.",
    }
    aliases = {
        "periodo": ["periodo", "periodo_factura"], "compania": ["compania", "compañia", "empresa", "comercializadora"],
        "total_pagar": ["total", "total_pagar", "importe_total"], "consumo_kwh": ["consumo", "consumo_kwh"],
        "potencia_kw": ["potencia", "potencia_kw"], "impuestos": ["impuestos"],
        "explicacion_total": ["explicacion_total"], "explicacion_consumo": ["explicacion_consumo"],
        "explicacion_potencia": ["explicacion_potencia"], "explicacion_impuestos": ["explicacion_impuestos"],
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


def deduplicar_historial(df):
    if df.empty:
        return df
    tmp = df.copy()
    if "compania" in tmp.columns:
        tmp["compania"] = tmp["compania"].apply(normalizar_compania)
    tmp["_periodo_norm"] = tmp["periodo"].astype(str).str.strip().str.lower()
    tmp["_total_norm"] = pd.to_numeric(tmp["total_pagar"], errors="coerce").round(2)
    tmp = tmp.drop_duplicates(subset=["_periodo_norm", "_total_norm"], keep="first")
    return tmp.drop(columns=["_periodo_norm", "_total_norm"], errors="ignore")


def guardar_historial(factura):
    fila = {
        "fecha_guardado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "periodo": factura.get("periodo", "No detectado"),
        "compania": normalizar_compania(factura.get("compania", "No detectada")),
        "total_pagar": limpiar_numero(factura.get("total_pagar")),
        "consumo_kwh": limpiar_numero(factura.get("consumo_kwh")),
        "potencia_kw": limpiar_numero(factura.get("potencia_kw")),
        "impuestos": limpiar_numero(factura.get("impuestos")),
    }
    df_prev = cargar_historial()
    df_new = pd.concat([df_prev, pd.DataFrame([fila])], ignore_index=True)
    df_new = deduplicar_historial(df_new)
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


def render_metric_card(label, value, tooltip, delta=None):
    delta_html = f'<div class="metric-delta">Frente a la anterior: {esc(delta)}</div>' if delta else ''
    st.markdown(
        f'''
        <div class="metric-card">
            <div class="metric-head">
                <div class="metric-label">{esc(label)}</div>
                <div class="tooltip-wrap" tabindex="0" aria-label="Más información sobre {esc(label)}">
                    <span class="tooltip-icon">?</span>
                    <div class="tooltip-bubble">{esc(tooltip)}</div>
                </div>
            </div>
            <div class="metric-value">{esc(value)}</div>
            {delta_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_history_table(df):
    cols = ["fecha_guardado", "periodo", "compania", "total_pagar", "consumo_kwh", "potencia_kw", "impuestos"]
    labels = {
        "fecha_guardado": "Fecha",
        "periodo": "Periodo",
        "compania": "Compañía",
        "total_pagar": "Total",
        "consumo_kwh": "Consumo",
        "potencia_kw": "Potencia",
        "impuestos": "Impuestos",
    }
    show = df[cols].copy()
    html = ['<div class="history-table"><table><thead><tr>']
    for c in cols:
        html.append(f'<th>{labels[c]}</th>')
    html.append('</tr></thead><tbody>')
    for _, row in show.iterrows():
        html.append('<tr>')
        html.append(f'<td>{esc(row["fecha_guardado"])}</td>')
        html.append(f'<td>{esc(row["periodo"])}</td>')
        html.append(f'<td>{esc(normalizar_compania(row["compania"]))}</td>')
        html.append(f'<td>{fmt_euro(row["total_pagar"])}</td>')
        html.append(f'<td>{fmt_num(row["consumo_kwh"], "kWh")}</td>')
        html.append(f'<td>{fmt_num(row["potencia_kw"], "kW")}</td>')
        html.append(f'<td>{fmt_euro(row["impuestos"])}</td>')
        html.append('</tr>')
    html.append('</tbody></table></div>')
    st.markdown(''.join(html), unsafe_allow_html=True)


init_state()
st.markdown(f'<div class="rz-header"><img src="{LOGO_DATA_URI}" alt="ReciboZen"></div>', unsafe_allow_html=True)
st.markdown('<div class="panel"><div class="section-title">Sube tu factura</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Sube tu factura", label_visibility="collapsed", type=["pdf"])
if uploaded_file is not None and st.session_state.get("last_uploaded_name") != uploaded_file.name:
    reset_current_results()
    st.session_state["last_uploaded_name"] = uploaded_file.name
st.markdown('<div class="hint">Sube un PDF de tu factura para analizarlo.</div></div>', unsafe_allow_html=True)

analizar = st.button("Analizar factura", type="primary", use_container_width=True)
spinner_placeholder = st.empty()
if uploaded_file and analizar:
    spinner_placeholder.markdown('<div class="spinner-card"><div class="spinner-dot"></div><div><strong>Analizando factura…</strong><div style="color:#486171;margin-top:.15rem;">Esto puede tardar unos segundos.</div></div></div>', unsafe_allow_html=True)
    try:
        time.sleep(0.35)
        texto_raw = leer_pdf(uploaded_file)
        extraidos_pdf = extraer_desde_pdf(texto_raw)
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
Reglas: español de lectura fácil, frases muy cortas, sin markdown, tooltips explicativos pero breves.
Factura:
{texto_raw[:12000]}
        """
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        parsed = parsear_bloques(response.text)
        parsed = combinar_datos(parsed, extraidos_pdf)
        st.session_state["factura_actual"] = parsed
        st.session_state["audio_b64"] = preparar_audio(parsed.get("guion_audio", "Resumen de la factura."))
        historial = guardar_historial(parsed)
        st.session_state["factura_anterior"] = historial.iloc[-2].to_dict() if len(historial) >= 2 else None
    except Exception as e:
        st.error(f"No se pudo analizar la factura: {e}")
    finally:
        spinner_placeholder.empty()

factura = st.session_state.get("factura_actual")
anterior = st.session_state.get("factura_anterior")
if factura:
    st.markdown('<div class="panel"><div class="section-title">Datos de esta factura</div>', unsafe_allow_html=True)
    st.markdown(f'''
        <div class="data-grid">
            <div class="data-card"><div class="data-label">Periodo</div><div class="data-value">{esc(factura.get("periodo", "No detectado"))}</div></div>
            <div class="data-card"><div class="data-label">Compañía</div><div class="data-value">{esc(normalizar_compania(factura.get("compania", "No detectada")))}</div></div>
        </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        render_metric_card("Total a pagar", fmt_euro(factura.get("total_pagar")), factura.get("explicacion_total"), calcular_delta(factura.get("total_pagar"), anterior.get("total_pagar") if anterior else None, "€") if anterior else None)
        render_metric_card("Consumo", fmt_num(factura.get("consumo_kwh"), "kWh"), factura.get("explicacion_consumo"), calcular_delta(factura.get("consumo_kwh"), anterior.get("consumo_kwh") if anterior else None, "kWh") if anterior else None)
    with c2:
        render_metric_card("Potencia contratada", fmt_num(factura.get("potencia_kw"), "kW"), factura.get("explicacion_potencia"), calcular_delta(factura.get("potencia_kw"), anterior.get("potencia_kw") if anterior else None, "kW") if anterior else None)
        render_metric_card("Impuestos", fmt_euro(factura.get("impuestos")), factura.get("explicacion_impuestos"), calcular_delta(factura.get("impuestos"), anterior.get("impuestos") if anterior else None, "€") if anterior else None)

    st.markdown('<div class="audio-panel"><div class="audio-title">Escuchar resumen</div><div class="audio-actions">', unsafe_allow_html=True)
    col_a, col_b = st.columns(2, gap="medium")
    with col_a:
        st.markdown('<div class="listen-btn">', unsafe_allow_html=True)
        if st.button("Escuchar", key="btn_escuchar", use_container_width=True):
            st.session_state["reproducir"] = True
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("Parar", key="btn_parar", use_container_width=True):
            st.session_state["reproducir"] = False
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.get("reproducir") and st.session_state.get("audio_b64"):
        st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=0)

hist = deduplicar_historial(cargar_historial())
if not hist.empty:
    if os.path.exists(HISTORIAL_CSV):
        hist.to_csv(HISTORIAL_CSV, index=False)
    st.markdown('<div class="panel"><div class="section-title">Historial de facturas guardadas</div>', unsafe_allow_html=True)
    render_history_table(hist.sort_values("fecha_guardado", ascending=False))
    st.markdown('<div class="history-note">Solo se guarda una vez cada factura si coincide el mismo periodo y el mismo importe total.</div>', unsafe_allow_html=True)
    st.download_button("Descargar historial facturas", data=hist.to_csv(index=False).encode("utf-8"), file_name="recibozen_historial.csv", mime="text/csv", use_container_width=True)
    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("Borrar historial", key="btn_borrar_historial", use_container_width=True):
        if os.path.exists(HISTORIAL_CSV):
            os.remove(HISTORIAL_CSV)
        st.session_state["factura_anterior"] = None
        st.success("Historial borrado correctamente.")
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)
