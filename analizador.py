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

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="ReciboZen", page_icon="🧘", layout="centered")

HISTORIAL_CSV = "recibozen_historial.csv"

API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if not API_KEY:
    st.error("Falta configurar GOOGLE_API_KEY en Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ── LOGO ──────────────────────────────────────────────────────────────────────
LOGO_DATA_URI = (
    "data:image/svg+xml;utf8,"
    "%3Csvg%20width%3D%22224%22%20height%3D%2296%22%20viewBox%3D%220%200%20420%2096%22"
    "%20fill%3D%22none%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20"
    "role%3D%22img%22%20aria-label%3D%22Logotipo%20de%20ReciboZen%22%3E"
    "%3Cdefs%3E%3ClinearGradient%20id%3D%22rzg%22%20x1%3D%2216%22%20y1%3D%2216%22"
    "%20x2%3D%2280%22%20y2%3D%2280%22%20gradientUnits%3D%22userSpaceOnUse%22%3E"
    "%3Cstop%20stop-color%3D%22%235BB7FF%22%2F%3E"
    "%3Cstop%20offset%3D%221%22%20stop-color%3D%22%231677C8%22%2F%3E"
    "%3C%2FlinearGradient%3E%3C%2Fdefs%3E"
    "%3Crect%20x%3D%228%22%20y%3D%228%22%20width%3D%2280%22%20height%3D%2280%22"
    "%20rx%3D%2224%22%20fill%3D%22%23EFF7FF%22%2F%3E"
    "%3Cpath%20d%3D%22M31%2032.5C31%2028.357%2034.357%2025%2038.5%2025H57.5"
    "C61.642%2025%2065%2028.357%2065%2032.5V63.5C65%2067.642%2061.642%2071"
    "%2057.5%2071H38.5C34.357%2071%2031%2067.642%2031%2063.5V32.5Z%22"
    "%20fill%3D%22url(%23rzg)%22%2F%3E"
    "%3Cpath%20d%3D%22M42.5%2041.5H53.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22"
    "%20stroke-linecap%3D%22round%22%2F%3E"
    "%3Cpath%20d%3D%22M42.5%2049.5H54.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22"
    "%20stroke-linecap%3D%22round%22%20opacity%3D%220.9%22%2F%3E"
    "%3Cpath%20d%3D%22M42.5%2057.5H50.5%22%20stroke%3D%22white%22%20stroke-width%3D%223.5%22"
    "%20stroke-linecap%3D%22round%22%20opacity%3D%220.86%22%2F%3E"
    "%3Cpath%20d%3D%22M66%2057C71.333%2053.667%2076.667%2053.667%2082%2057%22"
    "%20stroke%3D%22%237CC7FF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22%2F%3E"
    "%3Cpath%20d%3D%22M66%2065C71.333%2061.667%2076.667%2061.667%2082%2065%22"
    "%20stroke%3D%22%23A6DBFF%22%20stroke-width%3D%224%22%20stroke-linecap%3D%22round%22%2F%3E"
    "%3Ctext%20x%3D%22108%22%20y%3D%2249%22%20fill%3D%22%23163042%22"
    "%20font-family%3D%22Manrope%2C%20Inter%2C%20Arial%2C%20sans-serif%22"
    "%20font-size%3D%2234%22%20font-weight%3D%22800%22"
    "%20letter-spacing%3D%22-0.02em%22%3EReciboZen%3C%2Ftext%3E"
    "%3Ctext%20x%3D%22110%22%20y%3D%2269%22%20fill%3D%22%236B8295%22"
    "%20font-family%3D%22Inter%2C%20Arial%2C%20sans-serif%22"
    "%20font-size%3D%2214%22%20font-weight%3D%22500%22%3E"
    "Tu%20factura%20explicada%20con%20calma%3C%2Ftext%3E%3C%2Fsvg%3E"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
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
  font-family: Inter, sans-serif !important;
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

.section-title {
  font-family: Manrope, sans-serif;
  font-size: 1.12rem;
  font-weight: 800;
  margin: 0 0 .85rem 0;
}

.hint { margin-top:.6rem; color:var(--muted); font-size:.98rem; }

.data-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.85rem; }
.data-card, .metric-card {
  background:#fff;
  border:1px solid var(--line);
  border-radius:20px;
  padding:1rem .95rem;
  box-shadow:0 8px 20px rgba(18,48,70,.05);
}
.data-label, .metric-label { font-size:.92rem; color:var(--muted); margin-bottom:.28rem; }
.data-value { font-size:1.05rem; font-weight:700; color:var(--text); }

.metric-head { display:flex; align-items:center; gap:.45rem; margin-bottom:.35rem; }
.metric-value { font-size:2rem; line-height:1.05; font-weight:800; color:var(--text); letter-spacing:-.02em; }
.metric-delta { margin-top:.45rem; color:var(--muted); font-size:.92rem; font-weight:600; }

.tooltip-wrap { position:relative; display:inline-flex; align-items:center; }
.tooltip-icon {
  display:inline-flex; align-items:center; justify-content:center;
  width:22px; height:22px; border-radius:999px;
  border:1px solid rgba(15,95,166,.24);
  background:#eef6ff; color:var(--primary);
  font-size:.82rem; font-weight:800; cursor:help;
  box-shadow:0 3px 8px rgba(15,95,166,.08);
}
.tooltip-bubble {
  position:absolute; left:0; top:calc(100% + 8px);
  width:min(290px, 78vw); z-index:60;
  background:#123046; color:#ffffff !important;
  padding:.9rem 1rem; border-radius:14px;
  box-shadow:0 16px 32px rgba(18,48,70,.22);
  font-size:.93rem; line-height:1.46;
  opacity:0; visibility:hidden;
  transform:translateY(4px);
  transition:all .16s ease;
  pointer-events:none;
}
.tooltip-wrap:hover .tooltip-bubble,
.tooltip-wrap:focus-within .tooltip-bubble,
.tooltip-wrap:active .tooltip-bubble { opacity:1; visibility:visible; transform:translateY(0); }
.tooltip-bubble::before {
  content:''; position:absolute; top:-6px; left:12px;
  width:12px; height:12px; background:#123046; transform:rotate(45deg);
}

.spinner-card {
  display:flex; align-items:center; gap:.85rem;
  background:linear-gradient(180deg,#f5fbff 0%,#edf6ff 100%);
  border:1px solid rgba(15,95,166,.16);
  border-radius:18px; padding:1rem 1.05rem; margin-bottom:1rem;
}
.spinner-dot {
  width:18px; height:18px; border-radius:50%;
  border:3px solid rgba(15,95,166,.18);
  border-top-color:var(--primary);
  animation:rzspin 1s linear infinite;
}
@keyframes rzspin { to { transform:rotate(360deg); } }

/* ── BOTONES ── */
div.stButton button,
.stDownloadButton button,
.stFileUploader button,
[data-testid="stBaseButton-primary"],
.stButton button[kind="primary"] {
  width:100% !important;
  min-height:54px !important;
  border-radius:18px !important;
  font-size:1rem !important;
  font-weight:800 !important;
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  text-shadow:0 1px 1px rgba(0,0,0,.22) !important;
  background:linear-gradient(180deg,var(--primary-2) 0%,var(--primary) 100%) !important;
  border:none !important;
  box-shadow:0 12px 28px rgba(15,95,166,.22) !important;
  margin-top:0 !important;
  margin-bottom:0 !important;
  white-space:nowrap !important;
}
div.stButton button *,
.stDownloadButton button *,
.stFileUploader button * {
  color:#ffffff !important;
  fill:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
}

/* Escuchar → azul */
.listen-btn div.stButton button {
  background:linear-gradient(180deg,var(--primary-2) 0%,var(--primary) 100%) !important;
  box-shadow:0 12px 28px rgba(15,95,166,.22) !important;
}

/* Parar / Borrar → rojo */
.stop-btn div.stButton button,
.danger-btn div.stButton button {
  background:linear-gradient(180deg,var(--danger-2) 0%,var(--danger) 100%) !important;
  box-shadow:0 12px 28px rgba(179,52,59,.22) !important;
}

/* Grid de audio alineado */
.audio-actions {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;
  align-items:stretch;
  margin-top:.25rem;
}
.audio-actions div { min-width:0; }
.audio-actions .stButton { height:100%; }
.audio-actions .stButton button { height:54px !important; }

/* Uploader limpio */
.stFileUploader section {
  background:#f8fbfe !important;
  border:2px dashed rgba(31,125,203,.22) !important;
  border-radius:24px !important;
  padding:
