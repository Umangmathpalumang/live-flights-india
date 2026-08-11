with source as (
    select * from {{ source('raw', 'flight_states') }}
),
cleaned as (
    select
        icao24,
        nullif(trim(callsign), '') as callsign,
        origin_country,
        to_timestamp(last_contact) as last_contact_at,
        longitude,
        latitude,
        baro_altitude,
        geo_altitude,
        on_ground,
        velocity,
        true_track,
        vertical_rate,
        squawk,
        fetched_at
    from source
    where latitude is not null and longitude is not null
)
select * from cleaned
