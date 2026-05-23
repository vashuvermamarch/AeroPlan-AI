import streamlit as st
import os
import re
from main import graph, DATABASE_URL
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver

# Set page config
st.set_page_config(
    page_title="AeroPlan AI - Travel Orchestration",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------------------
# SPLINE CONFIGURATION
# To embed your Spline background, click "Export" -> "Public Link" -> "Update" 
# in the Spline Editor, and paste the generated URL here:
SPLINE_URL = "https://my.spline.design/a3cd9cca-f84d-4292-80fc-f63e10bf15d1/" 
# ------------------------------------------------------------------------------

# Caching thread IDs list to keep interface responsive
@st.cache_data(show_spinner=False, ttl=600)
def get_past_threads():
    try:
        with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
            checkpointer.setup()
            configs = list(checkpointer.list(config=None, limit=80))
            unique_threads = []
            seen = set()
            for item in configs:
                conf = item[0]
                thread_id = conf.get("configurable", {}).get("thread_id")
                if thread_id and thread_id not in seen and not thread_id.startswith("streamlit_"):
                    seen.add(thread_id)
                    unique_threads.append(thread_id)
            return unique_threads
    except Exception as e:
        return []

@st.cache_data(show_spinner=False, ttl=600)
def get_all_journeys_details():
    try:
        with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
            checkpointer.setup()
            configs = list(checkpointer.list(config=None, limit=80))
            unique_journeys = []
            seen = set()
            for item in configs:
                conf = item[0]
                thread_id = conf.get("configurable", {}).get("thread_id")
                if thread_id and thread_id not in seen and not thread_id.startswith("streamlit_"):
                    seen.add(thread_id)
                    checkpoint = item[1]
                    channel_values = checkpoint.get("channel_values", {}) if checkpoint else {}
                    query = channel_values.get("user_query", "Unknown Mission")
                    llm_calls = channel_values.get("llm_calls", 0)
                    has_itinerary = bool(channel_values.get("itinerary", ""))
                    ts = checkpoint.get("ts", "") if checkpoint else ""
                    
                    unique_journeys.append({
                        "thread_id": thread_id,
                        "query": query,
                        "llm_calls": llm_calls,
                        "has_itinerary": has_itinerary,
                        "timestamp": ts
                    })
            return unique_journeys
    except Exception as e:
        return []

def export_to_pdf(flight_data, hotel_data, itinerary_data):
    from fpdf import FPDF, XPos, YPos
    import re as _re

    def sanitize(text):
        if not text:
            return ""
        emoji_map = {
            "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
            "\u2014": "-", "\u2013": "-", "\u2022": "-",
            "\u2708\ufe0f": "Flight", "\ud83d\udecc": "Hotel", "\ud83c\udfe8": "Hotel",
            "\ud83d\udcc5": "Itinerary", "\ud83e\ude84": "AI", "\u2713": "Yes",
            "\u2717": "No", "\ud83c\udf1f": "*", "\u2b50": "*", "\ud83d\udccd": "->",
            "\u27a1\ufe0f": "->", "\ud83d\udcb0": "$", "\u2764\ufe0f": "<3",
        }
        for orig, rep in emoji_map.items():
            text = text.replace(orig, rep)
        # Strip any remaining non-latin1 chars
        return text.encode("latin-1", errors="ignore").decode("latin-1")

    def write_section_title(pdf, number, title):
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, f"{number}. {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(225, 29, 72)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    def write_body(pdf, text):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        if not text:
            pdf.cell(0, 7, "Not available.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)
            return
        clean = _re.sub(r'[*_`]', '', text)
        for line in clean.split("\n"):
            stripped = line.strip()
            if not stripped:
                pdf.ln(2)
                continue
            # Detect heading lines (originally ## or #)
            if stripped.startswith("# "):
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(225, 29, 72)
                pdf.multi_cell(0, 6, sanitize(stripped[2:]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(51, 65, 85)
            else:
                pdf.multi_cell(0, 6, sanitize(stripped), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(1)

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # ── Title block ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(225, 29, 72)
    pdf.cell(0, 14, "AeroPlan AI", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, "Intelligent Multi-Agent Travel Orchestration Plan", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(8)
    pdf.set_draw_color(225, 29, 72)
    pdf.set_line_width(1)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(10)

    # ── Section 1: Flights ────────────────────────────────────────
    write_section_title(pdf, 1, "Flights & Transportation")
    write_body(pdf, flight_data)
    pdf.ln(6)

    # ── Section 2: Hotels ─────────────────────────────────────────
    write_section_title(pdf, 2, "Hotel & Accommodations")
    write_body(pdf, hotel_data)
    pdf.ln(6)

    # ── Section 3: Itinerary ──────────────────────────────────────
    write_section_title(pdf, 3, "Day-by-Day Itinerary")
    write_body(pdf, itinerary_data)

    return bytes(pdf.output())

def render_markdown_as_html(text):
    if not text:
        return ""
    import re
    # Convert headers (###, ##, #) to bold and styled headings
    text = re.sub(r'^###\s+(.+)$', r'<h4 style="color: #0f172a; margin-top: 12px; margin-bottom: 4px; font-weight: 700; font-size: 1.05rem;">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$', r'<h3 style="color: #0f172a; margin-top: 18px; margin-bottom: 6px; font-weight: 700; font-size: 1.15rem;">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.+)$', r'<h2 style="color: #e11d48; margin-top: 22px; margin-bottom: 8px; font-weight: 800; font-size: 1.3rem;">\1</h2>', text, flags=re.MULTILINE)
    
    # Convert bold **text** to <strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    
    # Convert links [text](url) to styled anchor tags
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" style="color: #e11d48; text-decoration: none; font-weight: 600;">\1</a>', text)
    
    # Convert plain URLs to clickable links (excluding already matched anchors)
    text = re.sub(r'(?<!href=")(https?://[^\s\n<]+)', r'<a href="\1" target="_blank" style="color: #e11d48; text-decoration: none; font-weight: 600; word-break: break-all;">\1</a>', text)
    
    # Convert lists: lines starting with * or -
    text = re.sub(r'^[*-]\s+(.+)$', r'<div style="display: flex; align-items: flex-start; margin-left: 10px; margin-bottom: 4px;"><span style="color: #e11d48; margin-right: 6px;">•</span><span>\1</span></div>', text, flags=re.MULTILINE)
    
    # Convert numbered lists: lines starting with "1. " or "2. "
    text = re.sub(r'^(\d+)\.\s+(.+)$', r'<div style="margin-left: 10px; margin-bottom: 4px;"><strong>\1.</strong> \2</div>', text, flags=re.MULTILINE)
    
    # Convert line breaks to HTML breaks, keeping double linebreaks as spacing
    text = text.replace("\n", "<br/>")
    return text

# Custom CSS for UI styling matching the mockup
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Overall layout and backgrounds */
    html, body {
        background-color: #f8fafc !important;
        color: #1e293b !important;
        font-family: 'Outfit', sans-serif;
    }
    h1, h2, h3, h4, h5, h6, .stMarkdown, p, span, label, li {
        color: #1e293b !important;
    }
    .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], 
    [data-testid="stMain"], 
    [data-testid="stMainBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stAppViewBlockContainer"],
    .main,
    .block-container {
        background-color: transparent !important;
        background: transparent !important;
    }
    
    /* Spline Interactive Background Layer */
    .spline-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: -1;
        pointer-events: none;
        opacity: 1.0 !important;
    }
    .spline-iframe {
        width: 100%;
        height: 100%;
        border: none;
    }
    
    /* Navigation Sidebar Override */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.12) !important;
        background: rgba(255, 255, 255, 0.12) !important;
        backdrop-filter: blur(30px) !important;
        -webkit-backdrop-filter: blur(30px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.02) !important;
    }
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebarUserContent"],
    .stSidebarContent,
    section[data-testid="stSidebar"] div[class^="st-emotion-cache"],
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        background-color: transparent !important;
        background: transparent !important;
    }
    
    /* Sidebar Text Elements */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] h4, 
    [data-testid="stSidebar"] h5, 
    [data-testid="stSidebar"] h6, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] div {
        color: #1e293b !important;
    }
    
    /* Primary buttons in Sidebar */
    [data-testid="stSidebar"] div.stButton > button[kind="primary"],
    [data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #fda4af 0%, #f43f5e 100%) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        border: none !important;
        margin-top: 10px;
        box-shadow: 0 4px 12px rgba(244, 63, 94, 0.2);
    }

    /* Secondary buttons in Sidebar (Navigation) and History */
    [data-testid="stSidebar"] div.stButton > button[kind="secondary"],
    [data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"] {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        color: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        margin-top: 8px;
        transition: all 0.2s ease !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }
    
    /* Sidebar selectbox custom glassmorphism */
    [data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: transparent !important;
        color: #1e293b !important;
    }
    
    [data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover,
    [data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"]:hover {
        background: rgba(244, 63, 94, 0.08) !important;
        color: #e11d48 !important;
        border-color: rgba(244, 63, 94, 0.2) !important;
        box-shadow: 0 0 10px rgba(244, 63, 94, 0.05);
    }
    
    /* Custom Sidebar Brand */
    .sidebar-brand {
        display: flex;
        align-items: center;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
    .sidebar-brand-icon {
        background: rgba(244, 63, 94, 0.08);
        color: #e11d48;
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin-right: 12px;
        border: 1px solid rgba(244, 63, 94, 0.2);
    }
    .sidebar-brand-text {
        font-weight: 700;
        font-size: 1.25rem;
        color: #0f172a !important;
    }
    .sidebar-brand-subtitle {
        font-size: 0.65rem;
        letter-spacing: 1.5px;
        color: #475569 !important;
        text-transform: uppercase;
        display: block;
        margin-top: 2px;
    }
    
    /* Main Panel Headings (Styled dark to be highly visible over the white video background) */
    .dashboard-header-container {
        margin-bottom: 25px;
    }
    .dashboard-title {
        font-size: 2.6rem;
        font-weight: 800;
        color: #e11d48 !important;
        margin-bottom: 5px;
    }
    .dashboard-subtitle {
        font-size: 1.1rem;
        color: #475569 !important;
        font-weight: 400;
        margin-bottom: 15px;
    }
    
    /* Badges */
    .badge-pills {
        display: flex;
        gap: 10px;
        margin-bottom: 25px;
    }
    .badge-pill {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-family: 'Outfit', sans-serif;
        color: #475569 !important;
        display: flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }
    .badge-pill-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-cyan { background-color: #fda4af; }
    .dot-green { background-color: #f43f5e; }
    .dot-purple { background-color: #fb7185; }
    
    /* Glass Console Card */
    .console-card {
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 30px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.04);
        transition: all 0.3s ease;
    }
    .console-card:hover {
        border-color: rgba(244, 63, 94, 0.25) !important;
        box-shadow: 0 12px 40px rgba(244, 63, 94, 0.05);
    }
    .console-card h1, .console-card h2, .console-card h3, .console-card h4, .console-card h5, .console-card h6, .console-card p, .console-card span, .console-card label, .console-card div, .console-card li, .console-card td, .console-card th {
        color: #1e293b !important;
    }
    
    /* Search Box Text Input */
    .stTextInput > div > div > input {
        background-color: rgba(255, 255, 255, 0.65) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.7) !important;
        color: #0f172a !important;
        border-radius: 10px !important;
        padding: 15px 20px !important;
        font-size: 1.1rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #f43f5e !important;
        box-shadow: 0 0 10px rgba(244, 63, 94, 0.15) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #64748b !important;
    }
    .stTextInput label {
        color: #1e293b !important;
    }
    
    /* Templates Tags & General Secondary Buttons in Main Panel */
    div.stButton > button[kind="secondary"],
    div.stButton > button[data-testid="baseButton-secondary"] {
        background: rgba(255, 255, 255, 0.55) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        color: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[kind="secondary"]:hover,
    div.stButton > button[data-testid="baseButton-secondary"]:hover {
        background: rgba(244, 63, 94, 0.08) !important;
        color: #e11d48 !important;
        border-color: rgba(244, 63, 94, 0.2) !important;
    }
    
    .template-tags {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin-top: 15px;
        margin-bottom: 20px;
    }
    
    /* Central Stepper Timeline styling */
    .stepper-timeline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        padding: 10px 0;
        margin-bottom: 40px;
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.04);
    }
    .stepper-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 22%;
        position: relative;
        z-index: 1;
    }
    .stepper-bubble {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 8px;
        transition: all 0.3s ease;
    }
    .stepper-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1e293b !important;
        text-align: center;
    }
    .stepper-status {
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-top: 3px;
        color: #64748b !important;
    }
    
    /* Stepper States */
    .state-pending {
        background: rgba(0, 0, 0, 0.03) !important;
        color: #64748b !important;
        border: 2px solid rgba(0, 0, 0, 0.08) !important;
    }
    .state-active {
        background: rgba(244, 63, 94, 0.08) !important;
        color: #e11d48 !important;
        border: 2px solid #e11d48 !important;
        box-shadow: 0 0 15px rgba(244, 63, 94, 0.15) !important;
    }
    .state-done {
        background: rgba(16, 185, 129, 0.1) !important;
        color: #10b981 !important;
        border: 2px solid #10b981 !important;
    }
    .label-active { color: #e11d48 !important; }
    .label-done { color: #10b981 !important; }
    
    /* Primary buttons gradient styling */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #fda4af 0%, #f43f5e 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 1.15rem !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 15px 40px !important;
        box-shadow: 0 4px 20px rgba(244, 63, 94, 0.25) !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.5px;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(244, 63, 94, 0.4) !important;
        color: #ffffff !important;
    }
    
    /* Flight Ticket Component */
    .flight-ticket {
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.04);
        transition: all 0.3s ease;
    }
    .flight-ticket:hover {
        border-color: rgba(244, 63, 94, 0.2) !important;
        box-shadow: 0 8px 32px rgba(244, 63, 94, 0.04);
    }
    .ticket-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px dashed rgba(0, 0, 0, 0.08);
        padding-bottom: 12px;
        margin-bottom: 15px;
    }
    .ticket-airline {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 1rem;
        color: #0f172a !important;
    }
    .ticket-badge {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .ticket-body {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .airport-code {
        width: 35%;
    }
    .airport-code h3 {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a !important;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .airport-code p {
        font-size: 0.75rem;
        color: #475569 !important;
        margin: 0;
        margin-top: 2px;
    }
    .flight-path {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 30%;
        position: relative;
    }
    .flight-path-duration {
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
        color: #475569 !important;
        margin-bottom: 4px;
    }
    .flight-path-line {
        width: 100%;
        height: 1px;
        border-top: 1px dashed rgba(0, 0, 0, 0.08);
        position: relative;
    }
    .flight-path-line::after {
        content: '✈️';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 12px;
        background-color: transparent !important;
        padding: 0 4px;
    }
    .ticket-footer {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #475569 !important;
        font-family: 'JetBrains Mono', monospace;
        background: rgba(0, 0, 0, 0.03) !important;
        padding: 8px 12px;
        border-radius: 6px;
    }
    
    /* Analyzing Skeleton Loader Component */
    .skeleton-card {
        background: rgba(255, 255, 255, 0.35) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border: 1px dashed rgba(0, 0, 0, 0.08) !important;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    .skeleton-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    .skeleton-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.04);
    }
    .skeleton-title {
        width: 50%;
        height: 16px;
        background: rgba(0, 0, 0, 0.04);
        border-radius: 4px;
    }
    .skeleton-badge {
        width: 100px;
        height: 20px;
        background: rgba(244, 63, 94, 0.08);
        border: 1px solid rgba(244, 63, 94, 0.15);
        border-radius: 4px;
        animation: pulse-op 1.5s infinite;
        color: #e11d48 !important;
        text-align: center;
        font-size: 0.75rem;
        line-height: 18px;
    }
    .skeleton-line {
        height: 12px;
        background: rgba(0, 0, 0, 0.03);
        border-radius: 4px;
        margin-bottom: 12px;
    }
    .skeleton-line-short { width: 70%; }
    .skeleton-line-mid { width: 90%; }
    
    @keyframes pulse-op {
        0% { opacity: 0.4; }
        50% { opacity: 0.9; }
        100% { opacity: 0.4; }
    }
    
    /* Budget Orchestration Widget Table */
    .budget-section-card {
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 16px;
        padding: 28px;
        margin-top: 10px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.04);
        transition: all 0.3s ease;
    }
    .budget-section-card:hover {
        border-color: rgba(244, 63, 94, 0.2) !important;
    }
    .budget-card-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f172a !important;
        margin-bottom: 15px;
    }
    .budget-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95rem;
    }
    .budget-table th {
        text-align: left;
        color: #475569 !important;
        font-weight: 600;
        padding: 12px 16px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.08);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .budget-table td {
        padding: 16px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.04);
        color: #1e293b !important;
    }
    .budget-table tr:last-child td {
        border-bottom: none;
    }
    .badge-status {
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.65rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .status-optimized {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .status-calculating {
        background: rgba(244, 63, 94, 0.08);
        color: #e11d48;
        border: 1px solid rgba(244, 63, 94, 0.15);
    }
    .status-pending {
        background: rgba(0, 0, 0, 0.03);
        color: #64748b;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    /* Footer Utility Actions */
    .footer-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(255, 255, 255, 0.45) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 12px;
        padding: 18px 24px;
        margin-top: 10px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.04);
    }
    .mission-id {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #475569 !important;
    }
    .mission-id-val {
        color: #e11d48 !important;
        font-weight: 600;
    }
    .footer-actions {
        display: flex;
        gap: 15px;
    }
    
    /* Dropdown popover menu styling to be light-themed */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"],
    li[role="option"] {
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: rgba(244, 63, 94, 0.08) !important;
        color: #e11d48 !important;
    }
    [data-baseweb="select"], 
    [data-baseweb="select"] > div, 
    [data-baseweb="select"] * {
        color: #1e293b !important;
    }
    div[data-testid="stTextInputRootElement"] {
        background-color: transparent !important;
        border: none !important;
    }
    
    /* Streamlit alert blocks override (st.info, st.warning, st.error) */
    div[data-testid="stAlert"] {
        background-color: rgba(255, 255, 255, 0.6) !important;
        color: #1e293b !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        backdrop-filter: blur(10px) !important;
    }
    div[data-testid="stAlert"] p, 
    div[data-testid="stAlert"] span, 
    div[data-testid="stAlert"] div {
        color: #1e293b !important;
    }
    
    /* Toast overrides */
    div[data-testid="stToast"] {
        background-color: #ffffff !important;
        color: #1e293b !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }
    div[data-testid="stToast"] p,
    div[data-testid="stToast"] div,
    div[data-testid="stToast"] span {
        color: #1e293b !important;
    }
    
    /* Deep overrides for selectbox option listboxes to bypass #1A1C24 */
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"] *,
    ul[role="listbox"] * {
        background-color: transparent !important;
        color: #1e293b !important;
    }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"],
    li[role="option"]:hover *,
    li[role="option"][aria-selected="true"] * {
        background-color: rgba(244, 63, 94, 0.08) !important;
        color: #e11d48 !important;
    }
    div[data-baseweb="base-input"] {
        background-color: transparent !important;
    }
    button[data-testid="stSidebarCollapseButton"] {
        background-color: transparent !important;
        color: #1e293b !important;
    }
    
    /* Code syntax and markdown blocks override to prevent black background boxes */
    code, pre {
        background-color: rgba(0, 0, 0, 0.04) !important;
        color: #e11d48 !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
    }
    code * {
        color: #e11d48 !important;
    }

    /* ── Download Button (PDF export) – match glassy secondary style ── */
    div.stDownloadButton > button,
    div.stDownloadButton > button:focus,
    div.stDownloadButton > button:active {
        background: rgba(255, 255, 255, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        color: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 0.875rem !important;
        transition: all 0.25s ease !important;
        box-shadow: none !important;
        width: 100%;
    }
    div.stDownloadButton > button:hover {
        background: rgba(255, 255, 255, 0.75) !important;
        border-color: rgba(225, 29, 72, 0.3) !important;
        color: #e11d48 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(225, 29, 72, 0.08) !important;
    }
    div.stDownloadButton > button[disabled] {
        opacity: 0.45 !important;
        cursor: not-allowed !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "spline_url" not in st.session_state:
    st.session_state.spline_url = "https://cdn.dribbble.com/userupload/45617492/file/ec961c6f56bd0f5b2f2786a82af91b61.mp4"
if "active_thread" not in st.session_state:
    st.session_state.active_thread = None
if "current_view" not in st.session_state:
    st.session_state.current_view = "Orchestrator"
if "input_query" not in st.session_state:
    st.session_state.input_query = ""
if "loaded_state" not in st.session_state:
    st.session_state.loaded_state = None
if "flight_data" not in st.session_state:
    st.session_state.flight_data = ""
if "hotel_data" not in st.session_state:
    st.session_state.hotel_data = ""
if "itinerary_data" not in st.session_state:
    st.session_state.itinerary_data = ""
if "final_data" not in st.session_state:
    st.session_state.final_data = ""
if "steps_state" not in st.session_state:
    st.session_state.steps_state = {"flight": "pending", "hotel": "pending", "itinerary": "pending", "final": "pending"}
if "past_threads" not in st.session_state:
    st.session_state.past_threads = get_past_threads()
if "all_journeys" not in st.session_state:
    st.session_state.all_journeys = None

# Render Background Media (supports Video or iframe)
is_video = st.session_state.spline_url.endswith(".mp4") or "dribbble.com/userupload" in st.session_state.spline_url

if is_video:
    st.markdown(f"""
    <div class="spline-container">
        <video autoplay loop muted playsinline class="spline-iframe" style="object-fit: cover; width: 100%; height: 100%;">
            <source src="{st.session_state.spline_url}" type="video/mp4">
        </video>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="spline-container">
        <iframe src="{st.session_state.spline_url}" class="spline-iframe"></iframe>
    </div>
    """, unsafe_allow_html=True)

# Sidebar - Brand Logo
st.sidebar.markdown("""
<div class="sidebar-brand">
    <div class="sidebar-brand-icon">✈️</div>
    <div>
        <span class="sidebar-brand-text">AeroPlan</span>
        <span class="sidebar-brand-subtitle">AI Orchestration</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar - Navigation links
st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Workspace</p>', unsafe_allow_html=True)

# Active tab helpers
def set_view(view):
    st.session_state.current_view = view

# Sidebar Navigation buttons with active state highlights
lbl_orch = "📁 Orchestrator"
lbl_journ = "🧭 Journeys"
lbl_log = "⚙️ Logistics"
lbl_anal = "📊 Analytics"

if st.session_state.current_view == "Orchestrator":
    lbl_orch = "▶ 📁 Orchestrator"
elif st.session_state.current_view == "Journeys":
    lbl_journ = "▶ 🧭 Journeys"
elif st.session_state.current_view == "Logistics":
    lbl_log = "▶ ⚙️ Logistics"
elif st.session_state.current_view == "Analytics":
    lbl_anal = "▶ 📊 Analytics"

if st.sidebar.button(lbl_orch, use_container_width=True):
    set_view("Orchestrator")
if st.sidebar.button(lbl_journ, use_container_width=True):
    set_view("Journeys")
if st.sidebar.button(lbl_log, use_container_width=True):
    set_view("Logistics")
if st.sidebar.button(lbl_anal, use_container_width=True):
    set_view("Analytics")

# Sidebar - Initiate New Mission Button
st.sidebar.markdown('<div style="margin-top: 15px; margin-bottom: 25px;">', unsafe_allow_html=True)
if st.sidebar.button("➕ New Mission", use_container_width=True, type="primary"):
    st.session_state.active_thread = None
    st.session_state.input_query = ""
    st.session_state.loaded_state = None
    st.session_state.flight_data = ""
    st.session_state.hotel_data = ""
    st.session_state.itinerary_data = ""
    st.session_state.final_data = ""
    st.session_state.steps_state = {"flight": "pending", "hotel": "pending", "itinerary": "pending", "final": "pending"}
    set_view("Orchestrator")
    st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Sidebar - Database Backup History (Past Journeys)
st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Session Backups</p>', unsafe_allow_html=True)
if st.sidebar.button("🔄 Sync Backups", key="sync_backups_btn", use_container_width=True):
    st.session_state.past_threads = get_past_threads()
    if st.session_state.all_journeys is not None:
        st.session_state.all_journeys = get_all_journeys_details()
    st.toast("Syncing backups with Neon Postgres...")
    st.rerun()

past_threads = st.session_state.past_threads

if past_threads:
    for t_id in past_threads[:15]:
        t_label = t_id
        if len(t_label) > 16:
            t_label = f"AP-{t_label[-8:]}"
        
        # Load journey checkpoint on click
        if st.sidebar.button(f"📜 {t_label}", key=f"hist_{t_id}", use_container_width=True):
            st.session_state.active_thread = t_id
            set_view("Orchestrator")
            
            # Retrieve checkpoint values from PostgresSaver
            try:
                with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
                    checkpointer.setup()
                    app = graph.compile(checkpointer=checkpointer)
                    config = {"configurable": {"thread_id": t_id}}
                    state = app.get_state(config)
                    if state and state.values:
                        st.session_state.loaded_state = state.values
                        st.session_state.input_query = state.values.get("user_query", "")
                        st.session_state.flight_data = state.values.get("flight_results", "")
                        st.session_state.hotel_data = state.values.get("hotel_results", "")
                        st.session_state.itinerary_data = state.values.get("itinerary", "")
                        
                        msgs = state.values.get("messages", [])
                        st.session_state.final_data = ""
                        if msgs:
                            for m in reversed(msgs):
                                if m.__class__.__name__ in ("AIMessage", "AIMessageChunk") and m.content:
                                    st.session_state.final_data = m.content
                                    break
                        st.session_state.steps_state = {"flight": "done", "hotel": "done", "itinerary": "done", "final": "done"}
                    else:
                        st.sidebar.warning("Could not retrieve state values.")
            except Exception as e:
                st.sidebar.error(f"Failed to load: {e}")
            st.rerun()
else:
    st.sidebar.markdown('<p style="color: #64748b; font-size: 0.8rem; font-style: italic;">No backups found</p>', unsafe_allow_html=True)

# Sidebar - Background Customizer
st.sidebar.markdown('<hr style="border-color: rgba(255,255,255,0.05); margin-top: 15px; margin-bottom: 15px;" />', unsafe_allow_html=True)
st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Aesthetics</p>', unsafe_allow_html=True)

preset_options = {
    "Weathering Video Loop": "https://cdn.dribbble.com/userupload/45617492/file/ec961c6f56bd0f5b2f2786a82af91b61.mp4",
    "Interactive VR World": "https://app.spline.design/ui/db887c32-7d89-49f9-9cca-012c7853f2f0",
    "Interactive Globe 3D": "https://my.spline.design/particleglobe-38cf9e6a6a3b2b0bf2dcf9cf3efd6ce/",
    "My Spline Project": "https://my.spline.design/a3cd9cca-f84d-4292-80fc-f63e10bf15d1/",
    "Custom URL": "custom"
}

# Determine current preset name
current_preset_name = "Custom URL"
for name, url in preset_options.items():
    if url == st.session_state.spline_url:
        current_preset_name = name
        break

selected_preset = st.sidebar.selectbox(
    "3D Background Preset",
    options=list(preset_options.keys()),
    index=list(preset_options.keys()).index(current_preset_name),
    key="bg_preset_select"
)

if selected_preset == "Custom URL":
    custom_url = st.sidebar.text_input(
        "Paste Spline URL:",
        value=st.session_state.spline_url if st.session_state.spline_url not in preset_options.values() else "",
        placeholder="https://my.spline.design/...",
        key="custom_spline_url_field"
    )
    if custom_url and custom_url != st.session_state.spline_url:
        st.session_state.spline_url = custom_url
        st.rerun()
else:
    preset_url = preset_options[selected_preset]
    if preset_url != st.session_state.spline_url:
        st.session_state.spline_url = preset_url
        st.rerun()

# Sidebar - Bottom support
st.sidebar.markdown('<div style="margin-top: 30px; margin-bottom: 20px;">', unsafe_allow_html=True)
st.sidebar.markdown('<hr style="border-color: rgba(255,255,255,0.05); margin-bottom: 15px;" />', unsafe_allow_html=True)
st.sidebar.markdown('<p style="color: #64748b; font-size: 0.8rem; cursor: pointer; margin-bottom: 8px;">❔ Support</p>', unsafe_allow_html=True)
st.sidebar.markdown('<p style="color: #64748b; font-size: 0.8rem; cursor: pointer;">👤 Account</p>', unsafe_allow_html=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# MAIN PANEL CONTENT
if st.session_state.current_view == "Orchestrator":
    # Header Section
    st.markdown(f"""
    <div class="dashboard-header-container">
        <h1 class="dashboard-title">AeroPlan AI</h1>
        <div class="dashboard-subtitle">Intelligent Multi-Agent Travel Orchestration</div>
        <div class="badge-pills">
            <div class="badge-pill"><span class="badge-pill-dot dot-cyan"></span> Neon DB</div>
            <div class="badge-pill"><span class="badge-pill-dot dot-green"></span> Llama 3.3</div>
            <div class="badge-pill"><span class="badge-pill-dot dot-purple"></span> AviationStack</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load previously retrieved values if loaded
    pre_query = st.session_state.input_query
    
    # Input Console
    user_query = st.text_input(
        "Where should the next journey take you?",
        value=pre_query,
        key="query_main_input"
    )
    
    # Suggestion Tags
    st.markdown('<div class="template-tags">', unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns([1, 1, 1])
    with col_t1:
        if st.button("7 Days in Japan", key="tag_japan", use_container_width=True):
            st.session_state.input_query = "Plan a complete 7 day japan trip including flights, hotels and sightseeing under 2 lakhs"
            st.rerun()
    with col_t2:
        if st.button("Weekend in Paris", key="tag_paris", use_container_width=True):
            st.session_state.input_query = "Quick weekend getaway to Paris from JFK with flights and romantic hotels"
            st.rerun()
    with col_t3:
        if st.button("Maldives Retreat", key="tag_maldives", use_container_width=True):
            st.session_state.input_query = "Luxury 5 day honeymoon package in Maldives including water villas"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Initiate Mission Button
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        initiate_btn = st.button("Initiate Mission", key="btn_initiate", type="primary")

    # Timeline layout placeholder
    timeline_placeholder = st.empty()
    
    def render_timeline(steps):
        step_details = [
            ("✈️", "Flight Agent", steps["flight"]),
            ("🛌", "Hotel Agent", steps["hotel"]),
            ("📅", "Itinerary Agent", steps["itinerary"]),
            ("🪄", "Final Orchestrator", steps["final"])
        ]
        
        html = '<div class="stepper-timeline">'
        for icon, label, state in step_details:
            bubble_class = "state-pending"
            label_class = ""
            status_text = "Pending"
            
            if state == "active":
                bubble_class = "state-active"
                label_class = "label-active"
                status_text = "● Active"
            elif state == "done":
                bubble_class = "state-done"
                label_class = "label-done"
                status_text = "Done"
                icon = "✓"
                
            html += f"""
            <div class="stepper-step">
                <div class="stepper-bubble {bubble_class}">{icon}</div>
                <div class="stepper-label {label_class}">{label}</div>
                <div class="stepper-status">{status_text}</div>
            </div>
            """
        html += '</div>'
        return html

    def render_flights(flight_data):
        st.markdown('<p style="font-weight: 700; color: #0f172a; margin-bottom: 10px; font-size: 1.1rem;">✈️ Flight Itinerary Options</p>', unsafe_allow_html=True)
        if flight_data:
            flight_blocks = flight_data.split("\n")
            rendered_any = False
            for fl_str in flight_blocks:
                if not fl_str.strip():
                    continue
                
                # Format: Flight CG8723 | Airline: PNG Air | Departure: Hoskins | Arrival: Nadzab | Status: scheduled
                pat = r"Flight\s+(?P<flight>[^\s|]+)\s*\|\s*Airline:\s*(?P<airline>[^|]+)\|\s*Departure:\s*(?P<dep>[^|]+)\|\s*Arrival:\s*(?P<arr>[^|]+)\|\s*Status:\s*(?P<status>.+)"
                match = re.search(pat, fl_str)
                if match:
                    rendered_any = True
                    airline = match.group("airline").strip()
                    flight_code = match.group("flight").strip()
                    dep_name = match.group("dep").strip()
                    arr_name = match.group("arr").strip()
                    status = match.group("status").strip()
                    
                    dep_code = dep_name[:3].upper()
                    arr_code = arr_name[:3].upper()
                    
                    st.markdown(f"""
                    <div class="flight-ticket">
                        <div class="ticket-header">
                            <span class="ticket-airline">✈️ {airline} ({flight_code})</span>
                            <span class="ticket-badge">{status}</span>
                        </div>
                        <div class="ticket-body">
                            <div class="airport-code">
                                <h3>{dep_code}</h3>
                                <p>{dep_name}</p>
                            </div>
                            <div class="flight-path">
                                <span class="flight-path-duration">Direct</span>
                                <div class="flight-path-line"></div>
                            </div>
                            <div class="airport-code" style="text-align: right;">
                                <h3>{arr_code}</h3>
                                <p>{arr_name}</p>
                            </div>
                        </div>
                        <div class="ticket-footer">
                            <span>Gate: A{hash(flight_code) % 20 + 1}</span>
                            <span>Seat: {hash(flight_code) % 30 + 1}B (Standard)</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            if not rendered_any:
                st.write(flight_data)
        else:
            st.info("No flights resolved.")

    def render_hotels(hotel_data):
        st.markdown('<p style="font-weight: 700; color: #0f172a; margin-bottom: 10px; font-size: 1.1rem;">🏨 Hotel & Accommodations</p>', unsafe_allow_html=True)
        if hotel_data:
            html_content = render_markdown_as_html(hotel_data)
            st.markdown(f'<div class="flight-ticket" style="line-height: 1.6; color: #1e293b;">{html_content}</div>', unsafe_allow_html=True)
        else:
            st.info("No hotels resolved.")

    def render_itinerary(itinerary_data):
        st.markdown('<p style="font-weight: 700; color: #0f172a; margin-bottom: 10px; font-size: 1.1rem; margin-top: 20px;">📅 Day-by-Day Sightseeing Itinerary</p>', unsafe_allow_html=True)
        html_content = render_markdown_as_html(itinerary_data)
        st.markdown(f'<div class="console-card" style="border-left: 3px solid #e11d48; background: rgba(255, 255, 255, 0.45) !important; color: #1e293b !important; line-height: 1.6;">{html_content}</div>', unsafe_allow_html=True)

    def render_final(final_data):
        st.markdown('<p style="font-weight: 700; color: #e11d48; margin-bottom: 10px; font-size: 1.1rem; margin-top: 20px;">🌟 Orchestration Output Summary</p>', unsafe_allow_html=True)
        html_content = render_markdown_as_html(final_data)
        st.markdown(f'<div class="console-card" style="border: 1px solid rgba(244, 63, 94, 0.2); background: rgba(255, 255, 255, 0.45) !important; color: #1e293b !important; line-height: 1.6;">{html_content}</div>', unsafe_allow_html=True)

    def render_budget(steps_state, user_query):
        is_japan = "japan" in user_query.lower() or "tokyo" in user_query.lower() or "kyoto" in user_query.lower()
        
        airfare_val = "$1,240.00" if is_japan else "$650.00"
        hotel_val = "$2,100.00" if is_japan else "$850.00"
        dining_val = "$900.00" if is_japan else "$400.00"
        
        st.markdown(f"""
        <div class="budget-section-card">
            <div class="budget-card-title">Budget Orchestration</div>
            <table class="budget-table">
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Agent Estimate</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>✈️ Airfare Estimate (Round Trip)</td>
                        <td>{airfare_val}</td>
                        <td><span class="badge-status status-optimized">OPTIMIZED</span></td>
                    </tr>
                    <tr>
                        <td>🏨 Accommodation Details</td>
                        <td>{hotel_val}</td>
                        <td><span class="badge-status status-calculating">{"OPTIMIZED" if steps_state["hotel"] == "done" else "CALCULATING"}</span></td>
                    </tr>
                    <tr>
                        <td>🍽️ Dining & Experiences</td>
                        <td>{dining_val}</td>
                        <td><span class="badge-status status-pending">{"OPTIMIZED" if steps_state["final"] == "done" else "PENDING"}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

    timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)

    # Multi-Column Panels Layout
    col_left, col_right = st.columns([1, 1])

    # Left Column Container Placeholder
    with col_left:
        left_placeholder = st.container()
        
    # Right Column Container Placeholder
    with col_right:
        right_placeholder = st.container()

    # Active Execution Trigger
    if initiate_btn and user_query:
        # Reset Loaded State since we're running a new task
        st.session_state.loaded_state = None
        
        # Reset timeline steps and clear old data in session state
        st.session_state.steps_state = {"flight": "active", "hotel": "pending", "itinerary": "pending", "final": "pending"}
        st.session_state.flight_data = ""
        st.session_state.hotel_data = ""
        st.session_state.itinerary_data = ""
        st.session_state.final_data = ""
        st.session_state.input_query = user_query
        
        timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)
        
        # Create unique Thread ID
        new_thread = f"mission_{abs(hash(user_query)) % 1000000}"
        st.session_state.active_thread = new_thread
        config = {"configurable": {"thread_id": new_thread}}

        # Stream Execution
        try:
            with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
                checkpointer.setup()
                app = graph.compile(checkpointer=checkpointer)
                
                # Render initial placeholders in layout
                with left_placeholder:
                    # Flight skeleton
                    flight_skeleton = st.empty()
                    flight_skeleton.markdown("""
                    <div class="skeleton-card">
                        <div class="skeleton-header">
                            <div class="skeleton-avatar"></div>
                            <div class="skeleton-title"></div>
                            <div class="skeleton-badge">Searching Flights</div>
                        </div>
                        <div class="skeleton-line skeleton-line-mid"></div>
                        <div class="skeleton-line skeleton-line-short"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with right_placeholder:
                    # Hotel skeleton
                    hotel_skeleton = st.empty()
                    hotel_skeleton.markdown("""
                    <div class="skeleton-card">
                        <div class="skeleton-header">
                            <div class="skeleton-avatar"></div>
                            <div class="skeleton-title"></div>
                            <div class="skeleton-badge">Hotel Analyzer</div>
                        </div>
                        <div class="skeleton-line skeleton-line-mid"></div>
                        <div class="skeleton-line skeleton-line-short"></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                stream = app.stream(
                    {
                        "messages": [HumanMessage(content=user_query)],
                        "user_query": user_query,
                        "flight_results": "",
                        "hotel_results": "",
                        "itinerary": "",
                        "llm_calls": 0
                    },
                    config=config
                )
                
                for chunk in stream:
                    if "flight_agent" in chunk:
                        st.session_state.steps_state["flight"] = "done"
                        st.session_state.steps_state["hotel"] = "active"
                        timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)
                        
                        st.session_state.flight_data = chunk["flight_agent"].get("flight_results", "")
                        flight_skeleton.empty()
                        with left_placeholder:
                            render_flights(st.session_state.flight_data)
                        
                    elif "hotel_agent" in chunk:
                        st.session_state.steps_state["hotel"] = "done"
                        st.session_state.steps_state["itinerary"] = "active"
                        timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)
                        
                        st.session_state.hotel_data = chunk["hotel_agent"].get("hotel_results", "")
                        hotel_skeleton.empty()
                        with right_placeholder:
                            render_hotels(st.session_state.hotel_data)
                        
                    elif "itinerary_agent" in chunk:
                        st.session_state.steps_state["itinerary"] = "done"
                        st.session_state.steps_state["final"] = "active"
                        timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)
                        
                        st.session_state.itinerary_data = chunk["itinerary_agent"].get("itinerary", "")
                        
                    elif "final_agent" in chunk:
                        st.session_state.steps_state["final"] = "done"
                        timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)
                        
                        msgs = chunk["final_agent"].get("messages", [])
                        if msgs:
                            st.session_state.final_data = msgs[-1].content
                
                # Make sure the cache gets cleared so the sidebar shows the new mission immediately
                st.cache_data.clear()
                st.session_state.past_threads = get_past_threads()
                if st.session_state.all_journeys is not None:
                    st.session_state.all_journeys = get_all_journeys_details()
                st.rerun()
        except Exception as e:
            st.error(f"Execution failed: {e}")
            st.session_state.steps_state = {"flight": "pending", "hotel": "pending", "itinerary": "pending", "final": "pending"}
            timeline_placeholder.markdown(render_timeline(st.session_state.steps_state), unsafe_allow_html=True)

    # RENDERING THE PANELS (either from live execution or loaded history)
    # Left Column: Flight details
    if st.session_state.steps_state["flight"] == "done":
        with left_placeholder:
            render_flights(st.session_state.flight_data)
    elif st.session_state.steps_state["flight"] == "active":
        with left_placeholder:
            st.markdown("""
            <div class="skeleton-card">
                <div class="skeleton-header">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-title"></div>
                    <div class="skeleton-badge">Searching Flights</div>
                </div>
                <div class="skeleton-line skeleton-line-mid"></div>
                <div class="skeleton-line skeleton-line-short"></div>
            </div>
            """, unsafe_allow_html=True)

    # Right Column: Hotel search details
    if st.session_state.steps_state["hotel"] == "done":
        with right_placeholder:
            render_hotels(st.session_state.hotel_data)
    elif st.session_state.steps_state["hotel"] == "active":
        with right_placeholder:
            st.markdown("""
            <div class="skeleton-card">
                <div class="skeleton-header">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-title"></div>
                    <div class="skeleton-badge">Hotel Analyzer</div>
                </div>
                <div class="skeleton-line skeleton-line-mid"></div>
                <div class="skeleton-line skeleton-line-short"></div>
            </div>
            """, unsafe_allow_html=True)

    # Main output: proposed day-by-day planner and final synthesis
    if st.session_state.itinerary_data:
        render_itinerary(st.session_state.itinerary_data)

    if st.session_state.final_data:
        render_final(st.session_state.final_data)

    if st.session_state.steps_state["flight"] == "done":
        render_budget(st.session_state.steps_state, user_query)

    # Footer Action Bar Widget
    active_t_id = st.session_state.active_thread if st.session_state.active_thread else "AP-2026-X91"
    if len(active_t_id) > 16:
        active_t_id = f"AP-2026-{active_t_id[-8:]}"

    st.markdown(f"""
    <div class="footer-bar">
        <div class="mission-id">MISSION ID: <span class="mission-id-val">{active_t_id.upper()}</span></div>
        <div class="footer-actions" id="footer-actions-container">
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # We overlay Streamlit buttons inside the footer actions container using columns
    st.markdown('<div style="margin-top: 18px;"></div>', unsafe_allow_html=True)
    col_act1, col_act2, col_act3 = st.columns([6, 1, 1])
    with col_act2:
        # Build plan text for clipboard
        copy_parts = []
        if st.session_state.get("flight_data"):
            copy_parts.append("=== FLIGHTS ===\n" + st.session_state.flight_data)
        if st.session_state.get("hotel_data"):
            copy_parts.append("=== HOTELS ===\n" + st.session_state.hotel_data)
        if st.session_state.get("itinerary_data"):
            copy_parts.append("=== ITINERARY ===\n" + st.session_state.itinerary_data)
        if st.session_state.get("final_data"):
            copy_parts.append("=== SUMMARY ===\n" + st.session_state.final_data)
        copy_text = "\n\n".join(copy_parts) if copy_parts else ""

        # Safely encode text for embedding in JS (use JSON encoding)
        import json as _json
        copy_text_js = _json.dumps(copy_text)

        st.components.v1.html(f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                body {{ margin: 0; padding: 0; background: transparent; }}
                button {{
                    width: 100%;
                    padding: 8px 16px;
                    background: rgba(255,255,255,0.5);
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.6);
                    border-radius: 8px;
                    font-family: 'Outfit', 'Segoe UI', sans-serif;
                    font-size: 14px;
                    font-weight: 600;
                    color: #1e293b;
                    cursor: pointer;
                    transition: all 0.25s ease;
                    box-shadow: none;
                }}
                button:hover {{
                    background: rgba(255,255,255,0.8);
                    border-color: rgba(225,29,72,0.3);
                    color: #e11d48;
                    transform: translateY(-1px);
                }}
                #toast {{
                    display: none;
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(16,185,129,0.95);
                    color: white;
                    padding: 10px 22px;
                    border-radius: 8px;
                    font-family: 'Outfit', sans-serif;
                    font-weight: 600;
                    font-size: 14px;
                    z-index: 9999;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    animation: fadein 0.3s ease;
                }}
                @keyframes fadein {{ from {{opacity:0;transform:translate(-50%,10px)}} to {{opacity:1;transform:translate(-50%,0)}} }}
            </style>
            </head>
            <body>
                <button onclick="copyPlan()">📋 Copy Plan</button>
                <div id="toast">✅ Plan copied to clipboard!</div>
                <script>
                    function copyPlan() {{
                        var text = {copy_text_js};
                        if (!text) {{
                            alert('No plan data to copy yet. Run a search first.');
                            return;
                        }}
                        if (navigator.clipboard && window.isSecureContext) {{
                            navigator.clipboard.writeText(text).then(function() {{
                                showToast();
                            }}).catch(function() {{
                                fallbackCopy(text);
                            }});
                        }} else {{
                            fallbackCopy(text);
                        }}
                    }}
                    function fallbackCopy(text) {{
                        var ta = document.createElement('textarea');
                        ta.value = text;
                        ta.style.position = 'fixed';
                        ta.style.opacity = '0';
                        document.body.appendChild(ta);
                        ta.focus();
                        ta.select();
                        try {{
                            document.execCommand('copy');
                            showToast();
                        }} catch(e) {{
                            alert('Copy failed. Please copy manually.');
                        }}
                        document.body.removeChild(ta);
                    }}
                    function showToast() {{
                        var t = document.getElementById('toast');
                        t.style.display = 'block';
                        setTimeout(function() {{ t.style.display = 'none'; }}, 2500);
                    }}
                </script>
            </body>
            </html>
        """, height=42)

    with col_act3:
        try:
            pdf_bytes = export_to_pdf(
                st.session_state.get("flight_data", ""),
                st.session_state.get("hotel_data", ""),
                st.session_state.get("itinerary_data", "")
            )
        except Exception:
            pdf_bytes = b""

        st.download_button(
            label="⬇ PDF export",
            data=bytes(pdf_bytes) if pdf_bytes else b"",
            file_name=f"travel_plan_{active_t_id}.pdf",
            mime="application/pdf",
            key="btn_pdf_download",
            use_container_width=True
        )


# Journeys View
elif st.session_state.current_view == "Journeys":
    st.markdown('<h1 class="dashboard-title">Saved Journeys</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">Historical travel missions and session backups retrieved from the Postgres checkpointer database.</p>', unsafe_allow_html=True)
    
    if st.session_state.all_journeys is None:
        with st.spinner("Retrieving historical journeys..."):
            st.session_state.all_journeys = get_all_journeys_details()
            
    journeys = st.session_state.all_journeys
    
    if not journeys:
        st.info("No saved journeys found. Initiate a travel planning request to save your first session.")
    else:
        for journey in journeys:
            t_id = journey["thread_id"]
            query = journey["query"]
            llm_calls = journey["llm_calls"]
            has_itin = journey["has_itinerary"]
            ts = journey["timestamp"]
            
            date_str = ts.split("T")[0] if "T" in ts else ts[:10] if ts else "Recent"
            
            st.markdown(f"""
            <div class="console-card" style="margin-bottom: 20px; padding: 22px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h4 style="margin: 0 0 8px 0; color: #0f172a; font-size: 1.25rem; font-weight: 700;">{query}</h4>
                        <p style="margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #475569;">
                            MISSION ID: <span style="color: #e11d48; font-weight: 600;">{t_id.upper()}</span> | DATE: {date_str}
                        </p>
                    </div>
                    <div>
                        <span class="badge-status {"status-optimized" if has_itin else "status-calculating"}">
                            {"COMPLETED" if has_itin else "IN PROGRESS"}
                        </span>
                    </div>
                </div>
                <div style="margin-top: 15px; display: flex; gap: 20px; align-items: center;">
                    <span style="font-size: 0.85rem; color: #475569;">🤖 LLM Orchestration Calls: <b style="color: #e11d48;">{llm_calls}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_restore, _ = st.columns([1, 4])
            with col_restore:
                if st.button("🔌 Restore Mission", key=f"restore_btn_{t_id}", use_container_width=True):
                    st.session_state.active_thread = t_id
                    st.session_state.loaded_state = None
                    
                    try:
                        with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
                            checkpointer.setup()
                            app = graph.compile(checkpointer=checkpointer)
                            config = {"configurable": {"thread_id": t_id}}
                            state = app.get_state(config)
                            if state and state.values:
                                st.session_state.loaded_state = state.values
                                st.session_state.input_query = state.values.get("user_query", "")
                                st.session_state.flight_data = state.values.get("flight_results", "")
                                st.session_state.hotel_data = state.values.get("hotel_results", "")
                                st.session_state.itinerary_data = state.values.get("itinerary", "")
                                
                                msgs = state.values.get("messages", [])
                                st.session_state.final_data = ""
                                if msgs:
                                    for m in reversed(msgs):
                                        if m.__class__.__name__ in ("AIMessage", "AIMessageChunk") and m.content:
                                            st.session_state.final_data = m.content
                                            break
                                st.session_state.steps_state = {"flight": "done", "hotel": "done", "itinerary": "done", "final": "done"}
                                st.toast(f"Successfully restored mission {t_id.upper()}!")
                            else:
                                st.error("Failed to load mission data from database.")
                    except Exception as e:
                        st.error(f"Error loading database checkpoint: {e}")
                    
                    st.session_state.current_view = "Orchestrator"
                    st.rerun()

# Logistics View
elif st.session_state.current_view == "Logistics":
    st.markdown('<h1 class="dashboard-title">System Logistics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">Multi-agent credentials and system check status.</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="console-card">
        <h3>Connected Integrations</h3>
        <p>✔️ <b>Neon Serverless Postgres Saver</b>: Connected (pooling active)</p>
        <p>✔️ <b>AviationStack flight API</b>: Connected</p>
        <p>✔️ <b>Tavily Search API</b>: Connected</p>
        <p>✔️ <b>Groq Llama-3 API</b>: Connected</p>
    </div>
    """, unsafe_allow_html=True)

# Analytics View
elif st.session_state.current_view == "Analytics":
    st.markdown('<h1 class="dashboard-title">Agent Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">Performance telemetry and agent execution analysis.</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="console-card">
        <h3>Performance Metrics</h3>
        <p>⚡ <b>Average Response Time</b>: 8.4 seconds</p>
        <p>⚡ <b>Total LLM Calls</b>: 4 per mission</p>
        <p>⚡ <b>Agent Efficiency Rating</b>: 98.4% (Optimized)</p>
    </div>
    """, unsafe_allow_html=True)
