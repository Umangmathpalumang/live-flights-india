import os
import sys
import requests
import psycopg2
from datetime import datetime, timezone

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
OPENSKY_URL = "https://opensky-network.org/api/states/all"
BBOX = {"lamin": 6.0, "lomin": 68.0, "lamax": 37.5, "lomax": 97.5}

DB_PARAMS = {
    "dbname": os.environ.get("DBT_PG_DB", "flights"),
    "user": os.environ.get("DBT_PG_USER", "flights_user"),
    "password": os.environ.get("DBT_PG_PASSWORD"),
    "host": "localhost",
    "port": 5432,
}


def get_access_token():
    client_id = os.environ.get("OPENSKY_CLIENT_ID")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_states():
    headers = {}
    token = get_access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(OPENSKY_URL, params=BBOX, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json().get("states") or []


def to_row(s):
    def g(i):
        return s[i] if i < len(s) else None

    callsign = g(1)
    return (
        g(0),
        callsign.strip() if callsign else None,
        g(2), g(4), g(5), g(6), g(7), g(13), g(8), g(9), g(10), g(11), g(14),
    )


def store(rows):
    if not rows:
        print("No states returned this cycle.")
        return
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO raw.flight_states
           (icao24, callsign, origin_country, last_contact, longitude, latitude,
            baro_altitude, geo_altitude, on_ground, velocity, true_track,
            vertical_rate, squawk)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f"{datetime.now(timezone.utc).isoformat()} - stored {len(rows)} flight states")


if __name__ == "__main__":
    try:
        states = fetch_states()
        store([to_row(s) for s in states])
    except Exception as e:
        print(f"Ingestion error (will retry next cycle): {e}", file=sys.stderr)
        sys.exit(0)
