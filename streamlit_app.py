import streamlit as st
import requests
import uuid
import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
import re
import time
import folium
from folium import plugins
from streamlit_folium import st_folium
from streamlit_lottie import st_lottie
import urllib.parse

# ── Direct graph + PDF imports (no FastAPI needed) ────────────────────────────
from app.graph.graph import graph
from app.services.pdf_export import export_pdf

def get_lat_lon(destination):
    try:
        geolocator = Nominatim(user_agent="travel_planner_agent", timeout=10)
        location = geolocator.geocode(destination, language='en')
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None


# ─── Day-wise Map Helpers ─────────────────────────────────────────────────────

def parse_itinerary_days(text):
    """Split raw itinerary text into {day_num: day_text} dict."""
    parts = re.split(r'(?i)(Day\s+\d+[:\-]?)', text)
    days = {}
    i = 1
    while i < len(parts) - 1:
        header = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        match = re.search(r'\d+', header)
        if match:
            day_num = int(match.group())
            days[day_num] = content.strip()
        i += 2
    return days


def extract_place_names(day_text, destination):
    """Extract place/attraction names from a day's itinerary text, sorted by order of appearance."""
    skip = {
        'morning', 'afternoon', 'evening', 'night', 'day', 'today', 'tonight',
        'the', 'and', 'for', 'with', 'from', 'then', 'next', 'after', 'before',
        'later', 'also', 'some', 'your', 'our', 'their', 'this', 'that',
        'other', 'nearby', 'further', 'optional', 'free', 'rest', 'return'
    }
    landmark_kw = {
        'fort', 'temple', 'beach', 'museum', 'palace', 'garden', 'lake',
        'market', 'bazaar', 'park', 'monument', 'church', 'mosque', 'shrine',
        'waterfall', 'hill', 'valley', 'cave', 'island', 'bay', 'tower',
        'gate', 'bridge', 'mahal', 'mandir', 'dargah', 'ghats', 'ghat',
        'zoo', 'aquarium', 'stadium', 'square', 'plaza', 'falls', 'rock',
        'point', 'peak', 'road', 'street', 'place', 'area', 'harbor', 'port'
    }

    # Track (first_position, name) so we can sort by text order at the end
    found: dict[str, int] = {}  # name -> position of first occurrence in text

    def add(name, pos):
        name = name.strip().rstrip('.,;:')
        if len(name) > 3 and name not in found:
            words = name.lower().split()
            if not all(w in skip for w in words):
                found[name] = pos

    # Strategy 1: Places mentioned after action verbs (most reliable)
    action_pat = re.compile(
        r'(?:visit|explore|head to|go to|see|check out|stop at|'
        r'arrive at|reach|tour|walk to|drive to|stroll|proceed to)'
        r'\s+(?:the\s+|a\s+)?([A-Z][^.,\n]{3,50}?)(?=\s*[,.\'\n]|\s+and\b|\s+where\b|$)',
        re.IGNORECASE
    )
    for m in action_pat.finditer(day_text):
        add(m.group(1), m.start())

    # Strategy 2: Title-cased sequences that contain a landmark keyword
    title_pat = re.compile(r'\b([A-Z][a-zA-Z]*(?:\s+[A-Za-z]+){0,5})\b')
    for m in title_pat.finditer(day_text):
        name = m.group(1).strip()
        words_lower = name.lower().split()
        if any(kw in words_lower for kw in landmark_kw) and len(name) > 4:
            add(name, m.start())

    # Strategy 3: Title-cased multi-word proper nouns after prepositions
    prep_pat = re.compile(
        r'(?:at|in|to|towards|near|around|inside|through)\s+'
        r'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})'
    )
    for m in prep_pat.finditer(day_text):
        add(m.group(1), m.start())

    # Strategy 4: Title-cased 2-4 word sequences (fallback)
    fallback_pat = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b')
    for m in fallback_pat.finditer(day_text):
        name = m.group(1)
        words = name.lower().split()
        if not any(w in skip for w in words) and len(name) > 5:
            add(name, m.start())

    # ── KEY FIX: sort by position in text so route follows itinerary order ──
    sorted_places = sorted(found.items(), key=lambda x: x[1])
    return [name for name, _ in sorted_places[:10]]


def geocode_places(place_names, destination):
    """Geocode a list of place names, returning list of {name, lat, lon}."""
    geolocator = Nominatim(user_agent="travel_planner_agent_daymap", timeout=10)
    results = []
    cache = st.session_state.geocode_cache
    # Extract city name from destination (first part before comma)
    city = destination.split(',')[0].strip() if ',' in destination else destination

    for name in place_names:
        cache_key = f"{name}|{destination}"
        if cache_key in cache:
            lat, lon = cache[cache_key]
        else:
            lat, lon = None, None
            # Try progressively broader queries
            queries = [
                f"{name}, {destination}",
                f"{name}, {city}, India",
                f"{name}, {city}"
            ]
            for q in queries:
                try:
                    loc = geolocator.geocode(q, exactly_one=True, language='en')
                    if loc:
                        lat, lon = loc.latitude, loc.longitude
                        break
                except Exception:
                    pass
                time.sleep(0.5)  # Nominatim rate limit
            cache[cache_key] = (lat, lon)

        if lat and lon:
            results.append({"name": name, "lat": lat, "lon": lon})

    st.session_state.geocode_cache = cache
    return results


def build_day_map(locations, destination, day_num):
    """Build a Folium map with numbered markers and an animated directional route."""
    if not locations:
        # Fall back to city-centre pin
        lat, lon = get_lat_lon(destination)
        if not lat:
            lat, lon = 20.5937, 78.9629  # India centre
        m = folium.Map(location=[lat, lon], zoom_start=12,
                       tiles="CartoDB dark_matter")
        folium.Marker([lat, lon], popup=destination,
                      icon=folium.Icon(color="purple", icon="map-marker",
                                       prefix="fa")).add_to(m)
        return m

    centre_lat = sum(p["lat"] for p in locations) / len(locations)
    centre_lon = sum(p["lon"] for p in locations) / len(locations)

    m = folium.Map(location=[centre_lat, centre_lon], zoom_start=13,
                   tiles="CartoDB dark_matter")

    coords = []
    for idx, loc in enumerate(locations):
        popup_html = f"""
        <div style='font-family:Inter,sans-serif;min-width:160px'>
          <b style='font-size:14px;color:#667eea'>📍 {loc['name']}</b><br>
          <span style='color:#aaa;font-size:12px'>Stop {idx+1} of {len(locations)} · Day {day_num}</span>
        </div>"""
        # Gradient colour: first stop green, last stop red, middle purple
        if idx == 0:
            bg = "linear-gradient(135deg,#10b981,#059669)"   # green  — start
        elif idx == len(locations) - 1:
            bg = "linear-gradient(135deg,#ef4444,#b91c1c)"   # red    — end
        else:
            bg = "linear-gradient(135deg,#667eea,#764ba2)"   # purple — mid

        folium.Marker(
            location=[loc["lat"], loc["lon"]],
            popup=folium.Popup(popup_html, max_width=240),
            tooltip=f"{idx+1}. {loc['name']}",
            icon=folium.DivIcon(
                html=f"""<div style='background:{bg};
                    color:white;border-radius:50%;width:30px;height:30px;
                    display:flex;align-items:center;justify-content:center;
                    font-weight:700;font-size:13px;
                    box-shadow:0 2px 10px rgba(0,0,0,0.5);
                    border:2px solid white;cursor:pointer'>{idx+1}</div>""",
                icon_size=(30, 30), icon_anchor=(15, 15)
            )
        ).add_to(m)
        coords.append([loc["lat"], loc["lon"]])

    # ── Animated directional route (AntPath) ────────────────────────────────
    # Connects stops in the exact order they appear in the day's itinerary
    if len(coords) > 1:
        plugins.AntPath(
            locations=coords,
            color="#667eea",
            weight=4,
            opacity=0.85,
            delay=600,
            dash_array=[15, 25],
            pulse_color="#a78bfa",
        ).add_to(m)
        # Solid underline so the route is always visible even when animation is off
        folium.PolyLine(
            locations=coords,
            color="#667eea",
            weight=2,
            opacity=0.35,
        ).add_to(m)

    # Auto-fit bounds
    m.fit_bounds([[p["lat"], p["lon"]] for p in locations],
                 padding=[40, 40])
    return m



# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="✈️ AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
}
.hero-banner h1 {
    color: #fff;
    font-size: 2.8rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.hero-banner p {
    color: rgba(255,255,255,0.85);
    font-size: 1.1rem;
    margin-top: 0.5rem;
}

/* Cards */
.plan-card {
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

/* Stat boxes */
.stat-box {
    background: linear-gradient(135deg, rgba(102,126,234,0.2), rgba(118,75,162,0.2));
    border: 1px solid rgba(102,126,234,0.4);
    border-radius: 14px;
    padding: 1.2rem;
    text-align: center;
}
.stat-label {
    color: rgba(255,255,255,0.6);
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.stat-value {
    color: #fff;
    font-size: 1.6rem;
    font-weight: 700;
    margin-top: 4px;
}

/* Section headings */
.section-title {
    color: #a78bfa;
    font-size: 1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Itinerary block */
.itinerary-block {
    background: rgba(0,0,0,0.3);
    border-left: 3px solid #667eea;
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.5rem;
    color: rgba(255,255,255,0.88);
    font-size: 0.92rem;
    line-height: 1.9;
    white-space: pre-wrap;
}

/* Recommendation pills */
.rec-pill {
    display: inline-block;
    background: rgba(102,126,234,0.15);
    border: 1px solid rgba(102,126,234,0.35);
    border-radius: 999px;
    padding: 6px 14px;
    color: #c4b5fd;
    font-size: 0.85rem;
    margin: 4px 4px 4px 0;
}

/* Weather badge */
.weather-badge {
    background: linear-gradient(135deg, #06b6d4, #3b82f6);
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    color: #fff;
    font-size: 0.9rem;
    font-weight: 500;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(15, 12, 41, 0.9);
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* Input labels */
label {
    color: rgba(255,255,255,0.8) !important;
    font-weight: 500 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.6rem 1.5rem;
    transition: all 0.3s ease;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102,126,234,0.5);
}

/* Download button */
.stDownloadButton > button {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    width: 100%;
}

/* Alert / info box */
.clarification-box {
    background: rgba(251,191,36,0.12);
    border: 1px solid rgba(251,191,36,0.4);
    border-radius: 12px;
    padding: 1.2rem;
    color: #fbbf24;
}

/* Success banner */
.success-banner {
    background: rgba(16,185,129,0.12);
    border: 1px solid rgba(16,185,129,0.35);
    border-radius: 12px;
    padding: 0.8rem 1.2rem;
    color: #6ee7b7;
    font-weight: 500;
    margin-bottom: 1.2rem;
}

/* Spinner override */
.stSpinner > div {
    border-top-color: #667eea !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.6);
    border-radius: 8px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
}

/* Day selector buttons */
.day-btn-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}
.day-btn {
    background: rgba(255,255,255,0.07);
    border: 1.5px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.7);
    border-radius: 8px;
    padding: 6px 18px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.25s ease;
    font-family: Inter, sans-serif;
}
.day-btn:hover {
    border-color: #667eea;
    color: #a78bfa;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(102,126,234,0.3);
}
.day-btn.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: transparent;
    color: white;
    box-shadow: 0 4px 18px rgba(102,126,234,0.45);
    transform: translateY(-1px);
}

/* Map fade animation */
@keyframes mapFadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.map-container {
    animation: mapFadeIn 0.35s ease;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
# (FastAPI removed — graph is called directly)

# ─── Session State Init ───────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "plan" not in st.session_state:
    st.session_state.plan = None
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None
if "history" not in st.session_state:
    st.session_state.history = []
if "selected_day" not in st.session_state:
    st.session_state.selected_day = 1
if "geocode_cache" not in st.session_state:
    st.session_state.geocode_cache = {}
if "currency" not in st.session_state:
    st.session_state.currency = "INR"

EXCHANGE_RATES_URL = "https://api.exchangerate-api.com/v4/latest/INR"

@st.cache_data(ttl=3600)
def fetch_exchange_rates():
    try:
        r = requests.get(EXCHANGE_RATES_URL, timeout=5)
        if r.status_code == 200:
            return r.json().get("rates", {})
    except:
        pass
    return {"INR": 1.0, "USD": 0.012, "EUR": 0.011, "GBP": 0.009}

@st.cache_data
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


# ─── Helper: Run Graph Directly (no FastAPI) ─────────────────────────────────
def call_plan_api(
    query: str,
    trip_type: str,
    modify: bool = False,
    modification_request: str = ""
):
    """Invoke the LangGraph pipeline directly — no HTTP call needed."""
    state = {
        "user_query": query,
        "destination": None,
        "budget": None,
        "days": None,
        "weather": None,
        "trip_type": trip_type,
        "modify": modify,
        "modification_request": modification_request,
        "itinerary": "",
        "estimated_cost": 0,
        "recommendations": [],
        "missing_information": [],
        "previous_destination": None,
        "final_response": {}
    }
    try:
        result = graph.invoke(
            state,
            config={"configurable": {"thread_id": st.session_state.session_id}}
        )
        response = result["final_response"]
        response["weather"] = result.get("weather")
        # Generate PDF locally
        export_pdf(response)
        return {"plan": response}, None
    except Exception as e:
        return None, f"❌ Error generating plan: {str(e)}"


def fetch_pdf():
    """Read the latest PDF from disk (generated locally by export_pdf)."""
    import os
    pdf_path = "travel_plan.pdf"
    try:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                return f.read(), None
        return None, "No PDF available yet. Generate a plan first."
    except Exception as e:
        return None, str(e)


# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <h1>✈️ AI Travel Planner</h1>
    <p>Describe your dream trip — get a personalized itinerary, cost estimate & PDF in seconds</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    trip_type = st.selectbox(
        "Trip Style",
        options=["budget", "luxury"],
        format_func=lambda x: "💰 Budget" if x == "budget" else "💎 Luxury"
    )

    st.markdown("---")
    st.markdown("### 🔑 Session")
    st.code(f"ID: {st.session_state.session_id}", language=None)
    if st.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.plan = None
        st.session_state.pdf_path = None
        st.session_state.history = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Request History")
    if st.session_state.history:
        for i, h in enumerate(reversed(st.session_state.history[-5:]), 1):
            st.markdown(f"<small style='color:rgba(255,255,255,0.5)'>{i}. {h}</small>", unsafe_allow_html=True)
    else:
        st.markdown("<small style='color:rgba(255,255,255,0.4)'>No requests yet.</small>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🤖 AI Engine")
    st.markdown("""
    <div style='
        background: rgba(16,185,129,0.12);
        border: 1px solid rgba(16,185,129,0.4);
        border-radius: 10px;
        padding: 0.6rem 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    '>
        <span style='font-size:1.1rem'>🟢</span>
        <span style='color:#6ee7b7;font-weight:600;font-size:0.9rem'>Ready</span>
    </div>
    <div style='color:rgba(255,255,255,0.35);font-size:0.75rem;margin-top:6px;padding-left:4px'>
        Powered by LangGraph
    </div>
    """, unsafe_allow_html=True)

# ─── Main Tabs ────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🗺️ Plan My Trip", "✏️ Modify Plan"])

# ═══════════════════════════════════════════════════════════════════
# TAB 1 — Generate Plan
# ═══════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)

    col_input, col_tip = st.columns([3, 1])
    with col_input:
        query = st.text_area(
            "Describe your trip",
            placeholder="e.g. I want to travel to Goa for 5 days with a budget of 15000",
            height=110,
            key="trip_query"
        )
    with col_tip:
        st.markdown("""
        <div class="plan-card" style="height:100%;font-size:0.82rem;color:rgba(255,255,255,0.6)">
        <b style="color:#a78bfa">💡 Tips</b><br><br>
        • Include <b>destination</b><br>
        • Include <b>days</b><br>
        • Include <b>budget (₹)</b><br>
        • Choose trip style ←
        </div>
        """, unsafe_allow_html=True)

    if st.button("🚀 Generate Travel Plan", key="generate_btn"):
        if not query.strip():
            st.warning("Please describe your trip first.")
        else:
            with st.spinner("🤖 Planning your perfect trip..."):
                result, error = call_plan_api(query, trip_type)

            if error:
                st.markdown(f'<div class="clarification-box">⚠️ {error}</div>', unsafe_allow_html=True)
            else:
                plan = result.get("plan", {})

                # Clarification needed?
                if "clarification_needed" in plan:
                    st.markdown('<div class="clarification-box">', unsafe_allow_html=True)
                    st.markdown("**🙋 I need a bit more info:**")
                    for q in plan["clarification_needed"]:
                        st.markdown(f"&nbsp;&nbsp;• {q}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.session_state.plan = plan
                    st.session_state.history.append(query[:60])
                    st.session_state.selected_day = 1
                    st.session_state.geocode_cache = {}
                    st.markdown(
                        '<div class="success-banner">✅ Travel plan generated successfully!</div>',
                        unsafe_allow_html=True
                    )

    # ── Display Plan ──────────────────────────────────────────────
    if st.session_state.plan:
        plan = st.session_state.plan

        # Stats row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">📍 Destination</div>
                <div class="stat-value" style="font-size:1.2rem">{plan.get('destination','—')}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">📅 Duration</div>
                <div class="stat-value">{plan.get('days','—')} Days</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">💰 Est. Cost</div>
                <div class="stat-value">₹{plan.get('estimated_cost',0):,}</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-label">🌡️ Weather</div>
                <div class="stat-value" style="font-size:0.95rem">{(plan.get('weather') or 'N/A')[:20]}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Parse days from itinerary ────────────────────────────────────
        itinerary_text = plan.get("itinerary", "")
        destination = plan.get('destination', '')
        day_map_data = parse_itinerary_days(itinerary_text)
        total_days = len(day_map_data) if day_map_data else plan.get('days', 1)

        # Clamp selected_day to valid range
        if st.session_state.selected_day > total_days:
            st.session_state.selected_day = 1

        # ── Day selector button row ───────────────────────────────────────
        st.markdown('<div class="section-title">🗓️ Select Day to Explore</div>', unsafe_allow_html=True)
        day_cols = st.columns(min(total_days, 7))
        for d in range(1, total_days + 1):
            col_idx = (d - 1) % min(total_days, 7)
            with day_cols[col_idx]:
                is_active = (st.session_state.selected_day == d)
                btn_class = "day-btn active" if is_active else "day-btn"
                if st.button(
                    f"Day {d}",
                    key=f"day_btn_{d}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.selected_day = d
                    st.rerun()

        selected_day = st.session_state.selected_day
        selected_day_text = day_map_data.get(selected_day, "")

        # ── Geocode places for selected day ───────────────────────────────
        map_col, chart_col = st.columns([3, 2])

        with map_col:
            st.markdown(
                f'<div class="section-title">📍 Day {selected_day} — Interactive Map</div>',
                unsafe_allow_html=True
            )
            with st.spinner(f"📡 Locating Day {selected_day} places..."):
                place_names = extract_place_names(selected_day_text, destination)
                locations = geocode_places(place_names, destination)

            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            folium_map = build_day_map(locations, destination, selected_day)
            st_folium(folium_map, width="100%", height=420, returned_objects=[], key=f"map_day_{selected_day}")
            st.markdown('</div>', unsafe_allow_html=True)

            found = len(locations)
            if found:
                loc_pills = " &nbsp;·&nbsp; ".join(
                    f"<span style='color:#a78bfa'>{'①②③④⑤⑥⑦⑧'[i]} {l['name']}</span>"
                    for i, l in enumerate(locations)
                )
                st.markdown(
                    f"<div style='font-size:0.8rem;color:rgba(255,255,255,0.5);margin-top:6px'>"
                    f"📌 {found} location{'s' if found>1 else ''} mapped &nbsp;|&nbsp; {loc_pills}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div style='font-size:0.8rem;color:rgba(255,200,100,0.7);margin-top:6px'>"
                    "⚠️ Could not geocode specific places — showing city centre.</div>",
                    unsafe_allow_html=True
                )

        with chart_col:
            st.markdown('<div class="section-title">📊 Budget Breakdown</div>', unsafe_allow_html=True)
            breakdown = plan.get('cost_breakdown', {})
            if breakdown:
                df_chart = pd.DataFrame({
                    "Category": list(breakdown.keys()),
                    "Cost": list(breakdown.values())
                })
                fig = px.pie(df_chart, values="Cost", names="Category", hole=0.4,
                             color_discrete_sequence=['#667eea', '#06b6d4', '#10b981', '#f59e0b'])
                fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True, height=320)
            else:
                st.info("Budget breakdown not available.")

        st.markdown("<br>", unsafe_allow_html=True)

        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.markdown('<div class="section-title">🗓️ Full Itinerary</div>', unsafe_allow_html=True)

            if len(day_map_data) > 1:
                raw_days = re.split(r'(?i)(Day\s+\d+[:\-]?)', itinerary_text)
                if raw_days[0].strip():
                    st.markdown(f'<div class="itinerary-block">{raw_days[0]}</div>', unsafe_allow_html=True)
                for i in range(1, len(raw_days), 2):
                    day_header = raw_days[i].strip()
                    day_content = raw_days[i+1].strip() if i+1 < len(raw_days) else ""
                    day_num_match = re.search(r'\d+', day_header)
                    this_day = int(day_num_match.group()) if day_num_match else 0
                    is_selected = (this_day == selected_day)
                    with st.expander(
                        f"{'🔵 ' if is_selected else ''}{day_header}",
                        expanded=is_selected
                    ):
                        st.markdown(day_content)
            else:
                st.markdown(
                    f'<div class="itinerary-block">{itinerary_text}</div>',
                    unsafe_allow_html=True
                )

        with col_r:
            # Weather full
            if plan.get("weather"):
                st.markdown('<div class="section-title">🌤️ Weather</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="weather-badge">🌡️ {plan["weather"]}</div>',
                    unsafe_allow_html=True
                )
                st.markdown("<br>", unsafe_allow_html=True)

            # Recommendations
            st.markdown('<div class="section-title">💡 Recommendations</div>', unsafe_allow_html=True)
            recs = plan.get("recommendations", [])
            if recs:
                pills_html = "".join(
                    f'<span class="rec-pill">{"✅" if "sufficient" in r.lower() else "⚠️"} {r}</span>'
                    for r in recs
                )
                st.markdown(f'<div>{pills_html}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<small style="color:rgba(255,255,255,0.4)">No recommendations.</small>', unsafe_allow_html=True)

            # PDF Download
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">📄 Export</div>', unsafe_allow_html=True)
            pdf_bytes, pdf_err = fetch_pdf()
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Download PDF Plan",
                    data=pdf_bytes,
                    file_name=f"travel_plan_{plan.get('destination','trip')}.pdf",
                    mime="application/pdf",
                    key="pdf_download"
                )
            else:
                st.markdown(
                    f'<small style="color:rgba(255,255,255,0.4)">{pdf_err}</small>',
                    unsafe_allow_html=True
                )


# ═══════════════════════════════════════════════════════════════════
# TAB 2 — Modify Plan
# ═══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.plan:
        st.markdown("""
        <div class="clarification-box" style="background:rgba(102,126,234,0.1);border-color:rgba(102,126,234,0.4);color:#a78bfa">
            ℹ️ Generate a travel plan first in the <b>Plan My Trip</b> tab, then come back here to modify it.
        </div>
        """, unsafe_allow_html=True)
    else:
        plan = st.session_state.plan
        st.markdown(f"""
        <div class="success-banner">
            ✅ Current plan: <b>{plan.get('destination')}</b> — {plan.get('days')} days
        </div>
        """, unsafe_allow_html=True)

        mod_query = st.text_area(
            "What would you like to change?",
            placeholder="e.g. Add a beach visit on Day 2, or swap Day 3 activities with adventure sports",
            height=100,
            key="mod_query"
        )

        if st.button("✏️ Apply Modification", key="modify_btn"):
            if not mod_query.strip():
                st.warning("Please describe what you want to change.")
            else:
                with st.spinner("🔄 Updating your itinerary..."):
                    result, error = call_plan_api(
                        query=plan.get("destination", "") +
                              f" {plan.get('days','')} days {plan.get('estimated_cost','')}",
                        trip_type=trip_type,
                        modify=True,
                        modification_request=mod_query
                    )

                if error:
                    st.markdown(f'<div class="clarification-box">⚠️ {error}</div>', unsafe_allow_html=True)
                else:
                    updated_plan = result.get("plan", {})
                    if "clarification_needed" not in updated_plan:
                        st.session_state.plan = updated_plan
                        st.session_state.history.append(f"[Modified] {mod_query[:50]}")
                        st.markdown(
                            '<div class="success-banner">✅ Plan modified successfully!</div>',
                            unsafe_allow_html=True
                        )
                        st.rerun()
                    else:
                        st.warning("Could not apply modification. Try rephrasing your request.")

        # Show current itinerary preview
        st.markdown("---")
        st.markdown(
            '<div class="section-title">📋 Current Itinerary Preview</div>',
            unsafe_allow_html=True
        )
        
        itinerary_text = plan.get("itinerary", "No itinerary.")
        days_preview = re.split(r'(?i)(Day \d+:)', itinerary_text)
        
        if len(days_preview) > 1:
            if days_preview[0].strip():
                st.markdown(f'<div class="itinerary-block">{days_preview[0]}</div>', unsafe_allow_html=True)
            for i in range(1, len(days_preview), 2):
                day_header = days_preview[i].strip()
                day_content = days_preview[i+1].strip() if i+1 < len(days_preview) else ""
                with st.expander(day_header, expanded=(i==1)):
                    st.markdown(day_content)
        else:
            st.markdown(
                f'<div class="itinerary-block">{itinerary_text}</div>',
                unsafe_allow_html=True
            )
