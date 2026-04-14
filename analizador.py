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
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-3-flash-preview", "gemini-2.0-flash"]
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
<style>
:root {
    --bg: #f4f7f8;
    --surface: #ffffff;
    --surface-2: #f8fbfb;
    --text: #17313a;
    --muted: #5f7480;
    --line: #dbe6ea;
    --primary: #0f766e;
    --soft: #dff4ef;
    --success: #1f8f5f;
    --warn: #a06a17;
    --danger: #ba3a34;
    --shadow: 0 10px 30px rgba(11, 48, 58, 0.08);
}
html, body, [data-testid="stAppViewContainer"] { background: radial-gradient(circle at top right, #eef8f5 0%, #f4f7f8 38%, #f6f8fb 100%) !important; }
body, p, div, label, li, span, small { color: var(--text) !important; }
.block-container { max-width: 1180px; padding-top: 1.2rem; padding-bottom: 3rem; }
.hero { background: linear-gradient(135deg, rgba(255,255,255,.95), rgba(247,252,251,.9)); border: 1px solid rgba(15,118,110,.10); border-radius: 28px; padding: 1.35rem; box-shadow: var(--shadow); margin-bottom: 1rem; }
.hero-title { font-size: clamp(1.9rem, 2.8vw, 3rem); line-height: 1.05; margin: 0 0 .35rem 0; letter-spacing: -0.02em; }
.hero-sub { color: var(--muted) !important; font-size: 1.02rem; max-width: 60ch; }
.pill-row { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: .9rem; }
.pill { background: var(--soft); color: var(--primary) !important; border: 1px solid rgba(15,118,110,.12); border-radius: 999px; padding: .45rem .8rem; font-size: .92rem; font-weight: 700; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 20px; padding: 1rem; box-shadow: var(--shadow); margin-bottom: 1rem; }
.soft-card { background: var(--surface-2); border: 1px solid #e5eff1; border-radius: 14px; padding: .95rem; height: 100%; }
.metric-card { background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1rem; box-shadow: var(--shadow); min-height: 132px; }
.metric-label { font-size: .92rem; color: var(--muted) !important; margin-bottom: .35rem; font-weight: 700; }
.metric-value { font-size: clamp(1.55rem, 2.5vw, 2.25rem); line-height: 1.05; font-weight: 800; letter-spacing: -0.02em; }
.metric-help { margin-top: .45rem; color: var(--muted) !important; font-size: .95rem; }
.section-title { font-size: 1.18rem; margin-bottom: .8rem; font-weight: 800; }
.summary-box { background: linear-gradient(180deg, #fdfefe 0%, #f6fbfa 100%); border: 1px solid var(--line); border-radius: 18px; padding: 1rem; box-shadow: var(--shadow); }
.big-text { font-size: 1.06rem; line-height: 1.7; }
.helper-list { margin: 0; padding-left: 1.15rem; }
.helper-list li { margin-bottom: .5rem; }
.small-note { color: var(--muted) !important; font-size: .95rem; }
.history-table-wrap { overflow-x: auto; border-radius: 16px; border: 1px solid var(--line); }
.history-table { width: 100%; border-collapse: collapse; background: var(--surface); }
.history-table th, .history-table td { text-align: left; padding: .82rem .8rem; border-bottom: 1px solid #ebf0f2; font-size: .95rem; }
.history-table th { background: #f8fbfb; color: var(--muted) !important; font-weight: 800; }
.audio-box { background: #f8fbfb; border: 1px solid var(--line); border-radius: 16px; padding: .8rem; }
.badge-ok { display:inline-block; padding:.3rem .65rem; border-radius:999px; background:#e7f7ef; color:#1f8f5f !important; font-weight:800; font-size:.88rem; }
.badge-warn { display:inline-block; padding:.3rem .65rem; border-radius:999px; background:#fff4df; color:#a06a17 !important; font-weight:800; font-size:.88rem; }
.footer-note { text-align:center; color: var(--muted) !important; margin-top: 1rem; font-size: .9rem; }
div[data-testid="stFileUploader"] section { background: rgba(255,255,255,.82) !important; border: 2px dashed rgba(15,118,110,.3) !important; border-radius: 18px !important; }
.stButton > button { border-radius: 14px !important; height: 52px !important; font-weight: 800 !important; border: none !important; }
.stButton > button[kind="primary"] { background: var(--primary) !important; color: white !important; }
div[data-testid="column"] .stButton > button { background: white !important; color: var(--text) !important; border: 1px solid var(--line) !important; }
@media (max-width: 768px) { .hero { padding: 1rem; border-radius: 22px; } .metric-card { min-height: unset; } }
</style>
""", unsafe_allow_html=True)


def init_history_file():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "periodo", "empresa", "total_eur", "consumo_kwh",
                "potencia_kw", "impuestos_eur", "consejo", "resumen", "modelo", "proveedor"
            ])


def read_history():
    init_history_file()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_history_item(item):
    init_history_file()
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            item.get("timestamp", ""), item.get("periodo", ""), item.get("empresa", ""),
            item.get("total_eur", ""), item.get("consumo_kwh", ""), item.get("potencia_kw", ""),
            item.get("impuestos_eur", ""), item.get("consejo", ""), item.get("resumen", ""),
            item.get("modelo", ""), item.get("proveedor", "")
        ])


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
    data = uploaded_file.getvalue()
    return hashlib.sha256(data).hexdigest()


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
                raise RuntimeError("Gemini respondió sin texto.")
            return text, model, "Gemini"
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
                            return text, model, "Gemini"
                    except Exception as e2:
                        last_error = e2
                continue
    raise RuntimeError(f"Gemini no disponible: {last_error}")


def call_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("No hay OPENROUTER_API_KEY configurada.")
    if requests is None:
        raise RuntimeError("Falta instalar requests.")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.io",
        "X-Title": "ReciboZen"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Responde siempre en español claro."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
    if r.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:400]}")
    data = r.json()
    text = data["choices"][0]["message"]["content"].strip()
    used_model = data.get("model", OPENROUTER_MODEL)
    return text, used_model, "OpenRouter"


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
    t = t.replace("€", "").replace("EUR", "").replace("eur", "")
    t = t.replace("kWh", "").replace("kw", "").replace("kW", "")
    t = t.replace(" ", "")
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


def render_history_table(rows):
    if not rows:
        st.info("Todavía no hay historial guardado.")
        return
    html = ['<div class="history-table-wrap"><table class="history-table"><thead><tr>']
    cols = ["Fecha", "Periodo", "Empresa", "Total", "Consumo", "Proveedor"]
    for c in cols:
        html.append(f"<th>{escape(c)}</th>")
    html.append("</tr></thead><tbody>")
    for r in reversed(rows[-24:]):
        html.append("<tr>")
        html.append(f"<td>{escape(str(r.get('timestamp',''))[:16].replace('T',' '))}</td>")
        html.append(f"<td>{escape(r.get('periodo','') or '—')}</td>")
        html.append(f"<td>{escape(r.get('empresa','') or '—')}</td>")
        html.append(f"<td>{escape(format_eur(limpiar_numero(r.get('total_eur'))))}</td>")
        html.append(f"<td>{escape(format_num(limpiar_numero(r.get('consumo_kwh')), 'kWh'))}</td>")
        html.append(f"<td>{escape(r.get('proveedor','') or '—')}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


rows = read_history()
prev = latest_previous(rows)
cache = read_cache()

st.markdown('''
<div class="hero">
  <div class="pill">Ahorro inteligente</div>
  <h1 class="hero-title">ReciboZen</h1>
  <p class="hero-sub">Tu factura explicada con lenguaje claro, historial mensual y sistema automático para gastar la mínima cuota posible.</p>
  <div class="pill-row">
    <div class="pill">Primero Gemini</div>
    <div class="pill">Si falla, usa OpenRouter gratis</div>
    <div class="pill">Caché para no repetir gasto</div>
    <div class="pill">Diseño claro y responsive</div>
  </div>
</div>
''', unsafe_allow_html=True)

left, right = st.columns([1.45, 1], gap="large")

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Sube tu factura</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Carga aquí el PDF", type="pdf", label_visibility="collapsed")
    periodo_manual = st.text_input("Periodo de la factura (opcional)", placeholder="Ejemplo: marzo 2026")
    empresa_manual = st.text_input("Compañía (opcional)", placeholder="Ejemplo: Endesa")
    analizar = st.button("Analizar factura", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Estado del sistema</div>', unsafe_allow_html=True)
    if GOOGLE_API_KEY:
        st.markdown("<span class='badge-ok'>Gemini configurado</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-warn'>Gemini no configurado</span>", unsafe_allow_html=True)
    st.write("")
    if OPENROUTER_API_KEY:
        st.markdown("<span class='badge-ok'>OpenRouter configurado</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-warn'>OpenRouter no configurado</span>", unsafe_allow_html=True)
    st.markdown("<p class='small-note'>Si Gemini agota cuota, la app intenta seguir con OpenRouter.</p>", unsafe_allow_html=True)
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

with left:
    if analizar:
        try:
            if not uploaded_file:
                raise RuntimeError("Primero tienes que subir un PDF.")

            factura_hash = pdf_hash(uploaded_file)
            texto_raw = leer_pdf(uploaded_file)
            if not texto_raw:
                raise RuntimeError("No se pudo extraer texto del PDF.")

            if factura_hash in cache:
                cached = cache[factura_hash]
                meta = cached["meta"]
                html_txt = cached["html_txt"]
                audio_txt = cached["audio_txt"]
                modelo = cached["modelo"]
                proveedor = cached["proveedor"]
                origen = "caché"
            else:
                with st.spinner("Analizando la factura... si Gemini no puede, probaré otra vía gratis."):
                    raw_text, modelo, proveedor = analizar_con_fallback(texto_raw)
                    meta, html_txt, audio_txt = parsear_bloques(raw_text)
                    cache[factura_hash] = {
                        "meta": meta,
                        "html_txt": html_txt,
                        "audio_txt": audio_txt,
                        "modelo": modelo,
                        "proveedor": proveedor
                    }
                    write_cache(cache)
                    origen = "nuevo análisis"

            meta["periodo"] = periodo_manual.strip() or meta.get("periodo", "")
            meta["empresa"] = empresa_manual.strip() or meta.get("empresa", "")

            st.session_state["analisis_meta"] = meta
            st.session_state["analisis_html"] = html_txt
            st.session_state["audio_txt"] = audio_txt
            st.session_state["audio_b64"] = preparar_audio(audio_txt)
            st.session_state["modelo_usado"] = modelo
            st.session_state["proveedor_usado"] = proveedor
            st.session_state["origen_resultado"] = origen
            st.session_state["reproducir"] = False

            if origen != "caché":
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
                    "modelo": modelo,
                    "proveedor": proveedor,
                })
                rows = read_history()
                prev = latest_previous(rows)

            st.success(f"Factura lista. Fuente: {origen}. Proveedor usado: {proveedor}.")

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

        st.caption(f"Proveedor: {st.session_state.get('proveedor_usado','—')} · Modelo: {st.session_state.get('modelo_usado','—')} · Origen: {st.session_state.get('origen_resultado','—')}")

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
            st.markdown(st.session_state["analisis_html"], unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with b:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Datos de esta factura</div>', unsafe_allow_html=True)
            st.markdown(f"<div class='soft-card'><strong>Periodo:</strong><br>{escape(meta.get('periodo') or 'No indicado')}</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='soft-card'><strong>Empresa:</strong><br>{escape(meta.get('empresa') or 'No indicada')}</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='soft-card'><strong>Consejo útil:</strong><br>{escape(meta.get('consejo') or 'Sin consejo disponible')}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Escuchar resumen</div>', unsafe_allow_html=True)
            st.markdown('<div class="audio-box">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Reproducir", use_container_width=True):
                    st.session_state["reproducir"] = True
            with col2:
                if st.button("⏹️ Parar", use_container_width=True):
                    st.session_state["reproducir"] = False
            st.caption(st.session_state.get("audio_txt", ""))
            if st.session_state.get("reproducir"):
                st.components.v1.html(f'<audio autoplay controls style="width:100%;"><source src="data:audio/mp3;base64,{st.session_state["audio_b64"]}" type="audio/mp3"></audio>', height=50)
            st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Comparación e historial</div>', unsafe_allow_html=True)
    if rows:
        if pd is not None and len(rows) >= 2:
            try:
                df = pd.DataFrame(rows)
                df["total_num"] = df["total_eur"].apply(limpiar_numero)
                df["periodo_view"] = df["periodo"].replace("", pd.NA).fillna(df["timestamp"].str[:7])
                chart_df = df[["periodo_view", "total_num"]].dropna().tail(12)
                if not chart_df.empty:
                    st.line_chart(chart_df.set_index("periodo_view"))
            except Exception:
                pass
        render_history_table(rows)
    else:
        st.info("Cuando analices la primera factura, aquí verás la comparación entre meses.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="footer-note">ReciboZen · 2026 · Modo ahorro: Gemini + OpenRouter + caché</div>', unsafe_allow_html=True)
