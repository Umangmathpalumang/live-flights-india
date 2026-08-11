# Live Flights Over India — Real-Time Data Pipeline & Dashboard

A self-hosted, always-on data pipeline that tracks live aircraft over India in near real time, using free public ADS-B data. Built to demonstrate production-style ETL/ELT, dbt transformation modeling, and dashboarding on infrastructure I manage myself — not a notebook demo.

**Live dashboard:** http://140.245.210.94:8501

## Architecture

OpenSky Network API -> Python ingestion (systemd timer, every 60s) -> Postgres (raw.flight_states) -> dbt staging+marts (systemd timer, every 5 min) -> Streamlit dashboard (always-on systemd service)

## Why this design

- Systemd timers instead of a Python while-True loop: same pattern as production cron-style orchestration, automatic restart on failure, clean logs via journalctl.
- Raw/staging/marts separation mirrors the medallion pattern (Bronze/Silver/Gold) used in modern lakehouse and warehouse architectures.
- dbt for all transformation logic: SQL-based, version-controlled, same tool used across most modern Snowflake/BigQuery/Redshift stacks.
- 48-hour raw data retention: a deliberate, documented storage-cost decision rather than unbounded growth.

## Stack

Python, Postgres, dbt-postgres, Streamlit, Plotly, systemd, self-managed Ubuntu VPS

## Data source

OpenSky Network (https://opensky-network.org/) - free, open ADS-B flight tracking data, no API key required for basic anonymous access.

## Possible extensions

- Add a second data source (e.g. METAR weather data) and join it into the marts layer
- Swap Postgres for Snowflake/BigQuery to demonstrate cloud warehouse migration
- Add dbt tests and publish dbt docs as a static site
- Add Airflow/Dagster for orchestration instead of systemd timers
