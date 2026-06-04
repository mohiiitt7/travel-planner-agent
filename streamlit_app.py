import streamlit as st
import requests
import uuid

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
</style>
""", unsafe_allow_html=True)

# ─── Constants ───────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

# ─── Session State Init ───────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "plan" not in st.session_state:
    st.session_state.plan = None
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None
if "history" not in st.session_state:
    st.session_state.history = []


# ─── Helper: Call API ─────────────────────────────────────────────────────────
def call_plan_api(
    query: str,
    trip_type: str,
    modify: bool = False,
    modification_request: str = ""
):
    payload = {
        "session_id": st.session_state.session_id,
        "query": query,
        "trip_type": trip_type,
        "modify": modify,
        "modification_request": modification_request
    }
    try:
        resp = requests.post(f"{API_BASE}/plan", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to the API. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.Timeout:
        return None, "⏱️ Request timed out. The plan is taking too long — please try again."
    except requests.exceptions.HTTPError as e:
        return None, f"❌ API Error {e.response.status_code}: {e.response.text}"


def fetch_pdf():
    try:
        resp = requests.get(f"{API_BASE}/plan/latest-pdf", timeout=30)
        if resp.status_code == 200:
            return resp.content, None
        return None, "No PDF available yet."
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
    st.markdown("### 🔌 API Status")
    try:
        r = requests.get(f"{API_BASE}/", timeout=3)
        if r.status_code == 200:
            st.markdown("🟢 **API Online**")
        else:
            st.markdown("🔴 **API Offline**")
    except Exception:
        st.markdown("🔴 **API Offline**")

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

        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.markdown('<div class="section-title">🗓️ Itinerary</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="itinerary-block">{plan.get("itinerary","No itinerary available.")}</div>',
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
        st.markdown('<div class="section-title">📋 Current Itinerary Preview</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="itinerary-block">{plan.get("itinerary", "No itinerary.")}</div>',
            unsafe_allow_html=True
        )
