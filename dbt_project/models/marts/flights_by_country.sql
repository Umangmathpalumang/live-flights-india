select
    origin_country,
    count(*) as active_flights,
    round(avg(velocity)::numeric, 1) as avg_velocity_ms,
    round(avg(geo_altitude)::numeric, 0) as avg_altitude_m
from {{ ref('current_flights') }}
group by origin_country
order by active_flights desc
