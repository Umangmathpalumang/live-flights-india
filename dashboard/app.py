import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Live Flights Over India", layout="wide", page_icon="\U0001F6EB")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30_000, key="refresh")
except ImportError:
    pass

PG_URL = os.environ.get(
    "FLIGHTS_DB_URL",
    "postgresql+psycopg2://flights_user:password@localhost:5432/flights",
)
engine = create_engine(PG_URL)

# ---------- best-effort airline code map (OpenSky only gives us the callsign) ----------
AIRLINE_MAP = {
    "AIC": "Air India", "AXB": "Air India Express", "IGO": "IndiGo",
    "SEJ": "SpiceJet", "GOW": "Go First", "VTI": "Vistara", "AKJ": "Akasa Air",
    "UAE": "Emirates", "QTR": "Qatar Airways", "ETH": "Ethiopian Airlines",
    "THA": "Thai Airways", "SVA": "Saudia", "OMA": "Oman Air",
    "SIA": "Singapore Airlines", "CPA": "Cathay Pacific", "BAW": "British Airways",
    "DLH": "Lufthansa", "AFR": "Air France", "KLM": "KLM", "UAL": "United Airlines",
    "TAP": "TAP Air Portugal", "MSR": "EgyptAir", "GFA": "Gulf Air",
    "KAC": "Kuwait Airways", "FDB": "FlyDubai", "ANA": "All Nippon Airways",
}


def derive_airline(callsign):
    if pd.isna(callsign) or not str(callsign).strip() or len(str(callsign).strip()) < 3:
        return "Other / Unknown"
    prefix = str(callsign).strip()[:3].upper()
    return AIRLINE_MAP.get(prefix, f"Other ({prefix})")


# ---------- theme ----------
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

PALETTES = {
    "dark": dict(bg="#0E1117", card_bg="#161B24", card_border="#242B38",
                 text="#FFFFFF", muted="#8A93A6", accent="#5B8DEF",
                 track="#2A3140", map_style="carto-darkmatter"),
    "light": dict(bg="#F5F7FA", card_bg="#FFFFFF", card_border="#E3E7EE",
                  text="#111827", muted="#6B7280", accent="#3B6FD6",
                  track="#E2E8F0", map_style="carto-positron"),
}
P = PALETTES[st.session_state.theme]

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {P['bg']}; }}
    .kpi-card {{
        background-color: {P['card_bg']}; border: 1px solid {P['card_border']};
        border-radius: 14px; padding: 18px 20px; box-shadow: 0 4px 14px rgba(0,0,0,0.15);
    }}
    .kpi-label {{ color: {P['muted']}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; }}
    .kpi-value {{ color: {P['text']}; font-size: 32px; font-weight: 800; line-height: 1.1; }}
    .kpi-icon {{ font-size: 20px; margin-bottom: 8px; }}
    .section-title {{ color: {P['text']}; font-size: 18px; font-weight: 700; margin: 6px 0 14px 0; }}
    .hero-title {{ color: {P['text']}; font-size: 34px; font-weight: 800; margin-bottom: 2px; }}
    .hero-sub {{ color: {P['muted']}; font-size: 14px; margin-bottom: 10px; }}
    .last-updated {{ color: {P['muted']}; font-size: 12px; margin-top: -8px; }}
    .filter-bar {{
        background-color: {P['card_bg']}; border: 1px solid {P['card_border']};
        border-radius: 14px; padding: 14px 18px 4px 18px; margin-bottom: 18px;
    }}
    [data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; border: 1px solid {P['card_border']}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def kpi_card(icon, label, value):
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>""",
        unsafe_allow_html=True,
    )


# ---------- header row with theme toggle ----------
h1, h2 = st.columns([5, 1])
with h1:
    st.markdown('<div class="hero-title">\U0001F6EB Live Flights Over India</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Live ADS-B data via OpenSky Network &middot; ingested every ~60s &middot; '
        'transformed with dbt &middot; served from Postgres &middot; self-managed VPS</div>',
        unsafe_allow_html=True,
    )
with h2:
    is_dark = st.toggle("\U0001F319 Dark mode", value=(st.session_state.theme == "dark"), key="theme_toggle")
    new_theme = "dark" if is_dark else "light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()


@st.cache_data(ttl=25)
def load_data():
    flights = pd.read_sql("select * from marts.current_flights", engine)
    kpis = pd.read_sql("select * from marts.dashboard_kpis", engine)
    return flights, kpis


try:
    flights, kpis = load_data()
except Exception as e:
    st.error(f"Could not reach the database yet: {e}")
    st.stop()

if kpis.empty or flights.empty:
    st.warning("No data yet - the ingestion pipeline may still be starting up. Refresh in a minute.")
    st.stop()

flights = flights.copy()
flights["airline"] = flights["callsign"].apply(derive_airline)

# ---------- filter bar ----------
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
f1, f2, f3, f4 = st.columns([1.3, 1.3, 1, 1])
with f1:
    countries = sorted(flights["origin_country"].dropna().unique().tolist())
    sel_countries = st.multiselect("Country", countries, default=[], placeholder="All countries")
with f2:
    airlines = sorted(flights["airline"].dropna().unique().tolist())
    sel_airlines = st.multiselect("Airline", airlines, default=[], placeholder="All airlines")
with f3:
    status = st.selectbox("Status", ["All", "Airborne only", "On ground only"])
with f4:
    search = st.text_input("Search callsign", placeholder="e.g. AIC")
st.markdown('</div>', unsafe_allow_html=True)

filtered = flights.copy()
if sel_countries:
    filtered = filtered[filtered["origin_country"].isin(sel_countries)]
if sel_airlines:
    filtered = filtered[filtered["airline"].isin(sel_airlines)]
on_ground_bool = filtered["on_ground"].fillna(False).astype(bool)
if status == "Airborne only":
    filtered = filtered[~on_ground_bool]
elif status == "On ground only":
    filtered = filtered[on_ground_bool]
if search:
    filtered = filtered[filtered["callsign"].fillna("").str.contains(search, case=False)]

st.caption(f"Showing {len(filtered)} of {len(flights)} tracked aircraft")

# ---------- KPIs (reflect current filter) ----------
k = kpis.iloc[0]
total = len(filtered)
on_ground_n = int(filtered["on_ground"].fillna(False).astype(bool).sum())
domestic_n = int((filtered["origin_country"] == "India").sum())
international_n = total - domestic_n
avg_speed = round(filtered["velocity"].dropna().mean(), 1) if not filtered["velocity"].dropna().empty else "-"

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi_card("\u2708\ufe0f", "Flights (filtered)", total)
with c2:
    kpi_card("\U0001F6EC", "On Ground", on_ground_n)
with c3:
    kpi_card("\U0001F1EE\U0001F1F3", "Domestic (India)", domestic_n)
with c4:
    kpi_card("\U0001F30D", "International", international_n)
with c5:
    kpi_card("\U0001F4A8", "Avg Speed (m/s)", avg_speed)

st.markdown(f'<div class="last-updated">Last updated: {k["last_updated_at"]}</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ---------- map ----------
st.markdown('<div class="section-title">Current aircraft positions</div>', unsafe_allow_html=True)

if not filtered.empty:
    map_fig = px.scatter_mapbox(
        filtered,
        lat="latitude", lon="longitude", color="origin_country",
        size=filtered["geo_altitude"].fillna(1000).clip(lower=100), size_max=14,
        hover_name="callsign",
        hover_data={"airline": True, "origin_country": True, "geo_altitude": True, "velocity": True, "latitude": False, "longitude": False},
        zoom=3.4, center={"lat": 22.5, "lon": 80}, height=500,
    )
    map_fig.update_layout(
        mapbox_style=P["map_style"], paper_bgcolor=P["bg"], plot_bgcolor=P["bg"],
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(font=dict(color=P["text"], size=11), bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(map_fig, use_container_width=True)
else:
    st.info("No aircraft match the current filters.")

st.markdown("<br>", unsafe_allow_html=True)

# ---------- breakdowns ----------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('<div class="section-title">Top international origins</div>', unsafe_allow_html=True)
    intl = filtered[filtered["origin_country"] != "India"]["origin_country"].value_counts().sort_values(ascending=True).tail(12)
    if not intl.empty:
        bar_fig = go.Figure(go.Bar(x=intl.values, y=intl.index, orientation="h", marker=dict(color=P["accent"])))
        bar_fig.update_layout(
            paper_bgcolor=P["bg"], plot_bgcolor=P["bg"], font=dict(color=P["text"], size=12),
            margin=dict(l=0, r=10, t=10, b=0),
            xaxis=dict(gridcolor=P["card_border"], zeroline=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"), height=360,
        )
        st.plotly_chart(bar_fig, use_container_width=True)
    else:
        st.info("No international flights in the current filter.")

with col_right:
    st.markdown('<div class="section-title">Top airlines (filtered)</div>', unsafe_allow_html=True)
    top_airlines = filtered["airline"].value_counts().sort_values(ascending=True).tail(12)
    if not top_airlines.empty:
        air_fig = go.Figure(go.Bar(x=top_airlines.values, y=top_airlines.index, orientation="h", marker=dict(color=P["accent"])))
        air_fig.update_layout(
            paper_bgcolor=P["bg"], plot_bgcolor=P["bg"], font=dict(color=P["text"], size=12),
            margin=dict(l=0, r=10, t=10, b=0),
            xaxis=dict(gridcolor=P["card_border"], zeroline=False),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"), height=360,
        )
        st.plotly_chart(air_fig, use_container_width=True)
    else:
        st.info("No data for the current filter.")

st.markdown("<br>", unsafe_allow_html=True)

# ---------- snapshot + export ----------
top_row = st.columns([4, 1])
with top_row[0]:
    st.markdown('<div class="section-title">Current snapshot</div>', unsafe_allow_html=True)
with top_row[1]:
    st.download_button(
        "\u2B07\ufe0f Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="flights_snapshot.csv",
        mime="text/csv",
        use_container_width=True,
    )

if not filtered.empty:
    st.dataframe(filtered.sort_values("fetched_at", ascending=False), use_container_width=True, height=340)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div class="last-updated">Architecture: OpenSky Network API &rarr; Python ingestion (systemd timer, every 60s) '
    '&rarr; Postgres (raw schema) &rarr; dbt (staging + marts, refreshed every 5 min) &rarr; Streamlit dashboard '
    '(this page, systemd service, always on)</div>',
    unsafe_allow_html=True,
)
