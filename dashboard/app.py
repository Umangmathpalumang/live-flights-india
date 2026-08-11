import os
import pandas as pd
import plotly.express as px
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

st.title("\U0001F6EB Live Flights Over India")
st.caption(
    "Live ADS-B data via OpenSky Network - ingested every ~60s, transformed with dbt, "
    "served from Postgres. Built and deployed on a self-managed VPS."
)


@st.cache_data(ttl=25)
def load_data():
    flights = pd.read_sql("select * from marts.current_flights", engine)
    kpis = pd.read_sql("select * from marts.dashboard_kpis", engine)
    by_country = pd.read_sql("select * from marts.flights_by_country", engine)
    return flights, kpis, by_country


try:
    flights, kpis, by_country = load_data()
except Exception as e:
    st.error(f"Could not reach the database yet: {e}")
    st.stop()

if kpis.empty:
    st.warning("No data yet - the ingestion pipeline may still be starting up. Refresh in a minute.")
else:
    k = kpis.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active flights", int(k["total_active_flights"]))
    c2.metric("On ground", int(k["on_ground_count"]))
    c3.metric("Countries represented", int(k["countries_represented"]))
    c4.metric("Avg speed (m/s)", k["avg_velocity_ms"])
    st.caption(f"Last updated: {k['last_updated_at']}")

if not flights.empty:
    fig = px.scatter_geo(
        flights,
        lat="latitude",
        lon="longitude",
        hover_name="callsign",
        hover_data=["origin_country", "geo_altitude", "velocity"],
        color="origin_country",
        scope="asia",
        title="Current aircraft positions",
    )
    fig.update_geos(lataxis_range=[0, 40], lonaxis_range=[65, 100])
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Flights by origin country")
        st.bar_chart(by_country.set_index("origin_country")["active_flights"])
    with col2:
        st.subheader("Current snapshot")
        st.dataframe(
            flights.sort_values("fetched_at", ascending=False),
            use_container_width=True,
            height=380,
        )
else:
    st.info("Waiting for the first data snapshot from the ingestion pipeline...")

st.divider()
st.caption(
    "Architecture: OpenSky Network API -> Python ingestion (systemd timer, every 60s) -> "
    "Postgres (raw schema) -> dbt (staging + marts, refreshed every 5 min) -> Streamlit dashboard."
)
