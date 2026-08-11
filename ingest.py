import os
import sys
import requests
import psycopg2
from datetime import datetime, timezone

OPENSKY_URL = "https://opensky-network.org/api/states/all"
# Bounding box: mainland India plus margins
BBOX = {"lamin": 6.0, "lomin": 68.0, "lamax": 37.5, "lomax": 97.5}

DB_PARAMS = {
    "dbname": os.environ.get("DBT_PG_DB", "flights"),
    "user": os.environ.get("DBT_PG_USER", "flights_user"),
    "password": os.environ.get("DBT_PG_PASSWORD"),
    "host": "localhost",
    "port": 5432,
}


def fetch_states():
    auth = None
    user = os.environ.get("OPENSKY_USER")
    pw = os.environ.get("OPENSKY_PASS")
    if user and pw:
        auth = (user, pw)
    resp = requests.get(OPENSKY_URL, params=BBOX, auth=auth, timeout=20)
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
