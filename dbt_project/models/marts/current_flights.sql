with ranked as (
    select
        *,
        row_number() over (partition by icao24 order by fetched_at desc) as rn
    from {{ ref('stg_flight_states') }}
    where fetched_at > now() - interval '10 minutes'
)
select
    icao24, callsign, origin_country, last_contact_at,
    longitude, latitude, baro_altitude, geo_altitude,
    on_ground, velocity, true_track, vertical_rate, squawk, fetched_at
from ranked
where rn = 1
